import json
import logging
import signal
import time
from pathlib import Path

from mexipes.pipeline.stages import (
    ADVANCE_PRIORITY_STATUSES,
    STATUS_ADVANCEMENT_RANK,
    TERMINAL_STATUSES,
    get_next_stage,
    run_registered_stage,
)
from mexipes.region import resolve_region
from mexipes.schemas import (
    ExtractedRecipe,
    ImageDescriptionsResult,
    LocalizedRecipe,
    RecipeStatus,
    RecipeTagSet,
    RewrittenRecipe,
    SubstitutionsResult,
    recipe_time,
)
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


def _batch_exceeded(processed: int, batch_size: int) -> bool:
    """Return True when the batch limit is reached. batch_size <= 0 means unlimited."""
    return batch_size > 0 and processed >= batch_size


def _pending_recipe_count(store: RecipeStore, publication_id: int) -> int:
    index = store.load_status_index(publication_id)
    pending = 0
    for status_str in index.values():
        try:
            if RecipeStatus(status_str) not in TERMINAL_STATUSES:
                pending += 1
        except ValueError:
            pending += 1
    return pending


def _pipeline_progress_snapshot(store: RecipeStore, publication_id: int) -> tuple[int, int]:
    """Return (advancement_score, pending_count) for --all-stages progress checks.

    ``pending_count`` only drops when recipes reach ready/failed. ``advancement_score``
    increases on every successful stage (e.g. extracted→rewritten), so the all-stages
    loop must treat either metric improving as forward progress.
    """
    index = store.load_status_index(publication_id)
    score = 0
    pending = 0
    for status_str in index.values():
        try:
            status = RecipeStatus(status_str)
        except ValueError:
            pending += 1
            continue
        score += STATUS_ADVANCEMENT_RANK.get(status, 0)
        if status not in TERMINAL_STATUSES:
            pending += 1
    return score, pending


def run_pipeline_until_ready(
    store: RecipeStore,
    publication_id: int,
    *,
    stage: str | None = None,
    batch_size: int = 10,
    sleep_seconds: float = 0.0,
) -> None:
    """Run pipeline batches for a publication until every recipe is ready or failed."""
    interrupted = False

    def _handle_sigint(_signum, _frame) -> None:
        nonlocal interrupted
        interrupted = True
        logger.info("SIGINT received — finishing current batch then stopping.")

    previous_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _handle_sigint)
    try:
        batch_num = 0
        while not interrupted:
            _score, pending = _pipeline_progress_snapshot(store, publication_id)
            if pending == 0:
                logger.info("Publication %s: all recipes reached a terminal status.", publication_id)
                break

            batch_num += 1
            logger.info(
                "Publication %s batch %d: %d recipe(s) still pending (batch limit: %s).",
                publication_id,
                batch_num,
                pending,
                "unlimited" if batch_size <= 0 else batch_size,
            )
            before_score, before_pending = _pipeline_progress_snapshot(store, publication_id)
            run_pipeline(
                store,
                publication_id=publication_id,
                stage=stage,
                batch_size=batch_size,
            )
            if interrupted:
                break

            after_score, after_pending = _pipeline_progress_snapshot(store, publication_id)
            if after_score <= before_score and after_pending >= before_pending:
                logger.warning(
                    "Publication %s: no progress in batch %d (%d still pending) — stopping.",
                    publication_id,
                    batch_num,
                    after_pending,
                )
                break

            if sleep_seconds > 0 and after_pending > 0:
                time.sleep(sleep_seconds)
    finally:
        signal.signal(signal.SIGINT, previous_handler)


def _registered_publication_ids(store: RecipeStore) -> list[int]:
    """Return sorted IDs of all registered publications (those with a source.pdf)."""
    publications_dir = store.data_dir / "publications"
    if not publications_dir.exists():
        return []
    ids = []
    for pub_path in sorted(publications_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
        if pub_path.is_dir() and pub_path.name.isdigit() and (pub_path / "source.pdf").exists():
            ids.append(int(pub_path.name))
    return ids


def run_full_pipeline(
    store: RecipeStore,
    *,
    staging_dir: Path | None = None,
    batch_size: int = 10,
    sleep_seconds: float = 0.0,
) -> list[int]:
    """Ingest staged PDFs, then drive every registered publication to a terminal status.

    This is the one-shot entry point behind ``mexipes all``: it ingests any PDFs in
    ``staging_dir`` (default ``data/staging``), extracts recipes for publications that
    have not been extracted yet, and loops batches per publication until every recipe
    is ready or failed. Returns the list of processed publication IDs.
    """
    staging = staging_dir if staging_dir is not None else store.data_dir / "staging"
    if staging.exists():
        pdf_files = [p for p in staging.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
        if pdf_files:
            logger.info("Ingesting %d PDF(s) from %s...", len(pdf_files), staging)
            from mexipes.stages.ingest import ingest_pdfs

            ingest_pdfs(store, staging)

    publication_ids = _registered_publication_ids(store)
    if not publication_ids:
        logger.warning("No registered publications found. Nothing to process.")
        return []

    logger.info("Processing %d publication(s) through all stages: %s", len(publication_ids), publication_ids)
    for pub_id in publication_ids:
        logger.info("=== Publication %s: running all stages until ready ===", pub_id)
        # Extract first if this publication has no recipes yet; run_pipeline_until_ready
        # keys off the status index, which is empty until extraction has run.
        if not any(r_pub == pub_id for r_pub, _ in store.find_all_recipes()):
            from mexipes.stages.extract import extract_publication_recipes

            try:
                extract_publication_recipes(store, pub_id)
            except Exception:
                logger.exception("Extraction failed for Publication %s (skipping).", pub_id)
                continue
        run_pipeline_until_ready(
            store,
            pub_id,
            batch_size=batch_size,
            sleep_seconds=sleep_seconds,
        )
    return publication_ids


def run_stage_for_recipe(store: RecipeStore, publication_id: int, recipe_id: int, stage_name: str) -> None:
    """Run a specific pipeline stage for a single recipe, updating its status."""
    logger.info(f"Executing stage '{stage_name}' for Publication {publication_id}, Recipe {recipe_id}...")
    try:
        if stage_name == "extract":
            # Extraction is usually publication-level, but can be invoked per-recipe (noop if raw exists)
            from mexipes.stages.extract import extract_publication_recipes

            extract_publication_recipes(store, publication_id)
        else:
            run_registered_stage(store, publication_id, recipe_id, stage_name)
    except Exception as e:
        logger.exception(f"Stage '{stage_name}' failed for Publication {publication_id}, Recipe {recipe_id}")
        store.set_status(publication_id, recipe_id, RecipeStatus.FAILED, error=str(e))
        raise


def run_pipeline(
    store: RecipeStore,
    publication_id: int | None = None,
    recipe_id: tuple[int, int] | None = None,
    stage: str | None = None,
    advance_all: bool = False,
    batch_size: int = 10,
    all_stages: bool = False,
    sleep_seconds: float = 0.0,
) -> None:
    """Orchestrates stage advancement based on CLI parameters."""
    if all_stages:
        if publication_id is None:
            raise ValueError("--all-stages requires --publication")
        run_pipeline_until_ready(
            store,
            publication_id,
            stage=stage,
            batch_size=batch_size,
            sleep_seconds=sleep_seconds,
        )
        return

    # Check for PDFs in data/staging and auto-ingest if found
    staging_dir = store.data_dir / "staging"
    if staging_dir.exists():
        pdf_files = [p for p in staging_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
        if pdf_files:
            logger.info(f"Auto-ingesting {len(pdf_files)} PDFs from {staging_dir}...")
            from mexipes.stages.ingest import ingest_pdfs

            try:
                ingest_pdfs(store, staging_dir)
            except Exception as e:
                logger.error(f"Auto-ingestion failed: {e}")

    # Scenario 1: Specific recipe
    if recipe_id:
        pub_id, r_id = recipe_id
        if stage:
            run_stage_for_recipe(store, pub_id, r_id, stage)
        else:
            # Advance recipe to the next stage based on its current status
            current_status = store.get_status(pub_id, r_id)
            next_stage = get_next_stage(current_status)
            if next_stage:
                run_stage_for_recipe(store, pub_id, r_id, next_stage)
            else:
                logger.info(f"Recipe {pub_id}:{r_id} is already in status '{current_status.value}' (cannot advance).")
        return

    # Scenario 2: Specific publication
    if publication_id:
        if stage == "extract":
            from mexipes.stages.extract import extract_publication_recipes

            extract_publication_recipes(store, publication_id)
            return

        # Find all recipes for this publication and run stage / advance them
        recipes = [r for r in store.find_all_recipes() if r[0] == publication_id]
        if not recipes and not stage:
            # If no recipes are extracted yet, run extraction first
            from mexipes.stages.extract import extract_publication_recipes

            recipes = extract_publication_recipes(store, publication_id)

        processed = 0
        if stage:
            for pub_id, r_id in recipes:
                if _batch_exceeded(processed, batch_size):
                    break
                try:
                    run_stage_for_recipe(store, pub_id, r_id, stage)
                    processed += 1
                except Exception:
                    logger.exception(
                        "Stage '%s' failed for Publication %s, Recipe %s (continuing batch)",
                        stage,
                        pub_id,
                        r_id,
                    )
            return

        status_by_recipe = {r_id: store.get_status(publication_id, r_id) for _, r_id in recipes}
        for status_to_advance in ADVANCE_PRIORITY_STATUSES:
            for pub_id, r_id in recipes:
                if _batch_exceeded(processed, batch_size):
                    return
                if status_by_recipe[r_id] != status_to_advance:
                    continue
                next_stage = get_next_stage(status_to_advance)
                if not next_stage:
                    continue
                try:
                    run_stage_for_recipe(store, pub_id, r_id, next_stage)
                    status_by_recipe[r_id] = store.get_status(pub_id, r_id)
                    processed += 1
                except Exception:
                    logger.exception(
                        "Stage '%s' failed for Publication %s, Recipe %s (continuing batch)",
                        next_stage,
                        pub_id,
                        r_id,
                    )
        return

    # Scenario 3: Advance all recipes in the workspace
    if advance_all or (publication_id is None and recipe_id is None):
        logger.info(f"Advancing all recipes in workspace (max batch size: {batch_size})...")

        # First: check if any publications are registered but not yet extracted
        publications_dir = store.data_dir / "publications"
        if publications_dir.exists():
            for pub_path in sorted(publications_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 9999):
                if pub_path.is_dir() and pub_path.name.isdigit():
                    pub_id = int(pub_path.name)
                    pub_info_path = pub_path / "publication_info.json"
                    if pub_info_path.exists():
                        try:
                            info = json.loads(pub_info_path.read_text(encoding="utf-8"))
                            if info.get("status") == "registered":
                                logger.info(
                                    f"Publication {pub_id} is registered but not extracted. Starting extraction."
                                )
                                from mexipes.stages.extract import extract_publication_recipes

                                extract_publication_recipes(store, pub_id)
                        except Exception:
                            pass

        # Second: gather all recipes and advance them sequentially
        all_recipes = store.find_all_recipes()
        processed = 0
        status_by_recipe = {key: store.get_status(*key) for key in all_recipes}

        # Run multiple passes through status priorities to process in pipeline order
        # i.e. advance the furthest-along recipes first (LOCALIZED -> substitute,
        # then TAGGED -> localize, then IMAGES_DESCRIBED -> tag, etc.).
        for status_to_advance in ADVANCE_PRIORITY_STATUSES:
            for pub_id, r_id in all_recipes:
                if _batch_exceeded(processed, batch_size):
                    break
                recipe_key = (pub_id, r_id)
                if status_by_recipe[recipe_key] == status_to_advance:
                    next_stage = get_next_stage(status_to_advance)
                    if next_stage:
                        try:
                            run_stage_for_recipe(store, pub_id, r_id, next_stage)
                            status_by_recipe[recipe_key] = store.get_status(pub_id, r_id)
                            processed += 1
                        except Exception:
                            pass

        logger.info(f"Pipeline batch run completed. Advanced {processed} recipes.")


def export_recipes(store: RecipeStore, status_filter: RecipeStatus, output_path: Path) -> None:
    """Consolidates recipes at a given status into a single structured JSON file.

    Also writes a sibling ``<name>_facets.json`` index (slug -> recipe keys) for
    fast browse/filter and tag-overlap similarity.
    """
    recipes_keys = store.find_recipes_at_status(status_filter)
    logger.info(f"Found {len(recipes_keys)} recipes with status '{status_filter.value}' for export.")

    exported_list = []
    # facets: field -> slug -> list of "pub:recipe" keys
    facets: dict[str, dict[str, list[str]]] = {}
    publications_index: dict[str, dict] = {}

    for publication_id, recipe_id in recipes_keys:
        if str(publication_id) not in publications_index:
            publications_index[str(publication_id)] = store.publication_export_info(publication_id)
        extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
        rewritten = store.load_stage_output(publication_id, recipe_id, "rewritten", RewrittenRecipe)
        images = store.load_stage_output(publication_id, recipe_id, "images_described", ImageDescriptionsResult)
        localized = store.load_stage_output(publication_id, recipe_id, "localized", LocalizedRecipe)
        tags = store.load_stage_output(publication_id, recipe_id, "tags", RecipeTagSet)
        localized_tags = store.load_stage_output(publication_id, recipe_id, "localized_tags", RecipeTagSet)
        substitutions = store.load_stage_output(publication_id, recipe_id, "substitutions", SubstitutionsResult)

        recipe_key = f"{publication_id}:{recipe_id}"

        # Merge region: tags, then extraction, then publication metadata.
        metadata = store.load_publication_metadata(publication_id)
        recipe_region = (tags.region if tags and tags.region else None) or (extracted.region if extracted else None)
        region_es = (
            resolve_region(
                recipe_region,
                page_start=extracted.page_start if extracted else None,
                metadata=metadata,
            )
            if metadata
            else recipe_region
        )

        tag_data = tags.model_dump() if tags else None
        if tag_data is not None and region_es:
            tag_data["region"] = region_es

        # Recipe-level total_time facets (no longer a tag field).
        if rewritten and rewritten.total_time:
            slug = recipe_time.slug_for(rewritten.total_time)
            if slug:
                facets.setdefault("total_time", {}).setdefault(slug, []).append(recipe_key)

        # Accumulate facet index from tag slugs.
        if tag_data is not None:
            for field, slugs in vocab.slug_map_for(tag_data).items():
                field_index = facets.setdefault(field, {})
                for slug in slugs:
                    field_index.setdefault(slug, []).append(recipe_key)

        # Build consolidated recipe dictionary
        recipe_data = {
            "publication_id": publication_id,
            "recipe_id": recipe_id,
            "publication": publications_index[str(publication_id)],
            "title": localized.title_en
            if localized
            else (rewritten.title if rewritten else (extracted.title if extracted else f"Recipe {recipe_id}")),
            "region": region_es,
            "total_time": rewritten.total_time if rewritten else (extracted.total_time if extracted else None),
            "total_time_en": localized.total_time_en if localized else None,
            "total_time_bilingual": recipe_time.bilingual_entry(
                rewritten.total_time if rewritten else extracted.total_time if extracted else None,
                localized.total_time_en if localized else None,
            ),
            "original": {
                "title": extracted.title if extracted else None,
                "yields": extracted.yields if extracted else None,
                "total_time": extracted.total_time if extracted else None,
                "ingredients": extracted.ingredients if extracted else None,
                "instructions": extracted.instructions if extracted else None,
            }
            if extracted
            else None,
            "rewritten": rewritten.model_dump() if rewritten else None,
            "images": [img.model_dump() for img in images.descriptions] if images else [],
            "localized": localized.model_dump() if localized else None,
            "tags": tag_data,
            "tags_en": localized_tags.model_dump() if localized_tags else None,
            "tags_bilingual": vocab.to_bilingual(tag_data, localized_tags.model_dump() if localized_tags else None)
            if tag_data is not None
            else None,
            "substitutions": [sub.model_dump() for sub in substitutions.substitutions] if substitutions else [],
        }
        exported_list.append(recipe_data)

    output_path.write_text(json.dumps(exported_list, indent=4, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Consolidated export written to {output_path}")

    facets_path = output_path.with_name(f"{output_path.stem}_facets.json")
    facets_payload = {
        "publications": publications_index,
        "facets": facets,
    }
    facets_path.write_text(json.dumps(facets_payload, indent=4, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Facet index written to {facets_path}")
