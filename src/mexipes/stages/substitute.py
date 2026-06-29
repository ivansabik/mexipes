import logging

from mexipes.config import settings
from mexipes.llm import call_llm, load_prompt
from mexipes.schemas import LocalizedRecipe, RecipeStatus, SubstitutionsResult
from mexipes.schemas.pantry_substitutions import format_pantry_substitutions_prompt_section
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


def substitute_ingredients(store: RecipeStore, publication_id: int, recipe_id: int) -> SubstitutionsResult:
    """Stage 7: Recommends substitutions for ingredients that are hard to source in the US/Canada."""
    logger.info(f"Adding ingredient substitutions for Recipe {recipe_id} in Publication {publication_id}...")

    # Load localized recipe for ingredients context
    localized = store.load_stage_output(publication_id, recipe_id, "localized", LocalizedRecipe)
    if not localized:
        raise ValueError(f"No localized recipe data found for Publication {publication_id}, Recipe {recipe_id}")

    prompt_template = load_prompt("substitute_ingredients.md")
    prompt_template = prompt_template.replace(
        "<!-- PANTRY_GUIDE -->",
        format_pantry_substitutions_prompt_section(),
    )

    prompt = (
        f"{prompt_template}\n\n"
        f"RECIPE INGREDIENTS TO ANALYZE:\n"
        f"Title: {localized.title_en}\n"
        f"Ingredients:\n{localized.ingredients_en}\n"
    )

    substitutions = call_llm(
        model=settings.substitution.model,
        response_model=SubstitutionsResult,
        prompt=prompt,
        temperature=settings.substitution.temperature,
        max_retries=settings.substitution.max_retries,
    )

    # Save to storage
    store.save_stage_output(publication_id, recipe_id, "substitutions", substitutions)

    # This is the final stage of the pipeline, transition to READY
    store.set_status(publication_id, recipe_id, RecipeStatus.READY)
    logger.info(f"Successfully saved substitutions and marked Recipe {recipe_id} as READY.")

    return substitutions
