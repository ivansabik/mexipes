from __future__ import annotations

import hashlib
import json
import logging
import random
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Template
from pydantic import BaseModel

from mexipes.config import settings
from mexipes.dq import DQIssue, run_dq_checks
from mexipes.llm import call_llm, load_prompt
from mexipes.pipeline import pdf_processor
from mexipes.pipeline.orchestrator import run_pipeline_until_ready
from mexipes.review.models import (
    ConsolidatedReview,
    ModelRunConfig,
    RecipeReviewResult,
    ReviewFinding,
    ReviewRunArtifact,
    ReviewRunMetadata,
)
from mexipes.review.registry import Reviewer, resolve_reviewers
from mexipes.schemas import (
    ExtractedRecipe,
    ImageDescriptionsResult,
    LocalizedRecipe,
    RecipeTagSet,
    RewrittenRecipe,
    SubstitutionsResult,
)
from mexipes.stages.extract import extract_publication_recipes
from mexipes.stages.ingest import compute_md5, ingest_pdfs
from mexipes.storage import ReadOnlyRecipeStore, RecipeStore

logger = logging.getLogger(__name__)

STAGE_MODELS: dict[str, type[BaseModel]] = {
    "extracted": ExtractedRecipe,
    "rewritten": RewrittenRecipe,
    "images_described": ImageDescriptionsResult,
    "tags": RecipeTagSet,
    "localized": LocalizedRecipe,
    "localized_tags": RecipeTagSet,
    "substitutions": SubstitutionsResult,
}


@dataclass(frozen=True)
class PublicationCandidate:
    """A publication candidate that is either processed or a source PDF to ingest."""

    publication_id: int | None
    pdf_path: Path
    md5: str | None

    @property
    def is_processed(self) -> bool:
        return self.publication_id is not None


@dataclass(frozen=True)
class ReviewOutputPaths:
    run_dir: Path
    consolidated_json: Path
    markdown: Path | None


@dataclass
class ReviewRunResult:
    artifact: ReviewRunArtifact
    output_paths: ReviewOutputPaths
    per_publication_files: dict[int, Path]


def parse_id_ranges(raw: str | None) -> list[int] | None:
    """Parse comma-separated ids/ranges like ``1-3,7,10-12``."""
    if raw is None or not raw.strip():
        return None

    ids: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_s, end_s = token.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if start > end:
                raise ValueError(f"Invalid descending range: {token}")
            ids.update(range(start, end + 1))
        else:
            ids.add(int(token))
    return sorted(ids)


def parse_publication_options(values: list[str] | None) -> list[int] | None:
    """Parse repeatable/comma-separated ``--publication`` values."""
    if not values:
        return None
    merged: set[int] = set()
    for value in values:
        parsed = parse_id_ranges(value)
        if parsed:
            merged.update(parsed)
    return sorted(merged)


def sample_items[T](items: list[T], sample_size: int, rng: random.Random) -> list[T]:
    """Return a deterministic random sample while preserving sampled order."""
    if sample_size <= 0 or len(items) <= sample_size:
        return list(items)
    return rng.sample(items, sample_size)


def ensure_output_outside_publications(path: Path, store: RecipeStore) -> None:
    """Reject review output paths that resolve inside data/publications."""
    resolved = path.resolve(strict=False)
    publications_dir = (store.data_dir / "publications").resolve(strict=False)
    if resolved == publications_dir or resolved.is_relative_to(publications_dir):
        raise ValueError(f"Review output path must not be inside {publications_dir}: {resolved}")


def resolve_output_paths(
    store: RecipeStore,
    *,
    output_dir: Path | None = None,
    output: Path | None = None,
    markdown: Path | None = None,
    seed: int | None = None,
    now: datetime | None = None,
) -> ReviewOutputPaths:
    """Resolve and validate isolated review artifact paths."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    seed_part = "random" if seed is None else str(seed)

    if output is not None:
        consolidated_json = output
        run_dir = output.parent
    else:
        root = output_dir or settings.reviews_dir
        run_dir = root / f"review_{stamp}_{seed_part}"
        consolidated_json = run_dir / "consolidated.json"

    ensure_output_outside_publications(run_dir, store)
    ensure_output_outside_publications(consolidated_json, store)
    if markdown is not None:
        ensure_output_outside_publications(markdown, store)

    return ReviewOutputPaths(run_dir=run_dir, consolidated_json=consolidated_json, markdown=markdown)


def _publication_info_md5(store: RecipeStore, publication_id: int) -> str | None:
    info = store.load_publication_info(publication_id)
    if info and isinstance(info.get("md5"), str):
        return info["md5"]
    pdf_path = store.data_dir / "publications" / str(publication_id) / "source.pdf"
    if pdf_path.exists():
        return compute_md5(pdf_path)
    return None


def _processed_candidates(store: RecipeStore) -> list[PublicationCandidate]:
    candidates: list[PublicationCandidate] = []
    publications_dir = store.data_dir / "publications"
    if not publications_dir.exists():
        return candidates
    for path in sorted(publications_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 999999):
        if not path.is_dir() or not path.name.isdigit():
            continue
        pdf_path = path / "source.pdf"
        if not pdf_path.exists():
            continue
        publication_id = int(path.name)
        candidates.append(PublicationCandidate(publication_id, pdf_path, _publication_info_md5(store, publication_id)))
    return candidates


def _corpus_candidates(
    corpus_dir: Path,
    *,
    existing_md5s: set[str],
) -> list[PublicationCandidate]:
    if not corpus_dir.exists():
        return []
    candidates: list[PublicationCandidate] = []
    for pdf_path in sorted(p for p in corpus_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"):
        md5 = compute_md5(pdf_path)
        if md5 in existing_md5s:
            continue
        candidates.append(PublicationCandidate(None, pdf_path, md5))
    return candidates


def build_publication_candidates(
    store: RecipeStore,
    *,
    corpus_dir: Path,
    pinned_publications: list[int] | None = None,
    no_process: bool = False,
) -> list[PublicationCandidate]:
    """Build publication candidates from processed pubs and, optionally, corpus PDFs."""
    processed = _processed_candidates(store)
    if pinned_publications:
        by_id = {candidate.publication_id: candidate for candidate in processed}
        missing = [publication_id for publication_id in pinned_publications if publication_id not in by_id]
        if missing:
            raise ValueError(f"Pinned publication(s) are not processed: {missing}")
        return [by_id[publication_id] for publication_id in pinned_publications]

    if no_process:
        return processed

    existing_md5s = {candidate.md5 for candidate in processed if candidate.md5}
    return processed + _corpus_candidates(corpus_dir, existing_md5s=existing_md5s)


def select_publication_candidates(
    candidates: list[PublicationCandidate],
    *,
    sample_size: int,
    seed: int | None,
) -> list[PublicationCandidate]:
    rng = random.Random(seed)
    return sample_items(candidates, sample_size, rng)


def _find_publication_by_md5(store: RecipeStore, md5: str) -> int | None:
    for candidate in _processed_candidates(store):
        if candidate.md5 == md5:
            return candidate.publication_id
    return None


def create_workspace_store(run_dir: Path, prod_store: RecipeStore) -> RecipeStore:
    """Create the run-scoped workspace store used to process sampled corpus PDFs.

    All ingest/pipeline writes for review-only publications land under
    ``<run_dir>/_workspace`` instead of the prod ``data/publications`` tree.
    A placeholder directory seeds publication id allocation past the highest
    prod id so workspace ids never collide with prod ids in review findings.
    """
    workspace_store = RecipeStore(run_dir / "_workspace")
    max_prod_id = 0
    prod_publications = prod_store.data_dir / "publications"
    if prod_publications.exists():
        for entry in prod_publications.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                max_prod_id = max(max_prod_id, int(entry.name))
    if max_prod_id > 0:
        (workspace_store.data_dir / "publications" / str(max_prod_id)).mkdir(parents=True, exist_ok=True)
    return workspace_store


def _process_corpus_candidate(
    workspace_store: RecipeStore,
    candidate: PublicationCandidate,
    *,
    staging_dir: Path,
) -> int:
    """Ingest a sampled corpus PDF into the workspace store and run the pipeline there."""
    if candidate.md5 is None:
        raise ValueError(f"Corpus candidate is missing md5: {candidate.pdf_path}")
    publication_id = _find_publication_by_md5(workspace_store, candidate.md5)
    if publication_id is None:
        staging_dir.mkdir(parents=True, exist_ok=True)
        staged_pdf = staging_dir / candidate.pdf_path.name
        shutil.copy2(candidate.pdf_path, staged_pdf)
        ingest_pdfs(workspace_store, staging_dir)
        publication_id = _find_publication_by_md5(workspace_store, candidate.md5)
        if publication_id is None:
            raise RuntimeError(f"Failed to ingest sampled PDF: {candidate.pdf_path}")

    recipes = [key for key in workspace_store.find_all_recipes() if key[0] == publication_id]
    if not recipes:
        extract_publication_recipes(workspace_store, publication_id)

    run_pipeline_until_ready(workspace_store, publication_id, batch_size=0)
    return publication_id


def _issues_by_recipe(store: RecipeStore, publication_id: int) -> dict[int, list[DQIssue]]:
    report = run_dq_checks(store, publication_id=publication_id)
    grouped: dict[int, list[DQIssue]] = defaultdict(list)
    for issue in report.issues:
        if issue.recipe_id is not None:
            grouped[issue.recipe_id].append(issue)
    return grouped


def _all_recipe_ids(store: RecipeStore, publication_id: int) -> list[int]:
    return sorted(recipe_id for pub_id, recipe_id in store.find_all_recipes() if pub_id == publication_id)


def select_recipe_ids(
    store: RecipeStore,
    publication_id: int,
    *,
    recipes_per_pub: int,
    seed: int | None,
    pinned_recipes: list[int] | None = None,
    only_dq: bool = False,
    dq_issues_by_recipe: dict[int, list[DQIssue]] | None = None,
) -> list[int]:
    """Select recipe ids within a publication using deterministic random sampling."""
    candidates = pinned_recipes if pinned_recipes is not None else _all_recipe_ids(store, publication_id)
    if dq_issues_by_recipe is None:
        dq_issues_by_recipe = _issues_by_recipe(store, publication_id)
    if only_dq:
        candidates = [recipe_id for recipe_id in candidates if recipe_id in dq_issues_by_recipe]
    candidates = sorted(set(candidates))
    rng = random.Random(f"{seed}:{publication_id}:recipes")
    return sample_items(candidates, recipes_per_pub, rng)


def _stage_outputs_for_recipe(
    store: RecipeStore,
    publication_id: int,
    recipe_id: int,
    stage_names: tuple[str, ...],
) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for stage_name in stage_names:
        model = STAGE_MODELS[stage_name]
        value = store.load_stage_output(publication_id, recipe_id, stage_name, model)
        outputs[stage_name] = value.model_dump() if value is not None else None
    return outputs


def _dq_issue_to_dict(issue: DQIssue) -> dict[str, Any]:
    return {
        "publication_id": issue.publication_id,
        "recipe_id": issue.recipe_id,
        "stage": issue.stage,
        "field": issue.field,
        "severity": issue.severity,
        "message": issue.message,
    }


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _prompt_hash(prompt_name: str) -> str:
    prompt = load_prompt(prompt_name)
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def _render_reviewer_prompt(
    reviewer: Reviewer,
    *,
    publication_id: int,
    recipe_id: int,
    publication_metadata: dict[str, Any] | None,
    dq_issues: list[DQIssue],
    stage_outputs: dict[str, Any],
    max_findings: int,
) -> str:
    template = Template(load_prompt(reviewer.prompt_file))
    return template.render(
        persona=reviewer.persona,
        guidelines=reviewer.guidelines,
        publication_id=publication_id,
        recipe_id=recipe_id,
        reviewer_name=reviewer.name,
        max_findings=max_findings,
        publication_metadata_json=_json_dumps(publication_metadata or {}),
        dq_issues_json=_json_dumps([_dq_issue_to_dict(issue) for issue in dq_issues]),
        stage_outputs_json=_json_dumps(stage_outputs),
    )


def _recipe_pdf_bytes(store: RecipeStore, publication_id: int, recipe_id: int) -> bytes | None:
    extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
    pdf_path = store.data_dir / "publications" / str(publication_id) / "source.pdf"
    if not extracted or not pdf_path.exists() or extracted.page_start is None:
        return None
    page_start = max(1, extracted.page_start)
    page_end = extracted.page_end or extracted.page_start
    return pdf_processor.extract_chunk_pdf_bytes(pdf_path, page_start - 1, page_end - 1)


def _run_single_reviewer(
    store: RecipeStore,
    reviewer: Reviewer,
    *,
    publication_id: int,
    recipe_id: int,
    dq_issues: list[DQIssue],
    max_findings: int,
    pdf_bytes: bytes | None,
) -> RecipeReviewResult:
    metadata = store.load_publication_metadata(publication_id)
    stage_outputs = _stage_outputs_for_recipe(store, publication_id, recipe_id, reviewer.required_stages)
    prompt = _render_reviewer_prompt(
        reviewer,
        publication_id=publication_id,
        recipe_id=recipe_id,
        publication_metadata=metadata.model_dump() if metadata else None,
        dq_issues=dq_issues,
        stage_outputs=stage_outputs,
        max_findings=max_findings,
    )
    result = call_llm(
        model=settings.review.model,
        response_model=RecipeReviewResult,
        prompt=prompt,
        pdf_bytes=pdf_bytes if reviewer.needs_pdf else None,
        temperature=settings.review.temperature,
        max_retries=settings.review.max_retries,
    )
    # Normalize ids/persona defensively; this prevents small LLM slips from leaking
    # into the stable finding keys.
    result.publication_id = publication_id
    result.recipe_id = recipe_id
    result.persona = reviewer.name
    normalized_findings: list[ReviewFinding] = []
    for finding in result.findings[:max_findings]:
        finding.publication_id = publication_id
        finding.recipe_id = recipe_id
        finding.persona = reviewer.name
        finding.finding_key = None
        finding.populate_finding_key()
        normalized_findings.append(finding)
    result.findings = normalized_findings
    return result


def _synthesize_consolidated(findings: list[ReviewFinding]) -> ConsolidatedReview:
    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    infos = sum(1 for finding in findings if finding.severity == "info")
    return ConsolidatedReview(
        summary=f"Review completed with {errors} error(s), {warnings} warning(s), and {infos} info finding(s).",
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
    )


def _consolidate_findings(metadata: ReviewRunMetadata, findings: list[ReviewFinding]) -> ConsolidatedReview:
    if not findings:
        return ConsolidatedReview(summary="No evidence-backed findings were reported for the sampled recipes.")

    template = Template(load_prompt("review_consolidate.md"))
    prompt = template.render(
        metadata_json=metadata.model_dump_json(indent=2),
        findings_json=_json_dumps([finding.model_dump() for finding in findings]),
    )
    try:
        consolidated = call_llm(
            model=settings.consolidate.model,
            response_model=ConsolidatedReview,
            prompt=prompt,
            temperature=settings.consolidate.temperature,
            max_retries=settings.consolidate.max_retries,
        )
    except Exception:
        logger.exception("Consolidation LLM failed; falling back to deterministic summary.")
        return _synthesize_consolidated(findings)

    consolidated.error_count = sum(1 for finding in findings if finding.severity == "error")
    consolidated.warning_count = sum(1 for finding in findings if finding.severity == "warning")
    consolidated.info_count = sum(1 for finding in findings if finding.severity == "info")
    return consolidated


def _write_markdown(path: Path, artifact: ReviewRunArtifact) -> None:
    lines = [
        "# Mexipes Quality Review",
        "",
        artifact.consolidated.summary,
        "",
        "## Run Metadata",
        "",
        f"- Publications sampled: {artifact.metadata.sampled_publications}",
        f"- Recipes sampled: {artifact.metadata.sampled_recipes}",
        f"- Personas: {artifact.metadata.personas}",
        f"- Seed: {artifact.metadata.sample_seed}",
        "",
        "## Finding Counts",
        "",
        f"- Errors: {artifact.consolidated.error_count}",
        f"- Warnings: {artifact.consolidated.warning_count}",
        f"- Info: {artifact.consolidated.info_count}",
    ]
    if artifact.consolidated.recommended_reruns:
        lines.extend(["", "## Recommended Reruns", ""])
        for rerun in artifact.consolidated.recommended_reruns:
            lines.append(
                f"- `mexipes run --recipe {rerun.publication_id}:{rerun.recipe_id} --stage {rerun.stage}` — {rerun.reason}"
            )
    if artifact.findings:
        lines.extend(["", "## Findings", ""])
        for finding in artifact.findings:
            lines.append(
                f"- [{finding.severity}] {finding.publication_id}:{finding.recipe_id} "
                f"{finding.stage}.{finding.field} ({finding.finding_type}): {finding.issue}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_artifacts(
    artifact: ReviewRunArtifact,
    output_paths: ReviewOutputPaths,
) -> dict[int, Path]:
    output_paths.run_dir.mkdir(parents=True, exist_ok=True)
    output_paths.consolidated_json.write_text(artifact.model_dump_json(indent=4), encoding="utf-8")
    per_pub: dict[int, Path] = {}
    for publication_id in artifact.metadata.sampled_publications:
        pub_findings = [finding for finding in artifact.findings if finding.publication_id == publication_id]
        pub_path = output_paths.run_dir / f"publication-{publication_id}.json"
        pub_path.write_text(
            json.dumps([finding.model_dump() for finding in pub_findings], ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
        per_pub[publication_id] = pub_path
    if output_paths.markdown is not None:
        output_paths.markdown.parent.mkdir(parents=True, exist_ok=True)
        _write_markdown(output_paths.markdown, artifact)
    return per_pub


def run_quality_review(
    store: RecipeStore,
    *,
    publications: int = 3,
    recipes_per_pub: int = 3,
    pinned_publications: list[int] | None = None,
    pinned_recipes: list[int] | None = None,
    personas: str | None = None,
    only_dq: bool = False,
    seed: int | None = None,
    corpus_dir: Path = Path("all_pdfs"),
    no_process: bool = False,
    output_dir: Path | None = None,
    output: Path | None = None,
    markdown: Path | None = None,
    max_findings_per_recipe: int = 5,
) -> ReviewRunResult:
    """Run the on-demand quality review workflow and write isolated artifacts.

    Review never writes to ``data/publications``: processed publications are read
    through a read-only store view, and sampled corpus PDFs that still need
    processing are ingested and run inside ``<run_dir>/_workspace``.
    """
    prod_store = ReadOnlyRecipeStore(store.data_dir)
    reviewers = resolve_reviewers(personas)
    output_paths = resolve_output_paths(prod_store, output_dir=output_dir, output=output, markdown=markdown, seed=seed)
    candidates = build_publication_candidates(
        prod_store,
        corpus_dir=corpus_dir,
        pinned_publications=pinned_publications,
        no_process=no_process,
    )
    if not candidates:
        raise ValueError("No publication candidates found for review.")

    selected_candidates = select_publication_candidates(candidates, sample_size=publications, seed=seed)
    staging_dir = output_paths.run_dir / "_staging"
    workspace_store: RecipeStore | None = None
    stores_by_publication: dict[int, RecipeStore] = {}
    workspace_publications: list[int] = []
    selected_publications: list[int] = []
    sampled_recipes: dict[str, list[int]] = {}
    dq_by_pub_recipe: dict[tuple[int, int], list[DQIssue]] = {}

    for candidate in selected_candidates:
        if candidate.publication_id is not None:
            # Already-processed prod publications are reviewed as-is (read-only).
            publication_id = candidate.publication_id
            candidate_store: RecipeStore = prod_store
        else:
            if no_process:
                continue
            if workspace_store is None:
                workspace_store = create_workspace_store(output_paths.run_dir, prod_store)
            publication_id = _process_corpus_candidate(workspace_store, candidate, staging_dir=staging_dir)
            candidate_store = workspace_store
            workspace_publications.append(publication_id)

        issues_by_recipe = _issues_by_recipe(candidate_store, publication_id)
        recipe_ids = select_recipe_ids(
            candidate_store,
            publication_id,
            recipes_per_pub=recipes_per_pub,
            seed=seed,
            pinned_recipes=pinned_recipes,
            only_dq=only_dq,
            dq_issues_by_recipe=issues_by_recipe,
        )
        if not recipe_ids:
            logger.info("Publication %s has no recipes matching review filters; skipping.", publication_id)
            continue
        selected_publications.append(publication_id)
        stores_by_publication[publication_id] = candidate_store
        sampled_recipes[str(publication_id)] = recipe_ids
        for recipe_id in recipe_ids:
            dq_by_pub_recipe[(publication_id, recipe_id)] = issues_by_recipe.get(recipe_id, [])

    if not sampled_recipes:
        raise ValueError("No recipes selected for review after applying filters.")

    prompt_hashes = {reviewer.prompt_file: _prompt_hash(reviewer.prompt_file) for reviewer in reviewers}
    prompt_hashes["review_consolidate.md"] = _prompt_hash("review_consolidate.md")
    metadata = ReviewRunMetadata(
        sample_seed=seed,
        publications_sample_size=publications,
        recipes_per_pub=recipes_per_pub,
        sampled_publications=selected_publications,
        sampled_recipes=sampled_recipes,
        personas=[reviewer.name for reviewer in reviewers],
        model_config_by_role={
            "review": ModelRunConfig(
                model=settings.review.model,
                temperature=settings.review.temperature,
                max_retries=settings.review.max_retries,
            ),
            "consolidate": ModelRunConfig(
                model=settings.consolidate.model,
                temperature=settings.consolidate.temperature,
                max_retries=settings.consolidate.max_retries,
            ),
        },
        corpus_dir=str(corpus_dir),
        no_process=no_process,
        prompt_hashes=prompt_hashes,
        workspace_dir=str(workspace_store.data_dir) if workspace_store is not None else None,
        workspace_publications=workspace_publications,
    )

    all_findings: list[ReviewFinding] = []
    futures = []
    with ThreadPoolExecutor(
        max_workers=min(8, max(1, len(reviewers) * sum(len(v) for v in sampled_recipes.values())))
    ) as executor:
        for publication_id_str, recipe_ids in sampled_recipes.items():
            publication_id = int(publication_id_str)
            review_store = stores_by_publication[publication_id]
            pdf_bytes_by_recipe = {
                recipe_id: _recipe_pdf_bytes(review_store, publication_id, recipe_id) for recipe_id in recipe_ids
            }
            for recipe_id in recipe_ids:
                for reviewer in reviewers:
                    futures.append(
                        executor.submit(
                            _run_single_reviewer,
                            review_store,
                            reviewer,
                            publication_id=publication_id,
                            recipe_id=recipe_id,
                            dq_issues=dq_by_pub_recipe.get((publication_id, recipe_id), []),
                            max_findings=max_findings_per_recipe,
                            pdf_bytes=pdf_bytes_by_recipe[recipe_id],
                        )
                    )
        for future in as_completed(futures):
            result = future.result()
            all_findings.extend(result.findings)

    consolidated = _consolidate_findings(metadata, all_findings)
    artifact = ReviewRunArtifact(metadata=metadata, findings=all_findings, consolidated=consolidated)
    per_publication_files = _write_artifacts(artifact, output_paths)
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    return ReviewRunResult(artifact=artifact, output_paths=output_paths, per_publication_files=per_publication_files)
