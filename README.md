# Mexipes content pipeline

[![Tests](https://github.com/ivansabik/mexipes/actions/workflows/ci.yml/badge.svg)](https://github.com/ivansabik/mexipes/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Automated pipeline for converting recipe publication PDFs from Spanish into structured, localized English recipes.

## Features

- **Ingestion & Registry**: PDF validation, MD5 deduplication, and file organization.
- **Recipe Extraction**: Text extraction in overlapping page chunks utilizing Gemini model prompts.
- **Photographic Crop**: Automatic detection and cropping of food photography bounding boxes.
- **Copyright Compliance**: Spanish-language restructuring and order-shuffling.
- **Vision Descriptions**: Machine descriptions of plate styling, angle, lighting, and replicating text-to-image prompts.
- **Taxonomy Tagging**: Classification of course, protein, spiciness, budget, equipment, and chiles.
- **Localization**: English translation, URL slugs, and cultural introductions.
- **Sourcing Substitutions**: Sourcing substitutions for US and Canada target audiences.
- **On-demand Quality Review**: AI reviewer personas audit sampled publications/recipes and write isolated review artifacts for human triage.

---

## Prerequisites

- Python 3.12 or newer.
- A Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

### Quick setup (using Makefile)

```bash
make setup
```

This installs dependencies in editable mode and copies `.env.example` to `.env`. **Use editable install** (`pip install -e .`) so CLI changes to source under `src/mexipes/` take effect immediately; a non-editable install can leave stale code running after you edit prompts or pipeline logic.

Edit `.env` and set your API key:

```ini
GEMINI_API_KEY="your-api-key-here"
MEXIPES_DATA_DIR="./data"
```

Optional per-stage model overrides:

```ini
MEXIPES_EXTRACTION_MODEL="gemini/gemini-2.5-flash"
MEXIPES_REWRITE_MODEL="gemini/gemini-2.5-pro"
MEXIPES_TAGGING_MODEL="gemini/gemini-2.5-flash"
```

### Sample PDFs

The repo does not bundle PDFs. Copy your own recipe publication PDFs into `data/staging/` (flat directory, no subfolders) before running `mexipes ingest`. For smoke tests, you can hold a small subset in `data/sample_pdfs/` first, then copy one file at a time into `data/staging/` (see [Scoped runs](#scoped-runs) below).

---

## Usage

The pipeline is driven via the `mexipes` CLI.

### Pipeline stage order

Each recipe advances through these stages:

```
extract → rewrite → describe → tag → localize → substitute → ready
```

Tagging runs on the **rewritten Spanish text before localization**, so the localize stage can translate both the recipe body and its tag set into English.

### 1. Ingest new publications

Place raw PDF files in `data/staging/` (flat directory, no subfolders) and run:

```bash
mexipes ingest data/staging/
```

This validates PDFs, deduplicates by MD5, moves invalid files to `data/rejected/`, and registers new publications under `data/publications/<publication_id>/`.

### 2. Run processing pipeline

```bash
mexipes run --batch 10
```

Each invocation advances at most `--batch` recipes **one stage**. Large publications require repeated runs. Example loop until recipes reach `ready`:

```bash
while [ "$(grep -rl '"ready"' data/publications/*/recipes/*/status.json 2>/dev/null | wc -l | tr -d ' ')" -lt 3 ]; do
  mexipes run --publication 1 --batch 10
  mexipes status --publication 1
done
```

#### Scoped runs

Use `--publication N` to process one book at a time. This avoids extracting every registered PDF when you have multiple publications staged:

```bash
mexipes run --publication 1 --batch 10
```

Run a single stage for one recipe:

```bash
mexipes run --recipe 1:1 --stage tag
```

Valid stage names: `extract`, `rewrite`, `describe`, `tag`, `localize`, `substitute`.

### 3. Check status

```bash
mexipes status
mexipes status --publication 1
```

### 4. Run data quality checks

```bash
mexipes dq
mexipes dq --publication 1 --verbose
```

Exits with code 1 if any **errors** are found; warnings alone still pass.

### 5. Run on-demand quality review

`mexipes review` samples generated pipeline outputs, attaches the relevant source PDF pages, and asks specialized reviewer personas to produce evidence-backed findings. It is advisory and human-in-the-loop: it writes review artifacts only and never touches `data/publications/` — processed publications are read through a read-only store view.

Page fields (`page_start` / `page_end`, and publication `recipe_index` pages) are **1-based PDF document indices**, not printed book page numbers. A recipe on PDF page 13 that shows "15" in the footer is correct; do not treat book/ToC page mismatches as extraction errors.

```bash
mexipes review                              # 3 random publications x 3 random recipes
mexipes review --publications 5 --recipes-per-pub 4 --seed 42
mexipes review --publication 1 --recipes 1-25 --no-process
mexipes review --only-dq --personas extraction,taxonomy
```

Defaults keep cost bounded: `--publications/-P 3` and `--recipes-per-pub/-n 3`. If a sampled PDF from `--corpus-dir all_pdfs/` is not processed yet, review ingests and runs the normal pipeline inside the run's `_workspace/` subdirectory (never `data/publications/`) unless `--no-process` is set, in which case unprocessed PDFs are skipped. All review output — findings, staging, and workspace pipeline outputs — lives under `data/reviews/review_<timestamp>_<seed>/` and is gitignored.

Human-in-the-loop workflow:

1. Generate or update data with `mexipes run` / `mexipes all`.
2. Run `mexipes dq`.
3. Run `mexipes review`.
4. Human (or a follow-up agent) triages findings in `consolidated.json`: each finding has `triage_notes` set to `PLACEHOLDER` until filled. Use it to discard false positives, enrich context, or propose a concrete change.
   - one-off data issue → targeted rerun, e.g. `mexipes run --recipe 1:2 --stage tag`
   - systemic issue → prompt, DQ rule, or code change
   - weak/subjective issue → ignore or keep as consolidator `human_review`
5. Re-run affected stages, then `dq`, then `review` on a fresh seeded sample.

Judge models are configured independently with `MEXIPES_REVIEW_*` and `MEXIPES_CONSOLIDATE_*`.

### 6. Export consolidated data

```bash
mexipes export --output recipes.json --status ready
```

Writes two files:

- `recipes.json` — array of consolidated recipe objects (original, rewritten, localized, tags, substitutions)
- `recipes_facets.json` — inverted facet index (slug → `publication_id:recipe_id` keys) for browse/filter

### 7. Build similarity index (optional)

```bash
mexipes recommend --export recipes.json --output recipes_similar.json
```

Computes top-N tag-overlap neighbors per recipe from the export file.

---

## Data layout

```
data/
├── staging/              # drop new PDFs here
├── rejected/             # invalid or duplicate PDFs
├── sample_pdfs/          # optional holding area for smoke-test PDFs
├── reviews/              # gitignored mexipes review artifacts
└── publications/
    └── <id>/
        ├── source.pdf
        ├── publication_info.json
        ├── metadata.json
        └── recipes/
            └── <recipe_id>/
                ├── extracted.json
                ├── rewritten.json
                ├── images_described.json
                ├── tags.json
                ├── localized.json
                ├── localized_tags.json
                ├── substitutions.json
                ├── status.json
                └── images/
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Recipes stuck at `extracted` / `rewritten` / … | `--batch` limit reached | Re-run `mexipes run --publication N --batch 10` |
| Publication stays `registered` | Extraction chunk failed | Check logs; re-run `mexipes run --publication N --stage extract` |
| Recipe status `failed` | Stage exception | Read `status.json` for error; retry with `--recipe N:M --stage <name>` |
| `ImportError: dotenv` | Missing dependency | Run `pip install -e .` (includes `python-dotenv`) |
| Large PDF (>10 MB) | API payload limits | Pipeline auto-converts pages to JPEGs during LLM calls |
| Fewer recipes than expected after extract | Section-local `recipe_number` from source PDF | Fixed in extractor: storage IDs are always sequential; re-run `--stage extract` after clearing `recipes/` |
| Stale `metadata.json` after prompt/logic change | `--stage extract` reuses existing metadata | Delete `metadata.json` or run `extract_publication_metadata(...)` — see [Re-running metadata extraction](#re-running-metadata-extraction) |

### Re-running metadata extraction

Recipe extraction (`--stage extract`) **does not** regenerate `metadata.json` when the file already exists. To refresh publication metadata after a prompt or sanitization change, delete `data/publications/<id>/metadata.json` or run:

```python
from mexipes.config import settings
from mexipes.storage import RecipeStore
from mexipes.stages.extract import extract_publication_metadata

extract_publication_metadata(RecipeStore(settings.data_dir), publication_id=1)
```

After metadata changes, `tags.json` is stale until recipes are re-tagged (inherited tags merge at tag time). Re-run `mexipes run --publication N --stage tag` on affected recipes, then advance through localize and substitute if they were already `ready`.

---

## Development

### Code formatting & linting

```bash
make setup    # install deps + pre-commit/pre-push git hooks (once per clone)
make format   # ruff format
make lint     # ruff check --fix
make check    # CI-equivalent lint + format check (no auto-fix)
make clean    # remove caches
```

Git hooks (installed by `make setup`) auto-run ruff on commit and `make check` + `make test` on push. If hooks are not installed, run `make check` manually before pushing.

### AI agent context

AI agents: see [AGENTS.md](AGENTS.md) for repo orientation, pipeline invariants, and workflow guides.
