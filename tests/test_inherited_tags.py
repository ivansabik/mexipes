"""Tests for publication inherited-tag sanitization."""

from mexipes.inherited_tags import infer_region_from_title, region_claim_supported, sanitize_inherited_tags
from mexipes.schemas.publication import InheritedTags, PublicationMetadata, RegionalSection


def _metadata(
    *,
    document_title: str | None = None,
    regional_sections: list[RegionalSection] | None = None,
    inherited: InheritedTags | None = None,
) -> PublicationMetadata:
    return PublicationMetadata(
        document_title=document_title,
        pdf_pages="100",
        recipes_count="10",
        regional_sections=regional_sections or [],
        inherited_tags=inherited or InheritedTags(),
    )


def test_region_claim_unsupported_for_generic_title():
    metadata = _metadata(document_title="Recetario Bien Estar")
    assert region_claim_supported(metadata) is False


def test_region_claim_supported_for_regional_title():
    metadata = _metadata(document_title="La Cocina de Oaxaca")
    assert region_claim_supported(metadata) is True


def test_region_claim_supported_with_regional_sections():
    metadata = _metadata(
        document_title="Recetario Bien Estar",
        regional_sections=[RegionalSection(region_name="Veracruz", page_start=1, page_end=50)],
    )
    assert region_claim_supported(metadata) is True


def test_sanitize_clears_region_from_publisher_hallucination():
    metadata = _metadata(
        document_title="Recetario Bien Estar",
        inherited=InheritedTags(
            region="Estado de México",
            cuisine_style=["Tradicional Regional"],
            budget="Económico",
        ),
    )
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region is None
    assert sanitized.cuisine_style == []
    assert sanitized.budget == "Económico"


def test_sanitize_keeps_region_for_regional_cookbook():
    metadata = _metadata(
        document_title="La Cocina de Oaxaca",
        inherited=InheritedTags(
            region="Oaxaca",
            cuisine_style=["Tradicional Regional"],
        ),
    )
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region == "Oaxaca"
    assert sanitized.cuisine_style == ["Tradicional Regional"]


def test_sanitize_keeps_region_when_regional_sections_present():
    metadata = _metadata(
        document_title="Recetario Bien Estar",
        regional_sections=[RegionalSection(region_name="Yucatán", page_start=1, page_end=None)],
        inherited=InheritedTags(region="Yucatán", cuisine_style=["Tradicional Regional"]),
    )
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region == "Yucatán"
    assert sanitized.cuisine_style == ["Tradicional Regional"]


_TACOTALPA_TITLE = "Recetario platillos regionales de Tacotalpa, Tabasco. México Vol 1."


def test_region_claim_supported_for_tacotalpa_title():
    metadata = _metadata(document_title=_TACOTALPA_TITLE)
    assert region_claim_supported(metadata) is True


def test_infer_region_from_tacotalpa_title():
    assert infer_region_from_title(_TACOTALPA_TITLE) == "Tabasco"


def test_sanitize_fills_region_from_tacotalpa_title():
    metadata = _metadata(document_title=_TACOTALPA_TITLE)
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region == "Tabasco"
    assert sanitized.cuisine_style == ["Tradicional Regional"]
