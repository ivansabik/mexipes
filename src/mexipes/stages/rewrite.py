import logging

from mexipes.config import settings
from mexipes.llm import call_llm, load_prompt
from mexipes.schemas import ExtractedRecipe, RecipeStatus, RewrittenRecipe
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


def rewrite_recipe(store: RecipeStore, publication_id: int, recipe_id: int) -> RewrittenRecipe:
    """Stage 3: Rewrites the recipe in its original Spanish to be copyright-compliant.

    Preserves ingredients verbatim and produces a minimal neutral paraphrase of instructions.
    """
    logger.info(f"Rewriting Recipe {recipe_id} in Publication {publication_id}...")

    # Load extracted data
    extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
    if not extracted:
        raise ValueError(f"No extracted recipe data found for Publication {publication_id}, Recipe {recipe_id}")

    prompt_template = load_prompt("rewrite_recipe.md")

    prompt = prompt_template.format(
        title=extracted.title,
        ingredients=extracted.ingredients,
        instructions=extracted.instructions,
        yields=extracted.yields or "null",
    )

    rewritten = call_llm(
        model=settings.rewrite.model,
        response_model=RewrittenRecipe,
        prompt=prompt,
        temperature=settings.rewrite.temperature,
        max_retries=settings.rewrite.max_retries,
    )

    # Save to storage
    store.save_stage_output(publication_id, recipe_id, "rewritten", rewritten)
    store.set_status(publication_id, recipe_id, RecipeStatus.REWRITTEN)
    logger.info(f"Successfully saved rewritten recipe for Publication {publication_id}, Recipe {recipe_id}")

    return rewritten
