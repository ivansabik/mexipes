from pathlib import Path

from mexipes.review.runner import (
    build_publication_candidates,
    parse_id_ranges,
    parse_publication_options,
    select_publication_candidates,
    select_recipe_ids,
)
from mexipes.schemas import ExtractedRecipe, RecipeStatus
from mexipes.storage import RecipeStore


def _seed_publication(store: RecipeStore, publication_id: int, recipe_count: int = 5) -> None:
    pub_dir = store.get_publication_dir(publication_id)
    (pub_dir / "source.pdf").write_bytes(f"pdf-{publication_id}".encode())
    (pub_dir / "publication_info.json").write_text(
        f'{{"publication_id": {publication_id}, "md5": "md5-{publication_id}"}}',
        encoding="utf-8",
    )
    for recipe_id in range(1, recipe_count + 1):
        store.save_stage_output(
            publication_id,
            recipe_id,
            "extracted",
            ExtractedRecipe(title=f"Recipe {recipe_id}", ingredients="beans", instructions="cook beans"),
        )
        store.set_status(publication_id, recipe_id, RecipeStatus.EXTRACTED)


def test_parse_id_ranges() -> None:
    assert parse_id_ranges("1-3,7,10-11") == [1, 2, 3, 7, 10, 11]
    assert parse_publication_options(["1,2", "4-5"]) == [1, 2, 4, 5]


def test_publication_sampling_is_seeded(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path / "data")
    for publication_id in range(1, 6):
        _seed_publication(store, publication_id)

    candidates = build_publication_candidates(store, corpus_dir=tmp_path / "missing", no_process=True)
    first = select_publication_candidates(candidates, sample_size=3, seed=99)
    second = select_publication_candidates(candidates, sample_size=3, seed=99)

    assert [c.publication_id for c in first] == [c.publication_id for c in second]
    assert len(first) == 3


def test_recipe_sampling_is_seeded_and_honors_pinned_pool(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path / "data")
    _seed_publication(store, 1, recipe_count=8)

    first = select_recipe_ids(store, 1, recipes_per_pub=3, seed=123, pinned_recipes=[1, 2, 3, 4, 5])
    second = select_recipe_ids(store, 1, recipes_per_pub=3, seed=123, pinned_recipes=[1, 2, 3, 4, 5])

    assert first == second
    assert len(first) == 3
    assert set(first) <= {1, 2, 3, 4, 5}


def test_recipe_sampling_can_filter_to_dq_issues(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path / "data")
    _seed_publication(store, 1, recipe_count=5)

    selected = select_recipe_ids(
        store,
        1,
        recipes_per_pub=3,
        seed=1,
        only_dq=True,
        dq_issues_by_recipe={2: [], 5: []},
    )

    assert selected == [2, 5]
