"""Tag-overlap recipe similarity (content-based, no ML).

Scores recipe-to-recipe similarity from the slug-normalized tag set produced at
export time, using the weighted Jaccard formula from the plan:

    score(A, B) =
      0.35 * jaccard(dish_format)        # falls back to preparation_style if empty
    + 0.20 * jaccard(preparation_style)
    + 0.15 * jaccard(flavor_profile)
    + 0.10 * match(primary_protein)
    + 0.10 * match(region)
    + 0.10 * jaccard(key_ingredient)

Candidate generation uses an in-memory inverted index over a few high-signal
fields so we avoid a full O(n^2) scan on large corpora.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mexipes.schemas import tag_vocabularies as vocab

logger = logging.getLogger(__name__)

# Weighted components of the similarity score.
_WEIGHTS = {
    "dish_format": 0.35,
    "preparation_style": 0.20,
    "flavor_profile": 0.15,
    "primary_protein": 0.10,
    "region": 0.10,
    "key_ingredient": 0.10,
}

# Fields used to generate candidate pairs (inverted index blocking keys).
_BLOCKING_FIELDS = (
    "dish_format",
    "preparation_style",
    "primary_protein",
    "region",
    "flavor_profile",
    "key_ingredient",
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
    # dish_format falls back to preparation_style when a recipe has no format.
    a_dish = a.get("dish_format") or a.get("preparation_style") or set()
    b_dish = b.get("dish_format") or b.get("preparation_style") or set()

    score = _WEIGHTS["dish_format"] * _jaccard(a_dish, b_dish)
    score += _WEIGHTS["preparation_style"] * _jaccard(
        a.get("preparation_style", set()), b.get("preparation_style", set())
    )
    score += _WEIGHTS["flavor_profile"] * _jaccard(a.get("flavor_profile", set()), b.get("flavor_profile", set()))
    score += _WEIGHTS["primary_protein"] * _match(a.get("primary_protein", set()), b.get("primary_protein", set()))
    score += _WEIGHTS["region"] * _match(a.get("region", set()), b.get("region", set()))
    score += _WEIGHTS["key_ingredient"] * _jaccard(a.get("key_ingredient", set()), b.get("key_ingredient", set()))
    return score


def compute_similar(recipes: list[dict], top_n: int = 10) -> dict[str, list[dict]]:
    """Compute top-N similar recipes for each recipe in an export list.

    Args:
        recipes: Items from the consolidated export (each with publication_id,
            recipe_id, title, and a ``tags`` dict).
        top_n: Number of neighbors to keep per recipe.

    Returns:
        Map of ``"pub:recipe"`` -> list of ``{key, title, score}`` neighbors.
    """
    keys: list[str] = []
    titles: list[str] = []
    slug_maps: list[dict[str, set[str]]] = []

    for r in recipes:
        keys.append(f"{r.get('publication_id')}:{r.get('recipe_id')}")
        titles.append(r.get("title") or "")
        slug_maps.append(_slug_sets(r.get("tags")))

    # Build inverted index over blocking fields for candidate generation.
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
        results[keys[i]] = [
            {"key": keys[j], "title": titles[j], "score": round(s, 4)} for s, j in scored[:top_n]
        ]

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
