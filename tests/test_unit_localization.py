"""Tests for localization unit-conversion heuristics."""

from mexipes.unit_localization import find_suspicious_volume_upgrades


def test_flags_taza_to_quart_upgrade() -> None:
    es = "1T de leche de almendras\n1T agua\n1/2T crema"
    en = "1 quart almond milk\n1 quart water\n1/2 quart cream"
    issues = find_suspicious_volume_upgrades(es, en)
    assert len(issues) == 3


def test_ignores_cross_line_false_positive() -> None:
    es = "3 T de agua\n2 T de vinagre blanco"
    en = "3 cups water\n2 tablespoons white vinegar"
    assert find_suspicious_volume_upgrades(es, en) == []


def test_flags_aligned_line_quart_upgrade() -> None:
    es = "1T de leche"
    en = "1 quart milk"
    assert len(find_suspicious_volume_upgrades(es, en)) == 1


def test_allows_cup_translation() -> None:
    es = "1T de leche"
    en = "1 cup milk"
    assert find_suspicious_volume_upgrades(es, en) == []


def test_allows_tbsp_abbreviation() -> None:
    es = "2 cda de aceite"
    en = "2 tablespoons oil"
    assert find_suspicious_volume_upgrades(es, en) == []
