import pytest

from mexipes.review.registry import REVIEWERS, resolve_reviewers


def test_resolve_reviewers_defaults_to_all() -> None:
    reviewers = resolve_reviewers(None)

    assert [reviewer.name for reviewer in reviewers] == list(REVIEWERS)


def test_resolve_reviewers_filters_by_name() -> None:
    reviewers = resolve_reviewers("extraction,taxonomy")

    assert [reviewer.name for reviewer in reviewers] == ["extraction", "taxonomy"]
    assert reviewers[0].required_stages == ("extracted",)
    assert reviewers[0].needs_pdf is True


def test_resolve_reviewers_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown review persona"):
        resolve_reviewers("extraction,nope")


def test_extraction_guidelines_forbid_book_page_false_positives() -> None:
    guidelines = " ".join(REVIEWERS["extraction"].guidelines)

    assert "PDF document indices" in guidelines
    assert "printed" in guidelines
    assert "recipe_index" in guidelines
