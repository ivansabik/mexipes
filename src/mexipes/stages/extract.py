import hashlib
import json
import logging
import shutil
from pathlib import Path

import fitz
from pydantic import BaseModel, Field

from mexipes.config import settings
from mexipes.image_quality import assess_image_quality, is_low_quality
from mexipes.inherited_tags import region_claim_supported, sanitize_inherited_tags
from mexipes.llm import call_llm, load_prompt
from mexipes.pipeline import pdf_processor
from mexipes.recipe_validation import (
    crop_bounds_text,
    filter_index_entries_for_chunk,
    format_index_context,
    is_editorial_extraction,
    is_empty_recipe_extraction,
    is_non_recipe_extraction,
    is_valid_box_2d,
    matches_recipe_index,
    normalize_extracted_recipe_fields,
    resolve_index_title,
)
from mexipes.region import resolve_region
from mexipes.schemas import (
    ExtractedRecipe,
    ImageCrop,
    ImageDescriptionsResult,
    InheritedTags,
    PublicationMetadata,
    RecipeIndexEntry,
    RecipeStatus,
    recipe_time,
)
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.health_nutrition_tags import format_health_nutrition_prompt_section
from mexipes.storage import RecipeStore
from mexipes.text_utils import fold_text

logger = logging.getLogger(__name__)

MAX_CHUNK_BYTES = 15 * 1024 * 1024
INDEX_SCAN_MAX_PAGE = 40
INDEX_DISCOVERY_CHUNK = 10


class ExtractionResult(BaseModel):
    recipes: list[ExtractedRecipe]


class IndexPageDiscovery(BaseModel):
    has_index: bool = False
    page_start: int | None = None
    page_end: int | None = None


class RecipeIndexResult(BaseModel):
    recipe_index: list[RecipeIndexEntry] = Field(default_factory=list)


class CompanionPhotoResult(BaseModel):
    is_companion_photo: bool = False
    box_2d: list[int] | None = None


def normalize_inherited_tags(inherited: InheritedTags) -> InheritedTags:
    """Coerce LLM output to Spanish canonical labels (safety net after extraction)."""
    normalized = vocab.normalize_inherited_tags_data(inherited.model_dump())
    return InheritedTags(**normalized)


def dedupe_recipe_index(entries: list[RecipeIndexEntry]) -> list[RecipeIndexEntry]:
    """Merge duplicate index entries by (page, normalized title)."""
    seen: set[tuple[int | None, str]] = set()
    deduped: list[RecipeIndexEntry] = []
    for entry in entries:
        key = (entry.page, fold_text(entry.title))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _shrink_chunk_end(pdf_path: Path, start_idx: int, end_idx: int) -> int:
    """Return end_idx (exclusive, 0-based page after last included) that fits MAX_CHUNK_BYTES."""
    while end_idx > start_idx + 1:
        chunk_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, start_idx, end_idx - 1)
        if len(chunk_bytes) <= MAX_CHUNK_BYTES:
            return end_idx
        logger.info(
            f"Chunk pages {start_idx + 1} to {end_idx} is too large "
            f"({len(chunk_bytes) / (1024 * 1024):.1f} MB). Shrinking..."
        )
        end_idx -= 1
    return end_idx


def _extract_chunk_bytes(pdf_path: Path, start_idx: int, end_idx_exclusive: int) -> bytes:
    end_idx = _shrink_chunk_end(pdf_path, start_idx, end_idx_exclusive)
    return pdf_processor.extract_chunk_pdf_bytes(pdf_path, start_idx, end_idx - 1)


def discover_index_page_range(pdf_path: Path, total_pages: int) -> IndexPageDiscovery | None:
    """Scan early PDF pages to locate table-of-contents / recipe index range."""
    prompt = load_prompt("discover_index_pages.md")
    scan_end = min(INDEX_SCAN_MAX_PAGE, total_pages)
    chunk_start = 0

    while chunk_start < scan_end:
        chunk_end = min(scan_end, chunk_start + INDEX_DISCOVERY_CHUNK)
        chunk_bytes = _extract_chunk_bytes(pdf_path, chunk_start, chunk_end)
        try:
            result = call_llm(
                model=settings.metadata.model,
                response_model=IndexPageDiscovery,
                prompt=(
                    f"{prompt}\n\nThese are PDF pages {chunk_start + 1} to {chunk_end} of {total_pages} total pages."
                ),
                pdf_bytes=chunk_bytes,
                temperature=settings.metadata.temperature,
                max_retries=settings.metadata.max_retries,
            )
        except Exception as e:
            logger.warning(f"Index discovery failed for pages {chunk_start + 1}-{chunk_end}: {e}")
            chunk_start = chunk_end
            continue

        if result.has_index and result.page_start and result.page_end:
            logger.info(f"Discovered recipe index on pages {result.page_start}-{result.page_end}")
            return result
        chunk_start = chunk_end

    return None


def extract_recipe_index_from_pages(
    pdf_path: Path,
    page_start: int,
    page_end: int,
    total_pages: int,
) -> list[RecipeIndexEntry]:
    """Extract recipe index entries from a page range (1-based, inclusive)."""
    prompt = load_prompt("extract_recipe_index.md")
    start_idx = max(0, page_start - 1)
    end_idx = min(total_pages, page_end)
    chunk_bytes = _extract_chunk_bytes(pdf_path, start_idx, end_idx)
    try:
        result = call_llm(
            model=settings.metadata.model,
            response_model=RecipeIndexResult,
            prompt=(
                f"{prompt}\n\nExtract the recipe index from PDF pages "
                f"{page_start} to {page_end} (of {total_pages} total pages)."
            ),
            pdf_bytes=chunk_bytes,
            temperature=settings.metadata.temperature,
            max_retries=settings.metadata.max_retries,
        )
        return result.recipe_index
    except Exception as e:
        logger.warning(f"Recipe index extraction failed for pages {page_start}-{page_end}: {e}")
        return []


def enrich_metadata_with_recipe_index(
    metadata: PublicationMetadata,
    pdf_path: Path,
    total_pages: int,
) -> PublicationMetadata:
    """Discover and extract recipe index when not already populated from cover pages."""
    entries = list(metadata.recipe_index)

    if len(entries) < 5:
        discovery = discover_index_page_range(pdf_path, total_pages)
        if discovery and discovery.page_start and discovery.page_end:
            scanned = extract_recipe_index_from_pages(
                pdf_path,
                discovery.page_start,
                discovery.page_end,
                total_pages,
            )
            entries.extend(scanned)

    metadata.recipe_index = dedupe_recipe_index(entries)
    if metadata.recipe_index:
        logger.info(f"Recipe index contains {len(metadata.recipe_index)} entries")
    return metadata


def build_chunk_context(
    metadata: PublicationMetadata,
    start_idx: int,
    end_idx: int,
    overlap: int,
) -> str:
    """Build regional + recipe-index context for a recipe extraction chunk."""
    chunk_regions_text = []
    for sec in metadata.regional_sections:
        s_start = sec.page_start - 1
        s_end = sec.page_end if sec.page_end is not None else 999999
        s_end -= 1

        if s_start <= (end_idx - 1) and s_end >= start_idx:
            local_start = max(1, s_start - start_idx + 1)
            local_end = min(end_idx - start_idx, s_end - start_idx + 1)
            chunk_regions_text.append(f"Pages {local_start} to {local_end}: {sec.region_name}")

    parts = [f"**CONTEXT**:\n- Publication Title: '{metadata.document_title or ''}'"]

    if chunk_regions_text:
        region_str = ", ".join(chunk_regions_text)
        parts.append(f"- Regional Mappings for THIS chunk: {region_str}")
        parts.append(
            "If a recipe falls into these local page numbers, ALWAYS use that region unless its header overrides it."
        )
    elif region_claim_supported(metadata):
        inherited_region = metadata.inherited_tags.region or ""
        parts.extend(
            [
                "- This publication is explicitly regional.",
                f"If a recipe lacks an explicit region in its header, you may use '{inherited_region}' "
                "only when the title clearly names that region as the cuisine subject.",
                "- Do NOT infer region from author or publisher names.",
            ]
        )
    else:
        parts.extend(
            [
                "- Do NOT infer region from the publication title unless it explicitly "
                "names a Mexican region as the cuisine subject.",
                "- Do NOT infer region from author or publisher names.",
            ]
        )

    index_entries = filter_index_entries_for_chunk(
        metadata.recipe_index,
        start_idx,
        end_idx,
        overlap=overlap,
    )
    index_context = format_index_context(index_entries)
    if index_context:
        parts.append("")
        parts.append(index_context)

    return "\n".join(parts)


def _render_and_save_crop(
    *,
    pdf_path: Path,
    page_index: int,
    box_2d: list[int],
    images_dir: Path,
    crop_index: int,
    recipe_title: str,
    recipe_id: int,
) -> bool:
    """Render a crop to PNG; return True if saved."""
    try:
        png_bytes = pdf_processor.render_image_crop_bytes(
            pdf_path=pdf_path,
            page_index=page_index,
            box_2d=box_2d,
            dpi=300,
        )
    except Exception as img_err:
        logger.error(f"Failed to render image crop for Recipe {recipe_id} ('{recipe_title}'): {img_err}")
        return False

    if settings.image_quality.enabled:
        metrics = assess_image_quality(png_bytes)
        low_quality, reason = is_low_quality(metrics, settings.image_quality)
        if low_quality:
            logger.info(f"Discarded low-quality image crop ({reason}) for recipe '{recipe_title}' (Recipe {recipe_id})")
            return False

    dest_image_path = images_dir / f"{crop_index}.png"
    dest_image_path.parent.mkdir(parents=True, exist_ok=True)
    dest_image_path.write_bytes(png_bytes)
    logger.info(f"Extracted image crop {dest_image_path.name} for Recipe {recipe_id}")
    return True


def backfill_companion_photo(
    *,
    pdf_path: Path,
    recipe: ExtractedRecipe,
    recipe_id: int,
    publication_id: int,
    store: RecipeStore,
    assigned_photo_pages: set[int],
) -> None:
    """Attempt to attach a companion photo from page_end+1 when extraction missed it."""
    if recipe.images_count > 0 or recipe.page_end is None:
        return

    photo_page = recipe.page_end + 1  # 1-based
    photo_page_index = photo_page - 1
    if photo_page_index in assigned_photo_pages:
        return

    with fitz.open(pdf_path) as doc:
        if photo_page_index < 0 or photo_page_index >= len(doc):
            return

    page_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, photo_page_index, photo_page_index)
    prompt = load_prompt("extract_companion_photo.md")
    try:
        result = call_llm(
            model=settings.extraction.model,
            response_model=CompanionPhotoResult,
            prompt=f"{prompt}\n\nRecipe title: '{recipe.title}'",
            pdf_bytes=page_bytes,
            temperature=settings.extraction.temperature,
            max_retries=settings.extraction.max_retries,
        )
    except Exception as e:
        logger.warning(f"Companion photo backfill failed for '{recipe.title}' page {photo_page}: {e}")
        return

    if not result.is_companion_photo or not result.box_2d or not is_valid_box_2d(result.box_2d):
        return

    text_rects = pdf_processor.get_page_text_rects(pdf_path, photo_page_index)
    if crop_bounds_text(result.box_2d, text_rects):
        logger.info(f"Skipped companion photo backfill (bounds text) for '{recipe.title}'")
        return

    images_dir = store.get_images_dir(publication_id, recipe_id)
    if not _render_and_save_crop(
        pdf_path=pdf_path,
        page_index=photo_page_index,
        box_2d=result.box_2d,
        images_dir=images_dir,
        crop_index=1,
        recipe_title=recipe.title,
        recipe_id=recipe_id,
    ):
        return

    crop = ImageCrop(chunk_page_index=1, box_2d=result.box_2d)
    recipe.image_crops = [crop]
    recipe.images_count = 1
    recipe.page_end = photo_page
    assigned_photo_pages.add(photo_page_index)
    store.save_stage_output(publication_id, recipe_id, "extracted", recipe)
    logger.info(f"Backfilled companion photo from page {photo_page} for '{recipe.title}'")


def extract_publication_metadata(store: RecipeStore, publication_id: int) -> PublicationMetadata:
    """Stage 2 metadata: Extracts publication-level metadata from cover pages and TOC."""
    publication_dir = store.get_publication_dir(publication_id)
    pdf_path = publication_dir / "source.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"source.pdf not found in {publication_dir}")

    logger.info(f"Extracting metadata for Publication {publication_id}...")

    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)

        metadata_end = min(9, total_pages - 1)
        while metadata_end > 0:
            metadata_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, 0, metadata_end)
            if len(metadata_bytes) <= MAX_CHUNK_BYTES:
                break
            logger.info(
                f"Metadata chunk pages 1 to {metadata_end + 1} too large "
                f"({len(metadata_bytes) / (1024 * 1024):.1f} MB). Shrinking..."
            )
            metadata_end -= 1

        metadata_bytes = pdf_processor.extract_chunk_pdf_bytes(pdf_path, 0, metadata_end)

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

    metadata.pdf_pages = str(total_pages)
    metadata.inherited_tags = sanitize_inherited_tags(metadata)
    metadata.inherited_tags = normalize_inherited_tags(metadata.inherited_tags)
    metadata = enrich_metadata_with_recipe_index(metadata, pdf_path, total_pages)

    store.save_publication_metadata(publication_id, metadata)
    logger.info(f"Saved metadata.json for Publication {publication_id} (Total pages: {total_pages})")

    pub_info_path = publication_dir / "publication_info.json"
    if pub_info_path.exists():
        try:
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

    metadata = store.load_publication_metadata(publication_id)
    if not metadata:
        metadata = extract_publication_metadata(store, publication_id)

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
    assigned_photo_pages: set[int] = set()

    while chunk_idx < total_pages:
        start_idx = chunk_idx
        end_idx = min(total_pages, chunk_idx + chunk_size)
        end_idx = _shrink_chunk_end(pdf_path, start_idx, end_idx)

        actual_processed = end_idx - start_idx
        step = max(1, actual_processed - overlap)

        chunk_context = build_chunk_context(metadata, start_idx, end_idx, overlap)
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

            if is_editorial_extraction(recipe.ingredients, recipe.instructions, recipe.yields):
                logger.info(f"Skipping editorial/narrative extraction: '{recipe.title}'")
                continue

            # Convert page indices relative to chunk back to absolute PDF page indices
            if recipe.page_start is not None:
                recipe.page_start = start_idx + recipe.page_start
            if recipe.page_end is not None:
                recipe.page_end = start_idx + recipe.page_end

            if metadata.recipe_index and not matches_recipe_index(
                recipe.title, recipe.page_start, metadata.recipe_index
            ):
                logger.info(f"Skipping extraction not in recipe index: '{recipe.title}' (page {recipe.page_start})")
                continue

            recipe.title = resolve_index_title(recipe.title, recipe.page_start, metadata.recipe_index)

            title_lower = recipe.title.strip().lower()
            if title_lower in existing_titles:
                logger.info(f"Skipping duplicate recipe: '{recipe.title}'")
                continue
            existing_titles.add(title_lower)

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

            recipe_id = store.get_next_recipe_id(publication_id)

            recipe.region = resolve_region(recipe.region, page_start=recipe.page_start, metadata=metadata)
            recipe.total_time = recipe_time.normalize_total_time(recipe.total_time)

            kept_crops = []
            if valid_crops:
                images_dir = store.get_images_dir(publication_id, recipe_id)
                for crop in valid_crops:
                    fitz_page_num = start_idx + (crop.chunk_page_index - 1)
                    if _render_and_save_crop(
                        pdf_path=pdf_path,
                        page_index=fitz_page_num,
                        box_2d=crop.box_2d,
                        images_dir=images_dir,
                        crop_index=len(kept_crops) + 1,
                        recipe_title=recipe.title,
                        recipe_id=recipe_id,
                    ):
                        kept_crops.append(crop)
                        assigned_photo_pages.add(fitz_page_num)

            recipe.image_crops = kept_crops
            recipe.images_count = len(kept_crops)

            store.save_stage_output(publication_id, recipe_id, "extracted", recipe)
            store.set_status(publication_id, recipe_id, RecipeStatus.EXTRACTED)
            extracted_recipe_keys.append((publication_id, recipe_id))
            logger.info(f"Extracted recipe '{recipe.title}' as ID {recipe_id}")

            backfill_companion_photo(
                pdf_path=pdf_path,
                recipe=recipe,
                recipe_id=recipe_id,
                publication_id=publication_id,
                store=store,
                assigned_photo_pages=assigned_photo_pages,
            )

    stripped = strip_generic_recipe_images(store, publication_id)
    if stripped:
        logger.info(f"Removed generic template images from {stripped} recipe(s) in Publication {publication_id}")

    # When the LLM cannot read a TOC count, backfill from the actual extraction result.
    metadata = store.load_publication_metadata(publication_id)
    if metadata:
        count_str = (metadata.recipes_count or "").strip().lower()
        if not count_str or count_str in ("null", "none", "n/a"):
            actual = len(extracted_recipe_keys)
            metadata.recipes_count = str(actual)
            store.save_publication_metadata(publication_id, metadata)
            logger.info(f"Backfilled recipes_count={actual} for Publication {publication_id}")

    if not has_errors:
        pub_info_path = publication_dir / "publication_info.json"
        if pub_info_path.exists():
            try:
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
