"""Tests for text normalization helpers."""

from mexipes.text_utils import (
    convert_unicode_fractions,
    has_section_headers,
    has_unicode_fractions,
    normalize_extracted_text,
    normalize_title_en,
    normalize_title_es,
    strip_section_headers,
)


def test_convert_unicode_fractions():
    assert convert_unicode_fractions("½ taza de arroz") == "1/2 taza de arroz"
    assert convert_unicode_fractions("¼ y ¾") == "1/4 y 3/4"


def test_strip_section_headers():
    assert strip_section_headers("INGREDIENTES:\n2 tazas de arroz") == "2 tazas de arroz"
    assert strip_section_headers("PREPARACIÓN:\nCocer el arroz.") == "Cocer el arroz."


def test_normalize_extracted_text_combined():
    text = "INGREDIENTES:\n½ kilo de jitomate"
    assert normalize_extracted_text(text) == "1/2 kilo de jitomate"


def test_has_unicode_fractions():
    assert has_unicode_fractions("½ kilo")
    assert not has_unicode_fractions("1/2 kilo")


def test_has_section_headers():
    assert has_section_headers("INGREDIENTES:\n2 tazas")
    assert not has_section_headers("2 tazas de arroz")
    assert not has_section_headers("Modo de preparación:\n1. Cocer el arroz.")
    assert strip_section_headers("Modo de preparación:\n1. Cocer el arroz.") == "1. Cocer el arroz."


def test_normalize_title_es_all_caps():
    assert normalize_title_es("COLORADITO OAXAQUEÑO") == "Coloradito Oaxaqueño"
    assert normalize_title_es("MOLE DE OLLA CON POLLO") == "Mole de Olla con Pollo"


def test_normalize_title_es_mixed_case_unchanged():
    assert normalize_title_es("Mole Negro Oaxaqueño") == "Mole Negro Oaxaqueño"


def test_normalize_title_en_all_caps():
    assert normalize_title_en("BLACK MOLE WITH CHICKEN") == "Black Mole with Chicken"


def test_normalize_title_en_mixed_case_unchanged():
    assert normalize_title_en("Black Mole with Chicken") == "Black Mole with Chicken"
