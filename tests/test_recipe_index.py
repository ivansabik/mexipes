"""Tests for recipe index schema and chunk context helpers."""

from mexipes.recipe_validation import filter_index_entries_for_chunk, format_index_context, matches_recipe_index
from mexipes.schemas.publication import PublicationMetadata, RecipeIndexEntry


def test_publication_metadata_recipe_index_defaults_empty():
    meta = PublicationMetadata(pdf_pages="100", recipes_count="50")
    assert meta.recipe_index == []


def test_recipe_index_entry_fields():
    entry = RecipeIndexEntry(
        title="Esquites - Granos de maíz cocidos",
        page=40,
        section="STREET FOOD Y APERITIVOS",
    )
    assert entry.title.startswith("Esquites")
    assert entry.page == 40


def test_filter_index_entries_for_chunk():
    index = [
        RecipeIndexEntry(title="Masa Harina", page=38),
        RecipeIndexEntry(title="Esquites - Granos de maíz cocidos", page=40),
        RecipeIndexEntry(title="Guacamole", page=42),
        RecipeIndexEntry(title="Far away", page=200),
    ]
    # chunk pages 38-45 (0-based start_idx=37, end_idx=45 exclusive -> pages 38-45)
    filtered = filter_index_entries_for_chunk(index, chunk_start=37, chunk_end=45, overlap=1)
    pages = {e.page for e in filtered}
    assert pages == {38, 40, 42}


def test_format_index_context_includes_authoritative_header():
    entries = [RecipeIndexEntry(title="Guacamole", page=42)]
    ctx = format_index_context(entries)
    assert "RECIPE INDEX (authoritative)" in ctx
    assert "Guacamole" in ctx
    assert "p42" in ctx


def test_matches_recipe_index_subtitle():
    index = [RecipeIndexEntry(title="Esquites - Granos de maíz cocidos", page=40)]
    assert matches_recipe_index("Granos de Maíz Cocidos", 40, index)
    assert matches_recipe_index("Esquites", 40, index)
    assert not matches_recipe_index("Granos de Maíz Cocidos", 50, index)


def test_matches_recipe_index_empty_means_allow_all():
    assert matches_recipe_index("Anything", 10, [])
