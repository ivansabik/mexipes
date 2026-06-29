"""Tests for RecipeStore persistence helpers."""

from mexipes.schemas.recipe import RecipeStatus
from mexipes.storage import RecipeStore


def test_status_index_built_lazily_and_updated_on_set_status(tmp_path):
    store = RecipeStore(tmp_path)
    publication_id = 1

    store.set_status(publication_id, 1, RecipeStatus.EXTRACTED)
    store.set_status(publication_id, 2, RecipeStatus.TAGGED)

    index_path = store.get_publication_dir(publication_id) / "_index.json"
    assert index_path.exists()
    index = store.load_status_index(publication_id)
    assert index == {"1": "extracted", "2": "tagged"}

    store.set_status(publication_id, 1, RecipeStatus.READY)
    assert store.load_status_index(publication_id)["1"] == "ready"


def test_find_recipes_at_status_uses_index(tmp_path):
    store = RecipeStore(tmp_path)
    store.set_status(1, 1, RecipeStatus.READY)
    store.set_status(1, 2, RecipeStatus.TAGGED)
    store.set_status(2, 1, RecipeStatus.READY)

    ready = store.find_recipes_at_status(RecipeStatus.READY)
    assert set(ready) == {(1, 1), (2, 1)}

    tagged = store.find_recipes_at_status(RecipeStatus.TAGGED)
    assert tagged == [(1, 2)]


def test_rebuild_status_index_from_status_files(tmp_path):
    store = RecipeStore(tmp_path)
    publication_id = 3
    store.set_status(publication_id, 10, RecipeStatus.REWRITTEN)
    store.set_status(publication_id, 11, RecipeStatus.FAILED)

    index_path = store._status_index_path(publication_id)
    index_path.unlink()

    rebuilt = store.rebuild_status_index(publication_id)
    assert rebuilt == {"10": "rewritten", "11": "failed"}
    assert index_path.exists()


def test_get_next_recipe_id_allocates_sequentially(tmp_path):
    store = RecipeStore(tmp_path)
    publication_id = 4

    assert store.get_next_recipe_id(publication_id) == 1
    store.get_recipe_dir(publication_id, 1)
    assert store.get_next_recipe_id(publication_id) == 2
    assert store.get_next_recipe_id(publication_id) == 3

    counter_path = store.get_publication_dir(publication_id) / "_next_id.txt"
    assert counter_path.read_text(encoding="utf-8") == "4"


def test_get_next_recipe_id_respects_existing_recipe_dirs(tmp_path):
    store = RecipeStore(tmp_path)
    publication_id = 5
    store.get_recipe_dir(publication_id, 7)

    assert store.get_next_recipe_id(publication_id) == 8


def test_load_stage_output_logs_and_strict_raises(tmp_path, caplog):
    import logging

    from mexipes.schemas.recipe import ExtractedRecipe

    store = RecipeStore(tmp_path)
    recipe_dir = store.get_recipe_dir(1, 1)
    (recipe_dir / "extracted.json").write_text('{"title": "x"}', encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        result = store.load_stage_output(1, 1, "extracted", ExtractedRecipe)
    assert result is None
    assert "Failed to load" in caplog.text

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        store.load_stage_output(1, 1, "extracted", ExtractedRecipe, strict=True)
