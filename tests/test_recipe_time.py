"""Tests for recipe total_time vocabulary."""

from mexipes.schemas import recipe_time


def test_normalize_total_time_spanish():
    assert recipe_time.normalize_total_time("30-60 min") == "30-60 min"
    assert recipe_time.normalize_total_time("  2+ horas  ") == "2+ horas"


def test_normalize_total_time_english_to_spanish():
    assert recipe_time.normalize_total_time("Under 30 min") == "Menos de 30 min"
    assert recipe_time.normalize_total_time("2+ hours") == "2+ horas"


def test_normalize_total_time_unknown_fallback():
    assert recipe_time.normalize_total_time("maybe an hour") == "Desconocido"
    assert recipe_time.normalize_total_time(None) is None
    assert recipe_time.normalize_total_time("") is None


def test_es_to_en_and_slug():
    assert recipe_time.es_to_en("Desconocido") == "Unknown"
    assert recipe_time.es_to_en("N/A") == "N/A"
    assert recipe_time.slug_for("1-2 horas") == "1-2-hours"


def test_bilingual_entry():
    entry = recipe_time.bilingual_entry("30-60 min")
    assert entry == {"slug": "30-60-min", "es": "30-60 min", "en": "30-60 min"}
