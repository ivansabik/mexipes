"""Tests for pipeline orchestration helpers."""

from unittest.mock import patch

from mexipes.pipeline.orchestrator import (
    _batch_exceeded,
    _pending_recipe_count,
    _pipeline_progress_snapshot,
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
