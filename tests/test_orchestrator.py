"""Tests for pipeline orchestration helpers."""

from unittest.mock import patch

from mexipes.pipeline.orchestrator import (
    _batch_exceeded,
    _pending_recipe_count,
    _pipeline_progress_snapshot,
    _registered_publication_ids,
    run_full_pipeline,
    run_pipeline_until_ready,
)
from mexipes.schemas.recipe import RecipeStatus
from mexipes.storage import RecipeStore


def test_batch_exceeded_unlimited_when_zero():
    assert not _batch_exceeded(100, 0)
    assert not _batch_exceeded(100, -1)


def test_batch_exceeded_respects_positive_limit():
    assert not _batch_exceeded(9, 10)
    assert _batch_exceeded(10, 10)


def test_pending_recipe_count_excludes_terminal_statuses(tmp_path):
    store = RecipeStore(tmp_path)
    store.set_status(1, 1, RecipeStatus.READY)
    store.set_status(1, 2, RecipeStatus.FAILED)
    store.set_status(1, 3, RecipeStatus.TAGGED)

    assert _pending_recipe_count(store, 1) == 1


def test_run_pipeline_until_ready_stops_when_no_pending(tmp_path):
    store = RecipeStore(tmp_path)
    store.set_status(2, 1, RecipeStatus.READY)

    with patch("mexipes.pipeline.orchestrator.run_pipeline") as run_pipeline:
        run_pipeline_until_ready(store, 2, batch_size=10)

    run_pipeline.assert_not_called()


def test_pipeline_progress_snapshot_increases_on_intermediate_advance(tmp_path):
    store = RecipeStore(tmp_path)
    store.set_status(1, 1, RecipeStatus.EXTRACTED)
    store.set_status(1, 2, RecipeStatus.EXTRACTED)

    before_score, before_pending = _pipeline_progress_snapshot(store, 1)
    store.set_status(1, 1, RecipeStatus.REWRITTEN)
    store.set_status(1, 2, RecipeStatus.REWRITTEN)
    after_score, after_pending = _pipeline_progress_snapshot(store, 1)

    assert before_pending == after_pending == 2
    assert after_score > before_score


def test_run_pipeline_until_ready_loops_on_intermediate_advance(tmp_path):
    """Pending count unchanged (extracted→rewritten) must not stop the loop early."""
    store = RecipeStore(tmp_path)
    store.set_status(2, 1, RecipeStatus.EXTRACTED)
    store.set_status(2, 2, RecipeStatus.EXTRACTED)

    call_count = {"n": 0}

    def fake_run_pipeline(*_args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            store.set_status(2, 1, RecipeStatus.REWRITTEN)
            store.set_status(2, 2, RecipeStatus.REWRITTEN)
        elif call_count["n"] == 2:
            store.set_status(2, 1, RecipeStatus.READY)
            store.set_status(2, 2, RecipeStatus.READY)

    with patch("mexipes.pipeline.orchestrator.run_pipeline", side_effect=fake_run_pipeline):
        run_pipeline_until_ready(store, 2, batch_size=10)

    assert call_count["n"] == 2


def test_run_pipeline_until_ready_loops_until_terminal(tmp_path):
    store = RecipeStore(tmp_path)
    store.set_status(2, 1, RecipeStatus.EXTRACTED)
    store.set_status(2, 2, RecipeStatus.EXTRACTED)

    call_count = {"n": 0}

    def fake_run_pipeline(*_args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            store.set_status(2, 1, RecipeStatus.READY)
            store.set_status(2, 2, RecipeStatus.READY)

    with patch("mexipes.pipeline.orchestrator.run_pipeline", side_effect=fake_run_pipeline):
        run_pipeline_until_ready(store, 2, batch_size=10)

    assert call_count["n"] == 1


def _register_publication(store: RecipeStore, publication_id: int) -> None:
    """Create a minimal registered publication (source.pdf present)."""
    pub_dir = store.get_publication_dir(publication_id)
    (pub_dir / "source.pdf").write_bytes(b"%PDF-1.4 stub")


def test_registered_publication_ids_requires_source_pdf(tmp_path):
    store = RecipeStore(tmp_path)
    _register_publication(store, 3)
    _register_publication(store, 1)
    # A publication dir without source.pdf should be ignored.
    store.get_publication_dir(2)

    assert _registered_publication_ids(store) == [1, 3]


def test_run_full_pipeline_ingests_extracts_and_processes(tmp_path):
    store = RecipeStore(tmp_path)
    staging = tmp_path / "staging"
    staging.mkdir(exist_ok=True)
    (staging / "sample.pdf").write_bytes(b"%PDF-1.4 stub")

    def fake_ingest(_store, _staging):
        _register_publication(store, 1)

    def fake_extract(_store, publication_id):
        store.set_status(publication_id, 1, RecipeStatus.EXTRACTED)

    def fake_until_ready(_store, publication_id, **_kwargs):
        store.set_status(publication_id, 1, RecipeStatus.READY)

    with (
        patch("mexipes.stages.ingest.ingest_pdfs", side_effect=fake_ingest) as ingest,
        patch("mexipes.stages.extract.extract_publication_recipes", side_effect=fake_extract) as extract,
        patch("mexipes.pipeline.orchestrator.run_pipeline_until_ready", side_effect=fake_until_ready) as until_ready,
    ):
        processed = run_full_pipeline(store, staging_dir=staging, batch_size=5)

    ingest.assert_called_once()
    extract.assert_called_once()
    until_ready.assert_called_once()
    assert processed == [1]


def test_run_full_pipeline_skips_extraction_when_recipes_exist(tmp_path):
    store = RecipeStore(tmp_path)
    _register_publication(store, 1)
    store.set_status(1, 1, RecipeStatus.TAGGED)

    with (
        patch("mexipes.stages.extract.extract_publication_recipes") as extract,
        patch("mexipes.pipeline.orchestrator.run_pipeline_until_ready") as until_ready,
    ):
        processed = run_full_pipeline(store, staging_dir=tmp_path / "missing", batch_size=5)

    extract.assert_not_called()
    until_ready.assert_called_once()
    assert processed == [1]
