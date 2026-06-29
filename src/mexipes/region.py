"""Resolve recipe region from publication metadata when recipe-level region is absent."""

from mexipes.inherited_tags import region_claim_supported
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.publication import PublicationMetadata
from mexipes.text_utils import fold_text

_CANONICAL_REGIONS = vocab.es_values("region")
_CANONICAL_BY_FOLD = {fold_text(name): name for name in _CANONICAL_REGIONS}

# Values that must never be stored as a recipe region (prompt forbids these).
_JUNK_REGION_FOLDS = frozenset(
    {
        "mexico",
        "mexicana",
        "republica mexicana",
        "todas",
        "norte",
        "centro",
        "noroeste",
        "sureste",
        "occidente",
        "mesa del centro",
        "centro occidente",
        "zona centro",
    }
)

# Explicit aliases (folded key -> canonical Spanish label).
_REGION_ALIASES: dict[str, str] = {
    "distrito federal": "Ciudad de México",
    "d f": "Ciudad de México",
    "df": "Ciudad de México",
    "cdmx": "Ciudad de México",
    "n l": "Nuevo León",
    "nl": "Nuevo León",
}

# High-frequency city/locality -> state (folded key -> canonical state).
_CITY_TO_STATE: dict[str, str] = {
    "monterrey": "Nuevo León",
    "acapulco": "Guerrero",
    "jalcomulco": "Veracruz",
    "xalapa": "Veracruz",
    "zongolica": "Veracruz",
    "jerez": "Zacatecas",
    "los chenes": "Campeche",
    "matlatzinco": "Estado de México",
    "las varas": "Nayarit",
    "mina": "Nuevo León",
    "chacala": "Nayarit",
    "santa maria la ribera": "Ciudad de México",
    "camino real": "Jalisco",
    "othon p blanco": "Quintana Roo",
}


def _is_null_like(value: str | None) -> bool:
    """Return True if a string value is empty, None, or a literal null placeholder."""
    if value is None:
        return True
    return value.strip().lower() in ("", "null", "none", "n/a")


def _lookup_canonical(folded: str) -> str | None:
    if folded in _JUNK_REGION_FOLDS:
        return None
    if folded in _CANONICAL_BY_FOLD:
        return _CANONICAL_BY_FOLD[folded]
    if folded in _REGION_ALIASES:
        return _REGION_ALIASES[folded]
    if folded in _CITY_TO_STATE:
        return _CITY_TO_STATE[folded]
    return None


def normalize_region(value: str | None) -> str | None:
    """Coerce a raw region string to a canonical Mexican state label, or None if invalid.

    Layers (in order):
    1. Exact canonical match
    2. Case/accent fold against canonical labels
    3. ``City, State`` suffix extraction
    4. Explicit aliases (e.g. Distrito Federal -> Ciudad de México)
    5. City -> state gazetteer for frequent localities
    6. Junk/macro-zone rejection -> None
    """
    if _is_null_like(value):
        return None

    stripped = value.strip()
    if stripped in _CANONICAL_REGIONS:
        return stripped

    folded = fold_text(stripped)
    resolved = _lookup_canonical(folded)
    if resolved:
        return resolved

    if "," in stripped:
        suffix = stripped.split(",")[-1].strip()
        suffix_resolved = _lookup_canonical(fold_text(suffix))
        if suffix_resolved:
            return suffix_resolved

        city_part = stripped.split(",")[0].strip()
        city_resolved = _lookup_canonical(fold_text(city_part))
        if city_resolved:
            return city_resolved

    return None


def _region_from_sections(page_start: int | None, metadata: PublicationMetadata) -> str | None:
    if page_start is None:
        return None
    for sec in metadata.regional_sections:
        if page_start < sec.page_start:
            continue
        if sec.page_end is not None and page_start > sec.page_end:
            continue
        return sec.region_name
    return None


def resolve_region(
    recipe_region: str | None,
    *,
    page_start: int | None,
    metadata: PublicationMetadata,
) -> str | None:
    """Fill null recipe region from publication metadata.

    Priority (matches extract_recipes.md):
    1. Recipe-level region if present (normalized to canonical state)
    2. ``regional_sections`` match on ``page_start``
    3. ``inherited_tags.region`` book-wide fallback
    """
    normalized = normalize_region(recipe_region)
    if normalized:
        return normalized

    section_region = _region_from_sections(page_start, metadata)
    if section_region:
        coerced = vocab.normalize_value_to_es("region", section_region)
        return normalize_region(coerced)

    inherited = metadata.inherited_tags.region
    if not _is_null_like(inherited) and region_claim_supported(metadata):
        coerced = vocab.normalize_value_to_es("region", inherited)
        return normalize_region(coerced)

    return None
