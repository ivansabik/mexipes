import io
import random
from pathlib import Path

import fitz
from PIL import Image

from mexipes.pipeline.pdf_processor import (
    FULL_PAGE_BOX,
    get_substantial_page_images,
    resolve_photo_crop_box,
)


def _jpeg_bytes(width: int, height: int, *, seed: int) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (width, height))
    img.putdata([(rng.randint(40, 220), rng.randint(40, 220), rng.randint(40, 220)) for _ in range(width * height)])
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _write_two_image_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=500, height=500)
    page.insert_image(fitz.Rect(20, 80, 220, 480), stream=_jpeg_bytes(400, 800, seed=1))
    page.insert_image(fitz.Rect(280, 80, 480, 480), stream=_jpeg_bytes(400, 800, seed=2))
    page.insert_image(fitz.Rect(10, 10, 60, 40), stream=_jpeg_bytes(50, 30, seed=3))
    doc.save(path)
    doc.close()


def test_get_substantial_page_images_filters_small_and_sorts_reading_order(tmp_path: Path) -> None:
    pdf_path = tmp_path / "two_images.pdf"
    _write_two_image_pdf(pdf_path)

    images = get_substantial_page_images(pdf_path, 0)

    assert len(images) == 2
    assert all(image["coverage"] >= 0.12 for image in images)
    assert images[0]["box_2d"][1] < images[1]["box_2d"][1]


def test_resolve_photo_crop_box_uses_full_page_on_photo_only_spreads(tmp_path: Path) -> None:
    pdf_path = tmp_path / "photo_page.pdf"
    doc = fitz.open()
    page = doc.new_page(width=500, height=500)
    page.insert_image(fitz.Rect(0, 0, 500, 500), stream=_jpeg_bytes(500, 500, seed=5))
    doc.save(pdf_path)
    doc.close()

    images = get_substantial_page_images(pdf_path, 0)
    assert len(images) == 1
    assert resolve_photo_crop_box(pdf_path, 0, images[0]) == FULL_PAGE_BOX


def test_resolve_photo_crop_box_uses_embedded_bbox_on_mixed_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mixed.pdf"
    doc = fitz.open()
    page = doc.new_page(width=500, height=500)
    page.insert_text((40, 40), "Sopa con verduras ingredientes", fontsize=14)
    page.insert_image(fitz.Rect(50, 120, 450, 420), stream=_jpeg_bytes(400, 300, seed=4))
    doc.save(pdf_path)
    doc.close()

    images = get_substantial_page_images(pdf_path, 0)
    assert len(images) == 1
    crop = resolve_photo_crop_box(pdf_path, 0, images[0])
    assert crop != FULL_PAGE_BOX
    assert crop[0] >= 100
    assert crop[2] <= 900
