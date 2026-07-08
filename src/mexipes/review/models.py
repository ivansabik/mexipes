from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReviewSeverity = Literal["error", "warning", "info"]
SuggestedAction = Literal[
    "rerun_stage",
    "repair_field",
    "prompt_change",
    "dq_rule_change",
    "human_review",
    "no_action",
]


class ReviewFinding(BaseModel):
    """A single evidence-backed quality finding for one recipe field/stage."""

    publication_id: int
    recipe_id: int
    persona: str = Field(..., description="Reviewer persona that produced this finding")
    stage: str = Field(..., description="Pipeline stage or cross-stage area being reviewed")
    field: str = Field(..., description="Field or output area affected by the issue")
    finding_type: str = Field(..., description="Stable issue category, e.g. ocr_artifact or tag_semantic_error")
    severity: ReviewSeverity = "warning"
    confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Advisory LLM confidence only; use for ranking, not hard gating",
    )
    issue: str
    evidence: str = Field(..., description="Concrete source/output evidence for the issue")
    suggested_action: SuggestedAction
    rerun_stage: str | None = Field(None, description="Stage to rerun when suggested_action is rerun_stage")
    finding_key: str | None = Field(
        None,
        description="Stable key derived from publication, recipe, stage, field, and finding_type",
    )

    @model_validator(mode="after")
    def populate_finding_key(self) -> ReviewFinding:
        if not self.finding_key:
            self.finding_key = make_finding_key(
                self.publication_id,
                self.recipe_id,
                self.stage,
                self.field,
                self.finding_type,
            )
        return self


class RecipeReviewResult(BaseModel):
    """Findings for one reviewer against one recipe."""

    publication_id: int
    recipe_id: int
    persona: str
    findings: list[ReviewFinding] = Field(default_factory=list)


class ReviewGroup(BaseModel):
    """A consolidated set of related findings with one recommended next step."""

    title: str
    severity: ReviewSeverity = "warning"
    suggested_action: SuggestedAction
    finding_keys: list[str] = Field(default_factory=list)
    summary: str
    recommendation: str


class RerunRecommendation(BaseModel):
    """Targeted stage rerun recommended by the consolidator."""

    publication_id: int
    recipe_id: int
    stage: str
    reason: str


class ConsolidatedReview(BaseModel):
    """Cross-publication review summary and prioritized recommendations."""

    summary: str
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    grouped_findings: list[ReviewGroup] = Field(default_factory=list)
    recommended_reruns: list[RerunRecommendation] = Field(default_factory=list)
    prompt_improvements: list[str] = Field(default_factory=list)
    dq_code_improvements: list[str] = Field(default_factory=list)
    human_review: list[str] = Field(default_factory=list)


class ModelRunConfig(BaseModel):
    """Model settings used for one review role."""

    model: str
    temperature: float
    max_retries: int


class ReviewRunMetadata(BaseModel):
    """Reproducibility metadata embedded in review artifacts."""

    sample_seed: int | None = None
    publications_sample_size: int
    recipes_per_pub: int
    sampled_publications: list[int] = Field(default_factory=list)
    sampled_recipes: dict[str, list[int]] = Field(default_factory=dict)
    personas: list[str] = Field(default_factory=list)
    model_config_by_role: dict[str, ModelRunConfig] = Field(default_factory=dict)
    corpus_dir: str | None = None
    no_process: bool = False
    prompt_hashes: dict[str, str] = Field(default_factory=dict)
    workspace_dir: str | None = Field(
        None,
        description="Run-scoped store where sampled corpus PDFs were processed (never data/publications)",
    )
    workspace_publications: list[int] = Field(
        default_factory=list,
        description="Publication ids that live in workspace_dir instead of data/publications",
    )


class ReviewRunArtifact(BaseModel):
    """Full JSON payload written for a review run."""

    metadata: ReviewRunMetadata
    findings: list[ReviewFinding] = Field(default_factory=list)
    consolidated: ConsolidatedReview


def make_finding_key(publication_id: int, recipe_id: int, stage: str, field: str, finding_type: str) -> str:
    """Return a stable, low-cardinality key for tracking findings across runs."""
    parts = [publication_id, recipe_id, stage, field, finding_type]
    return ":".join(str(part).strip().lower().replace(" ", "_") for part in parts)
