"""Apply triage_notes to review findings per the remediation plan."""

from __future__ import annotations

import json
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parents[1] / "data/reviews/review_20260718T182938Z_random"

PROTEIN_IN_KEY_INGREDIENT = {
    "cerdo",
    "pescado",
    "pollo",
    "puerco",
    "res",
    "cordero",
}

SUBSTITUTE_LOCALIZE_FP_TYPES = {
    "substitution_policy_error",
}


def triage_finding(f: dict) -> str | None:
    """Return triage note if finding should be discarded; None to leave unchanged."""
    key = f.get("finding_key") or ""
    field = f.get("field") or ""
    ftype = f.get("finding_type") or ""
    stage = f.get("stage") or ""
    issue = (f.get("issue") or "").lower()
    pub = f.get("publication_id")
    recipe = f.get("recipe_id")

    # Already triaged
    existing = f.get("triage_notes") or ""
    if existing and existing != "PLACEHOLDER":
        return None

    if field == "page_start" and pub == 1:
        return "Discard: PDF page index is correct; book/ToC page may differ (AGENTS.md #20)."

    if field == "total_time":
        if ftype in ("data_precision_loss", "data_granularity_loss", "imprecise_extraction"):
            return "Discard: intentional total_time bucketing; exact minutes map to canonical ranges."
        if ftype in ("rewrite_drift", "tag_semantic_error") and "desconocido" in issue and pub == 3 and recipe == 21:
            return "Discard: total_time not inferred from instruction steps by design."
        if ftype == "rewrite_drift" and pub == 1 and recipe in (4, 5, 16):
            return "Discard: 1 hora → 30-60 min and similar mappings are canonical bucket rules."
        if ftype == "missing_source_content" and pub == 3 and recipe == 36:
            return "Discard: inferred total_time from steps not supported; source had no explicit time."

    if field == "key_ingredient" and ftype == "tag_semantic_error":
        if any(p in issue for p in ("cerdo", "pescado", "pollo", "pork", "fish")):
            return "Discard: proteins belong in primary_protein, not key_ingredient."
        if "guayaba" in issue or "guava" in issue:
            return "Discard: guayaba not in key_ingredient vocab; use closest staple or leave empty."

    if stage == "substitute" and ftype in SUBSTITUTE_LOCALIZE_FP_TYPES:
        if any(w in issue for w in ("natas", "crema", "gallina", "chicken breast", "mexican crema")):
            return "Discard: localize name translation ≠ substitutions.json entry; pantry do-not-substitute."

    if field == "image_crops" and ftype == "image_crop_includes_text":
        if pub == 1 and recipe == 16:
            return "Discard: title-on-photo overlay acceptable; fix is snap-to-photo not reject overlay."
        if "nutritional" in issue or "valor nutricional" in issue:
            return "Action: crop includes nutrition table on paper — re-extract with photo-only box."

    if stage == "rewrite" and ftype == "rewrite_drift":
        if pub == 1 and recipe == 9 and "moler" in issue:
            return "Discard: functional verb change OK; no mandatory paraphrase for copyright."
        if ftype == "rewrite_drift" and not any(
            w in issue for w in ("anecdote", "headnote", "story", "omit", "dropped", "missing", "olive")
        ):
            return "Discard: style-only rewrite drift; functional steps may stay verbatim."

    if field == "total_time_en" and ftype == "tag_semantic_error" and pub == 1 and recipe == 5:
        return "Discard: 1 hora → 30-60 min bucket is canonical; localized mapping follows rewritten bucket."

    return None


def apply_triage(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    updated = 0
    if isinstance(data, list):
        findings = data
    else:
        findings = data.get("findings", [])
    for f in findings:
        note = triage_finding(f)
        if note:
            f["triage_notes"] = note
            updated += 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return updated


def main() -> None:
    total = 0
    consolidated = REVIEW_DIR / "consolidated.json"
    total += apply_triage(consolidated)
    for pub_file in REVIEW_DIR.glob("publication-*.json"):
        total += apply_triage(pub_file)
    print(f"Updated triage_notes on {total} findings")


if __name__ == "__main__":
    main()
