import logging

from mexipes.config import settings
from mexipes.llm import call_llm, load_prompt
from mexipes.schemas import LocalizedRecipe, RecipeStatus, RecipeTagSet, RewrittenRecipe, recipe_time
from mexipes.schemas import tag_vocabularies as vocab
from mexipes.schemas.tags import TagTranslations
from mexipes.storage import RecipeStore
from mexipes.text_utils import normalize_title_en

logger = logging.getLogger(__name__)


def _deterministic_localize(data: dict) -> tuple[dict, set[str]]:
    """Map Spanish tag values to English via vocabulary lookup.

    Returns the partially localized data and the set of open-field Spanish values
    that were not found in the controlled vocabulary (candidates for LLM translation).
    """
    out = dict(data)
    leftovers: set[str] = set()

    for field in vocab.VOCABULARIES:
        if field not in data:
            continue
        mapping = vocab.es_to_en(field)
        if field in vocab.SCALAR_FIELDS:
            value_es = data[field]
            if value_es is None:
                continue
            if field in vocab.OPEN_FIELDS and value_es not in mapping:
                leftovers.add(value_es)
            out[field] = mapping.get(value_es, value_es)
        else:
            localized: list[str] = []
            for value_es in data[field] or []:
                if field in vocab.OPEN_FIELDS and value_es not in mapping:
                    leftovers.add(value_es)
                localized.append(mapping.get(value_es, value_es))
            out[field] = localized

    return out, leftovers


def _translate_leftover_tags(leftovers: set[str]) -> dict[str, str]:
    """Translate open-vocabulary Spanish tag values to English via a small LLM call."""
    if not leftovers:
        return {}

    prompt_template = load_prompt("localize_tags.md")
    terms = sorted(leftovers)
    prompt = f"{prompt_template}\n\nSPANISH TERMS TO TRANSLATE:\n" + "\n".join(f"- {term}" for term in terms)

    result = call_llm(
        model=settings.localize.model,
        response_model=TagTranslations,
        prompt=prompt,
        temperature=settings.localize.temperature,
        max_retries=settings.localize.max_retries,
    )

    return {item.es: item.en for item in result.translations}


def _apply_leftover_translations(data: dict, translations: dict[str, str]) -> dict:
    """Replace passthrough Spanish values in open fields with LLM translations."""
    if not translations:
        return data

    out = dict(data)
    for field in vocab.OPEN_FIELDS:
        if field not in out or field not in vocab.VOCABULARIES:
            continue
        if field in vocab.SCALAR_FIELDS:
            value = out[field]
            if value and value in translations:
                out[field] = translations[value]
        else:
            out[field] = [translations.get(v, v) for v in (out[field] or [])]
    return out


def localize_tag_set(tags: RecipeTagSet) -> RecipeTagSet:
    """Translate a Spanish canonical tag set to English.

    Closed-vocabulary fields (including ``health_nutrition``) are mapped
    deterministically. Open-field values not in the vocabulary are translated
    via a small LLM call; skipped when there are no leftovers.
    """
    data = tags.model_dump()
    out, leftovers = _deterministic_localize(data)
    if leftovers:
        logger.debug("Localizing %d open-field tag value(s) via LLM: %s", len(leftovers), sorted(leftovers))
        translations = _translate_leftover_tags(leftovers)
        out = _apply_leftover_translations(out, translations)
    return RecipeTagSet(**out)


def localize_recipe(store: RecipeStore, publication_id: int, recipe_id: int) -> LocalizedRecipe:
    """Localize the rewritten recipe (Spanish -> English) and translate its tags.

    Runs after the tagging stage, so it also maps the Spanish tag set into an
    English ``localized_tags`` output using vocabulary lookup plus LLM fallback
    for free-form open-field values.
    """
    logger.info(f"Localizing Recipe {recipe_id} in Publication {publication_id}...")

    # Load rewritten data (required for recipe LLM localization unless already localized).
    rewritten = store.load_stage_output(publication_id, recipe_id, "rewritten", RewrittenRecipe)
    existing_localized = store.load_stage_output(publication_id, recipe_id, "localized", LocalizedRecipe)

    if rewritten:
        prompt_template = load_prompt("localize_recipe.md")

        prompt = (
            f"{prompt_template}\n\n"
            f"RECIPE TO LOCALIZE:\n"
            f"Title: {rewritten.title}\n"
            f"Yields: {rewritten.yields or 'null'}\n"
            f"Total time: {rewritten.total_time or 'null'}\n"
            f"Ingredients:\n{rewritten.ingredients}\n"
            f"Instructions:\n{rewritten.instructions}\n"
        )

        localized = call_llm(
            model=settings.localize.model,
            response_model=LocalizedRecipe,
            prompt=prompt,
            temperature=settings.localize.temperature,
            max_retries=settings.localize.max_retries,
        )

        localized.title_en = normalize_title_en(localized.title_en)
        localized.total_time_en = recipe_time.es_to_en(rewritten.total_time)
        store.save_stage_output(publication_id, recipe_id, "localized", localized)
    elif existing_localized:
        logger.info("No rewritten recipe data; reusing existing localized.json and refreshing localized tags only.")
        localized = existing_localized
    else:
        raise ValueError(f"No rewritten recipe data found for Publication {publication_id}, Recipe {recipe_id}")

    # Translate the (Spanish) tag set into English.
    tags = store.load_stage_output(publication_id, recipe_id, "tags", RecipeTagSet)
    if tags:
        localized_tags = localize_tag_set(tags)
        store.save_stage_output(publication_id, recipe_id, "localized_tags", localized_tags)
    else:
        logger.warning(
            f"No tags found for Publication {publication_id}, Recipe {recipe_id}; "
            "skipping tag localization (run the tag stage first)."
        )

    store.set_status(publication_id, recipe_id, RecipeStatus.LOCALIZED)
    logger.info(f"Successfully saved localized recipe for Publication {publication_id}, Recipe {recipe_id}")

    return localized
