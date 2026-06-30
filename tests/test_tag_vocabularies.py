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
        "budget": "Económico",
    }
    data.update(overrides)
    return data


def test_sanitize_drops_botana_from_course():
    data = _minimal_tag_data(
        course=["Plato Principal", "Botana"],
        meal_type="Botana",
    )
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["course"] == ["Plato Principal"]
    assert cleaned["meal_type"] == "Botana"


def test_sanitize_coerces_english_then_keeps():
    data = _minimal_tag_data(course=["Main Dish", "Dessert"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["course"] == ["Plato Principal", "Postre"]


def test_sanitize_dedupes_and_drops_unknown():
    data = _minimal_tag_data(course=["Postre", "Postre", "Totally Unknown"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["course"] == ["Postre"]


def test_sanitize_drops_unknown_key_ingredients():
    data = _minimal_tag_data(key_ingredient=["Nuez", "Canela", "Jitomate"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["key_ingredient"] == ["Jitomate"]


def test_sanitize_caps_key_ingredient_at_three():
    data = _minimal_tag_data(
        key_ingredient=["Jitomate", "Aguacate", "Cilantro", "Chile", "Masa"],
    )
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["key_ingredient"] == ["Jitomate", "Aguacate", "Cilantro"]


def test_primary_protein_species_coerced_to_pescado():
    data = _minimal_tag_data(primary_protein="Atún")
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["primary_protein"] == "Pescado"


def test_primary_protein_puerco_coerced_to_cerdo():
    data = _minimal_tag_data(primary_protein="Puerco")
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["primary_protein"] == "Cerdo"


def test_meal_type_coerced_from_legacy_list():
    data = _minimal_tag_data(meal_type=["Comida", "Cena", "Botana"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["meal_type"] == "Botana"


def test_meal_type_scalar_preserved():
    data = _minimal_tag_data(meal_type="Cena")
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["meal_type"] == "Cena"


def test_dish_format_legacy_mapped_to_antojitos():
    data = _minimal_tag_data(dish_format=["Huaraches"])
    cleaned = vocab.sanitize_recipe_tags_data(data)
    assert cleaned["dish_format"] == ["Antojitos"]


def test_sanitized_tags_do_not_leak_untranslated_into_localized():
    data = _minimal_tag_data(course=["Plato Principal", "Botana"], meal_type="Botana")
    tags = RecipeTagSet(**vocab.sanitize_recipe_tags_data(data))
    localized = localize_tag_set(tags)
    assert "Botana" not in localized.course
    assert localized.course == ["Main Dish"]
    assert localized.meal_type == "Snack"


def test_localize_open_chile_via_llm_fallback():
    tags = RecipeTagSet(
        **_minimal_tag_data(
            chile_type=["Chilcuacle", "Ancho"],
        )
    )
    mock_response = TagTranslations(
        translations=[
            TagTranslation(es="Chilcuacle", en="Chilcuacle Chile"),
        ]
    )

    with patch("mexipes.stages.localize.call_llm", return_value=mock_response):
        localized = localize_tag_set(tags)

    assert localized.chile_type == ["Chilcuacle Chile", "Ancho"]


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


def test_tag_schema_version_is_three():
    tags = RecipeTagSet(**_minimal_tag_data())
    assert tags.tag_schema_version == 3
