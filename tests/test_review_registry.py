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
    assert "food photograph" in guidelines


def test_fidelity_guidelines_allow_verbatim_functional_rewrite() -> None:
    guidelines = " ".join(REVIEWERS["fidelity"].guidelines)
    assert "anecdotes" in guidelines.lower() or "headnotes" in guidelines.lower()
    assert "style-only" in guidelines.lower()


def test_taxonomy_guidelines_separate_protein_from_key_ingredient() -> None:
    guidelines = " ".join(REVIEWERS["taxonomy"].guidelines)
    assert "primary_protein" in guidelines
    assert "key_ingredient" in guidelines
