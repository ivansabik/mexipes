"""Tests for publication-metadata region resolution."""

from mexipes.region import resolve_region
from mexipes.schemas.publication import InheritedTags, PublicationMetadata, RegionalSection


def _metadata(
    *,
    document_title: str | None = None,
    regional_sections: list[RegionalSection] | None = None,
    inherited_region: str | None = None,
) -> PublicationMetadata:
    return PublicationMetadata(
        document_title=document_title,
        pdf_pages="100",
        recipes_count="10",
        regional_sections=regional_sections or [],
        inherited_tags=InheritedTags(region=inherited_region),
    )


def test_preserves_recipe_region():
    metadata = _metadata(
        regional_sections=[RegionalSection(region_name="Oaxaca", page_start=1, page_end=50)],
        inherited_region="Yucatán",
    )
    assert resolve_region("Puebla", page_start=10, metadata=metadata) == "Puebla"


def test_null_like_recipe_region_triggers_fallback():
    metadata = _metadata(
        document_title="La Cocina de Yucatán",
        inherited_region="Yucatán",
    )
    assert resolve_region("", page_start=1, metadata=metadata) == "Yucatán"
    assert resolve_region("null", page_start=1, metadata=metadata) == "Yucatán"


def test_regional_section_match():
    metadata = _metadata(
        regional_sections=[
            RegionalSection(region_name="Veracruz", page_start=10, page_end=30),
            RegionalSection(region_name="Oaxaca", page_start=31, page_end=None),
        ],
    )
    assert resolve_region(None, page_start=15, metadata=metadata) == "Veracruz"
    assert resolve_region(None, page_start=31, metadata=metadata) == "Oaxaca"
    assert resolve_region(None, page_start=99, metadata=metadata) == "Oaxaca"
    assert resolve_region(None, page_start=5, metadata=metadata) is None


def test_section_wins_over_inherited_region():
    metadata = _metadata(
        regional_sections=[RegionalSection(region_name="Veracruz", page_start=1, page_end=20)],
        inherited_region="Yucatán",
    )
    assert resolve_region(None, page_start=5, metadata=metadata) == "Veracruz"


def test_inherited_region_when_no_section_match():
    metadata = _metadata(
        regional_sections=[RegionalSection(region_name="Veracruz", page_start=1, page_end=20)],
        inherited_region="Yucatán",
    )
    assert resolve_region(None, page_start=50, metadata=metadata) == "Yucatán"


def test_inherited_region_only():
    metadata = _metadata(
        document_title="La Cocina de Aguascalientes",
        inherited_region="Aguascalientes",
    )
    assert resolve_region(None, page_start=5, metadata=metadata) == "Aguascalientes"


def test_inherited_region_blocked_when_claim_unsupported():
    metadata = _metadata(
        document_title="Recetario Bien Estar",
        inherited_region="Estado de México",
    )
    assert resolve_region(None, page_start=5, metadata=metadata) is None


def test_no_metadata_sources_returns_none():
    metadata = _metadata()
    assert resolve_region(None, page_start=5, metadata=metadata) is None


def test_section_match_without_page_start_falls_back_to_inherited():
    metadata = _metadata(
        regional_sections=[RegionalSection(region_name="Veracruz", page_start=1, page_end=20)],
        inherited_region="Yucatán",
    )
    assert resolve_region(None, page_start=None, metadata=metadata) == "Yucatán"


def test_inherited_region_from_tacotalpa_title():
    metadata = _metadata(
        document_title="Recetario platillos regionales de Tacotalpa, Tabasco. México Vol 1.",
        inherited_region="Tabasco",
    )
    assert resolve_region(None, page_start=12, metadata=metadata) == "Tabasco"
