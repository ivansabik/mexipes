"""Tests for region normalization."""

from mexipes.region import normalize_region, resolve_region
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


def test_normalize_region_case_and_accent_fold():
    assert normalize_region("VERACRUZ") == "Veracruz"
    assert normalize_region("Yucatan") == "Yucatán"
    assert normalize_region("OAXACA") == "Oaxaca"


def test_normalize_region_city_state_suffix():
    assert normalize_region("Zongolica, Veracruz") == "Veracruz"
    assert normalize_region("Monterrey, N.L.") == "Nuevo León"


def test_normalize_region_distrito_federal_alias():
    assert normalize_region("Distrito Federal") == "Ciudad de México"
    assert normalize_region("DISTRITO FEDERAL") == "Ciudad de México"


def test_normalize_region_city_gazetteer():
    assert normalize_region("Jalcomulco") == "Veracruz"
    assert normalize_region("Acapulco") == "Guerrero"
    assert normalize_region("Los Chenes") == "Campeche"


def test_normalize_region_junk_to_none():
    assert normalize_region("México") is None
    assert normalize_region("TODAS") is None
    assert normalize_region("Noroeste") is None
    assert normalize_region("Centro") is None


def test_normalize_region_ambiguous_locality_to_none():
    assert normalize_region("Benito Juárez") is None


def test_normalize_region_canonical_passthrough():
    assert normalize_region("Oaxaca") == "Oaxaca"
    assert normalize_region("Ciudad de México") == "Ciudad de México"


def test_resolve_region_normalizes_recipe_level():
    metadata = _metadata(
        regional_sections=[RegionalSection(region_name="Oaxaca", page_start=1, page_end=50)],
    )
    assert resolve_region("VERACRUZ", page_start=10, metadata=metadata) == "Veracruz"


def test_resolve_region_junk_falls_through_to_section():
    metadata = _metadata(
        regional_sections=[RegionalSection(region_name="Veracruz", page_start=1, page_end=50)],
    )
    assert resolve_region("México", page_start=10, metadata=metadata) == "Veracruz"


def test_resolve_region_junk_without_section_returns_none():
    metadata = _metadata()
    assert resolve_region("TODAS", page_start=10, metadata=metadata) is None
