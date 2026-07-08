from mexipes.review.models import ConsolidatedReview, ReviewFinding, ReviewRunMetadata
from mexipes.review.runner import _consolidate_findings


def test_consolidation_updates_counts_from_findings(monkeypatch) -> None:
    findings = [
        ReviewFinding(
            publication_id=1,
            recipe_id=1,
            persona="extraction",
            stage="extracted",
            field="instructions",
            finding_type="ocr_artifact",
            severity="error",
            issue="Hyphenated OCR artifact remains.",
            evidence="machaca-\\ndos",
            suggested_action="dq_rule_change",
        ),
        ReviewFinding(
            publication_id=1,
            recipe_id=2,
            persona="taxonomy",
            stage="tags",
            field="dish_format",
            finding_type="tag_semantic_error",
            severity="warning",
            issue="Dish format is too broad.",
            evidence="Tagged Otro for tacos.",
            suggested_action="rerun_stage",
            rerun_stage="tag",
        ),
    ]

    def fake_call_llm(**_kwargs):
        return ConsolidatedReview(summary="Grouped review")

    monkeypatch.setattr("mexipes.review.runner.call_llm", fake_call_llm)
    metadata = ReviewRunMetadata(publications_sample_size=1, recipes_per_pub=2)

    consolidated = _consolidate_findings(metadata, findings)

    assert consolidated.summary == "Grouped review"
    assert consolidated.error_count == 1
    assert consolidated.warning_count == 1
    assert consolidated.info_count == 0


def test_consolidation_skips_llm_when_no_findings(monkeypatch) -> None:
    called = False

    def fake_call_llm(**_kwargs):
        nonlocal called
        called = True
        return ConsolidatedReview(summary="Should not be used")

    monkeypatch.setattr("mexipes.review.runner.call_llm", fake_call_llm)

    consolidated = _consolidate_findings(ReviewRunMetadata(publications_sample_size=1, recipes_per_pub=1), [])

    assert called is False
    assert "No evidence-backed findings" in consolidated.summary
