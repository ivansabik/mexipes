"""Data Quality (DQ) checks for extracted and processed recipe data."""

import json
import logging
from dataclasses import dataclass, field

from mexipes.inherited_tags import region_claim_supported
from mexipes.recipe_validation import is_non_recipe_extraction
from mexipes.schemas import recipe_time
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.health_nutrition_tags import VALID_HEALTH_NUTRITION_ES
from mexipes.schemas.publication import PublicationMetadata
from mexipes.schemas.recipe import (
    ExtractedRecipe,
    ImageDescriptionsResult,
    LocalizedRecipe,
    RewrittenRecipe,
)
from mexipes.schemas.substitutions import SubstitutionsResult
from mexipes.schemas.tags import RecipeTagSet
from mexipes.storage import RecipeStore
from mexipes.text_utils import has_section_headers, has_unicode_fractions

logger = logging.getLogger(__name__)

# Stage name → Pydantic model mapping
STAGE_MODELS: dict[str, type] = {
    "extracted": ExtractedRecipe,
    "rewritten": RewrittenRecipe,
    "images_described": ImageDescriptionsResult,
    "localized": LocalizedRecipe,
    "tags": RecipeTagSet,
    "localized_tags": RecipeTagSet,
    "substitutions": SubstitutionsResult,
}

# Spanish canonical sets (tags stage) and English canonical sets (localized_tags).
VALID_SPICINESS = vocab.es_values("spiciness")
VALID_DIFFICULTY = vocab.es_values("difficulty")
VALID_TOTAL_TIME_ES = recipe_time.es_values()
VALID_TOTAL_TIME_EN = recipe_time.en_values()
VALID_BUDGET = vocab.es_values("budget")
VALID_CANONICAL_REGIONS = vocab.es_values("region")

# List fields whose membership is checked (as warnings), excluding open fields.
_CHECKED_LIST_FIELDS = (
    "course",
    "meal_type",
    "protein",
    "dietary",
    "cooking_method",
    "cuisine_style",
    "season",
    "dish_format",
    "preparation_style",
    "flavor_profile",
    "texture",
    "occasion",
    "pairs_well_with",
    "allergens",
    "make_ahead",
    "health_nutrition",
)


@dataclass
class DQIssue:
    """A single data quality issue."""

    publication_id: int
    recipe_id: int | None  # None for publication-level issues
    stage: str
    field: str
    severity: str  # "error" or "warning"
    message: str

    def __str__(self) -> str:
        loc = f"P{self.publication_id}"
        if self.recipe_id is not None:
            loc += f":R{self.recipe_id}"
        return f"[{self.severity.upper()}] {loc} ({self.stage}.{self.field}): {self.message}"


@dataclass
class DQReport:
    """Aggregated data quality report."""

    issues: list[DQIssue] = field(default_factory=list)
    publications_checked: int = 0
    recipes_checked: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def add(self, issue: DQIssue) -> None:
        self.issues.append(issue)

    def summary(self) -> str:
        lines = [
            f"DQ Report: {self.publications_checked} publications, {self.recipes_checked} recipes checked",
            f"  Errors: {self.error_count}",
            f"  Warnings: {self.warning_count}",
            f"  Result: {'PASS ✓' if self.passed else 'FAIL ✗'}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_null_like(value: str | None) -> bool:
    """Return True if a string value is empty, None, or the literal 'null'."""
    if value is None:
        return True
    return value.strip().lower() in ("", "null", "none", "n/a")


def _check_not_null(
    report: DQReport,
    pub_id: int,
    recipe_id: int | None,
    stage: str,
    field_name: str,
    value: str | None,
) -> None:
    if _is_null_like(value):
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field=field_name,
                severity="error",
                message="Value is null or empty",
            )
        )


def _check_min_length(
    report: DQReport,
    pub_id: int,
    recipe_id: int | None,
    stage: str,
    field_name: str,
    value: str | None,
    min_len: int,
) -> None:
    if value and len(value.strip()) < min_len:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field=field_name,
                severity="warning",
                message=f"Value too short ({len(value.strip())} chars, expected >= {min_len})",
            )
        )


def _check_enum_value(
    report: DQReport,
    pub_id: int,
    recipe_id: int | None,
    stage: str,
    field_name: str,
    value: str,
    allowed: set[str],
) -> None:
    if value not in allowed:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field=field_name,
                severity="error",
                message=f"Invalid value '{value}'. Must be one of: {sorted(allowed)}",
            )
        )


# ---------------------------------------------------------------------------
# Stage-specific validators
# ---------------------------------------------------------------------------


def _validate_publication_metadata(report: DQReport, pub_id: int, metadata: PublicationMetadata) -> None:
    stage = "metadata"
    _check_not_null(report, pub_id, None, stage, "pdf_pages", metadata.pdf_pages)
    _check_not_null(report, pub_id, None, stage, "recipes_count", metadata.recipes_count)

    inherited = metadata.inherited_tags
    for field_name in vocab.INHERITED_TAG_FIELDS:
        if field_name == "health_nutrition":
            allowed = VALID_HEALTH_NUTRITION_ES
            for tag in inherited.health_nutrition:
                if tag not in allowed:
                    report.add(
                        DQIssue(
                            publication_id=pub_id,
                            recipe_id=None,
                            stage=stage,
                            field=f"inherited_tags.{field_name}",
                            severity="warning",
                            message=f"Unknown inherited health_nutrition tag '{tag}'",
                        )
                    )
            continue
        if field_name not in vocab.VOCABULARIES:
            continue
        allowed = vocab.es_values(field_name)
        value = getattr(inherited, field_name)
        if field_name in vocab.SCALAR_FIELDS:
            if value and value not in allowed and field_name not in vocab.OPEN_FIELDS:
                report.add(
                    DQIssue(
                        publication_id=pub_id,
                        recipe_id=None,
                        stage=stage,
                        field=f"inherited_tags.{field_name}",
                        severity="warning",
                        message=f"Unknown inherited {field_name} value '{value}' (not in canonical vocabulary)",
                    )
                )
        else:
            _check_list_vocab(report, pub_id, None, stage, f"inherited_tags.{field_name}", value or [], allowed)

    # pdf_pages should be a valid integer
    try:
        pages = int(metadata.pdf_pages)
        if pages <= 0:
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=None,
                    stage=stage,
                    field="pdf_pages",
                    severity="error",
                    message=f"Invalid page count: {pages}",
                )
            )
    except ValueError:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=None,
                stage=stage,
                field="pdf_pages",
                severity="error",
                message=f"pdf_pages is not a valid integer: '{metadata.pdf_pages}'",
            )
        )


def _validate_extracted(
    report: DQReport,
    pub_id: int,
    recipe_id: int,
    recipe: ExtractedRecipe,
    *,
    expect_region: bool = False,
) -> None:
    stage = "extracted"
    _check_not_null(report, pub_id, recipe_id, stage, "title", recipe.title)
    _check_not_null(report, pub_id, recipe_id, stage, "ingredients", recipe.ingredients)
    _check_not_null(report, pub_id, recipe_id, stage, "instructions", recipe.instructions)
    _check_min_length(report, pub_id, recipe_id, stage, "ingredients", recipe.ingredients, 10)
    _check_min_length(report, pub_id, recipe_id, stage, "instructions", recipe.instructions, 20)

    if is_non_recipe_extraction(recipe.ingredients, recipe.instructions):
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="instructions",
                severity="error",
                message="Likely non-recipe extraction (section header or modality label with placeholder ingredients)",
            )
        )

    if recipe.has_multiple_recipes:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="has_multiple_recipes",
                severity="warning",
                message=(
                    "Extraction flagged multiple recipes in one record; "
                    "ingredients/instructions may be tangled and downstream quality may suffer"
                ),
            )
        )

    if expect_region and _is_null_like(recipe.region):
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="region",
                severity="warning",
                message="Region not inferred",
            )
        )

    if recipe.region and recipe.region not in VALID_CANONICAL_REGIONS:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="region",
                severity="warning",
                message=f"Non-canonical region value '{recipe.region}'",
            )
        )

    if has_unicode_fractions(recipe.ingredients) or has_unicode_fractions(recipe.instructions):
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="ingredients",
                severity="warning",
                message="Unicode fraction characters remain (expected ASCII fractions like 1/2)",
            )
        )

    if has_section_headers(recipe.ingredients) or has_section_headers(recipe.instructions):
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="ingredients",
                severity="warning",
                message="Leftover section header (INGREDIENTES:/PREPARACIÓN:) in extracted text",
            )
        )

    if recipe.images_count != len(recipe.image_crops):
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="images_count",
                severity="warning",
                message=(
                    f"images_count ({recipe.images_count}) does not match len(image_crops) ({len(recipe.image_crops)})"
                ),
            )
        )

    if recipe.total_time and recipe.total_time not in VALID_TOTAL_TIME_ES:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="total_time",
                severity="warning",
                message=f"Non-canonical total_time value '{recipe.total_time}'",
            )
        )


def _validate_rewritten(report: DQReport, pub_id: int, recipe_id: int, recipe: RewrittenRecipe) -> None:
    stage = "rewritten"
    _check_not_null(report, pub_id, recipe_id, stage, "title", recipe.title)
    _check_not_null(report, pub_id, recipe_id, stage, "ingredients", recipe.ingredients)
    _check_not_null(report, pub_id, recipe_id, stage, "instructions", recipe.instructions)
    _check_min_length(report, pub_id, recipe_id, stage, "instructions", recipe.instructions, 30)

    if not recipe.total_time:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="total_time",
                severity="warning",
                message="total_time not set (run rewrite or tag stage to infer)",
            )
        )
    elif recipe.total_time not in VALID_TOTAL_TIME_ES:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="total_time",
                severity="warning",
                message=f"Non-canonical total_time value '{recipe.total_time}'",
            )
        )


def _validate_localized(report: DQReport, pub_id: int, recipe_id: int, recipe: LocalizedRecipe) -> None:
    stage = "localized"
    _check_not_null(report, pub_id, recipe_id, stage, "title_en", recipe.title_en)
    _check_not_null(report, pub_id, recipe_id, stage, "slug", recipe.slug)
    _check_not_null(report, pub_id, recipe_id, stage, "ingredients_en", recipe.ingredients_en)
    _check_not_null(report, pub_id, recipe_id, stage, "instructions_en", recipe.instructions_en)

    # Slug format check
    if recipe.slug and " " in recipe.slug:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="slug",
                severity="error",
                message=f"Slug contains spaces: '{recipe.slug}'",
            )
        )

    if recipe.total_time_en and recipe.total_time_en not in VALID_TOTAL_TIME_EN:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="total_time_en",
                severity="warning",
                message=f"Non-canonical total_time_en value '{recipe.total_time_en}'",
            )
        )


def _check_list_vocab(
    report: DQReport,
    pub_id: int,
    recipe_id: int | None,
    stage: str,
    field_name: str,
    values: list[str],
    allowed: set[str],
) -> None:
    """Warn (do not error) on list values outside the controlled vocabulary."""
    for value in values:
        if value not in allowed:
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=recipe_id,
                    stage=stage,
                    field=field_name,
                    severity="warning",
                    message=f"Unknown {field_name} value '{value}' (not in canonical vocabulary)",
                )
            )


def _validate_tag_set(
    report: DQReport,
    pub_id: int,
    recipe_id: int,
    tags: RecipeTagSet,
    stage: str,
    lang: str,
) -> None:
    """Validate a tag set in either Spanish (``lang='es'``) or English (``lang='en'``)."""
    values_fn = vocab.es_values if lang == "es" else vocab.en_values

    # Required scalars
    _check_enum_value(report, pub_id, recipe_id, stage, "spiciness", tags.spiciness, values_fn("spiciness"))
    _check_enum_value(report, pub_id, recipe_id, stage, "difficulty", tags.difficulty, values_fn("difficulty"))
    _check_enum_value(report, pub_id, recipe_id, stage, "budget", tags.budget, values_fn("budget"))
    _check_enum_value(
        report, pub_id, recipe_id, stage, "primary_protein", tags.primary_protein, values_fn("primary_protein")
    )

    # Optional scalars (warn if set to an unknown value)
    for field_name in ("serving_size", "kid_friendly"):
        value = getattr(tags, field_name)
        if value and value not in values_fn(field_name):
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=recipe_id,
                    stage=stage,
                    field=field_name,
                    severity="warning",
                    message=f"Unknown {field_name} value '{value}' (not in canonical vocabulary)",
                )
            )

    # List fields with controlled vocab
    for field_name in _CHECKED_LIST_FIELDS:
        _check_list_vocab(
            report, pub_id, recipe_id, stage, field_name, getattr(tags, field_name), values_fn(field_name)
        )

    # Coverage warnings
    if not tags.course:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="course",
                severity="warning",
                message="No course tags assigned",
            )
        )
    if not tags.dish_format and not tags.preparation_style:
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage=stage,
                field="dish_format",
                severity="warning",
                message="No dish_format or preparation_style assigned",
            )
        )

    # health_nutrition validated via _CHECKED_LIST_FIELDS with lang-aware values_fn


def _validate_tags(report: DQReport, pub_id: int, recipe_id: int, tags: RecipeTagSet) -> None:
    _validate_tag_set(report, pub_id, recipe_id, tags, stage="tags", lang="es")


def _validate_localized_tags(report: DQReport, pub_id: int, recipe_id: int, tags: RecipeTagSet) -> None:
    _validate_tag_set(report, pub_id, recipe_id, tags, stage="localized_tags", lang="en")


def _validate_images_described(report: DQReport, pub_id: int, recipe_id: int, result: ImageDescriptionsResult) -> None:
    stage = "images_described"
    for i, desc in enumerate(result.descriptions):
        _check_not_null(report, pub_id, recipe_id, stage, f"descriptions[{i}].description", desc.description)
        _check_not_null(report, pub_id, recipe_id, stage, f"descriptions[{i}].suggested_prompt", desc.suggested_prompt)
        _check_min_length(report, pub_id, recipe_id, stage, f"descriptions[{i}].description", desc.description, 20)


def _validate_substitutions(report: DQReport, pub_id: int, recipe_id: int, result: SubstitutionsResult) -> None:
    stage = "substitutions"
    for i, sub in enumerate(result.substitutions):
        _check_not_null(report, pub_id, recipe_id, stage, f"substitutions[{i}].original", sub.original)
        _check_not_null(report, pub_id, recipe_id, stage, f"substitutions[{i}].substitute", sub.substitute)
        _check_not_null(report, pub_id, recipe_id, stage, f"substitutions[{i}].notes", sub.notes)


# ---------------------------------------------------------------------------
# Cross-stage consistency checks
# ---------------------------------------------------------------------------


def _validate_cross_stage(
    report: DQReport,
    pub_id: int,
    recipe_id: int,
    extracted: ExtractedRecipe | None,
    rewritten: RewrittenRecipe | None,
    localized: LocalizedRecipe | None,
) -> None:
    """Check consistency across stages."""
    if extracted and rewritten and extracted.title.strip().lower() != rewritten.title.strip().lower():
        report.add(
            DQIssue(
                publication_id=pub_id,
                recipe_id=recipe_id,
                stage="cross_stage",
                field="title",
                severity="warning",
                message=(f"Title changed between extraction and rewrite: '{extracted.title}' → '{rewritten.title}'"),
            )
        )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_dq_checks(
    store: RecipeStore,
    publication_id: int | None = None,
) -> DQReport:
    """Run all DQ checks across publications and recipes.

    Args:
        store: The RecipeStore instance.
        publication_id: If set, only check this publication. Otherwise check all.

    Returns:
        A DQReport with all issues found.
    """
    report = DQReport()

    publications_dir = store.data_dir / "publications"
    if not publications_dir.exists():
        return report

    # Determine which publications to check
    pub_dirs = []
    if publication_id is not None:
        pub_path = publications_dir / str(publication_id)
        if pub_path.exists():
            pub_dirs.append(pub_path)
    else:
        pub_dirs = sorted(
            [p for p in publications_dir.iterdir() if p.is_dir() and p.name.isdigit()],
            key=lambda p: int(p.name),
        )

    for pub_path in pub_dirs:
        pub_id = int(pub_path.name)
        report.publications_checked += 1

        # -- Publication-level checks --
        pub_info_path = pub_path / "publication_info.json"
        if not pub_info_path.exists():
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=None,
                    stage="publication",
                    field="publication_info.json",
                    severity="error",
                    message="Missing publication_info.json",
                )
            )
            continue

        try:
            pub_info = json.loads(pub_info_path.read_text(encoding="utf-8"))
        except Exception as e:
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=None,
                    stage="publication",
                    field="publication_info.json",
                    severity="error",
                    message=f"Failed to parse publication_info.json: {e}",
                )
            )
            continue

        if not pub_info.get("md5"):
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=None,
                    stage="publication",
                    field="md5",
                    severity="error",
                    message="Missing MD5 hash",
                )
            )

        source_pdf = pub_path / "source.pdf"
        if not source_pdf.exists():
            report.add(
                DQIssue(
                    publication_id=pub_id,
                    recipe_id=None,
                    stage="publication",
                    field="source.pdf",
                    severity="error",
                    message="Missing source.pdf file",
                )
            )

        # -- Metadata checks --
        metadata = store.load_publication_metadata(pub_id)
        if metadata:
            _validate_publication_metadata(report, pub_id, metadata)
        else:
            if pub_info.get("status") not in ("registered",):
                report.add(
                    DQIssue(
                        publication_id=pub_id,
                        recipe_id=None,
                        stage="metadata",
                        field="metadata.json",
                        severity="warning",
                        message="No metadata.json found (not yet extracted)",
                    )
                )

        # -- Recipe-level checks --
        recipes_dir = pub_path / "recipes"
        if not recipes_dir.exists():
            continue

        for recipe_path in sorted(
            recipes_dir.iterdir(),
            key=lambda p: int(p.name) if p.name.isdigit() else 999999,
        ):
            if not recipe_path.is_dir() or not recipe_path.name.isdigit():
                continue
            recipe_id = int(recipe_path.name)
            report.recipes_checked += 1

            # Check status file exists
            status_file = recipe_path / "status.json"
            if not status_file.exists():
                report.add(
                    DQIssue(
                        publication_id=pub_id,
                        recipe_id=recipe_id,
                        stage="status",
                        field="status.json",
                        severity="warning",
                        message="Missing status.json file",
                    )
                )

            # Load and validate each stage output
            extracted = store.load_stage_output(pub_id, recipe_id, "extracted", ExtractedRecipe)
            rewritten = store.load_stage_output(pub_id, recipe_id, "rewritten", RewrittenRecipe)
            localized = store.load_stage_output(pub_id, recipe_id, "localized", LocalizedRecipe)
            tags = store.load_stage_output(pub_id, recipe_id, "tags", RecipeTagSet)
            localized_tags = store.load_stage_output(pub_id, recipe_id, "localized_tags", RecipeTagSet)
            images_desc = store.load_stage_output(pub_id, recipe_id, "images_described", ImageDescriptionsResult)
            substitutions = store.load_stage_output(pub_id, recipe_id, "substitutions", SubstitutionsResult)

            if not extracted:
                report.add(
                    DQIssue(
                        publication_id=pub_id,
                        recipe_id=recipe_id,
                        stage="extracted",
                        field="extracted.json",
                        severity="error",
                        message="Missing extracted.json — recipe has no base data",
                    )
                )
                continue

            _validate_extracted(
                report,
                pub_id,
                recipe_id,
                extracted,
                expect_region=region_claim_supported(metadata) if metadata else False,
            )

            if rewritten:
                _validate_rewritten(report, pub_id, recipe_id, rewritten)
            if localized:
                _validate_localized(report, pub_id, recipe_id, localized)
            if tags:
                _validate_tags(report, pub_id, recipe_id, tags)
            if localized_tags:
                _validate_localized_tags(report, pub_id, recipe_id, localized_tags)
            if images_desc:
                _validate_images_described(report, pub_id, recipe_id, images_desc)
            if substitutions:
                _validate_substitutions(report, pub_id, recipe_id, substitutions)

            # Cross-stage consistency
            _validate_cross_stage(report, pub_id, recipe_id, extracted, rewritten, localized)

            # Image file consistency: check that cropped images exist if expected
            if extracted.images_count > 0:
                images_dir = recipe_path / "images"
                if not images_dir.exists():
                    report.add(
                        DQIssue(
                            publication_id=pub_id,
                            recipe_id=recipe_id,
                            stage="extracted",
                            field="images",
                            severity="warning",
                            message=f"Expected {extracted.images_count} images but images/ directory is missing",
                        )
                    )
                else:
                    image_files = [f for f in images_dir.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")]
                    if len(image_files) != extracted.images_count:
                        report.add(
                            DQIssue(
                                publication_id=pub_id,
                                recipe_id=recipe_id,
                                stage="extracted",
                                field="images",
                                severity="warning",
                                message=(
                                    f"Image count mismatch: expected {extracted.images_count}, "
                                    f"found {len(image_files)} files"
                                ),
                            )
                        )

    return report
