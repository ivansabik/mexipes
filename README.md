# Mexipes content pipeline

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

### Sample PDF corpus

The repo includes **202 sample PDFs** in [`all_pdfs/`](all_pdfs/). They are not wired to the CLI automatically — copy files into `data/staging/` before ingest. For smoke tests, copy a subset to `data/sample_pdfs/` first, then stage one PDF at a time (see [Scoped runs](#scoped-runs) below).

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

### 5. Export consolidated data

```bash
mexipes export --output recipes.json --status ready
```

Writes two files:

- `recipes.json` — array of consolidated recipe objects (original, rewritten, localized, tags, substitutions)
- `recipes_facets.json` — inverted facet index (slug → `publication_id:recipe_id` keys) for browse/filter

### 6. Build similarity index (optional)

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
make format   # ruff format
make lint     # ruff check --fix
make clean    # remove caches
```
