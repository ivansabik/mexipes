# Mexipes — Agent Context

Convert Spanish recipe publication PDFs into structured, localized English content via Gemini LLM stages.

## Repo map

```
src/mexipes/
  cli.py                # Typer CLI: mexipes ingest|run|status|dq|export|recommend
  config.py             # Per-stage model config via MEXIPES_* env vars + .env
  pipeline/
    orchestrator.py     # Stage sequencing, batch runs, export
    pdf_processor.py    # PDF page extraction helpers
  stages/               # One module per stage
    ingest.py           # PDF validation + MD5 dedup
    extract.py          # PDF → structured Spanish recipes (+ image crop detection)
    rewrite.py          # Copyright-compliant paraphrasing
    describe.py         # Image description + text-to-image prompts
    tag.py              # Taxonomy classification (on Spanish text)
    localize.py         # Spanish → English translation (recipe + tags)
    substitute.py       # US/Canada ingredient substitutions
  prompts/              # LLM prompt templates (*.md), loaded via importlib.resources
  schemas/              # Pydantic models
    recipe.py           # RecipeStatus enum, ExtractedRecipe, RewrittenRecipe, etc.
    tags.py             # RecipeTagSet model (27+ fields)
    tag_vocabularies.py # Controlled vocabulary — code, not data files
    health_nutrition_tags.py  # health_nutrition vocab; validation uses English canonical set
    publication.py      # PublicationMetadata, InheritedTags
    substitutions.py
    pantry_substitutions.py
  storage.py            # RecipeStore — all persistence is file-based (no database)
  llm.py                # instructor + litellm wrapper (Gemini thinking disabled)
  inherited_tags.py     # Publication-level tag sanitization + merge
  dq.py                 # Data quality checks (comprehensive)
  region.py             # Geographic resolution logic
  recipe_validation.py  # Non-recipe extraction detection
  text_utils.py         # Title normalization, section header detection
  recommend/            # Tag-overlap similarity index
data/publications/<pub>/recipes/<id>/   # Stage JSON outputs + status.json
tests/                  # unit tests (no API key needed)
```

**Canonical example:** `data/publications/1/recipes/1/` — fully processed recipe (`status.json` → `"ready"`).

## Pipeline order

Each recipe advances through these stages in order:

```
extract → rewrite → describe → tag → localize → substitute → ready
```

| Stage | Status after | Output file(s) | Notes |
|-------|-------------|-----------------|-------|
| extract | `extracted` | `extracted.json` | Also generates `metadata.json` at publication level |
| rewrite | `rewritten` | `rewritten.json` | Copyright-compliant paraphrase |
| describe | `images_described` | `images_described.json` | Status/file name ≠ stage name |
| tag | `tagged` | `tags.json` | Runs on **Spanish** text, before localize |
| localize | `localized` | `localized.json` + `localized_tags.json` | Translates both recipe and tag set |
| substitute | `ready` | `substitutions.json` | Sets `ready` directly (not `substitutions_added`) |

## Gotchas

1. **Tag runs on Spanish before localize.** The localize stage translates both the recipe body and the tag set. This is why tag must come first.
2. **`describe` outputs `images_described`.** The stage name is `describe` but the status is `IMAGES_DESCRIBED` and the file is `images_described.json`. Don't look for `described.json`.
3. **Editable install required.** Run `pip install -e ".[dev]"`. Non-editable installs leave stale code after prompt or pipeline edits.
4. **`metadata.json` is not regenerated on re-extract** when the file already exists. Delete it manually, then re-run extraction. See README troubleshooting.
5. **Tag vocabulary is code, not data.** `tag_vocabularies.py` contains `(slug, es, en)` tuples. Changes require updating tests. Slugs drive export facets.
6. **`health_nutrition` validation uses English canonical labels** (`VALID_HEALTH_NUTRITION_EN`), unlike other tag fields validated against Spanish. Tagging still emits Spanish labels; localize maps them to English. See `health_nutrition_tags.py`.
7. **Inherited tags merge at tag time,** not during extraction. Publication-level tags propagate to recipes via `inherited_tags.py` during the tag stage.
8. **Prompts are packaged resources** in `src/mexipes/prompts/`, loaded via `importlib.resources` in `llm.py`. Some use `<!-- PLACEHOLDER -->` injection at runtime (TAG_TAXONOMY, HEALTH_NUTRITION_TAXONOMY, PANTRY_GUIDE, INHERITED_TAGS_TAXONOMY).
9. **LLM thinking is disabled.** `llm.py` sets `thinking={"type": "disabled"}` for Gemini structured output compatibility. Don't remove this.
10. **Auto-ingestion on run.** `run_pipeline()` automatically ingests any PDFs found in `data/staging/` before processing recipes.
11. **Tests don't need API keys.** Safe to run `make test` anytime as a validation step.
12. **Sample PDFs are not in the repo.** Copy your own PDFs into `data/staging/` before `mexipes ingest`. They are not auto-staged from any bundled directory.
13. **`--batch` limits each run.** Each `mexipes run` advances at most `--batch` recipes (default 10) by one stage. Re-run until recipes reach `ready`.
14. **Per-stage models are configurable** via `MEXIPES_*` env vars (e.g. `MEXIPES_TAGGING_MODEL`). See `config.py`.
15. **Export writes two local artifacts:** `recipes.json` + `recipes_facets.json` (auto-named from stem). Both are gitignored — regenerate with `mexipes export`.
16. **`SUBSTITUTIONS_ADDED` status exists but is unused.** The substitute stage jumps straight to `READY`.
17. **Region resolution has a priority order:** recipe-level tag → regional_sections by page range → inherited_tags.region (gated by title evidence via `region_claim_supported()`).
18. **Never commit `.env`.** Already in `.gitignore`. Use `.env.example` as template.

## Common commands

```bash
make setup                                    # editable install + .env from .env.example
make test                                     # no API key needed
make lint                                     # ruff check --fix
make format                                   # ruff format

mexipes ingest data/staging/                  # register new PDFs
mexipes run --publication 1 --batch 10        # advance up to 10 recipes one stage
mexipes run --recipe 1:1 --stage tag          # run specific stage for one recipe
mexipes status --publication 1                # check progress
mexipes dq --publication 1 --verbose          # data quality checks
mexipes export --output recipes.json          # export ready recipes
mexipes recommend --export recipes.json       # build similarity index
```

## Where to change what

| Task | Files to touch |
|------|---------------|
| Change extraction | `stages/extract.py`, `prompts/extract_*.md`, `schemas/recipe.py` |
| Change tags/facets | `schemas/tag_vocabularies.py`, `stages/tag.py`, `prompts/tag_recipe.md`, `schemas/health_nutrition_tags.py` |
| Change localization | `stages/localize.py`, `prompts/localize_*.md` |
| Change rewriting | `stages/rewrite.py`, `prompts/rewrite_recipe.md` |
| Change image description | `stages/describe.py`, `prompts/describe_image.md` |
| Change substitutions | `stages/substitute.py`, `prompts/substitute_ingredients.md`, `schemas/substitutions.py`, `schemas/pantry_substitutions.py` |
| Add DQ check | `dq.py` |
| Change export shape | `pipeline/orchestrator.py` → `export_recipes()` |
| Change per-stage model | `config.py` or `.env` (`MEXIPES_TAGGING_MODEL`, etc.) |
| Change inherited tag logic | `inherited_tags.py`, `stages/tag.py` |
| Change similarity/recommendations | `recommend/similarity.py` |

## Workflow: Debugging stuck/failed recipes

1. Read `data/publications/<pub>/recipes/<id>/status.json` — check the `error` field.
2. Re-run the failed stage: `mexipes run --recipe N:M --stage <name>`
3. If many recipes seem stuck at the same stage, re-run with `--batch` — each `mexipes run` only advances up to `--batch` recipes (default 10) by one stage.
4. For metadata refresh: delete `metadata.json`, then `mexipes run --publication N --stage extract`
5. After metadata or tag vocab changes: re-tag → re-localize → re-substitute the full chain.
6. Verify: `mexipes dq --publication N` and `make test`

## Workflow: Changing tag vocabulary

1. Edit `schemas/tag_vocabularies.py` (and/or `health_nutrition_tags.py`).
2. Update `prompts/tag_recipe.md` if LLM instructions reference the vocabulary.
3. Run `pytest tests/test_tag_vocabularies.py`.
4. Re-tag affected recipes: `mexipes run --publication N --stage tag`
5. Re-localize and re-substitute if recipes were already past those stages.
6. Re-export if needed: `mexipes export --output recipes.json`

## Further reading

See [README.md](README.md) for human-oriented setup, usage details, and troubleshooting tables.
