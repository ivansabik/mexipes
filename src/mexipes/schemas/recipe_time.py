"""Canonical total-time buckets for recipe fields (not tags).

Values are Spanish-first ``(slug, es, en)`` tuples, matching the former tag
vocabulary plus uncertainty labels.
"""

from __future__ import annotations

TimeTerm = tuple[str, str, str]  # (slug, es, en)

TOTAL_TIME: list[TimeTerm] = [
    ("under-30-min", "Menos de 30 min", "Under 30 min"),
    ("30-60-min", "30-60 min", "30-60 min"),
    ("1-2-hours", "1-2 horas", "1-2 hours"),
    ("2-plus-hours", "2+ horas", "2+ hours"),
    ("unknown", "Desconocido", "Unknown"),
    ("not-applicable", "N/A", "N/A"),
]

_ES_VALUES = {es for _, es, _ in TOTAL_TIME}
_EN_VALUES = {en for _, _, en in TOTAL_TIME}
_ES_TO_EN = {es: en for _, es, en in TOTAL_TIME}
_EN_TO_ES = {en: es for _, es, en in TOTAL_TIME}
_ES_TO_SLUG = {es: slug for slug, es, _ in TOTAL_TIME}


def es_values() -> set[str]:
    return set(_ES_VALUES)


def en_values() -> set[str]:
    return set(_EN_VALUES)


def es_to_en(value_es: str | None) -> str | None:
    if value_es is None:
        return None
    return _ES_TO_EN.get(value_es, value_es)


def slug_for(value_es: str | None) -> str | None:
    if not value_es:
        return None
    return _ES_TO_SLUG.get(value_es)


def bilingual_entry(value_es: str | None, value_en: str | None = None) -> dict[str, str] | None:
    if not value_es:
        return None
    dict_en = _ES_TO_EN.get(value_es, value_es)
    final_en = value_en if (dict_en == value_es and value_en is not None) else dict_en
    return {
        "slug": _ES_TO_SLUG.get(value_es, _fallback_slug(value_es)),
        "es": value_es,
        "en": final_en,
    }


def normalize_total_time(value: str | None) -> str | None:
    """Coerce a Spanish or English label into the canonical Spanish bucket."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped in _ES_VALUES:
        return stripped
    if stripped in _EN_TO_ES:
        return _EN_TO_ES[stripped]
    return "Desconocido"


def _fallback_slug(value: str) -> str:
    out = []
    for ch in value.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in " /_":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")
