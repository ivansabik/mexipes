"""Tests for the substitution pantry guide."""

from mexipes.schemas.pantry_substitutions import (
    SKIP_ENTRIES,
    SPECIALTY_ENTRIES,
    format_pantry_substitutions_prompt_section,
)


def _all_entry_names() -> list[str]:
    names: list[str] = []
    for entry in SKIP_ENTRIES + SPECIALTY_ENTRIES:
        names.extend(entry.names)
    return names


def test_format_pantry_substitutions_prompt_section_renders():
    text = format_pantry_substitutions_prompt_section()
    assert "### Do not substitute" in text
    assert "### Specialty items" in text
    assert "### Masa disambiguation" in text


def test_prompt_includes_new_cheeses():
    text = format_pantry_substitutions_prompt_section()
    for term in ("queso añejo", "queso asadero", "queso de bola", "requesón"):
        assert term in text


def test_prompt_includes_maggi_prepared_kit():
    text = format_pantry_substitutions_prompt_section()
    assert "Jugoso al Sartén" in text
    assert "Pastor seasoning sheets" in text
    assert "Mexico-only pre-seasoned cooking sheets" in text


def test_no_duplicate_names_across_entries():
    names = _all_entry_names()
    normalized = [n.lower().strip() for n in names]
    assert len(normalized) == len(set(normalized)), (
        f"Duplicate pantry entry names: {[n for n in normalized if normalized.count(n) > 1]}"
    )
