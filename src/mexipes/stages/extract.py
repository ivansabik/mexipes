import hashlib
import logging
import shutil

import fitz
from pydantic import BaseModel

from mexipes.config import settings
from mexipes.image_quality import assess_image_quality, is_low_quality
from mexipes.inherited_tags import region_claim_supported, sanitize_inherited_tags
from mexipes.llm import call_llm, load_prompt
from mexipes.pipeline import pdf_processor
from mexipes.recipe_validation import (
    crop_bounds_text,
    is_empty_recipe_extraction,
    is_non_recipe_extraction,
    is_valid_box_2d,
    normalize_extracted_recipe_fields,
)
from mexipes.region import resolve_region
from mexipes.schemas import (
    ExtractedRecipe,
    ImageDescriptionsResult,
    InheritedTags,
    PublicationMetadata,
    RecipeStatus,
)
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas import recipe_time
from mexipes.schemas.health_nutrition_tags import format_health_nutrition_prompt_section
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    recipes: list[ExtractedRecipe]


def normalize_inherited_tags(inherited: InheritedTags) -> InheritedTags:
    """Coerce LLM output to Spanish canonical labels (safety net after extraction)."""
    normalized = vocab.normalize_inherited_tags_data(inherited.model_dump())
    return InheritedTags(**normalized)


def extract_publication_metadata(store: RecipeStore, publication_id: int) -> PublicationMetadata:
    """Stage 2 metadata: Extracts publication-level metadata from cover pages and TOC."""
    publication_dir = store.get_publication_dir(publication_id)
    pdf_path = publication_dir / "source.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"source.pdf not found in {publication_dir}")

    logger.info(f"Extracting metadata for Publication {publication_id}...")

    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)

        # Use first 10 pages for metadata (usually covers cover and table of contents)
        # Shrink if too large (over 15MB) to prevent API payload errors
        metadata_end = min(9, total_pages - 1)
        while metadata_end > 0:
            metadata_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, 0, metadata_end)
            if len(metadata_bytes) <= 15 * 1024 * 1024:
                break
            logger.info(
                f"Metadata chunk pages 1 to {metadata_end + 1} too large ({len(metadata_bytes) / (1024 * 1024):.1f} MB). Shrinking..."
            )
            metadata_end -= 1

        metadata_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, 0, metadata_end)

        # Extract full text to find section headers deep in the publication
        full_text = ""
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                full_text += f"\n--- PAGE {i + 1} ---\n{text}\n"

    prompt_template = load_prompt("extract_publication_metadata.md")
    prompt_template = prompt_template.replace(
        "<!-- INHERITED_TAGS_TAXONOMY -->",
        vocab.format_inherited_tags_prompt_section(),
    )
    prompt_template = prompt_template.replace(
        "<!-- HEALTH_NUTRITION_TAXONOMY -->",
        format_health_nutrition_prompt_section(),
    )
    prompt = f"{prompt_template}\n\nFULL TEXT FOR REGIONAL SECTIONS EXTRACTION:\n{full_text}"

    metadata = call_llm(
        model=settings.metadata.model,
        response_model=PublicationMetadata,
        prompt=prompt,
        pdf_bytes=metadata_bytes,
        temperature=settings.metadata.temperature,
        max_retries=settings.metadata.max_retries,
    )

    # Force absolute page count ground truth
    metadata.pdf_pages = str(total_pages)
    metadata.inherited_tags = sanitize_inherited_tags(metadata)
    metadata.inherited_tags = normalize_inherited_tags(metadata.inherited_tags)

    store.save_publication_metadata(publication_id, metadata)
    logger.info(f"Saved metadata.json for Publication {publication_id} (Total pages: {total_pages})")

    # Update publication status to parsed
    pub_info_path = publication_dir / "publication_info.json"
    if pub_info_path.exists():
        try:
            import json

            info = json.loads(pub_info_path.read_text(encoding="utf-8"))
            info["status"] = "metadata_extracted"
            pub_info_path.write_text(json.dumps(info, indent=4), encoding="utf-8")
        except Exception:
            pass

    return metadata


def strip_generic_recipe_images(store: RecipeStore, publication_id: int) -> int:
    """Remove image crops that are generic publication templates.

    Identical image content appearing on multiple recipes in the same
    publication indicates a repeating decorative sidebar, not a recipe photo.
    """
    hash_to_locations: dict[str, list[tuple[int, str]]] = {}

    for pub_id, recipe_id in store.find_all_recipes():
        if pub_id != publication_id:
            continue
        images_dir = store.get_images_dir(publication_id, recipe_id)
        for img_path in sorted(images_dir.glob("*.png")):
            digest = hashlib.md5(img_path.read_bytes()).hexdigest()
            hash_to_locations.setdefault(digest, []).append((recipe_id, img_path.name))

    generic_hashes = {
        digest for digest, locations in hash_to_locations.items() if len({recipe_id for recipe_id, _ in locations}) >= 2
    }
    if not generic_hashes:
        return 0

    generic_recipe_ids = {recipe_id for digest in generic_hashes for recipe_id, _ in hash_to_locations[digest]}

    cleaned = 0
    for recipe_id in sorted(generic_recipe_ids):
        extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
        if not extracted or extracted.images_count == 0:
            continue

        extracted.images_count = 0
        extracted.image_crops = []
        store.save_stage_output(publication_id, recipe_id, "extracted", extracted)

        images_dir = store.get_images_dir(publication_id, recipe_id)
        shutil.rmtree(images_dir, ignore_errors=True)

        images_described_path = store.get_recipe_dir(publication_id, recipe_id) / "images_described.json"
        if images_described_path.exists():
            store.save_stage_output(
                publication_id,
                recipe_id,
                "images_described",
                ImageDescriptionsResult(descriptions=[]),
            )

        cleaned += 1
        logger.info(f"Stripped generic template image from Recipe {recipe_id} in Publication {publication_id}")

    return cleaned


def extract_publication_recipes(store: RecipeStore, publication_id: int) -> list[tuple[int, int]]:
    """Stage 2 recipes: Processes a publication in overlapping chunks to extract all recipes and image crops."""
    publication_dir = store.get_publication_dir(publication_id)
    pdf_path = publication_dir / "source.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"source.pdf not found in {publication_dir}")

    # Ensure publication metadata exists
    metadata = store.load_publication_metadata(publication_id)
    if not metadata:
        metadata = extract_publication_metadata(store, publication_id)

    # Gather existing titles in this publication to prevent duplicates
    existing_titles = set()
    for pub_id, r_id in store.find_all_recipes():
        if pub_id == publication_id:
            recipe_extracted = store.load_stage_output(publication_id, r_id, "extracted", ExtractedRecipe)
            if recipe_extracted:
                existing_titles.add(recipe_extracted.title.strip().lower())

    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)

    chunk_idx = 0
    chunk_size = 8
    overlap = 1
    recipe_prompt = load_prompt("extract_recipes.md")
    extracted_recipe_keys = []
    has_errors = False

    while chunk_idx < total_pages:
        start_idx = chunk_idx
        end_idx = min(total_pages, chunk_idx + chunk_size)

        # Shrink chunk dynamically if it's too large (over 15MB)
        while end_idx > start_idx + 1:
            chunk_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, start_idx, end_idx - 1)
            if len(chunk_bytes) <= 15 * 1024 * 1024:
                break
            logger.info(
                f"Chunk pages {start_idx + 1} to {end_idx} is too large ({len(chunk_bytes) / (1024 * 1024):.1f} MB). Shrinking..."
            )
            end_idx -= 1

        # Compute step for advancement
        actual_processed = end_idx - start_idx
        step = max(1, actual_processed - overlap)

        # Translate absolute regional sections to local page numbers relative to this chunk
        chunk_regions_text = []
        for sec in metadata.regional_sections:
            s_start = sec.page_start - 1  # 0-based
            s_end = sec.page_end
            if s_end is None:
                s_end = 999999
            else:
                s_end -= 1  # 0-based

            # Check if section overlaps with current chunk
            if s_start <= (end_idx - 1) and s_end >= start_idx:
                local_start = max(1, s_start - start_idx + 1)
                local_end = min(end_idx - start_idx, s_end - start_idx + 1)
                chunk_regions_text.append(f"Pages {local_start} to {local_end}: {sec.region_name}")

        if chunk_regions_text:
            region_str = ", ".join(chunk_regions_text)
            chunk_context = (
                f"**CONTEXT**:\n"
                f"- Publication Title: '{metadata.document_title or ''}'\n"
                f"- Regional Mappings for THIS chunk: {region_str}\n"
                f"If a recipe falls into these local page numbers, ALWAYS use that region unless its header overrides it."
            )
        elif region_claim_supported(metadata):
            inherited_region = metadata.inherited_tags.region or ""
            chunk_context = (
                f"**CONTEXT**:\n"
                f"- Publication Title: '{metadata.document_title or ''}'\n"
                f"- This publication is explicitly regional. "
                f"If a recipe lacks an explicit region in its header, you may use '{inherited_region}' "
                f"only when the title clearly names that region as the cuisine subject.\n"
                f"- Do NOT infer region from author or publisher names."
            )
        else:
            chunk_context = (
                f"**CONTEXT**:\n"
                f"- Publication Title: '{metadata.document_title or ''}'\n"
                f"- Do NOT infer region from the publication title unless it explicitly "
                f"names a Mexican region as the cuisine subject. "
                f"Do NOT infer region from author or publisher names."
            )

        dynamic_prompt = f"{recipe_prompt}\n\n{chunk_context}"

        logger.info(f"Processing chunk: pages {start_idx + 1} to {end_idx}...")
        chunk_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, start_idx, end_idx - 1)

        try:
            result = call_llm(
                model=settings.extraction.model,
                response_model=ExtractionResult,
                prompt=dynamic_prompt,
                pdf_bytes=chunk_bytes,
                temperature=settings.extraction.temperature,
                max_retries=settings.extraction.max_retries,
            )
        except Exception as e:
            logger.error(f"Error calling LLM for chunk {start_idx + 1}-{end_idx}: {e}")
            has_errors = True
            chunk_idx += step
            continue

        chunk_idx += step

        for recipe in result.recipes:
            title_lower = recipe.title.strip().lower()
            if title_lower in existing_titles:
                logger.info(f"Skipping duplicate recipe: '{recipe.title}'")
                continue
            existing_titles.add(title_lower)

            title, ingredients, instructions = normalize_extracted_recipe_fields(
                title=recipe.title,
                ingredients=recipe.ingredients,
                instructions=recipe.instructions,
            )
            recipe.title = title
            recipe.ingredients = ingredients
            recipe.instructions = instructions

            if is_non_recipe_extraction(recipe.ingredients, recipe.instructions):
                logger.info(f"Skipping non-recipe extraction (section header or modality label): '{recipe.title}'")
                continue

            if is_empty_recipe_extraction(recipe.ingredients, recipe.instructions):
                logger.info(f"Skipping incomplete recipe (empty ingredients or instructions): '{recipe.title}'")
                continue

            # Filter image crops: drop malformed boxes, and drop boxes that bound the
            # recipe text (full-bleed background photos with the title/ingredients/
            # instructions printed on top — any such crop would capture that text).
            valid_crops = []
            for crop in recipe.image_crops:
                if not is_valid_box_2d(crop.box_2d):
                    logger.warning(f"Dropped malformed image crop for recipe '{recipe.title}'")
                    continue
                crop_page_index = start_idx + (crop.chunk_page_index - 1)
                text_rects = pdf_processor.get_page_text_rects(pdf_path, crop_page_index)
                if crop_bounds_text(crop.box_2d, text_rects):
                    logger.info(
                        f"Dropped image crop bounding recipe text "
                        f"(full-bleed background with overlaid text) for recipe '{recipe.title}'"
                    )
                    continue
                valid_crops.append(crop)
            recipe.image_crops = valid_crops

            # Always allocate a sequential storage ID. recipe_number is source metadata
            # (often section-local, e.g. 1–20 per chapter) and must not be used as the
            # on-disk recipe folder ID or later extractions overwrite earlier recipes.
            recipe_id = store.get_next_recipe_id(publication_id)

            # Convert page indices relative to chunk back to absolute PDF page indices
            if recipe.page_start is not None:
                recipe.page_start = start_idx + recipe.page_start
            if recipe.page_end is not None:
                recipe.page_end = start_idx + recipe.page_end

            recipe.region = resolve_region(recipe.region, page_start=recipe.page_start, metadata=metadata)
            recipe.total_time = recipe_time.normalize_total_time(recipe.total_time)

            # Render crops, discard low-quality images, and save survivors
            kept_crops = []
            if valid_crops:
                images_dir = store.get_images_dir(publication_id, recipe_id)
                for crop in valid_crops:
                    fitz_page_num = start_idx + (crop.chunk_page_index - 1)
                    try:
                        png_bytes = pdf_processor.render_image_crop_bytes(
                            pdf_path=pdf_path,
                            page_index=fitz_page_num,
                            box_2d=crop.box_2d,
                            dpi=300,
                        )
                    except Exception as img_err:
                        logger.error(
                            f"Failed to render image crop for Recipe {recipe_id} ('{recipe.title}'): {img_err}"
                        )
                        continue

                    if settings.image_quality.enabled:
                        metrics = assess_image_quality(png_bytes)
                        low_quality, reason = is_low_quality(metrics, settings.image_quality)
                        if low_quality:
                            logger.info(
                                f"Discarded low-quality image crop ({reason}) "
                                f"for recipe '{recipe.title}' (Recipe {recipe_id})"
                            )
                            continue

                    dest_image_path = images_dir / f"{len(kept_crops) + 1}.png"
                    dest_image_path.parent.mkdir(parents=True, exist_ok=True)
                    dest_image_path.write_bytes(png_bytes)
                    kept_crops.append(crop)
                    logger.info(f"Extracted image crop {dest_image_path.name} for Recipe {recipe_id}")

            recipe.image_crops = kept_crops
            recipe.images_count = len(kept_crops)

            # Save extracted recipe data
            store.save_stage_output(publication_id, recipe_id, "extracted", recipe)
            store.set_status(publication_id, recipe_id, RecipeStatus.EXTRACTED)
            extracted_recipe_keys.append((publication_id, recipe_id))
            logger.info(f"Extracted recipe '{recipe.title}' as ID {recipe_id}")

    stripped = strip_generic_recipe_images(store, publication_id)
    if stripped:
        logger.info(f"Removed generic template images from {stripped} recipe(s) in Publication {publication_id}")

    # Update publication status to recipes extracted only if no errors occurred
    if not has_errors:
        pub_info_path = publication_dir / "publication_info.json"
        if pub_info_path.exists():
            try:
                import json

                info = json.loads(pub_info_path.read_text(encoding="utf-8"))
                info["status"] = "recipes_extracted"
                pub_info_path.write_text(json.dumps(info, indent=4), encoding="utf-8")
            except Exception:
                pass
    else:
        logger.error(
            f"Extraction completed with errors for Publication {publication_id}. "
            "Status remains registered for retrying."
        )

    return extracted_recipe_keys
