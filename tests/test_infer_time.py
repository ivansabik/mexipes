"""Tests for total_time inference and backfill."""

import json
from unittest.mock import patch

from mexipes.schemas import RewrittenRecipe
from mexipes.stages.infer_time import ensure_total_time
from mexipes.storage import RecipeStore


def _rewritten(**overrides) -> RewrittenRecipe:
    data = {
        "title": "Pollo en salsa",
        "ingredients": "pollo\nsal",
        "instructions": "Cocinar 20 minutos.",
    }
    data.update(overrides)
    return RewrittenRecipe(**data)


def test_ensure_total_time_skips_when_set(tmp_path):
    store = RecipeStore(tmp_path)
    store.get_publication_dir(1)
    store.save_stage_output(1, 1, "rewritten", _rewritten(total_time="30-60 min"))

    with patch("mexipes.stages.infer_time._infer_total_time_from_recipe") as infer:
        result = ensure_total_time(store, 1, 1)
        infer.assert_not_called()

    assert result.total_time == "30-60 min"


def test_ensure_total_time_backfills_from_legacy_tags(tmp_path):
    store = RecipeStore(tmp_path)
    store.get_publication_dir(1)
    store.save_stage_output(1, 1, "rewritten", _rewritten())
    tags_path = store.get_recipe_dir(1, 1) / "tags.json"
    tags_path.write_text(json.dumps({"total_time": "2+ horas"}), encoding="utf-8")

    with patch("mexipes.stages.infer_time._infer_total_time_from_recipe") as infer:
        result = ensure_total_time(store, 1, 1)
        infer.assert_not_called()

    assert result.total_time == "2+ horas"


def test_ensure_total_time_defaults_desconocido_when_missing(tmp_path):
    store = RecipeStore(tmp_path)
    store.get_publication_dir(1)
    store.save_stage_output(1, 1, "rewritten", _rewritten())

    with patch("mexipes.stages.infer_time._infer_total_time_from_recipe") as infer:
        result = ensure_total_time(store, 1, 1)
        infer.assert_not_called()

    assert result.total_time == "Desconocido"
    saved = store.load_stage_output(1, 1, "rewritten", RewrittenRecipe)
    assert saved.total_time == "Desconocido"
