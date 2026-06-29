"""Shared heuristics for detecting non-recipe extractions."""

from mexipes.text_utils import normalize_extracted_text, normalize_title_es

PLACEHOLDER_INGREDIENTS = "Ingredientes implícitos en la técnica / Ver instrucciones"
MIN_SUBSTANTIVE_INSTRUCTION_LEN = 25


def is_non_recipe_extraction(ingredients: str | None, instructions: str | None) -> bool:
    """Return True when extraction looks like a section header, not a real recipe.

    Matches program/section titles with placeholder ingredients and very short
    instructions (e.g. 'MODALIDAD CALIENTE'). Genuine base preparations have
    substantial instructions and are not dropped.
    """
    instr = (instructions or "").strip()
    if len(instr) >= MIN_SUBSTANTIVE_INSTRUCTION_LEN:
        return False

    ing = (ingredients or "").strip()
    if not ing:
        return True
    return ing.lower() == PLACEHOLDER_INGREDIENTS.lower()


def is_empty_recipe_extraction(ingredients: str | None, instructions: str | None) -> bool:
    """Return True when either ingredients or instructions are missing after strip."""
    return not (ingredients or "").strip() or not (instructions or "").strip()


def is_valid_box_2d(box_2d: list[int] | None) -> bool:
    """Return True when box_2d is [ymin, xmin, ymax, xmax] in [0, 1000] with positive area."""
    if not box_2d or len(box_2d) != 4:
        return False
    ymin, xmin, ymax, xmax = box_2d
    if not all(isinstance(v, int) and 0 <= v <= 1000 for v in box_2d):
        return False
    return ymax > ymin and xmax > xmin


# A crop whose area is this fraction (or more) covered by page text is treated as
# "bounding text" — i.e. a full-bleed background photo with the recipe printed on
# top, where any crop necessarily includes the title/ingredients/instructions.
#
# Calibrated against the sample corpus: genuine "background photo with the whole
# recipe overlaid" pages cover ~0.34+ of the crop with text, whereas a real framed
# food photo whose box merely extends too far and clips a column of text sits around
# ~0.10-0.15. 0.25 sits in the gap so it drops the former and keeps the latter.
TEXT_BOUND_AREA_THRESHOLD = 0.25


def _box_area(box: tuple[int, int, int, int] | list[int]) -> int:
    ymin, xmin, ymax, xmax = box
    return max(0, ymax - ymin) * max(0, xmax - xmin)


def _intersection_area(a: list[int], b: tuple[int, int, int, int] | list[int]) -> int:
    ay0, ax0, ay1, ax1 = a
    by0, bx0, by1, bx1 = b
    iy = max(0, min(ay1, by1) - max(ay0, by0))
    ix = max(0, min(ax1, bx1) - max(ax0, bx0))
    return iy * ix


def box_text_overlap_fraction(box_2d: list[int], text_rects: list[tuple[int, int, int, int]]) -> float:
    """Fraction of the crop box's area covered by overlapping text rectangles.

    ``box_2d`` and each entry of ``text_rects`` are ``[ymin, xmin, ymax, xmax]``
    normalized to a 0-1000 grid. Overlapping text rects may slightly overcount,
    which is acceptable for a conservative "contains text" signal.
    """
    crop_area = _box_area(box_2d)
    if crop_area <= 0:
        return 0.0
    covered = sum(_intersection_area(box_2d, rect) for rect in text_rects)
    return min(1.0, covered / crop_area)


def crop_bounds_text(
    box_2d: list[int] | None,
    text_rects: list[tuple[int, int, int, int]],
    threshold: float = TEXT_BOUND_AREA_THRESHOLD,
) -> bool:
    """Return True when a crop box overlaps page text enough to be "bounding text".

    Catches full-bleed background photographs that have the recipe's title,
    ingredients, or instructions printed on top: any crop of such a page would
    necessarily include that text, so it is not a usable standalone food photo.
    A small caption or page number inside an otherwise-photographic crop stays
    well under ``threshold`` and is preserved.
    """
    if not box_2d or len(box_2d) != 4 or not text_rects:
        return False
    return box_text_overlap_fraction(box_2d, text_rects) >= threshold


def normalize_extracted_recipe_fields(
    *,
    title: str,
    ingredients: str,
    instructions: str,
) -> tuple[str, str, str]:
    """Apply deterministic cleanup to extracted recipe text fields."""
    return (
        normalize_title_es(title),
        normalize_extracted_text(ingredients),
        normalize_extracted_text(instructions),
    )
