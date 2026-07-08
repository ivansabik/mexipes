import json
from pathlib import Path


def test_review_golden_fixture_documents_known_cases() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "review" / "golden_cases.json"
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert {case["name"] for case in cases} == {"ocr_artifact", "clean_recipe"}
    assert cases[0]["expected_finding_type"] == "ocr_artifact"
    assert cases[1]["expected_findings"] == []
