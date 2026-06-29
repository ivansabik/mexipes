"""Single source of truth for recipe pipeline stage order and dispatch."""

from __future__ import annotations

from collections.abc import Callable

from mexipes.schemas.recipe import RecipeStatus
from mexipes.storage import RecipeStore

# (stage_name, status_before_stage, status_after_stage)
PIPELINE_STAGES: list[tuple[str, RecipeStatus, RecipeStatus]] = [
    ("rewrite", RecipeStatus.EXTRACTED, RecipeStatus.REWRITTEN),
    ("describe", RecipeStatus.REWRITTEN, RecipeStatus.IMAGES_DESCRIBED),
    ("tag", RecipeStatus.IMAGES_DESCRIBED, RecipeStatus.TAGGED),
    ("localize", RecipeStatus.TAGGED, RecipeStatus.LOCALIZED),
    ("substitute", RecipeStatus.LOCALIZED, RecipeStatus.READY),
]

NEXT_STAGE_BY_STATUS: dict[RecipeStatus, str] = {before: stage_name for stage_name, before, _after in PIPELINE_STAGES}

# Furthest-along recipes first when batching workspace-wide advancement.
ADVANCE_PRIORITY_STATUSES: list[RecipeStatus] = [before for _stage_name, before, _after in reversed(PIPELINE_STAGES)]

TERMINAL_STATUSES: frozenset[RecipeStatus] = frozenset({RecipeStatus.READY, RecipeStatus.FAILED})

# Monotonic rank for progress detection in --all-stages (higher = further along).
STATUS_ADVANCEMENT_RANK: dict[RecipeStatus, int] = {RecipeStatus.EXTRACTED: 0}
for _rank, (_name, _before, after) in enumerate(PIPELINE_STAGES, start=1):
    STATUS_ADVANCEMENT_RANK[after] = _rank
STATUS_ADVANCEMENT_RANK[RecipeStatus.READY] = len(PIPELINE_STAGES)
STATUS_ADVANCEMENT_RANK[RecipeStatus.FAILED] = len(PIPELINE_STAGES)


def get_next_stage(status: RecipeStatus) -> str | None:
    """Map current RecipeStatus to the next stage name to run."""
    return NEXT_STAGE_BY_STATUS.get(status)


def run_registered_stage(store: RecipeStore, publication_id: int, recipe_id: int, stage_name: str) -> None:
    """Run a registered pipeline stage for a single recipe."""
    runners: dict[str, Callable[[RecipeStore, int, int], None]] = {
        "rewrite": _run_rewrite,
        "describe": _run_describe,
        "tag": _run_tag,
        "localize": _run_localize,
        "substitute": _run_substitute,
    }
    runner = runners.get(stage_name)
    if runner is None:
        raise ValueError(f"Unknown stage: {stage_name}")
    runner(store, publication_id, recipe_id)


def _run_rewrite(store: RecipeStore, publication_id: int, recipe_id: int) -> None:
    from mexipes.stages.rewrite import rewrite_recipe

    rewrite_recipe(store, publication_id, recipe_id)


def _run_describe(store: RecipeStore, publication_id: int, recipe_id: int) -> None:
    from mexipes.stages.describe import describe_images

    describe_images(store, publication_id, recipe_id)


def _run_tag(store: RecipeStore, publication_id: int, recipe_id: int) -> None:
    from mexipes.stages.tag import tag_recipe

    tag_recipe(store, publication_id, recipe_id)


def _run_localize(store: RecipeStore, publication_id: int, recipe_id: int) -> None:
    from mexipes.stages.localize import localize_recipe

    localize_recipe(store, publication_id, recipe_id)


def _run_substitute(store: RecipeStore, publication_id: int, recipe_id: int) -> None:
    from mexipes.stages.substitute import substitute_ingredients

    substitute_ingredients(store, publication_id, recipe_id)
