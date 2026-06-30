"""Tests for publication inherited-tag sanitization and merge behavior."""

from mexipes.inherited_tags import (
    infer_region_from_title,
    region_claim_supported,
    sanitize_inherited_tags,
)
from mexipes.schemas import RecipeTagSet
from mexipes.schemas.publication import InheritedTags, PublicationMetadata, RegionalSection
from mexipes.stages.tag import _merge_inherited_tags


def _minimal_tag_data(**overrides) -> dict:
    data = {
        "primary_protein": "Pollo",
        "spiciness": "Medio",
        "difficulty": "Fácil",
        "budget": "Moderado",
    }
    data.update(overrides)
    return data


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
            budget="Económico",
        ),
    )
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region is None
    assert sanitized.budget == "Económico"


def test_sanitize_keeps_region_for_regional_cookbook():
    metadata = _metadata(
        document_title="La Cocina de Oaxaca",
        inherited=InheritedTags(region="Oaxaca"),
    )
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region == "Oaxaca"


def test_sanitize_keeps_region_when_regional_sections_present():
    metadata = _metadata(
        document_title="Recetario Bien Estar",
        regional_sections=[RegionalSection(region_name="Yucatán", page_start=1, page_end=None)],
        inherited=InheritedTags(region="Yucatán"),
    )
    sanitized = sanitize_inherited_tags(metadata)
    assert sanitized.region == "Yucatán"


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


def test_merge_budget_overrides_recipe_value():
    tags = RecipeTagSet(**_minimal_tag_data(budget="Moderado"))
    inherited = InheritedTags(budget="Económico")
    _merge_inherited_tags(tags, inherited)
    assert tags.budget == "Económico"


def test_merge_appends_inherited_dietary():
    tags = RecipeTagSet(**_minimal_tag_data(dietary=["Vegetariano"]))
    inherited = InheritedTags(dietary=["Sin Lácteos"])
    _merge_inherited_tags(tags, inherited)
    assert tags.dietary == ["Vegetariano", "Sin Lácteos"]
