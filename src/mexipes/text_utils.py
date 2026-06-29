"""Deterministic text normalization for extracted and localized recipe content."""

from __future__ import annotations

import re
import unicodedata

FRACTION_MAP: dict[str, str] = {
    "½": "1/2",
    "¼": "1/4",
    "¾": "3/4",
    "⅓": "1/3",
    "⅔": "2/3",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
    "⅕": "1/5",
}

UNICODE_FRACTION_PATTERN = re.compile(r"[½¼¾⅓⅔⅛⅜⅝⅞⅕]")

SECTION_HEADER_LINE_PATTERN = re.compile(
    r"(?i)^\s*("
    r"INGREDIENTES?|PREPARACI[ÓO]N|PROCEDIMIENTO|ELABORACI[ÓO]N|"
    r"MODO DE PREPARAR|MODO DE PREPARACI[ÓO]N"
    r")\s*:?\s*\n?"
)

SECTION_HEADER_INLINE_PATTERN = re.compile(r"(?i)\b(INGREDIENTES?|PREPARACI[ÓO]N|PROCEDIMIENTO|ELABORACI[ÓO]N)\s*:")

SPANISH_TITLE_STOPWORDS = frozenset(
    {"de", "del", "la", "el", "los", "las", "con", "y", "e", "en", "a", "al", "para", "por", "o", "u"}
)

ENGLISH_TITLE_STOPWORDS = frozenset(
    {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as"}
)


def convert_unicode_fractions(text: str) -> str:
    """Replace unicode fraction characters with ASCII equivalents."""
    for uni, ascii_frac in FRACTION_MAP.items():
        text = text.replace(uni, ascii_frac)
    return text


def strip_section_headers(text: str) -> str:
    """Remove a leading section header line (INGREDIENTES:, PREPARACIÓN:, etc.)."""
    return SECTION_HEADER_LINE_PATTERN.sub("", text, count=1).strip()


def normalize_extracted_text(text: str) -> str:
    """Apply fraction conversion and header stripping to extracted recipe text."""
    return strip_section_headers(convert_unicode_fractions(text))


def has_unicode_fractions(text: str | None) -> bool:
    """Return True if text still contains unicode fraction characters."""
    return bool(UNICODE_FRACTION_PATTERN.search(text or ""))


def has_section_headers(text: str | None) -> bool:
    """Return True if text contains leftover section header labels."""
    if not text:
        return False
    t = text.strip()
    # Benign instructional lead-in (stripped at extraction; not a DQ issue).
    if re.match(r"(?i)^\s*modo de preparación\s*:", t):
        return False
    if SECTION_HEADER_LINE_PATTERN.match(t):
        return True
    return bool(SECTION_HEADER_INLINE_PATTERN.search(t))


def _is_all_caps(title: str) -> bool:
    """Return True when every alphabetic character in the title is uppercase."""
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return False
    return all(c.isupper() for c in letters)


def _title_case_words(title: str, stopwords: frozenset[str]) -> str:
    words = title.split()
    result: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in stopwords:
            result.append(word[:1].upper() + word[1:].lower() if word else word)
        else:
            result.append(word.lower())
    return " ".join(result)


def normalize_title_es(title: str) -> str:
    """Title-case a Spanish recipe title when it is fully uppercase."""
    if not _is_all_caps(title):
        return title
    return _title_case_words(title, SPANISH_TITLE_STOPWORDS)


def normalize_title_en(title: str) -> str:
    """Title-case an English recipe title when it is fully uppercase."""
    if not _is_all_caps(title):
        return title
    return _title_case_words(title, ENGLISH_TITLE_STOPWORDS)


def fold_text(value: str) -> str:
    """Accent-insensitive lowercase fold for matching."""
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().strip()


def normalize_dual_line_title(title: str) -> str:
    """Normalize title separators from dual-line headers (e.g. 'A / B' -> 'A - B')."""
    title = title.strip()
    if " / " in title:
        title = title.replace(" / ", " - ")
    # Collapse repeated separators
    while " -  - " in title:
        title = title.replace(" -  - ", " - ")
    return title
