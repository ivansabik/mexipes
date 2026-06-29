import logging

from mexipes.config import settings
from mexipes.llm import call_llm, load_prompt
from mexipes.schemas import ExtractedRecipe, ImageDescription, ImageDescriptionsResult, RecipeStatus
from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


def describe_images(store: RecipeStore, publication_id: int, recipe_id: int) -> ImageDescriptionsResult:
    """Stage 4: Processes each cropped photograph for the recipe, generating descriptions and suggested prompts."""
    logger.info(f"Describing images for Recipe {recipe_id} in Publication {publication_id}...")

    # Load extracted data
    extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
    if not extracted:
        raise ValueError(f"No extracted recipe data found for Publication {publication_id}, Recipe {recipe_id}")

    images_dir = store.get_images_dir(publication_id, recipe_id)
    descriptions = []

    # Check if there are any crops
    if not extracted.image_crops or extracted.images_count == 0:
        logger.info(f"No images found for Recipe {recipe_id}, skipping LLM description.")
        result = ImageDescriptionsResult(descriptions=[])
        store.save_stage_output(publication_id, recipe_id, "images_described", result)
        store.set_status(publication_id, recipe_id, RecipeStatus.IMAGES_DESCRIBED)
        return result

    prompt_template = load_prompt("describe_image.md")

    # Iterate through each image crop
    for idx in range(len(extracted.image_crops)):
        image_filename = f"{idx + 1}.png"
        image_path = images_dir / image_filename

        if not image_path.exists():
            logger.warning(f"Expected crop file {image_path} does not exist. Skipping.")
            continue

        logger.info(f"  Analyzing image crop {image_filename}...")

        try:
            desc = call_llm(
                model=settings.describe.model,
                response_model=ImageDescription,
                prompt=prompt_template,
                image_path=image_path,
                temperature=settings.describe.temperature,
                max_retries=settings.describe.max_retries,
            )
            # Ensure the image file name is set correctly
            desc.image_file = image_filename
            descriptions.append(desc)
        except Exception as e:
            logger.error(f"Failed to describe image {image_filename}: {e}")

    result = ImageDescriptionsResult(descriptions=descriptions)

    # Save to storage
    store.save_stage_output(publication_id, recipe_id, "images_described", result)
    store.set_status(publication_id, recipe_id, RecipeStatus.IMAGES_DESCRIBED)
    logger.info(
        f"Successfully described {len(descriptions)} images for Publication {publication_id}, Recipe {recipe_id}"
    )

    return result
