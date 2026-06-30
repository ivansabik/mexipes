"""Tag-overlap recipe similarity (content-based, no ML).

Scores recipe-to-recipe similarity from the slug-normalized tag set produced at
export time:

    score(A, B) =
      0.40 * jaccard(dish_format)
    + 0.20 * match(region)
    + 0.15 * match(primary_protein)
    + 0.15 * jaccard(key_ingredient)
    + 0.10 * jaccard(cooking_method)

Candidate generation uses an in-memory inverted index over high-signal fields.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mexipes.schemas import tag_vocabularies as vocab

logger = logging.getLogger(__name__)

_WEIGHTS = {
    "dish_format": 0.40,
    "region": 0.20,
    "primary_protein": 0.15,
    "key_ingredient": 0.15,
    "cooking_method": 0.10,
}

_BLOCKING_FIELDS = (
    "dish_format",
    "primary_protein",
    "region",
    "key_ingredient",
    "cooking_method",
)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _match(a: set[str], b: set[str]) -> float:
    """1.0 if both are non-empty and identical, else 0.0 (scalar fields)."""
    return 1.0 if a and a == b else 0.0


def _slug_sets(tag_data: dict | None) -> dict[str, set[str]]:
    if not tag_data:
        return {}
    return {field: set(slugs) for field, slugs in vocab.slug_map_for(tag_data).items()}


def score_pair(a: dict[str, set[str]], b: dict[str, set[str]]) -> float:
    """Weighted similarity between two slug-set maps (see module docstring)."""
    score = _WEIGHTS["dish_format"] * _jaccard(a.get("dish_format", set()), b.get("dish_format", set()))
    score += _WEIGHTS["region"] * _match(a.get("region", set()), b.get("region", set()))
    score += _WEIGHTS["primary_protein"] * _match(a.get("primary_protein", set()), b.get("primary_protein", set()))
    score += _WEIGHTS["key_ingredient"] * _jaccard(a.get("key_ingredient", set()), b.get("key_ingredient", set()))
    score += _WEIGHTS["cooking_method"] * _jaccard(a.get("cooking_method", set()), b.get("cooking_method", set()))
    return score


def compute_similar(recipes: list[dict], top_n: int = 10) -> dict[str, list[dict]]:
    """Compute top-N similar recipes for each recipe in an export list."""
    keys: list[str] = []
    titles: list[str] = []
    slug_maps: list[dict[str, set[str]]] = []

    for r in recipes:
        keys.append(f"{r.get('publication_id')}:{r.get('recipe_id')}")
        titles.append(r.get("title") or "")
        slug_maps.append(_slug_sets(r.get("tags")))

    inverted: dict[tuple[str, str], list[int]] = {}
    for idx, smap in enumerate(slug_maps):
        for field in _BLOCKING_FIELDS:
            for slug in smap.get(field, set()):
                inverted.setdefault((field, slug), []).append(idx)

    results: dict[str, list[dict]] = {}
    for i, smap in enumerate(slug_maps):
        candidates: set[int] = set()
        for field in _BLOCKING_FIELDS:
            for slug in smap.get(field, set()):
                candidates.update(inverted.get((field, slug), ()))
        candidates.discard(i)

        scored: list[tuple[float, int]] = []
        for j in candidates:
            s = score_pair(smap, slug_maps[j])
            if s > 0:
                scored.append((s, j))

        scored.sort(key=lambda t: (-t[0], keys[t[1]]))
        results[keys[i]] = [{"key": keys[j], "title": titles[j], "score": round(s, 4)} for s, j in scored[:top_n]]

    return results


def write_similar_from_export(
    export_path: Path,
    output_path: Path | None = None,
    top_n: int = 10,
) -> Path:
    """Read a consolidated export JSON and write a ``similar_recipes`` index."""
    export_path = Path(export_path)
    recipes = json.loads(export_path.read_text(encoding="utf-8"))
    if not isinstance(recipes, list):
        raise ValueError(f"Expected a list of recipes in {export_path}")

    similar = compute_similar(recipes, top_n=top_n)

    if output_path is None:
        output_path = export_path.with_name(f"{export_path.stem}_similar.json")
    output_path = Path(output_path)
    output_path.write_text(json.dumps(similar, indent=4, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Similarity index for {len(similar)} recipes written to {output_path}")
    return output_path
