# Mexipes

![Tests](https://github.com/ivansabik/mexipes/actions/workflows/ci.yml/badge.svg)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

Mexipes turns Mexican cookbook PDFs into structured, English-language recipes: ingredients, steps, tags, image descriptions, and US/Canada ingredient substitutions.

It was inspired by a project I did for the Data Mining and Statistical Learning course in Georgia Tech's MSc in Analytics. That project asked whether ingredient lists alone can show regional differences inside a cuisine that usually gets lumped into one category. Mexican food is a good test case. It changes a lot from region to region, its traditional cuisine is on UNESCO's Intangible Cultural Heritage list, and outside Mexico it is mostly known through Tex-Mex and its later adaptations. Getting the data was the hard part, so this repo focuses on building a clean, curated recipe dataset.

Some things you could do with it:

- Auto-tag recipes by region for recipe sites and apps like Allrecipes or Kiwilimon, so people can find dishes from a specific part of Mexico.
- Train or evaluate recipe-generation models on Mexican cuisine.
- Look at ingredient usage, flavor pairings, or nutrition across regions.
- Give chefs, product developers at food companies and restaurant chains, and culinary researchers a large set of traditional recipes to work from.

Publications move through file-based stages. The pipeline extracts recipes and crops food photos, rewrites the Spanish text, describes images, tags on Spanish text, localizes the recipe and tags into English, and applies US and Canada ingredient substitutions. Outputs land as JSON under `data/publications/`. `mexipes recommend` builds a tag-overlap similarity index for related-recipe suggestion.

LLM calls go through LiteLLM and instructor. Defaults use Gemini (`gemini/gemini-2.5-flash` and `gemini/gemini-2.5-pro`). Override the model per stage with `MEXIPES_*_MODEL`.

## What it does

- Ingests PDFs with validation and MD5 deduplication
- Extracts recipes from overlapping page chunks and crops food photography
- Rewrites Spanish recipe text (structure and order shuffled for paraphrase)
- Describes plate styling and writes text-to-image style prompts
- Tags course, protein, spiciness, budget, equipment, chiles, and related facets
- Localizes recipes and tag sets into English (slugs and short cultural intros)
- Suggests ingredient substitutions for US and Canada pantries
- Runs advisory AI review personas on sampled recipes without changing pipeline data

## Requirements

- Python 3.12 or newer
- An LLM provider API key. Defaults expect `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/). Other LiteLLM providers need their own keys (see LiteLLM docs)

Install is local and editable (`pip install -e ".[dev]"`). There is no published PyPI package yet.

## Setup

```bash
make setup
```

This installs dependencies in editable mode, installs git hooks, and copies `.env.example` to `.env` if needed. Prefer the editable install so edits under `src/mexipes/` (including prompts) take effect without reinstalling.

Edit `.env`:

```ini
GEMINI_API_KEY="your-api-key-here"
MEXIPES_DATA_DIR="./data"
```

Optional per-stage model overrides (LiteLLM model IDs):

```ini
MEXIPES_EXTRACTION_MODEL="gemini/gemini-2.5-flash"
MEXIPES_REWRITE_MODEL="gemini/gemini-2.5-pro"
MEXIPES_TAGGING_MODEL="gemini/gemini-2.5-flash"
```

### Sample PDFs

The repo does not bundle cookbook PDFs. Copy your own files into `data/staging/` (flat directory, no subfolders) before `mexipes ingest`. For smoke tests, keep a small set in `data/sample_pdfs/` and copy one file at a time into staging (see [Scoped runs](#scoped-runs)).

## Pipeline stage order

```
extract → rewrite → describe → tag → localize → substitute → ready
```

Tagging runs on rewritten Spanish text before localization, so localize can translate both the recipe body and its tag set into English.

The `describe` stage writes `images_described.json` and sets status `images_described`.

## Usage

### 1. Ingest new publications

```bash
mexipes ingest data/staging/
```

Validates PDFs, deduplicates by MD5, moves invalid files to `data/rejected/`, and registers publications under `data/publications/<publication_id>/`.

### 2. Run the pipeline

```bash
mexipes run --batch 10
```

Each invocation advances at most `--batch` recipes by one stage. Large publications need repeated runs. Example loop until a few recipes reach `ready`:

```bash
while [ "$(grep -rl '"ready"' data/publications/*/recipes/*/status.json 2>/dev/null | wc -l | tr -d ' ')" -lt 3 ]; do
  mexipes run --publication 1 --batch 10
  mexipes status --publication 1
done
```

#### Scoped runs

Process one book at a time:

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

### 4. Data quality checks

```bash
mexipes dq
mexipes dq --publication 1 --verbose
```

Exits with code 1 when any errors are found. Warnings alone still pass.

### 5. On-demand quality review

`mexipes review` samples pipeline outputs, attaches the relevant source PDF pages, and asks reviewer personas to produce findings with evidence. The command is advisory: it writes only under `data/reviews/` and leaves `data/publications/` alone. Processed publications are read through a read-only store.

Page fields (`page_start` / `page_end`, and publication `recipe_index` pages) are 1-based PDF document indices, not printed book page numbers. A recipe on PDF page 13 that shows "15" in the footer is correct.

```bash
mexipes review                              # 3 random publications x 3 random recipes
mexipes review --publications 5 --recipes-per-pub 4 --seed 42
mexipes review --publication 1 --recipes 1-25 --no-process
mexipes review --only-dq --personas extraction,taxonomy
```

Defaults keep the sample small (`--publications/-P 3`, `--recipes-per-pub/-n 3`). If a sampled PDF from `--corpus-dir` is not processed yet, review ingests and runs the pipeline inside the run's `_workspace/` subdirectory (not `data/publications/`) unless `--no-process` is set. All review output lives under `data/reviews/review_<timestamp>_<seed>/` and is gitignored.

Typical workflow:

1. Generate or update data with `mexipes run` or `mexipes all`.
2. Run `mexipes dq`.
3. Run `mexipes review`.
4. Triage findings in `consolidated.json`. Each finding starts with `triage_notes` set to `PLACEHOLDER`. Fill that field to discard false positives, add context, or propose a change.
   - one-off data issue: targeted rerun, e.g. `mexipes run --recipe 1:2 --stage tag`
   - systemic issue: prompt, DQ rule, or code change
   - weak or subjective issue: ignore, or leave as consolidator `human_review`
5. Re-run affected stages, then `dq`, then `review` on a fresh seeded sample.

Review and consolidate models use `MEXIPES_REVIEW_*` and `MEXIPES_CONSOLIDATE_*`.

### 6. Export

```bash
mexipes export --output recipes.json --status ready
```

Writes:

- `recipes.json`: consolidated recipe objects (original, rewritten, localized, tags, substitutions)
- `recipes_facets.json`: inverted facet index (slug → `publication_id:recipe_id`) for browse and filter UIs

### 7. Similarity index (optional)

```bash
mexipes recommend --export recipes.json --output recipes_similar.json
```

Computes top-N tag-overlap neighbors per recipe from the export file. Use this for related-recipe suggestion.

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

## FAQ

### Where do PDFs go, and do I commit them?

Put source PDFs in `data/staging/` for ingest. After ingest they live under `data/publications/<id>/source.pdf`. Sample and corpus PDFs are not part of the repo. Keep large PDF trees out of git (see `.gitignore`).

### Why tag before English localization?

Tags are assigned on Spanish rewritten text. The localize stage then translates both the recipe and the tag set, so English labels stay aligned with the controlled vocabulary mapping.

### Why is the status `images_described` instead of `described`?

The stage CLI name is `describe`, but the status and output file use `images_described` / `images_described.json`.

### Why do recipes move slowly? What does `--batch` do?

Each `mexipes run` advances at most `--batch` recipes (default 10) by a single stage. Re-run until recipes reach `ready`, or raise `--batch` if you want wider batches per invocation.

### Are PDF page numbers the same as printed book pages?

No. Stored page fields are positions in the PDF file (1-based). Printed footer or ToC numbers often differ by a fixed offset. That mismatch is expected.

### Does `mexipes review` change pipeline data?

No. Review writes only under `data/reviews/`. Findings are for human triage and are never auto-applied to `data/publications/`.

### Can I use a model other than Gemini?

Yes. Calls go through LiteLLM. Override per stage with `MEXIPES_*_MODEL` using LiteLLM model IDs. The LLM wrapper passes `drop_params=True` so Gemini-only options like `thinking` are ignored by other providers.

Caveats: extract and describe send PDFs or images, so those stages need a vision-capable model. Other providers need their own API keys. Structured JSON via instructor is assumed; day-to-day testing has focused on Gemini.

### Are rewritten recipes safe to publish?

The rewrite stage paraphrases Spanish text so the output is not a verbatim copy of the source. You still need rights to process the PDFs and to redistribute anything you publish from them.

### Where should AI agents look for deeper context?

See [AGENTS.md](AGENTS.md) for pipeline invariants, status mapping, and workflow guides.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Recipes stuck at `extracted` / `rewritten` / … | `--batch` limit reached | Re-run `mexipes run --publication N --batch 10` |
| Publication stays `registered` | Extraction chunk failed | Check logs; re-run `mexipes run --publication N --stage extract` |
| Recipe status `failed` | Stage exception | Read `status.json` for the error; retry with `--recipe N:M --stage <name>` |
| `ImportError: dotenv` | Missing dependency | Run `pip install -e .` (includes `python-dotenv`) |
| Large PDF (>10 MB) | API payload limits | Pipeline converts pages to JPEGs during LLM calls |
| Fewer recipes than expected after extract | Section-local `recipe_number` from source PDF | Storage IDs are sequential; re-run `--stage extract` after clearing `recipes/` |
| Stale `metadata.json` after prompt/logic change | `--stage extract` reuses existing metadata | Delete `metadata.json` or call `extract_publication_metadata(...)` (below) |

### Re-running metadata extraction

Recipe extraction (`--stage extract`) does not regenerate `metadata.json` when the file already exists. To refresh publication metadata after a prompt or sanitization change, delete `data/publications/<id>/metadata.json` or run:

```python
from mexipes.config import settings
from mexipes.storage import RecipeStore
from mexipes.stages.extract import extract_publication_metadata

extract_publication_metadata(RecipeStore(settings.data_dir), publication_id=1)
```

After metadata changes, `tags.json` is stale until recipes are re-tagged (inherited tags merge at tag time). Re-run `mexipes run --publication N --stage tag` on affected recipes, then advance through localize and substitute if they were already `ready`.

## Development

```bash
make setup    # install deps + pre-commit/pre-push git hooks (once per clone)
make format   # ruff format
make lint     # ruff check --fix
make check    # CI-equivalent lint + format check (no auto-fix)
make test     # pytest (no API key needed)
make clean    # remove caches
```

Git hooks from `make setup` run ruff on commit and `make check` plus `make test` on push. If hooks are not installed, run `make check` before pushing.

## License

MIT. See [LICENSE](LICENSE).
