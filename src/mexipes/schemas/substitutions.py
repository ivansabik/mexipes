from pydantic import BaseModel, Field


class IngredientSubstitution(BaseModel):
    original: str = Field(..., description="The original ingredient in Spanish or localized English")
    substitute: str = Field(..., description="The recommended replacement ingredient")
    notes: str = Field(
        ...,
        description="Explanation of why this replacement works, how it affects flavor/texture, and measurement adjustments",
    )
    available_in: list[str] = Field(
        default_factory=list,
        description="Regions where this substitute is commonly sold, e.g. ['US', 'Canada']",
    )


class SubstitutionsResult(BaseModel):
    """Output of Stage 7 (substitutions)"""

    substitutions: list[IngredientSubstitution] = Field(default_factory=list)
