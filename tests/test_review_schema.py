from mexipes.review.models import TRIAGE_NOTES_PLACEHOLDER, ReviewFinding, make_finding_key


def test_review_finding_populates_stable_key() -> None:
    finding = ReviewFinding(
        publication_id=1,
        recipe_id=2,
        persona="taxonomy",
        stage="tags",
        field="primary_protein",
        finding_type="tag semantic error",
        issue="Protein tag does not match the recipe.",
        evidence="The recipe contains chicken but tag says Ninguno.",
        suggested_action="rerun_stage",
        rerun_stage="tag",
    )

    assert finding.finding_key == "1:2:tags:primary_protein:tag_semantic_error"
    assert finding.triage_notes == TRIAGE_NOTES_PLACEHOLDER


def test_make_finding_key_is_stable_and_normalized() -> None:
    assert make_finding_key(1, 2, "Localized Tags", "Primary Protein", "Bad Value") == (
        "1:2:localized_tags:primary_protein:bad_value"
    )


def test_triage_notes_round_trip_in_artifact_json() -> None:
    finding = ReviewFinding(
        publication_id=1,
        recipe_id=2,
        persona="extraction",
        stage="extract",
        field="ingredients",
        finding_type="ocr_artifact",
        issue="Broken hyphenation in ingredient.",
        evidence="PDF shows 'aza-\\nhúcar'.",
        suggested_action="repair_field",
        triage_notes="Discard: OCR looks fine after re-check.",
    )

    dumped = finding.model_dump()
    assert dumped["triage_notes"] == "Discard: OCR looks fine after re-check."
    restored = ReviewFinding.model_validate(dumped)
    assert restored.triage_notes == "Discard: OCR looks fine after re-check."
