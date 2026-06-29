from pathlib import Path

from mexipes.schemas import ExtractedRecipe, ImageCrop, ImageDescriptionsResult
from mexipes.stages.extract import strip_generic_recipe_images
from mexipes.storage import RecipeStore


def _write_png(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_strip_generic_recipe_images_removes_repeated_template(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path)
    publication_id = 1
    shared_image = b"generic-sidebar-template"

    for recipe_id in (1, 7):
        extracted = ExtractedRecipe(
            title=f"Recipe {recipe_id}",
            ingredients="test",
            instructions="test",
            images_count=1,
            image_crops=[ImageCrop(chunk_page_index=1, box_2d=[0, 499, 1000, 1000])],
        )
        store.save_stage_output(publication_id, recipe_id, "extracted", extracted)
        _write_png(store.get_images_dir(publication_id, recipe_id) / "1.png", shared_image)

    cleaned = strip_generic_recipe_images(store, publication_id)

    assert cleaned == 2
    for recipe_id in (1, 7):
        extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
        assert extracted is not None
        assert extracted.images_count == 0
        assert extracted.image_crops == []
        assert not (store.get_images_dir(publication_id, recipe_id) / "1.png").exists()


def test_strip_generic_recipe_images_keeps_unique_recipe_photos(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path)
    publication_id = 1

    for recipe_id, image_bytes in ((1, b"recipe-a-photo"), (2, b"recipe-b-photo")):
        extracted = ExtractedRecipe(
            title=f"Recipe {recipe_id}",
            ingredients="test",
            instructions="test",
            images_count=1,
            image_crops=[ImageCrop(chunk_page_index=1, box_2d=[0, 499, 1000, 1000])],
        )
        store.save_stage_output(publication_id, recipe_id, "extracted", extracted)
        _write_png(store.get_images_dir(publication_id, recipe_id) / "1.png", image_bytes)

    cleaned = strip_generic_recipe_images(store, publication_id)

    assert cleaned == 0
    for recipe_id in (1, 2):
        extracted = store.load_stage_output(publication_id, recipe_id, "extracted", ExtractedRecipe)
        assert extracted is not None
        assert extracted.images_count == 1
        assert (store.get_images_dir(publication_id, recipe_id) / "1.png").exists()


def test_strip_generic_recipe_images_clears_images_described(tmp_path: Path) -> None:
    store = RecipeStore(tmp_path)
    publication_id = 1
    shared_image = b"generic-sidebar-template"

    for recipe_id in (1, 2):
        extracted = ExtractedRecipe(
            title=f"Recipe {recipe_id}",
            ingredients="test",
            instructions="test",
            images_count=1,
            image_crops=[ImageCrop(chunk_page_index=1, box_2d=[0, 499, 1000, 1000])],
        )
        store.save_stage_output(publication_id, recipe_id, "extracted", extracted)
        store.save_stage_output(
            publication_id,
            recipe_id,
            "images_described",
            ImageDescriptionsResult(descriptions=[]),
        )
        _write_png(store.get_images_dir(publication_id, recipe_id) / "1.png", shared_image)

    strip_generic_recipe_images(store, publication_id)

    for recipe_id in (1, 2):
        described = store.load_stage_output(
            publication_id, recipe_id, "images_described", ImageDescriptionsResult
        )
        assert described is not None
        assert described.descriptions == []
