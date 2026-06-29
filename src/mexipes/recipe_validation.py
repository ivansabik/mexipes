"""Shared heuristics for detecting non-recipe extractions."""

from __future__ import annotations

import re

from mexipes.schemas.publication import RecipeIndexEntry
from mexipes.text_utils import fold_text, normalize_dual_line_title, normalize_extracted_text, normalize_title_es

PLACEHOLDER_INGREDIENTS = "Ingredientes implícitos en la técnica / Ver instrucciones"
MIN_SUBSTANTIVE_INSTRUCTION_LEN = 25
INDEX_PAGE_TOLERANCE = 3

# Spanish imperative cooking verbs commonly used in recipe instructions.
COOKING_IMPERATIVE_PATTERN = re.compile(
    r"\b("
    r"mezcl\w+|pon\w+|calient\w+|añad\w+|cuez\w+|frí\w+|horné\w+|viert\w+|"
    r"incorpor\w+|retir\w+|sirv\w+|precalient\w+|extiend\w+|form\w+|cort\w+|"
    r"pel\w+|pic\w+|remov\w+|sal\w+|dej\w+|cuec\w+|sofrí\w+|tuest\w+|ase\w+|"
    r"introduc\w+|tritur\w+|exprim\w+|escurr\w+|apíl\w+|cubr\w+|reserve\w+|"
    r"repart\w+|adorn\w+|rocí\w+|espolvore\w+|horne\w+|cuele\w+|pase\w+"
    r")\b",
    re.IGNORECASE,
)

NARRATIVE_MARKERS = (
    "durante siglos",
    "se practicaba",
    "consumía",
    "arqueológic",
    "sin duda",
    "ancestral",
    "se conoce con exactitud",
    "nixtamalización",
    "pruebas arqueológicas",
    "primero se nixtamalizaban",
    "la preparación de tortillas consumía",
)


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


def is_editorial_extraction(
    ingredients: str | None,
    instructions: str | None,
    yields: str | None = None,
) -> bool:
    """Return True when extraction looks like editorial/intro prose, not a recipe.

    Distinguishes narrative essays (historical context, no cooking steps) from
    genuine recipes with imperative preparation instructions.
    """
    instr = (instructions or "").strip()
    if not instr:
        return True

    imperative_count = len(COOKING_IMPERATIVE_PATTERN.findall(instr))
    narrative_hits = sum(1 for marker in NARRATIVE_MARKERS if marker in fold_text(instr))

    # Strong recipe signal: multiple imperative verbs and yields present
    if imperative_count >= 2:
        return False
    if imperative_count >= 1 and (yields or "").strip():
        return False

    # Strong editorial signal: narrative markers without cooking imperatives
    if narrative_hits >= 2 and imperative_count == 0:
        return True
    return narrative_hits >= 1 and imperative_count == 0 and not (yields or "").strip()


def _title_fuzzy_match(extracted_folded: str, index_folded: str) -> bool:
    if extracted_folded == index_folded:
        return True
    if extracted_folded in index_folded or index_folded in extracted_folded:
        return True
    if " - " in index_folded:
        short_part, long_part = index_folded.split(" - ", 1)
        if extracted_folded in (short_part, long_part):
            return True
        if short_part in extracted_folded or long_part in extracted_folded:
            return True
    return False


def matches_recipe_index(
    title: str,
    page: int | None,
    recipe_index: list[RecipeIndexEntry],
    *,
    page_tolerance: int = INDEX_PAGE_TOLERANCE,
) -> bool:
    """Return True when title/page fuzzy-match an entry in the recipe index."""
    if not recipe_index:
        return True
    if page is None:
        return False

    extracted_folded = fold_text(title)
    for entry in recipe_index:
        if entry.page is None:
            continue
        if abs(entry.page - page) > page_tolerance:
            continue
        if _title_fuzzy_match(extracted_folded, fold_text(entry.title)):
            return True
    return False


def resolve_index_title(
    title: str,
    page: int | None,
    recipe_index: list[RecipeIndexEntry],
    *,
    page_tolerance: int = INDEX_PAGE_TOLERANCE,
) -> str:
    """Return canonical index title when a fuzzy match exists, else the given title."""
    if not recipe_index or page is None:
        return title

    extracted_folded = fold_text(title)
    for entry in recipe_index:
        if entry.page is None:
            continue
        if abs(entry.page - page) > page_tolerance:
            continue
        if _title_fuzzy_match(extracted_folded, fold_text(entry.title)):
            return entry.title
    return title


def filter_index_entries_for_chunk(
    recipe_index: list[RecipeIndexEntry],
    chunk_start: int,
    chunk_end: int,
    *,
    overlap: int = 1,
) -> list[RecipeIndexEntry]:
    """Return index entries whose page falls within the chunk range (1-based, inclusive)."""
    # Extend range by overlap pages on each side for boundary recipes
    lo = max(1, chunk_start + 1 - overlap)
    hi = chunk_end + overlap
    return [e for e in recipe_index if e.page is not None and lo <= e.page <= hi]


def format_index_context(entries: list[RecipeIndexEntry]) -> str:
    """Format recipe index entries for injection into extraction prompt context."""
    if not entries:
        return ""
    lines = [
        "**RECIPE INDEX (authoritative)**:",
        "- Only extract recipes that appear in this index for pages in this chunk.",
        '- Use the index title exactly (including " - " separator when present).',
        "- Skip any page content NOT listed in the index (intro essays, chapter openers).",
        "- Index entries for this chunk:",
    ]
    for entry in entries:
        section = f" [{entry.section}]" if entry.section else ""
        lines.append(f"  - p{entry.page}: {entry.title}{section}")
    return "\n".join(lines)


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
    title = normalize_dual_line_title(title)
    return (
        normalize_title_es(title),
        normalize_extracted_text(ingredients),
        normalize_extracted_text(instructions),
    )
