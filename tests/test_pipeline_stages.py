"""Tests for pipeline stage registry and advancement mapping."""

from mexipes.pipeline.stages import (
    ADVANCE_PRIORITY_STATUSES,
    NEXT_STAGE_BY_STATUS,
    PIPELINE_STAGES,
    get_next_stage,
)
from mexipes.schemas.recipe import RecipeStatus


def test_pipeline_stage_order():
    stage_names = [name for name, _before, _after in PIPELINE_STAGES]
    assert stage_names == ["rewrite", "describe", "tag", "localize", "substitute"]


def test_next_stage_by_status_matches_pipeline():
    for stage_name, before, _after in PIPELINE_STAGES:
        assert NEXT_STAGE_BY_STATUS[before] == stage_name
        assert get_next_stage(before) == stage_name


def test_advance_priority_is_furthest_along_first():
    assert ADVANCE_PRIORITY_STATUSES[0] == RecipeStatus.LOCALIZED
    assert ADVANCE_PRIORITY_STATUSES[-1] == RecipeStatus.EXTRACTED
