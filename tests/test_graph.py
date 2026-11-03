"""Unit tests for workflow routing helpers (no API key, no graph invoke)."""

from mexipes.graph import (
    actionable_reruns,
    decide_route,
    has_prompt_candidate,
    route_after_evaluate,
    trial_passed,
)
from mexipes.review.models import ConsolidatedReview, RerunRecommendation, ReviewFinding, ReviewGroup


def test_actionable_reruns_earliest_stage_wins() -> None:
    recommended = [
        RerunRecommendation(publication_id=1, recipe_id=2, stage="localize", reason="late"),
        RerunRecommendation(publication_id=1, recipe_id=2, stage="tag", reason="earlier"),
        RerunRecommendation(publication_id=1, recipe_id=3, stage="describe", reason="ok"),
    ]
    assert actionable_reruns(recommended) == [(1, 2, "tag"), (1, 3, "describe")]


def test_actionable_reruns_drops_extract_unknown_and_applied() -> None:
    recommended = [
        RerunRecommendation(publication_id=1, recipe_id=1, stage="extract", reason="no"),
        RerunRecommendation(publication_id=1, recipe_id=1, stage="mystery", reason="no"),
        RerunRecommendation(publication_id=1, recipe_id=1, stage="rewrite", reason="yes"),
        RerunRecommendation(publication_id=1, recipe_id=2, stage="tag", reason="already"),
    ]
    assert actionable_reruns(recommended, applied=[(1, 2, "tag")]) == [(1, 1, "rewrite")]


def test_decide_route_fix_prompt_end() -> None:
    assert decide_route(
        fixes_applied=0,
        max_loops=3,
        pending_reruns=[(1, 1, "tag")],
        prompt_candidate=True,
    ) == ("fix", None)
    assert decide_route(
        fixes_applied=3,
        max_loops=3,
        pending_reruns=[(1, 1, "tag")],
        prompt_candidate=False,
    ) == ("end", "max_loops")
    assert decide_route(
        fixes_applied=1,
        max_loops=3,
        pending_reruns=[],
        prompt_candidate=True,
    ) == ("prompt_trial", None)
    assert decide_route(
        fixes_applied=0,
        max_loops=3,
        pending_reruns=[],
        prompt_candidate=False,
        recommended_count=2,
    ) == ("end", "no_new_reruns")
    assert decide_route(
        fixes_applied=0,
        max_loops=3,
        pending_reruns=[],
        prompt_candidate=False,
        recommended_count=0,
    ) == ("end", "clean")


def test_route_after_evaluate_reads_state() -> None:
    assert route_after_evaluate({"next_route": "fix"}) == "fix"
    assert route_after_evaluate({}) == "end"


def test_has_prompt_candidate() -> None:
    empty = ConsolidatedReview(summary="none")
    assert has_prompt_candidate(empty) is False
    with_group = ConsolidatedReview(
        summary="x",
        grouped_findings=[
            ReviewGroup(
                title="t",
                suggested_action="prompt_change",
                finding_keys=["1:1:tag:x:y"],
                summary="s",
                recommendation="r",
            )
        ],
    )
    assert has_prompt_candidate(with_group) is True
    assert has_prompt_candidate(with_group.model_dump()) is True


def test_trial_passed_requires_cleared_targets_and_no_new_keys() -> None:
    before = [
        ReviewFinding(
            publication_id=1,
            recipe_id=1,
            persona="taxonomy",
            stage="tag",
            field="region",
            finding_type="wrong_region",
            issue="bad",
            evidence="e",
            suggested_action="prompt_change",
        )
    ]
    target = {before[0].finding_key}
    assert trial_passed(target_keys=target, before_findings=before, after_findings=[]) is True
    assert trial_passed(target_keys=target, before_findings=before, after_findings=before) is False

    new_finding = ReviewFinding(
        publication_id=1,
        recipe_id=1,
        persona="taxonomy",
        stage="tag",
        field="course",
        finding_type="wrong_course",
        issue="new",
        evidence="e",
        suggested_action="rerun_stage",
    )
    assert trial_passed(target_keys=target, before_findings=before, after_findings=[new_finding]) is False
