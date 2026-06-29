"""Tests for tag vocabulary sanitization and localization."""

from unittest.mock import patch

from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.tags import RecipeTagSet, TagTranslation, TagTranslations
from mexipes.stages.localize import localize_tag_set


def _minimal_tag_data(**overrides) -> dict:
    data = {
        "primary_protein": "Pollo",
        "spiciness": "Medio",
        "difficulty": "Fácil",
        "total_time": "30-60 min",
        "budget": "Económico",
    }
    data.update(overrides)
    return data


def test_sanitize_drops_botana_from_course_and_occasion():
    data = _minimal_tag_data(
        course=["Plato Principal", "Botana"],
        meal_type=["Comida", "Botana"],
        occasion=["Entre Semana", "Botana"],
    )
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["course"] == ["Plato Principal"]
    assert cleaned["occasion"] == ["Entre Semana"]
    # 'Botana' is a valid meal_type and must be preserved there.
    assert cleaned["meal_type"] == ["Comida", "Botana"]


def test_sanitize_coerces_english_then_keeps():
    data = _minimal_tag_data(course=["Main Dish", "Dessert"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["course"] == ["Plato Principal", "Postre"]


def test_sanitize_dedupes_and_drops_unknown():
    data = _minimal_tag_data(course=["Postre", "Postre", "Totally Unknown"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["course"] == ["Postre"]


def test_sanitize_coerces_health_nutrition_to_spanish():
    data = _minimal_tag_data(
        health_nutrition=["Keto-Friendly", "Low Carb"],  # legacy English input
    )
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["health_nutrition"] == ["Apto para Keto", "Bajo en Carbohidratos"]


def test_sanitize_leaves_open_fields_untouched():
    data = _minimal_tag_data(key_ingredient=["Nuez", "Canela"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["key_ingredient"] == ["Nuez", "Canela"]


def test_primary_protein_species_coerced_to_pescado():
    # 'Atún' is a required-scalar value that is not in the vocabulary; it must be
    # coerced to the canonical 'Pescado' bucket to avoid a hard DQ error.
    data = _minimal_tag_data(primary_protein="Atún", protein=["Atún", "Camarón"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["primary_protein"] == "Pescado"
    assert cleaned["protein"] == ["Pescado", "Camarón"]


def test_protein_list_dedupes_after_alias():
    data = _minimal_tag_data(protein=["Atún", "Pescado", "Salmón"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["protein"] == ["Pescado"]


def test_inherited_protein_species_coerced_and_deduped():
    inherited = vocab.normalize_inherited_tags_data({"protein": ["Atún", "Pescado"], "primary_protein": "Salmón"})
    assert inherited["protein"] == ["Pescado"]
    assert inherited["primary_protein"] == "Pescado"


def test_primary_protein_puerco_coerced_to_cerdo():
    data = _minimal_tag_data(primary_protein="Puerco", protein=["Pollo", "Puerco"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["primary_protein"] == "Cerdo"
    assert cleaned["protein"] == ["Pollo", "Cerdo"]


def test_invalid_kid_friendly_scalar_dropped():
    data = _minimal_tag_data(kid_friendly="Medio", spiciness="Medio")
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["kid_friendly"] is None
    assert cleaned["spiciness"] == "Medio"


def test_sanitized_tags_do_not_leak_untranslated_into_localized():
    data = _minimal_tag_data(course=["Plato Principal", "Botana"], meal_type=["Botana"])
    tags = RecipeTagSet(**vocab.sanitize_recipe_tags_data(data))
    localized = localize_tag_set(tags)
    # No Spanish 'Botana' should survive in the English course field.
    assert "Botana" not in localized.course
    assert localized.course == ["Main Dish"]
    assert localized.meal_type == ["Snack"]


def test_health_nutrition_localizes_to_english():
    tags = RecipeTagSet(
        **_minimal_tag_data(
            health_nutrition=["Apto para Keto", "Bajo en Carbohidratos", "Alto en Proteína"],
        )
    )
    localized = localize_tag_set(tags)
    assert localized.health_nutrition == ["Keto-Friendly", "Low Carb", "High Protein"]


def test_localize_open_fields_via_llm_fallback():
    tags = RecipeTagSet(
        **_minimal_tag_data(
            key_ingredient=["Nuez", "Canela", "Jitomate"],
        )
    )
    mock_response = TagTranslations(
        translations=[
            TagTranslation(es="Nuez", en="Walnut"),
            TagTranslation(es="Canela", en="Cinnamon"),
        ]
    )

    with patch("mexipes.stages.localize.call_llm", return_value=mock_response):
        localized = localize_tag_set(tags)

    assert localized.key_ingredient == ["Walnut", "Cinnamon", "Tomato"]


def test_localize_skips_llm_when_no_open_field_leftovers():
    tags = RecipeTagSet(
        **_minimal_tag_data(
            course=["Plato Principal"],
            key_ingredient=["Jitomate", "Aguacate"],
        )
    )

    with patch("mexipes.stages.localize.call_llm") as mock_llm:
        localized = localize_tag_set(tags)
        mock_llm.assert_not_called()

    assert localized.key_ingredient == ["Tomato", "Avocado"]
