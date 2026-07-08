import io
import random
from pathlib import Path

import fitz
from PIL import Image

from mexipes.schemas import ExtractedRecipe
from mexipes.schemas.recipe import RecipeStatus
from mexipes.stages.extract import harvest_embedded_photos
from mexipes.storage import RecipeStore


def _jpeg_bytes(width: int, height: int, *, seed: int) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (width, height))
    img.putdata([(rng.randint(40, 220), rng.randint(40, 220), rng.randint(40, 220)) for _ in range(width * height)])
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _write_two_image_pdf(path: Path) -> None:
    doc = fitz.open()
    # Pages 1-3 are blank placeholders (skipped by harvest promo filter).
    for _ in range(3):
        doc.new_page(width=500, height=500)
    page = doc.new_page(width=500, height=500)
    page.insert_image(fitz.Rect(20, 80, 220, 480), stream=_jpeg_bytes(400, 800, seed=11))
    page.insert_image(fitz.Rect(280, 80, 480, 480), stream=_jpeg_bytes(400, 800, seed=12))
    doc.save(path)
    doc.close()


def _seed_publication(tmp_path: Path) -> tuple[RecipeStore, int, Path]:
    store = RecipeStore(tmp_path)
    publication_id = 1
    publication_dir = store.get_publication_dir(publication_id)
    pdf_path = publication_dir / "source.pdf"
    _write_two_image_pdf(pdf_path)

    for recipe_id, title in ((1, "Left recipe"), (2, "Right recipe")):
        extracted = ExtractedRecipe(
            title=title,
            ingredients="test",
            instructions="test",
            page_start=4,
            page_end=4,
            images_count=0,
            image_crops=[],
        )
        store.save_stage_output(publication_id, recipe_id, "extracted", extracted)
        store.set_status(publication_id, recipe_id, RecipeStatus.EXTRACTED)

    return store, publication_id, pdf_path


def test_harvest_embedded_photos_assigns_distinct_images(tmp_path: Path) -> None:
    store, publication_id, pdf_path = _seed_publication(tmp_path)

    attached = harvest_embedded_photos(store, publication_id, pdf_path, assigned_xrefs=set())

    assert attached == 2
    left = store.load_stage_output(publication_id, 1, "extracted", ExtractedRecipe)
    right = store.load_stage_output(publication_id, 2, "extracted", ExtractedRecipe)
    assert left is not None and right is not None
    assert left.images_count == 1
    assert right.images_count == 1
    # Two side-by-side photos on a text-free page → crop each embedded image, not full page.
    assert left.image_crops[0].box_2d != [0, 0, 1000, 1000]
    assert right.image_crops[0].box_2d != [0, 0, 1000, 1000]
    assert left.image_crops[0].box_2d != right.image_crops[0].box_2d
    assert (store.get_images_dir(publication_id, 1) / "1.png").exists()
    assert (store.get_images_dir(publication_id, 2) / "1.png").exists()


def test_harvest_picks_image_matching_recipe_zone_on_two_up_page(tmp_path: Path) -> None:
    """On a two-up page, each recipe gets the photo nearest its text block."""
    store = RecipeStore(tmp_path)
    publication_id = 1
    pdf_path = store.get_publication_dir(publication_id) / "source.pdf"

    doc = fitz.open()
    for _ in range(3):
        doc.new_page(width=500, height=500)
    page = doc.new_page(width=500, height=500)
    page.insert_text((300, 40), "En salsa de manzana", fontsize=12)
    page.insert_text((300, 60), "8 costillas de cerdo 1 cebolla", fontsize=10)
    page.insert_text((40, 280), "BBQ", fontsize=14)
    page.insert_text((40, 300), "1 costillar de cerdo de 1 kilo", fontsize=10)
    page.insert_image(fitz.Rect(20, 60, 240, 260), stream=_jpeg_bytes(220, 200, seed=31))
    page.insert_image(fitz.Rect(260, 300, 480, 500), stream=_jpeg_bytes(220, 200, seed=32))
    doc.save(pdf_path)
    doc.close()

    top = ExtractedRecipe(
        title="En salsa de manzana",
        ingredients="8 costillas de cerdo\n1 cebolla",
        instructions="test top",
        page_start=4,
        page_end=4,
        images_count=0,
        image_crops=[],
    )
    bottom = ExtractedRecipe(
        title="BBQ",
        ingredients="1 costillar de cerdo de 1 kilo",
        instructions="test bottom",
        page_start=4,
        page_end=4,
        images_count=0,
        image_crops=[],
    )
    store.save_stage_output(publication_id, 1, "extracted", top)
    store.save_stage_output(publication_id, 2, "extracted", bottom)
    store.set_status(publication_id, 1, RecipeStatus.EXTRACTED)
    store.set_status(publication_id, 2, RecipeStatus.EXTRACTED)

    attached = harvest_embedded_photos(store, publication_id, pdf_path, assigned_xrefs=set())

    assert attached == 2
    top_recipe = store.load_stage_output(publication_id, 1, "extracted", ExtractedRecipe)
    bottom_recipe = store.load_stage_output(publication_id, 2, "extracted", ExtractedRecipe)
    assert top_recipe is not None and bottom_recipe is not None
    assert top_recipe.image_crops[0].box_2d[0] < 200
    assert bottom_recipe.image_crops[0].box_2d[0] > 200
    assert not (store.get_images_dir(publication_id, 1) / "2.png").exists()
    assert not (store.get_images_dir(publication_id, 2) / "2.png").exists()


def test_harvest_prefers_photo_only_page_at_anchor_over_next_mixed_page(tmp_path: Path) -> None:
    """Photo-only spread on the recipe page beats a closer inline photo on the next page."""
    store = RecipeStore(tmp_path)
    publication_id = 1
    pdf_path = store.get_publication_dir(publication_id) / "source.pdf"

    doc = fitz.open()
    for _ in range(3):
        doc.new_page(width=500, height=500)
    photo_page = doc.new_page(width=500, height=500)
    photo_page.insert_image(fitz.Rect(0, 0, 500, 500), stream=_jpeg_bytes(500, 500, seed=21))
    mixed_page = doc.new_page(width=500, height=500)
    mixed_page.insert_text((40, 40), "Con tequila costillas de cerdo", fontsize=12)
    mixed_page.insert_image(fitz.Rect(20, 80, 480, 320), stream=_jpeg_bytes(460, 240, seed=22))
    mixed_page.insert_image(fitz.Rect(20, 340, 480, 480), stream=_jpeg_bytes(460, 140, seed=23))
    doc.save(pdf_path)
    doc.close()

    for recipe_id, title, page in ((1, "Picantes", 4), (2, "Con tequila", 5)):
        extracted = ExtractedRecipe(
            title=title,
            ingredients="costillas de cerdo" if recipe_id == 2 else "costillitas de cerdo",
            instructions="test",
            page_start=page,
            page_end=page,
            images_count=0,
            image_crops=[],
        )
        store.save_stage_output(publication_id, recipe_id, "extracted", extracted)
        store.set_status(publication_id, recipe_id, RecipeStatus.EXTRACTED)

    attached = harvest_embedded_photos(store, publication_id, pdf_path, assigned_xrefs=set())

    assert attached == 2
    picantes = store.load_stage_output(publication_id, 1, "extracted", ExtractedRecipe)
    tequila = store.load_stage_output(publication_id, 2, "extracted", ExtractedRecipe)
    assert picantes is not None and tequila is not None
    assert picantes.image_crops[0].chunk_page_index == 4
    assert picantes.image_crops[0].box_2d == [0, 0, 1000, 1000]
    assert tequila.image_crops[0].chunk_page_index == 5
    assert tequila.image_crops[0].box_2d[0] < 200


def test_harvest_embedded_photos_respects_assigned_xrefs(tmp_path: Path) -> None:
    store, publication_id, pdf_path = _seed_publication(tmp_path)
    with fitz.open(pdf_path) as doc:
        page = doc[3]
        infos = page.get_image_info(xrefs=True)
        left_xref = int(min(infos, key=lambda info: info["bbox"][0])["xref"])

    attached = harvest_embedded_photos(store, publication_id, pdf_path, assigned_xrefs={left_xref})

    assert attached == 1
    recipe = store.load_stage_output(publication_id, 1, "extracted", ExtractedRecipe)
    assert recipe is not None
    assert recipe.images_count == 1
    still_empty = store.load_stage_output(publication_id, 2, "extracted", ExtractedRecipe)
    assert still_empty is not None
    assert still_empty.images_count == 0
