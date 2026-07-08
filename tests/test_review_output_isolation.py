from pathlib import Path

import pytest

from mexipes.review.runner import (
    create_workspace_store,
    ensure_output_outside_publications,
    resolve_output_paths,
)
from mexipes.schemas import ExtractedRecipe, RecipeStatus
from mexipes.storage import ReadOnlyRecipeStore, RecipeStore


def test_output_guard_rejects_publications_tree(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path / "data")
    bad_path = store.data_dir / "publications" / "1" / "review.json"

    with pytest.raises(ValueError, match="must not be inside"):
        ensure_output_outside_publications(bad_path, store)


def test_output_guard_allows_reviews_tree(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path / "data")

    ensure_output_outside_publications(store.data_dir / "reviews" / "review_1" / "consolidated.json", store)


def test_resolve_output_paths_uses_run_stamped_folder(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path / "data")

    paths = resolve_output_paths(store, output_dir=store.data_dir / "reviews", seed=42)

    assert paths.run_dir.parent == store.data_dir / "reviews"
    assert paths.run_dir.name.startswith("review_")
    assert paths.run_dir.name.endswith("_42")
    assert paths.consolidated_json == paths.run_dir / "consolidated.json"


def test_read_only_store_rejects_all_writes(tmp_path: Path) -> None:
    RecipeStore(tmp_path / "data")  # create the prod layout first
    store = ReadOnlyRecipeStore(tmp_path / "data")

    with pytest.raises(PermissionError):
        store.save_stage_output(1, 1, "extracted", ExtractedRecipe(title="t", ingredients="i", instructions="s"))
    with pytest.raises(PermissionError):
        store.set_status(1, 1, RecipeStatus.EXTRACTED)
    with pytest.raises(PermissionError):
        store.get_next_recipe_id(1)


def test_read_only_store_reads_do_not_touch_publications(tmp_path: Path) -> None:
    prod = RecipeStore(tmp_path / "data")
    prod.save_stage_output(1, 1, "extracted", ExtractedRecipe(title="Recipe", ingredients="beans", instructions="cook"))
    prod.set_status(1, 1, RecipeStatus.EXTRACTED)
    index_path = prod.data_dir / "publications" / "1" / "_index.json"
    index_path.unlink()

    store = ReadOnlyRecipeStore(tmp_path / "data")
    assert store.load_stage_output(1, 1, "extracted", ExtractedRecipe) is not None
    # Loading from a non-existent recipe must not create its directory.
    assert store.load_stage_output(1, 99, "extracted", ExtractedRecipe) is None
    assert not (store.data_dir / "publications" / "1" / "recipes" / "99").exists()
    # Rebuilding the status index must stay in-memory.
    index = store.load_status_index(1)
    assert index == {"1": RecipeStatus.EXTRACTED.value}
    assert not index_path.exists()


def test_workspace_store_ids_do_not_collide_with_prod(tmp_path: Path) -> None:
    prod = RecipeStore(tmp_path / "data")
    (prod.data_dir / "publications" / "7").mkdir(parents=True)
    run_dir = tmp_path / "data" / "reviews" / "review_x"

    workspace = create_workspace_store(run_dir, prod)

    assert workspace.data_dir == run_dir / "_workspace"
    assert workspace.get_next_publication_id() == 8
