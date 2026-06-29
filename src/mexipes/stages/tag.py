import logging

from mexipes.config import settings
from mexipes.inherited_tags import protein_inheritance_allowed
from mexipes.llm import call_llm, load_prompt
from mexipes.region import resolve_region
from mexipes.schemas import ExtractedRecipe, RecipeStatus, RecipeTagSet, RewrittenRecipe
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.health_nutrition_tags import format_health_nutrition_prompt_section
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


def _merge_inherited_tags(tags: RecipeTagSet, inherited) -> None:
    """Merge publication-level theme tags into a Spanish recipe tag set.

    Only fields in INHERITABLE_MERGE_FIELDS are merged. Region is handled by
    resolve_region(). Budget overrides the recipe value when inherited is set.
    """
    for field_name in vocab.INHERITABLE_MERGE_FIELDS:
        if field_name == "protein" and not protein_inheritance_allowed(inherited):
            continue

        value = getattr(inherited, field_name, None)
        if not value:
            continue

        recipe_value = getattr(tags, field_name, None)

        if field_name == "budget" and isinstance(value, str):
            normalized = vocab.normalize_value_to_es(field_name, value)
            setattr(tags, field_name, normalized)
            continue

        if isinstance(value, list):
            if recipe_value is None:
                continue
            normalized = vocab.normalize_list_to_es(field_name, value)
            for item in normalized:
                if item not in recipe_value:
                    recipe_value.append(item)
        elif isinstance(value, str) and not recipe_value:
            normalized = vocab.normalize_value_to_es(field_name, value)
            setattr(tags, field_name, normalized)


def _format_inherited_context(inherited) -> str:
    """Build tag-LLM context string for publication theme tags."""
    if not inherited:
        return ""

    inherited_items = []
    for field_name in vocab.INHERITABLE_MERGE_FIELDS:
        if field_name == "protein" and not protein_inheritance_allowed(inherited):
            continue
        value = getattr(inherited, field_name, None)
        if value:
            inherited_items.append(f"{field_name}: {value}")
    if inherited.region:
        inherited_items.append(f"region: {inherited.region}")

    if not inherited_items:
        return ""
    return f"Etiquetas globales/heredadas de esta publicación: {', '.join(inherited_items)}\n"


def tag_recipe(store: RecipeStore, publication_id: int, recipe_id: int) -> RecipeTagSet:
    """Tagging stage: classify the rewritten (Spanish) recipe using the taxonomy.

    Runs before localization so the localize stage can translate the tag set
    into English. Output values are Spanish canonical.
    """
    logger.info(f"Tagging Recipe {recipe_id} in Publication {publication_id}...")

    # Tag from the rewritten Spanish text (closest clean source to the original).
    extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
    rewritten = store.load_stage_output(publication_id, recipe_id, "rewritten", RewrittenRecipe)
    if not rewritten:
        raise ValueError(f"No rewritten recipe data found for Publication {publication_id}, Recipe {recipe_id}")

    # Load publication metadata for context
    metadata = store.load_publication_metadata(publication_id)
    pub_title = metadata.document_title if metadata else "Unknown"
    inherited_tags = metadata.inherited_tags if metadata else None

    inherited_context_str = _format_inherited_context(inherited_tags)

    prompt_template = load_prompt("tag_recipe.md")
    prompt_template = prompt_template.replace(
        "<!-- TAG_TAXONOMY -->",
        vocab.format_tag_taxonomy_prompt_section(),
    )
    prompt_template = prompt_template.replace(
        "<!-- HEALTH_NUTRITION_TAXONOMY -->",
        format_health_nutrition_prompt_section(),
    )

    prompt = (
        f"{prompt_template}\n\n"
        f"CONTEXTO:\n"
        f"Título de la publicación: '{pub_title}'\n"
        f"{inherited_context_str}\n"
        f"RECETA A ETIQUETAR (en español):\n"
        f"Título: {rewritten.title}\n"
        f"Rendimiento: {rewritten.yields or 'null'}\n"
        f"Ingredientes:\n{rewritten.ingredients}\n"
        f"Instrucciones:\n{rewritten.instructions}\n"
    )

    tags = call_llm(
        model=settings.tagging.model,
        response_model=RecipeTagSet,
        prompt=prompt,
        temperature=settings.tagging.temperature,
        max_retries=settings.tagging.max_retries,
    )

    # Safety net: drop values the model placed in the wrong closed-vocabulary field
    # (e.g. 'Botana' in course/occasion) so they do not leak untranslated into the
    # localized English tag set.
    tags = RecipeTagSet(**vocab.sanitize_recipe_tags_data(tags.model_dump()))

    if inherited_tags:
        _merge_inherited_tags(tags, inherited_tags)

    if metadata:
        recipe_region = tags.region or (extracted.region if extracted else None)
        page_start = extracted.page_start if extracted else None
        tags.region = resolve_region(recipe_region, page_start=page_start, metadata=metadata)

    store.save_stage_output(publication_id, recipe_id, "tags", tags)
    store.set_status(publication_id, recipe_id, RecipeStatus.TAGGED)
    logger.info(f"Successfully saved tags for Publication {publication_id}, Recipe {recipe_id}")

    return tags
