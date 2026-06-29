import json
import logging

from pydantic import BaseModel, Field

from mexipes.config import settings
from mexipes.llm import call_llm, load_prompt
from mexipes.schemas import RewrittenRecipe, recipe_time
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


class TotalTimeEstimate(BaseModel):
    total_time: str = Field(
        ...,
        description=(
            "Tiempo total (uno de: Menos de 30 min, 30-60 min, 1-2 horas, "
            "2+ horas, Desconocido, N/A)"
        ),
    )


def _infer_total_time_from_recipe(rewritten: RewrittenRecipe) -> str:
    prompt_template = load_prompt("infer_total_time.md")
    prompt = (
        f"{prompt_template}\n\n"
        f"RECETA:\n"
        f"Título: {rewritten.title}\n"
        f"Rendimiento: {rewritten.yields or 'null'}\n"
        f"Ingredientes:\n{rewritten.ingredients}\n"
        f"Instrucciones:\n{rewritten.instructions}\n"
    )
    result = call_llm(
        model=settings.tagging.model,
        response_model=TotalTimeEstimate,
        prompt=prompt,
        temperature=settings.tagging.temperature,
        max_retries=settings.tagging.max_retries,
    )
    normalized = recipe_time.normalize_total_time(result.total_time)
    return normalized or "Desconocido"


def ensure_total_time(store: RecipeStore, publication_id: int, recipe_id: int) -> RewrittenRecipe:
    """Ensure rewritten.json has total_time: backfill from legacy tags or infer via LLM."""
    rewritten = store.load_stage_output(publication_id, recipe_id, "rewritten", RewrittenRecipe)
    if not rewritten:
        raise ValueError(f"No rewritten recipe data found for Publication {publication_id}, Recipe {recipe_id}")

    if rewritten.total_time:
        return rewritten

    tags_path = store.get_recipe_dir(publication_id, recipe_id) / "tags.json"
    if tags_path.exists():
        try:
            tags_data = json.loads(tags_path.read_text(encoding="utf-8"))
            legacy_time = tags_data.get("total_time")
            if legacy_time:
                normalized = recipe_time.normalize_total_time(legacy_time)
                if normalized:
                    rewritten.total_time = normalized
                    store.save_stage_output(publication_id, recipe_id, "rewritten", rewritten)
                    logger.info(
                        "Backfilled total_time from legacy tags for Publication %s, Recipe %s: %s",
                        publication_id,
                        recipe_id,
                        normalized,
                    )
                    return rewritten
        except (json.JSONDecodeError, OSError):
            pass

    logger.info("Inferring total_time for Publication %s, Recipe %s...", publication_id, recipe_id)
    rewritten.total_time = _infer_total_time_from_recipe(rewritten)
    store.save_stage_output(publication_id, recipe_id, "rewritten", rewritten)
    logger.info(
        "Inferred total_time for Publication %s, Recipe %s: %s",
        publication_id,
        recipe_id,
        rewritten.total_time,
    )
    return rewritten
