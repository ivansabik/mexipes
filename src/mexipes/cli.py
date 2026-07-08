import logging
from pathlib import Path

import typer

from mexipes.config import settings
from mexipes.schemas.recipe import RecipeStatus
from mexipes.storage import RecipeStore

# Initialize logging for the CLI entry point
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = typer.Typer(help="Mexipes Automated Recipe Content Pipeline CLI")


def get_store() -> RecipeStore:
    return RecipeStore(settings.data_dir)


@app.command()
def ingest(
    staging_dir: Path = typer.Argument(..., help="Directory containing raw PDF files to ingest"),
):
    """Stage 1: Scan a folder of new PDFs, deduplicate, and register them."""
    typer.echo(f"Ingesting PDFs from {staging_dir}...")
    from mexipes.stages.ingest import ingest_pdfs

    store = get_store()
    ingest_pdfs(store, staging_dir)


@app.command()
def run(
    publication_id: int | None = typer.Option(
        None, "--publication", "-p", help="Run pipeline for all recipes in a publication ID"
    ),
    recipe: str | None = typer.Option(
        None,
        "--recipe",
        "-r",
        help="Run pipeline for a specific recipe (format: publication_id:recipe_id)",
    ),
    stage: str | None = typer.Option(
        None,
        "--stage",
        "-s",
        help="Run a specific stage (extract, rewrite, describe, tag, localize, substitute)",
    ),
    advance_all: bool = typer.Option(False, "--advance-all", help="Advance all pending recipes through the next stage"),
    all_stages: bool = typer.Option(
        False,
        "--all-stages",
        help="Loop batches until all recipes in --publication reach ready (requires --publication)",
    ),
    batch_size: int = typer.Option(
        10,
        "--batch",
        help="Max recipes per batch (0 = unlimited)",
    ),
    sleep_seconds: float = typer.Option(
        0.0,
        "--sleep",
        help="Seconds to wait between batches when using --all-stages",
    ),
):
    """Run pipeline stages for publications/recipes."""
    store = get_store()
    from mexipes.pipeline.orchestrator import run_pipeline

    parsed_recipe = None
    if recipe:
        if ":" not in recipe:
            typer.echo("Error: Recipe must be in format 'publication_id:recipe_id'", err=True)
            raise typer.Exit(code=1)
        try:
            pub_id_str, r_id_str = recipe.split(":")
            parsed_recipe = (int(pub_id_str), int(r_id_str))
        except ValueError:
            typer.echo("Error: Recipe IDs must be integers", err=True)
            raise typer.Exit(code=1) from None

    if all_stages and publication_id is None:
        typer.echo("Error: --all-stages requires --publication", err=True)
        raise typer.Exit(code=1)

    typer.echo("Running content pipeline...")
    run_pipeline(
        store=store,
        publication_id=publication_id,
        recipe_id=parsed_recipe,
        stage=stage,
        advance_all=advance_all,
        batch_size=batch_size,
        all_stages=all_stages,
        sleep_seconds=sleep_seconds,
    )


@app.command("all")
def run_all(
    staging_dir: Path = typer.Option(
        Path("data/staging"),
        "--staging",
        help="Directory of PDFs to ingest before processing",
    ),
    batch_size: int = typer.Option(
        10,
        "--batch",
        help="Max recipes advanced per batch, per publication (0 = unlimited)",
    ),
    sleep_seconds: float = typer.Option(
        0.0,
        "--sleep",
        help="Seconds to wait between batches",
    ),
    export_output: Path | None = typer.Option(
        None,
        "--export",
        "-o",
        help="If set, export ready recipes to this JSON file after processing",
    ),
):
    """End-to-end: ingest staged PDFs and run every publication through all stages to ready."""
    store = get_store()
    from mexipes.pipeline.orchestrator import export_recipes, run_full_pipeline

    typer.echo("Running full pipeline (ingest + all stages for every publication)...")
    publication_ids = run_full_pipeline(
        store,
        staging_dir=staging_dir,
        batch_size=batch_size,
        sleep_seconds=sleep_seconds,
    )
    typer.echo(f"Processed {len(publication_ids)} publication(s): {publication_ids}")

    if export_output is not None:
        typer.echo(f"Exporting ready recipes to {export_output}...")
        export_recipes(store, RecipeStatus.READY, export_output)


@app.command()
def status(
    publication_id: int | None = typer.Option(
        None, "--publication", "-p", help="Show status for a specific publication ID"
    ),
):
    """Check processing status of recipes."""
    store = get_store()
    if publication_id:
        typer.echo(f"Status for Publication {publication_id}:")
        publication_dir = store.get_publication_dir(publication_id)
        pdf_path = publication_dir / "source.pdf"
        if not pdf_path.exists():
            typer.echo(f"Publication {publication_id} not found.")
            return

        metadata = store.load_publication_metadata(publication_id)
        if not metadata:
            typer.echo("  Status: Registered (Metadata not yet extracted)")
            return

        typer.echo(f"  Title: {metadata.document_title}")
        typer.echo(f"  Pages: {metadata.pdf_pages}")
        typer.echo(f"  Estimated Recipes: {metadata.recipes_count}")

        # Show status of recipes in this publication
        recipes_dir = store.get_publication_dir(publication_id) / "recipes"
        if not recipes_dir.exists():
            typer.echo("  No recipes extracted yet.")
            return

        counts = {}
        for r_path in sorted(recipes_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999):
            if r_path.is_dir() and r_path.name.isdigit():
                r_id = int(r_path.name)
                stat = store.get_status(publication_id, r_id)
                counts[stat] = counts.get(stat, 0) + 1
        typer.echo("  Recipe counts by status:")
        for stat, count in counts.items():
            typer.echo(f"    - {stat.value}: {count}")
    else:
        typer.echo("Mexipes Pipeline Status:")
        # List total publications and recipes at each stage
        publications_dir = store.data_dir / "publications"
        if not publications_dir.exists():
            typer.echo("  No publications registered yet.")
            return
        publications = [p for p in publications_dir.iterdir() if p.is_dir() and p.name.isdigit()]
        typer.echo(f"  Registered Publications: {len(publications)}")

        counts = {}
        for r_pub, r_recipe in store.find_all_recipes():
            stat = store.get_status(r_pub, r_recipe)
            counts[stat] = counts.get(stat, 0) + 1
        typer.echo("  Total recipe counts by status:")
        if not counts:
            typer.echo("    No recipes found.")
        for stat, count in counts.items():
            typer.echo(f"    - {stat.value}: {count}")


@app.command("backfill-images")
def backfill_images(
    publication_id: int = typer.Option(..., "--publication", "-p", help="Publication ID to backfill images for"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-render full-page photos even when recipes already have images",
    ),
):
    """Deterministically harvest embedded photos for extracted recipes (no LLM)."""
    store = get_store()
    publication_dir = store.get_publication_dir(publication_id)
    pdf_path = publication_dir / "source.pdf"
    if not pdf_path.exists():
        typer.echo(f"Publication {publication_id} not found (no source.pdf).", err=True)
        raise typer.Exit(code=1)

    from mexipes.stages.extract import collect_assigned_xrefs, harvest_embedded_photos

    typer.echo(f"Backfilling embedded photos for Publication {publication_id}...")
    assigned_xrefs = collect_assigned_xrefs(store, publication_id, pdf_path) if not force else set()
    attached = harvest_embedded_photos(store, publication_id, pdf_path, assigned_xrefs, force=force)
    typer.echo(f"Attached photos to {attached} recipe(s).")


@app.command()
def export(
    output: Path = typer.Option(Path("recipes.json"), "--output", "-o", help="Path to write consolidated JSON"),
    status_filter: RecipeStatus = typer.Option(
        RecipeStatus.READY,
        "--status",
        help="Only export recipes with this status",
    ),
):
    """Export completed recipe data to a single JSON file."""
    store = get_store()
    typer.echo(f"Exporting recipes with status '{status_filter.value}' to {output}...")
    from mexipes.pipeline.orchestrator import export_recipes

    export_recipes(store, status_filter, output)


@app.command()
def recommend(
    export_file: Path = typer.Option(
        Path("recipes.json"), "--export", "-e", help="Consolidated export JSON to read tags from"
    ),
    output: Path = typer.Option(
        Path("recipes_similar.json"), "--output", "-o", help="Path to write the similarity index"
    ),
    top_n: int = typer.Option(10, "--top-n", help="Number of similar recipes to keep per recipe"),
):
    """Build an offline tag-overlap similarity index (top-N similar recipes)."""
    from mexipes.recommend.similarity import write_similar_from_export

    if not export_file.exists():
        typer.echo(f"Export file not found: {export_file}. Run 'mexipes export' first.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Computing top-{top_n} similar recipes from {export_file}...")
    out = write_similar_from_export(export_file, output, top_n=top_n)
    typer.echo(f"Similarity index written to {out}")


@app.command()
def dq(
    publication_id: int | None = typer.Option(
        None, "--publication", "-p", help="Run DQ checks for a specific publication only"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all individual issues"),
):
    """Run data quality checks on extracted and processed recipe data."""
    store = get_store()
    from mexipes.dq import run_dq_checks

    typer.echo("Running data quality checks...")
    report = run_dq_checks(store, publication_id=publication_id)

    # Print summary
    typer.echo("")
    typer.echo(report.summary())

    # Print issues
    if report.issues:
        typer.echo("")
        errors = [i for i in report.issues if i.severity == "error"]
        warnings = [i for i in report.issues if i.severity == "warning"]

        if errors:
            typer.echo("Errors:")
            for issue in errors:
                typer.echo(f"  {issue}")

        if warnings and verbose:
            typer.echo("Warnings:")
            for issue in warnings:
                typer.echo(f"  {issue}")
        elif warnings and not verbose:
            typer.echo(f"  ({len(warnings)} warnings hidden, use --verbose to show)")

    raise typer.Exit(code=0 if report.passed else 1)


@app.command()
def review(
    publications: int = typer.Option(
        3,
        "--publications",
        "-P",
        help="Number of publications to randomly sample",
    ),
    recipes_per_pub: int = typer.Option(
        3,
        "--recipes-per-pub",
        "-n",
        help="Number of recipes to randomly sample per selected publication",
    ),
    publication: list[str] | None = typer.Option(
        None,
        "--publication",
        "-p",
        help="Pin publication id(s), repeatable or comma/range syntax such as 1,2-3",
    ),
    recipes: str | None = typer.Option(
        None,
        "--recipes",
        help="Pin recipe candidate ids/ranges within selected publication(s), e.g. 1-25,30,40-42",
    ),
    personas: str | None = typer.Option(
        None,
        "--personas",
        help="Comma-separated reviewers to run (default: all)",
    ),
    only_dq: bool = typer.Option(
        False,
        "--only-dq",
        help="Review only recipes with deterministic DQ issues",
    ),
    seed: int | None = typer.Option(None, "--seed", help="Seed both random sampling levels"),
    corpus_dir: Path = typer.Option(
        Path("all_pdfs"),
        "--corpus-dir",
        help=(
            "Source PDF corpus for sampling unprocessed publications; "
            "they are processed inside the run's _workspace, never data/publications"
        ),
    ),
    no_process: bool = typer.Option(
        False,
        "--no-process",
        help="Only review already-processed publications; skip unprocessed corpus PDFs entirely",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Root directory for run-stamped review artifacts (default: MEXIPES_REVIEWS_DIR/data/reviews)",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Explicit consolidated JSON output path (must not be under data/publications)",
    ),
    markdown: Path | None = typer.Option(
        None,
        "--markdown",
        help="Optional Markdown summary path (must not be under data/publications)",
    ),
    max_findings_per_recipe: int = typer.Option(
        5,
        "--max-findings-per-recipe",
        help="Maximum findings each reviewer may return for one recipe",
    ),
):
    """Run an on-demand AI quality review over sampled publications and recipes."""
    store = get_store()
    from mexipes.review.runner import parse_id_ranges, parse_publication_options, run_quality_review

    try:
        pinned_publications = parse_publication_options(publication)
        pinned_recipes = parse_id_ranges(recipes)
        result = run_quality_review(
            store,
            publications=publications,
            recipes_per_pub=recipes_per_pub,
            pinned_publications=pinned_publications,
            pinned_recipes=pinned_recipes,
            personas=personas,
            only_dq=only_dq,
            seed=seed,
            corpus_dir=corpus_dir,
            no_process=no_process,
            output_dir=output_dir,
            output=output,
            markdown=markdown,
            max_findings_per_recipe=max_findings_per_recipe,
        )
    except Exception as exc:
        typer.echo(f"Review failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    artifact = result.artifact
    typer.echo("Quality review completed.")
    typer.echo(f"  Publications: {artifact.metadata.sampled_publications}")
    typer.echo(f"  Recipes: {artifact.metadata.sampled_recipes}")
    typer.echo(
        "  Findings: "
        f"{artifact.consolidated.error_count} error(s), "
        f"{artifact.consolidated.warning_count} warning(s), "
        f"{artifact.consolidated.info_count} info"
    )
    typer.echo(f"  Consolidated JSON: {result.output_paths.consolidated_json}")
    if artifact.metadata.workspace_dir:
        typer.echo(
            f"  Workspace (review-only publications {artifact.metadata.workspace_publications}): "
            f"{artifact.metadata.workspace_dir}"
        )
    if result.output_paths.markdown:
        typer.echo(f"  Markdown summary: {result.output_paths.markdown}")


if __name__ == "__main__":
    app()
