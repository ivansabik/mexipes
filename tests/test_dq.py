"""Tests for data quality checks."""

import json

from mexipes.dq import run_dq_checks
from mexipes.schemas.recipe import ExtractedRecipe
from mexipes.storage import RecipeStore


def _write_minimal_publication(store: RecipeStore, publication_id: int, recipe_id: int) -> None:
    pub_dir = store.get_publication_dir(publication_id)
    (pub_dir / "publication_info.json").write_text(
        json.dumps({"md5": "abc", "status": "extracted"}),
        encoding="utf-8",
    )
    (pub_dir / "source.pdf").write_bytes(b"%PDF-1.4")
    store.save_stage_output(
        publication_id,
        recipe_id,
        "extracted",
        ExtractedRecipe(
            title="Sopa",
            ingredients="agua y sal",
            instructions="Hervir el agua y sazonar.",
            has_multiple_recipes=True,
        ),
    )


def test_dq_warns_on_has_multiple_recipes(tmp_path):
    store = RecipeStore(tmp_path)
    _write_minimal_publication(store, 1, 1)

    report = run_dq_checks(store, publication_id=1)
    warnings = [i for i in report.issues if i.field == "has_multiple_recipes"]
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
