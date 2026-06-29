"""Tests for non-recipe extraction heuristics."""

from mexipes.recipe_validation import (
    PLACEHOLDER_INGREDIENTS,
    box_text_overlap_fraction,
    crop_bounds_text,
    is_editorial_extraction,
    is_empty_recipe_extraction,
    is_non_recipe_extraction,
    is_valid_box_2d,
    matches_recipe_index,
    normalize_extracted_recipe_fields,
    resolve_index_title,
)
from mexipes.schemas.publication import RecipeIndexEntry
from mexipes.text_utils import normalize_dual_line_title

# Text block rects (normalized 0-1000, [ymin, xmin, ymax, xmax]) from the real
# "Atole de cacao" page (data/publications/1/recipes/8): a full-bleed background
# photo with the title, yields, and ingredients/prep overlaid on top.
ATOLE_TEXT_RECTS = [
    (167, 343, 259, 657),  # title
    (263, 446, 313, 554),  # yields
    (417, 114, 805, 892),  # ingredients + preparation
]


def test_non_recipe_section_header():
    assert is_non_recipe_extraction(
        PLACEHOLDER_INGREDIENTS,
        "MODALIDAD CALIENTE",
    )


def test_base_preparation_with_long_instructions_not_dropped():
    assert not is_non_recipe_extraction(
        PLACEHOLDER_INGREDIENTS,
        "Paso 1: Mezclar los ingredientes en un recipiente grande. "
        "Paso 2: Dejar reposar durante 24 horas a temperatura ambiente.",
    )


def test_real_recipe_not_dropped():
    assert not is_non_recipe_extraction(
        "2 tazas de arroz\n1 litro de agua",
        "Lavar el arroz y cocerlo en agua hirviendo durante 20 minutos.",
    )


def test_empty_recipe_extraction():
    assert is_empty_recipe_extraction("", "Some instructions here that are long enough.")
    assert is_empty_recipe_extraction("2 tazas de arroz", "")
    assert is_empty_recipe_extraction(None, None)
    assert not is_empty_recipe_extraction(
        "2 tazas de arroz",
        "Cocer el arroz durante 20 minutos.",
    )


def test_is_valid_box_2d():
    assert is_valid_box_2d([100, 200, 500, 800])
    assert not is_valid_box_2d([100, 200, 100, 800])  # zero height
    assert not is_valid_box_2d([100, 200, 500])  # wrong length
    assert not is_valid_box_2d([100, 200, 500, 1500])  # out of range
    assert not is_valid_box_2d(None)


def test_full_page_crop_over_overlaid_text_is_dropped():
    # The full-page crop the model emitted for the Atole page must be rejected.
    assert crop_bounds_text([0, 0, 1000, 1000], ATOLE_TEXT_RECTS)


def test_side_by_side_photo_crop_is_kept():
    # Photo on the left half, recipe text on the right half: crop covers only the
    # photo and overlaps no text, so it is preserved.
    text_rects = [(100, 520, 900, 980)]
    assert not crop_bounds_text([0, 0, 1000, 500], text_rects)


def test_small_caption_inside_photo_crop_is_kept():
    # A tiny caption inside a large photographic crop stays under the threshold.
    caption = [(960, 20, 990, 200)]
    assert not crop_bounds_text([0, 0, 1000, 1000], caption)


def test_framed_photo_with_clipped_text_column_is_kept():
    # A real food photo whose box extends too far left and clips a column of
    # instruction text (~0.15 coverage, like P2 recipes) must NOT be dropped.
    crop = [470, 400, 960, 999]
    clipped_text = [(0, 400, 300, 560), (430, 400, 520, 540)]
    assert box_text_overlap_fraction(crop, clipped_text) < 0.25
    assert not crop_bounds_text(crop, clipped_text)


def test_crop_bounds_text_no_rects_or_bad_box():
    assert not crop_bounds_text([0, 0, 1000, 1000], [])
    assert not crop_bounds_text(None, ATOLE_TEXT_RECTS)
    assert not crop_bounds_text([0, 0, 1000], ATOLE_TEXT_RECTS)


def test_box_text_overlap_fraction_values():
    assert box_text_overlap_fraction([0, 0, 1000, 1000], []) == 0.0
    # A text rect fully inside the crop contributes its own area fraction.
    frac = box_text_overlap_fraction([0, 0, 1000, 1000], [(0, 0, 500, 1000)])
    assert abs(frac - 0.5) < 1e-9
    # Text entirely outside the crop contributes nothing.
    assert box_text_overlap_fraction([0, 0, 500, 500], [(0, 600, 500, 1000)]) == 0.0


def test_normalize_extracted_recipe_fields():
    title, ingredients, instructions = normalize_extracted_recipe_fields(
        title="MOLE DE OLLA",
        ingredients="INGREDIENTES:\n½ kilo de carne",
        instructions="PREPARACIÓN:\nCocer la carne.",
    )
    assert title == "Mole de Olla"
    assert ingredients == "1/2 kilo de carne"
    assert instructions == "Cocer la carne."


def test_editorial_extraction_drops_narrative_essay():
    narrative = (
        "Durante siglos las tortillas han sido el combustible de México. "
        "No se conoce con exactitud la fecha de la primera elaboración de este pan, "
        "pero las pruebas arqueológicas indican que se trata, sin duda, de un arte ancestral. "
        "Primero se nixtamalizaban los granos secos de maíz."
    )
    assert is_editorial_extraction("granos secos de maíz\nagua con cal", narrative, None)


def test_editorial_extraction_keeps_imperative_recipe():
    instructions = (
        "Mezcle la masa harina y 120 ml de agua con las manos hasta obtener una masa húmeda. "
        "Añada más agua si fuera necesario. Cúbrala y resérvela en el frigorífico."
    )
    assert not is_editorial_extraction("450 g de masa harina", instructions, "PARA 6 PERSONAS")


def test_normalize_dual_line_title_separator():
    assert normalize_dual_line_title("Chilaquiles rojos / Tortilla con chile") == (
        "Chilaquiles rojos - Tortilla con chile"
    )
    assert normalize_dual_line_title("Esquites - Granos de maíz cocidos") == ("Esquites - Granos de maíz cocidos")


def test_resolve_index_title_from_subtitle():
    index = [RecipeIndexEntry(title="Esquites - Granos de maíz cocidos", page=40)]
    assert resolve_index_title("Granos de Maíz Cocidos", 40, index) == ("Esquites - Granos de maíz cocidos")


def test_matches_recipe_index_fuzzy_subtitle():
    index = [RecipeIndexEntry(title="Gorditas - Tortitas de harina rellenas", page=39)]
    assert matches_recipe_index("Tortitas de Harina Rellenas", 39, index)
