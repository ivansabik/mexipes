"""Sanitize publication-level inherited tags to prevent geographic hallucination."""

import re
import unicodedata

from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.publication import InheritedTags, PublicationMetadata

# Title patterns that explicitly claim a regional cookbook subject.
_REGIONAL_TITLE_PREFIXES = (
    r"cocina de ",
    r"recetario de ",
    r"gastronom[ií]a de ",
    r"platillos regionales de ",
    r"platillos de ",
    r"comida tradicional de ",
    r"recetas de ",
    r"recetas tradicionales de ",
    r"sabores de ",
    r"delicias de ",
)

_TRADICIONAL_REGIONAL = "Tradicional Regional"
_MAX_HEALTH_NUTRITION_TAGS = 3
_VEGAN_DIETARY = frozenset({"Vegano", "Vegetariano"})

# Trim geographic remainder at volume/edition markers.
_REMAINDER_TRIM = re.compile(r"[.;]|(?:\s|^)vol(?:\.|\s|\d)|(?:\s|^)m[eé]xico(?:\s|$)", re.IGNORECASE)


def _normalize_for_match(text: str) -> str:
    """Lowercase and strip accents for fuzzy title matching."""
    lowered = text.lower()
    return "".join(c for c in unicodedata.normalize("NFD", lowered) if unicodedata.category(c) != "Mn")


def _known_region_names() -> list[str]:
    return [es for _, es, _ in vocab.VOCABULARIES["region"]]


def _trim_remainder(remainder: str) -> str:
    """Drop trailing edition/volume text from the geographic phrase."""
    trimmed = _REMAINDER_TRIM.split(remainder, maxsplit=1)[0].strip()
    return trimmed.rstrip(" ,.")


def _match_region_in_text(text: str) -> str | None:
    """Return the longest known region name found at the start or within *text*."""
    normalized = _normalize_for_match(text)
    for region in sorted(_known_region_names(), key=len, reverse=True):
        region_norm = _normalize_for_match(region)
        if normalized.startswith(region_norm):
            return region
        # City+state patterns: "tacotalpa, tabasco" — match state anywhere after prefix.
        if region_norm in normalized:
            return region
    return None


def _regional_remainder(title: str | None) -> str | None:
    """Return the geographic phrase after a regional title prefix, or None."""
    if not title or not title.strip():
        return None

    normalized_title = _normalize_for_match(title)
    for prefix_pattern in _REGIONAL_TITLE_PREFIXES:
        match = re.search(prefix_pattern, normalized_title)
        if not match:
            continue
        remainder = _trim_remainder(normalized_title[match.end() :])
        if remainder and _match_region_in_text(remainder):
            return remainder
    return None


def _title_claims_region(title: str | None) -> bool:
    """Return True when the document title explicitly names a region as cuisine subject."""
    return _regional_remainder(title) is not None


def _title_implies_traditional_regional(title: str | None) -> bool:
    """Return True when the title explicitly describes regional/traditional cuisine."""
    if not title:
        return False
    normalized = _normalize_for_match(title)
    return "regionales" in normalized or "regional" in normalized or "tradicional" in normalized


def infer_region_from_title(title: str | None) -> str | None:
    """Infer canonical inherited region from a regional cookbook title.

    Returns the longest matching known region (state) from the geographic phrase,
    e.g. "platillos regionales de Tacotalpa, Tabasco" -> "Tabasco".
    """
    remainder = _regional_remainder(title)
    if not remainder:
        return None
    return _match_region_in_text(remainder)


def region_claim_supported(metadata: PublicationMetadata) -> bool:
    """Return True when metadata provides evidence the book is regionally scoped."""
    if metadata.regional_sections:
        return True
    return _title_claims_region(metadata.document_title)


def protein_inheritance_allowed(inherited: InheritedTags) -> bool:
    """Return True when publication-level protein tags may propagate to recipes."""
    if not inherited.protein:
        return False
    if len(inherited.protein) == 1:
        return True
    return bool(set(inherited.dietary) & _VEGAN_DIETARY)


def sanitize_inherited_tags(metadata: PublicationMetadata) -> InheritedTags:
    """Clear unsupported or over-broad inherited tags before they propagate to recipes."""
    inherited = metadata.inherited_tags.model_copy(deep=True)

    if not region_claim_supported(metadata):
        if inherited.region:
            inherited.region = None
        if _TRADICIONAL_REGIONAL in inherited.cuisine_style:
            inherited.cuisine_style = [style for style in inherited.cuisine_style if style != _TRADICIONAL_REGIONAL]
    else:
        if not inherited.region:
            inherited.region = infer_region_from_title(metadata.document_title)
        if (
            _title_implies_traditional_regional(metadata.document_title)
            and _TRADICIONAL_REGIONAL not in inherited.cuisine_style
        ):
            inherited.cuisine_style = [*inherited.cuisine_style, _TRADICIONAL_REGIONAL]

    if not protein_inheritance_allowed(inherited):
        inherited.protein = []

    if len(inherited.health_nutrition) > _MAX_HEALTH_NUTRITION_TAGS:
        inherited.health_nutrition = inherited.health_nutrition[:_MAX_HEALTH_NUTRITION_TAGS]

    return inherited
