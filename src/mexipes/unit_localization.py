"""Heuristics for detecting suspicious unit conversions during localization."""

from __future__ import annotations

import re

# Spanish cup abbreviation (taza) — standalone T or taza, not tbsp (cda).
_TAZA_QTY = re.compile(
    r"(?P<qty>\d+(?:\s+\d+/\d+|\d+/\d+)?|\d+/\d+)\s*(?:T\b|taza(?:s)?)",
    re.IGNORECASE,
)
_QUART_GALLON_EN = re.compile(
    r"(?P<qty>\d+(?:\s+\d+/\d+|\d+/\d+)?|\d+/\d+)\s*(?:quarts?|gallons?)\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-záéíóúñ]{4,}", re.IGNORECASE)


def _tokens(line: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD.finditer(line)}


def _lines_share_context(es_line: str, en_line: str) -> bool:
    return bool(_tokens(es_line) & _tokens(en_line))


def find_suspicious_volume_upgrades(ingredients_es: str, ingredients_en: str) -> list[str]:
    """Return messages when taza/T quantities appear upgraded to quart/gallon in English."""
    if not ingredients_es or not ingredients_en:
        return []

    es_lines = [ln.strip() for ln in ingredients_es.splitlines() if ln.strip()]
    en_lines = [ln.strip() for ln in ingredients_en.splitlines() if ln.strip()]
    issues: list[str] = []

    if len(es_lines) == len(en_lines):
        for es_line, en_line in zip(es_lines, en_lines, strict=True):
            if not _TAZA_QTY.search(es_line):
                continue
            m_en = _QUART_GALLON_EN.search(en_line)
            if m_en:
                issues.append(f"T/taza line mapped to quart/gallon: '{es_line[:60]}' -> '{en_line[:60]}'")
        return issues

    for es_line in es_lines:
        m_es = _TAZA_QTY.search(es_line)
        if not m_es:
            continue
        qty = m_es.group("qty")
        qty_pat = re.escape(qty).replace(r"\ ", r"\s+")
        for en_line in en_lines:
            if not re.search(rf"\b{qty_pat}\s*(?:quarts?|gallons?)\b", en_line, re.IGNORECASE):
                continue
            if _lines_share_context(es_line, en_line):
                issues.append(f"T/taza quantity '{qty}' maps to quart/gallon: '{es_line[:50]}' -> '{en_line[:50]}'")
                break

    return issues
