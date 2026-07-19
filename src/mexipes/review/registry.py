from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reviewer:
    """Configuration for one single-shot quality reviewer."""

    name: str
    persona: str
    prompt_file: str
    required_stages: tuple[str, ...]
    needs_pdf: bool
    guidelines: tuple[str, ...]


REVIEWERS: dict[str, Reviewer] = {
    "extraction": Reviewer(
        name="extraction",
        persona="meticulous Spanish recipe extraction auditor and OCR/layout specialist",
        prompt_file="review_recipe.md",
        required_stages=("extracted",),
        needs_pdf=True,
        guidelines=(
            "Compare extracted.json against the attached source PDF pages for this recipe.",
            "Check whether the extraction is a complete recipe, not a section header or editorial prose.",
            "Flag OCR artifacts: broken hyphenation, impossible words, stray headers, or meaning-changing accent errors.",
            "Flag missing content and wrong page continuation by checking ingredients/instructions against the PDF.",
            "Check image metadata against the page: images_count, image_crops, and crops that include text/decorations.",
            (
                "Page fields are 1-based PDF document indices (file page 1 = first PDF page), never printed "
                "book/footer page numbers. Do NOT flag `page_start`/`page_end` when they differ from a "
                "printed corner/footer number or from a `recipe_index[].page` that merely echoes the ToC "
                "book page. Attached PDF pages were sliced by `page_start`/`page_end` — if the recipe "
                "text is on those attachments, the page fields are correct."
            ),
            "Prefer concrete evidence over speculation; cite PDF page and exact text when possible.",
        ),
    ),
    "fidelity": Reviewer(
        name="fidelity",
        persona="copyright-compliance editor and bilingual culinary data auditor",
        prompt_file="review_recipe.md",
        required_stages=("extracted", "rewritten"),
        needs_pdf=True,
        guidelines=(
            "Compare extracted.json to rewritten.json and the attached source PDF pages.",
            "Ingredients must remain verbatim in Spanish.",
            "Instructions must preserve the same steps, order, techniques, quantities, and functional details.",
            "Rewritten text must not add tips, serving suggestions, commentary, or invented details.",
            "Title, yield, and total time must not drift. When extracted total_time is null, rewritten may legitimately show `Desconocido` after inference — that is not rewrite drift.",
        ),
    ),
    "taxonomy": Reviewer(
        name="taxonomy",
        persona="Mexican culinary taxonomy specialist",
        prompt_file="review_recipe.md",
        required_stages=("rewritten", "tags"),
        needs_pdf=True,
        guidelines=(
            "Review tags.json against the Spanish recipe text and attached source PDF.",
            "Focus on semantic correctness, not just vocabulary validity.",
            "Check primary_protein, dietary, course, meal_type, dish_format, cooking_method, key_ingredient, allergens, and region.",
            "Do not over-tag. Prefer canonical vocabulary and respect max list lengths.",
            "Treat inherited publication tags as context, not proof if recipe evidence contradicts them.",
        ),
    ),
    "localization": Reviewer(
        name="localization",
        persona="professional Spanish-English culinary localizer and US/Canada ingredient sourcing expert",
        prompt_file="review_recipe.md",
        required_stages=("rewritten", "localized", "substitutions"),
        needs_pdf=True,
        guidelines=(
            "Compare rewritten.json to localized.json for missing ingredients, changed quantities, skipped steps, or awkward translations.",
            "Enforce canonical total_time_en mapping: Under 30 min, 30-60 min, 1-2 hours, 2+ hours, Unknown, N/A.",
            "Review substitutions.json against the pantry philosophy: default empty; only substitute genuinely hard-to-source ingredients.",
            "Flag unnecessary substitutions and missing substitutions separately.",
        ),
    ),
}


def all_reviewer_names() -> list[str]:
    return list(REVIEWERS)


def resolve_reviewers(personas: str | None) -> list[Reviewer]:
    """Return reviewers requested by comma-separated persona names."""
    if personas is None or not personas.strip():
        return list(REVIEWERS.values())

    requested = [name.strip() for name in personas.split(",") if name.strip()]
    unknown = [name for name in requested if name not in REVIEWERS]
    if unknown:
        valid = ", ".join(all_reviewer_names())
        raise ValueError(f"Unknown review persona(s): {', '.join(unknown)}. Valid personas: {valid}")
    return [REVIEWERS[name] for name in requested]
