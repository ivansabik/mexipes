"""LangGraph workflow: process → review → evaluate → fix (capped) → optional prompt trial."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from datetime import UTC, datetime
from difflib import unified_diff
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from mexipes.config import settings
from mexipes.llm import call_llm, load_prompt, prompt_dir_override
from mexipes.pipeline.orchestrator import (
    run_full_pipeline,
    run_pipeline_until_ready,
    run_stage_for_recipe,
)
from mexipes.pipeline.stages import PIPELINE_STAGES
from mexipes.review.models import ConsolidatedReview, RerunRecommendation, ReviewFinding
from mexipes.review.registry import REVIEWERS, resolve_reviewers
from mexipes.review.runner import _issues_by_recipe, _recipe_pdf_bytes, _run_single_reviewer, run_quality_review
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)

RERUNNABLE_STAGES: tuple[str, ...] = tuple(name for name, _before, _after in PIPELINE_STAGES)
STAGE_RANK: dict[str, int] = {name: index for index, (name, _before, _after) in enumerate(PIPELINE_STAGES)}

ALLOWED_PROMPT_FILES: frozenset[str] = frozenset(
    {
        "rewrite_recipe.md",
        "infer_total_time.md",
        "tag_recipe.md",
        "localize_recipe.md",
        "localize_tags.md",
        "describe_image.md",
        "substitute_ingredients.md",
    }
)

PROMPT_TO_STAGE: dict[str, str] = {
    "rewrite_recipe.md": "rewrite",
    "infer_total_time.md": "rewrite",
    "tag_recipe.md": "tag",
    "localize_recipe.md": "localize",
    "localize_tags.md": "localize",
    "describe_image.md": "describe",
    "substitute_ingredients.md": "substitute",
}

MAX_PROMPT_TRIAL_RECIPES = 3

RouteName = Literal["fix", "prompt_trial", "end"]


class WorkflowState(TypedDict, total=False):
    publication_id: int | None
    publication_ids: list[int]
    batch_size: int
    max_loops: int
    fixes_applied: int
    applied: list[tuple[int, int, str]]
    review_dir: str | None
    stop_reason: str | None
    prompt_trial: dict[str, Any] | None
    pending_reruns: list[tuple[int, int, str]]
    pin_recipes: dict[str, list[int]]
    findings: list[dict[str, Any]]
    consolidator: dict[str, Any] | None
    has_prompt_candidate: bool
    next_route: RouteName
    dq_notes: list[str]


class PromptRewrite(BaseModel):
    """Structured prompt rewrite for a single trial."""

    prompt_file: str = Field(..., description="Allow-listed prompt filename under mexipes.prompts")
    updated_prompt: str = Field(..., description="Full replacement prompt text")


def actionable_reruns(
    recommended: list[RerunRecommendation] | list[dict[str, Any]],
    *,
    applied: list[tuple[int, int, str]] | None = None,
) -> list[tuple[int, int, str]]:
    """Earliest rerunnable stage per recipe; drop extract, unknown, and already-applied keys."""
    applied_set = set(applied or ())
    best: dict[tuple[int, int], tuple[int, str]] = {}
    for item in recommended:
        if isinstance(item, dict):
            pub_id = int(item["publication_id"])
            recipe_id = int(item["recipe_id"])
            stage = str(item["stage"])
        else:
            pub_id = item.publication_id
            recipe_id = item.recipe_id
            stage = item.stage
        if stage not in STAGE_RANK:
            continue
        key = (pub_id, recipe_id)
        rank = STAGE_RANK[stage]
        previous = best.get(key)
        if previous is None or rank < previous[0]:
            best[key] = (rank, stage)
    selected: list[tuple[int, int, str]] = []
    for (pub_id, recipe_id), (_rank, stage) in sorted(best.items(), key=lambda item: (item[0][0], item[0][1])):
        triple = (pub_id, recipe_id, stage)
        if triple in applied_set:
            continue
        selected.append(triple)
    return selected


def has_prompt_candidate(consolidated: ConsolidatedReview | dict[str, Any] | None) -> bool:
    if consolidated is None:
        return False
    if isinstance(consolidated, dict):
        groups = consolidated.get("grouped_findings") or []
        return any(group.get("suggested_action") == "prompt_change" for group in groups)
    return any(group.suggested_action == "prompt_change" for group in consolidated.grouped_findings)


def decide_route(
    *,
    fixes_applied: int,
    max_loops: int,
    pending_reruns: list[tuple[int, int, str]],
    prompt_candidate: bool,
    recommended_count: int = 0,
) -> tuple[RouteName, str | None]:
    """Return next graph node and optional stop_reason when routing to end."""
    if pending_reruns and fixes_applied < max_loops:
        return "fix", None
    if pending_reruns and fixes_applied >= max_loops:
        return "end", "max_loops"
    if prompt_candidate:
        return "prompt_trial", None
    if recommended_count > 0 and not pending_reruns:
        return "end", "no_new_reruns"
    return "end", "clean"


def route_after_evaluate(state: WorkflowState) -> RouteName:
    return state.get("next_route") or "end"


def trial_passed(
    *,
    target_keys: set[str],
    before_findings: list[ReviewFinding],
    after_findings: list[ReviewFinding],
) -> bool:
    """True when every target key is gone and no new finding keys appear."""
    before_keys = {finding.finding_key for finding in before_findings if finding.finding_key}
    after_keys = {finding.finding_key for finding in after_findings if finding.finding_key}
    if any(key in after_keys for key in target_keys):
        return False
    return not (after_keys - before_keys)


def _recipe_ids_for_publication(store: RecipeStore, publication_id: int) -> list[int]:
    return sorted(recipe_id for pub_id, recipe_id in store.find_all_recipes() if pub_id == publication_id)


def _backup_recipe(store: RecipeStore, publication_id: int, recipe_id: int, run_id: str) -> None:
    recipe_dir = store.data_dir / "publications" / str(publication_id) / "recipes" / str(recipe_id)
    if not recipe_dir.exists():
        return
    backup_dir = store.data_dir / "backups" / run_id / str(publication_id) / str(recipe_id)
    if backup_dir.exists():
        return
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(recipe_dir, backup_dir)


def _copy_publication_subset(
    src_store: RecipeStore,
    dest_store: RecipeStore,
    publication_id: int,
    recipe_ids: list[int],
) -> None:
    src_pub = src_store.data_dir / "publications" / str(publication_id)
    dest_pub = dest_store.get_publication_dir(publication_id)
    for name in ("source.pdf", "publication_info.json", "metadata.json"):
        src = src_pub / name
        if src.exists():
            shutil.copy2(src, dest_pub / name)
    for recipe_id in recipe_ids:
        src_recipe = src_pub / "recipes" / str(recipe_id)
        if not src_recipe.exists():
            continue
        dest_recipe = dest_store.get_recipe_dir(publication_id, recipe_id)
        if dest_recipe.exists():
            shutil.rmtree(dest_recipe)
        shutil.copytree(src_recipe, dest_recipe)


def _findings_for_prompt_groups(
    consolidator: ConsolidatedReview,
    findings: list[ReviewFinding],
) -> tuple[list[ReviewFinding], list[str]]:
    keys: set[str] = set()
    suggestions: list[str] = []
    for group in consolidator.grouped_findings:
        if group.suggested_action != "prompt_change":
            continue
        keys.update(group.finding_keys)
        if group.recommendation:
            suggestions.append(group.recommendation)
    suggestions.extend(consolidator.prompt_improvements)
    cited = [finding for finding in findings if finding.finding_key in keys]
    return cited, suggestions


def _rewrite_prompt_candidate(
    *,
    suggestions: list[str],
    findings: list[ReviewFinding],
) -> PromptRewrite:
    allow_list = ", ".join(sorted(ALLOWED_PROMPT_FILES))
    prompt = (
        "You rewrite one Mexipes pipeline prompt to address the findings below.\n"
        f"Choose exactly one prompt_file from this allow-list: {allow_list}.\n"
        "Return the full updated_prompt text for that file.\n"
        "Do not invent a new filename.\n\n"
        f"Suggestions:\n{json.dumps(suggestions, ensure_ascii=False, indent=2)}\n\n"
        f"Findings:\n{json.dumps([f.model_dump(exclude={'triage_notes'}) for f in findings], ensure_ascii=False, indent=2)}\n"
    )
    return call_llm(
        model=settings.consolidate.model,
        response_model=PromptRewrite,
        prompt=prompt,
        temperature=0.1,
        max_retries=settings.consolidate.max_retries,
    )


def build_workflow(store: RecipeStore):
    """Compile the process → review → evaluate → fix / prompt_trial graph."""

    backup_run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    def process_node(state: WorkflowState) -> dict[str, Any]:
        publication_id = state.get("publication_id")
        batch_size = state.get("batch_size", 10)
        if publication_id is None:
            publication_ids = run_full_pipeline(store, batch_size=batch_size)
        else:
            if not any(pub == publication_id for pub, _recipe in store.find_all_recipes()):
                from mexipes.stages.extract import extract_publication_recipes

                extract_publication_recipes(store, publication_id)
            run_pipeline_until_ready(store, publication_id, batch_size=batch_size)
            publication_ids = [publication_id]
        return {
            "publication_ids": publication_ids,
            "fixes_applied": 0,
            "applied": [],
            "pin_recipes": {},
            "stop_reason": None,
            "prompt_trial": None,
            "dq_notes": [],
        }

    def review_node(state: WorkflowState) -> dict[str, Any]:
        publication_ids = state.get("publication_ids") or []
        pin_recipes = state.get("pin_recipes") or {}
        all_findings: list[ReviewFinding] = []
        consolidator: ConsolidatedReview | None = None
        review_dir: str | None = None

        for publication_id in publication_ids:
            if str(publication_id) in pin_recipes:
                recipe_ids = pin_recipes[str(publication_id)]
            else:
                recipe_ids = _recipe_ids_for_publication(store, publication_id)
            if not recipe_ids:
                logger.info("Publication %s has no recipes to review; skipping.", publication_id)
                continue
            result = run_quality_review(
                store,
                publications=1,
                recipes_per_pub=len(recipe_ids),
                pinned_publications=[publication_id],
                pinned_recipes=recipe_ids,
                no_process=True,
            )
            all_findings.extend(result.artifact.findings)
            consolidator = result.artifact.consolidated
            review_dir = str(result.output_paths.run_dir)

        if consolidator is None:
            consolidator = ConsolidatedReview(summary="No recipes reviewed.")

        pending = actionable_reruns(consolidator.recommended_reruns, applied=state.get("applied") or [])
        prompt_candidate = has_prompt_candidate(consolidator)
        return {
            "findings": [finding.model_dump() for finding in all_findings],
            "consolidator": consolidator.model_dump(),
            "review_dir": review_dir,
            "pending_reruns": pending,
            "has_prompt_candidate": prompt_candidate,
            "dq_notes": list(consolidator.dq_code_improvements),
        }

    def evaluate_node(state: WorkflowState) -> dict[str, Any]:
        pending = list(state.get("pending_reruns") or [])
        fixes_applied = int(state.get("fixes_applied") or 0)
        max_loops = int(state.get("max_loops") or 3)
        prompt_candidate = bool(state.get("has_prompt_candidate"))
        consolidator = state.get("consolidator") or {}
        recommended_count = len(consolidator.get("recommended_reruns") or [])
        next_route, stop_reason = decide_route(
            fixes_applied=fixes_applied,
            max_loops=max_loops,
            pending_reruns=pending,
            prompt_candidate=prompt_candidate,
            recommended_count=recommended_count,
        )
        return {"next_route": next_route, "stop_reason": stop_reason}

    def fix_node(state: WorkflowState) -> dict[str, Any]:
        pending = list(state.get("pending_reruns") or [])
        applied = list(state.get("applied") or [])
        backed_up: set[tuple[int, int]] = set()
        pin: dict[str, list[int]] = {}
        pubs: set[int] = set()

        for publication_id, recipe_id, stage in pending:
            key = (publication_id, recipe_id)
            if key not in backed_up:
                _backup_recipe(store, publication_id, recipe_id, backup_run_id)
                backed_up.add(key)
            try:
                run_stage_for_recipe(store, publication_id, recipe_id, stage)
            except Exception:
                logger.exception(
                    "Workflow fix failed for %s:%s stage %s; continuing.",
                    publication_id,
                    recipe_id,
                    stage,
                )
            applied.append((publication_id, recipe_id, stage))
            pin.setdefault(str(publication_id), [])
            if recipe_id not in pin[str(publication_id)]:
                pin[str(publication_id)].append(recipe_id)
            pubs.add(publication_id)

        for publication_id in sorted(pubs):
            run_pipeline_until_ready(store, publication_id, batch_size=state.get("batch_size", 10))

        return {
            "applied": applied,
            "fixes_applied": int(state.get("fixes_applied") or 0) + 1,
            "pin_recipes": pin,
            "pending_reruns": [],
        }

    def prompt_trial_node(state: WorkflowState) -> dict[str, Any]:
        consolidator_data = state.get("consolidator")
        findings_data = state.get("findings") or []
        if not consolidator_data:
            return {
                "prompt_trial": {"passed": False, "reason": "no consolidator"},
                "stop_reason": "clean",
            }

        consolidator = ConsolidatedReview.model_validate(consolidator_data)
        findings = [ReviewFinding.model_validate(item) for item in findings_data]
        cited, suggestions = _findings_for_prompt_groups(consolidator, findings)
        if not cited or not suggestions:
            return {
                "prompt_trial": {"passed": False, "reason": "no prompt_change findings"},
                "stop_reason": state.get("stop_reason") or "clean",
            }

        # Cap trial recipes; keep first N unique (pub, recipe) in finding order.
        selected: list[tuple[int, int]] = []
        for finding in cited:
            pair = (finding.publication_id, finding.recipe_id)
            if pair not in selected:
                selected.append(pair)
            if len(selected) >= MAX_PROMPT_TRIAL_RECIPES:
                break

        target_keys = {finding.finding_key for finding in cited if finding.finding_key}
        before = [finding for finding in findings if (finding.publication_id, finding.recipe_id) in selected]

        try:
            rewrite = _rewrite_prompt_candidate(suggestions=suggestions, findings=cited)
        except Exception as exc:
            logger.exception("Prompt rewrite LLM failed.")
            return {
                "prompt_trial": {"passed": False, "reason": f"rewrite failed: {exc}"},
                "stop_reason": state.get("stop_reason") or "clean",
            }

        if rewrite.prompt_file not in ALLOWED_PROMPT_FILES:
            return {
                "prompt_trial": {
                    "passed": False,
                    "reason": f"disallowed prompt_file: {rewrite.prompt_file}",
                },
                "stop_reason": state.get("stop_reason") or "clean",
            }

        stage = PROMPT_TO_STAGE[rewrite.prompt_file]
        original = load_prompt(rewrite.prompt_file)
        diff = "".join(
            unified_diff(
                original.splitlines(keepends=True),
                rewrite.updated_prompt.splitlines(keepends=True),
                fromfile=f"a/{rewrite.prompt_file}",
                tofile=f"b/{rewrite.prompt_file}",
            )
        )

        with tempfile.TemporaryDirectory(prefix="mexipes-prompt-trial-") as tmp:
            tmp_path = Path(tmp)
            prompt_dir = tmp_path / "prompts"
            prompt_dir.mkdir()
            packaged = Path(__file__).resolve().parent / "prompts"
            for path in packaged.glob("*.md"):
                shutil.copy2(path, prompt_dir / path.name)
            (prompt_dir / rewrite.prompt_file).write_text(rewrite.updated_prompt, encoding="utf-8")

            trial_store = RecipeStore(tmp_path / "data")
            pubs = sorted({pub_id for pub_id, _recipe_id in selected})
            for publication_id in pubs:
                recipe_ids = [recipe_id for pub_id, recipe_id in selected if pub_id == publication_id]
                _copy_publication_subset(store, trial_store, publication_id, recipe_ids)

            try:
                with prompt_dir_override(prompt_dir):
                    for publication_id, recipe_id in selected:
                        run_stage_for_recipe(trial_store, publication_id, recipe_id, stage)
                    for publication_id in pubs:
                        run_pipeline_until_ready(trial_store, publication_id, batch_size=0)
            except Exception as exc:
                logger.exception("Prompt trial stage rerun failed.")
                return {
                    "prompt_trial": {"passed": False, "reason": f"stage failed: {exc}"},
                    "stop_reason": state.get("stop_reason") or "clean",
                }

            after: list[ReviewFinding] = []
            personas = sorted({finding.persona for finding in cited if finding.persona in REVIEWERS})
            reviewers = resolve_reviewers(",".join(personas)) if personas else list(REVIEWERS.values())
            for publication_id, recipe_id in selected:
                dq_by_recipe = _issues_by_recipe(trial_store, publication_id)
                pdf_bytes = _recipe_pdf_bytes(trial_store, publication_id, recipe_id)
                for reviewer in reviewers:
                    result = _run_single_reviewer(
                        trial_store,
                        reviewer,
                        publication_id=publication_id,
                        recipe_id=recipe_id,
                        dq_issues=dq_by_recipe.get(recipe_id, []),
                        max_findings=5,
                        pdf_bytes=pdf_bytes,
                    )
                    after.extend(result.findings)

        passed = trial_passed(target_keys=target_keys, before_findings=before, after_findings=after)
        recipe_ids = [f"{pub}:{recipe}" for pub, recipe in selected]
        if not passed:
            return {
                "prompt_trial": {
                    "passed": False,
                    "prompt_file": rewrite.prompt_file,
                    "recipe_ids": recipe_ids,
                    "reason": "target findings remain or new findings appeared",
                },
                "stop_reason": state.get("stop_reason") or "clean",
            }

        # shortcut: one trial on at most 3 cited recipes, reviewer variance can reject a good prompt;
        # a pass does not cover recipes that were not in the trial.
        return {
            "prompt_trial": {
                "passed": True,
                "prompt_file": rewrite.prompt_file,
                "diff": diff,
                "recipe_ids": recipe_ids,
                "reason": "target findings cleared",
            },
            "stop_reason": state.get("stop_reason") or "clean",
        }

    graph = StateGraph(WorkflowState)
    graph.add_node("process", process_node)
    graph.add_node("review", review_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("fix", fix_node)
    graph.add_node("prompt_trial", prompt_trial_node)

    graph.add_edge(START, "process")
    graph.add_edge("process", "review")
    graph.add_edge("review", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"fix": "fix", "prompt_trial": "prompt_trial", "end": END},
    )
    graph.add_edge("fix", "review")
    graph.add_edge("prompt_trial", END)
    return graph.compile()


def run_workflow(
    store: RecipeStore,
    *,
    publication_id: int | None = None,
    batch_size: int = 10,
    max_loops: int = 3,
) -> WorkflowState:
    """Invoke the compiled workflow and return the final state."""
    app = build_workflow(store)
    initial: WorkflowState = {
        "publication_id": publication_id,
        "batch_size": batch_size,
        "max_loops": max_loops,
        "fixes_applied": 0,
        "applied": [],
        "pin_recipes": {},
    }
    return app.invoke(initial)
