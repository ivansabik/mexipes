from enum import Enum

from pydantic import BaseModel, Field


def validate_box_2d(box_2d: list[int]) -> bool:
    """Return True when box_2d is a valid normalized crop bounding box."""
    if len(box_2d) != 4:
        return False
    ymin, xmin, ymax, xmax = box_2d
    if not all(isinstance(v, int) and 0 <= v <= 1000 for v in box_2d):
        return False
    return ymax > ymin and xmax > xmin


class RecipeStatus(str, Enum):
    EXTRACTED = "extracted"
    REWRITTEN = "rewritten"
    IMAGES_DESCRIBED = "images_described"
    LOCALIZED = "localized"
    TAGGED = "tagged"
    SUBSTITUTIONS_ADDED = "substitutions_added"
    READY = "ready"
    FAILED = "failed"


class ImageCrop(BaseModel):
    chunk_page_index: int
    box_2d: list[int]  # [ymin, xmin, ymax, xmax] normalized to 1000x1000


class ExtractedRecipe(BaseModel):
    """Output of Stage 2 (extraction)"""

    recipe_number: int | None = None
    title: str = Field(..., description="Original Spanish recipe title")
    region: str | None = Field(None, description="Inferred region of the recipe")
    yields: str | None = Field(None, description="Serving yield information in Spanish")
    ingredients: str = Field(..., description="List of ingredients in Spanish")
    instructions: str = Field(..., description="Preparation steps in Spanish")
    page_start: int | None = None
    page_end: int | None = None
    images_count: int = 0
    image_crops: list[ImageCrop] = Field(default_factory=list)
    has_multiple_recipes: bool = False


class RewrittenRecipe(BaseModel):
    """Output of Stage 3 (rewriting for copyright compliance)"""

    title: str = Field(..., description="Original Spanish recipe title")
    yields: str | None = Field(None, description="Yield information in Spanish")
    ingredients: str = Field(..., description="Ingredients reproduced verbatim from the source")
    instructions: str = Field(..., description="Neutral close-paraphrase of instructions in Spanish")


class ImageDescription(BaseModel):
    """Output of Stage 4 (image description)"""

    image_file: str
    description: str = Field(..., description="Detailed description of the image content")
    style_notes: str = Field(..., description="Plating, lighting, and angle notes")
    suggested_prompt: str = Field(..., description="Prompt generated for replicating this food image")


class LocalizedRecipe(BaseModel):
    """Output of Stage 5 (localization to English)"""

    title_en: str = Field(..., description="English translated title")
    slug: str = Field(..., description="URL-friendly slug (e.g. mole-negro-oaxaqueno)")
    yields_en: str | None = Field(None, description="Serving yield in English")
    ingredients_en: str = Field(..., description="Ingredients translated to English")
    instructions_en: str = Field(..., description="Instructions translated to English")


class ImageDescriptionsResult(BaseModel):
    """Output of Stage 4 (contains multiple ImageDescription objects)"""

    descriptions: list[ImageDescription] = Field(default_factory=list)
