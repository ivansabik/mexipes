import logging
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)


def extract_chunk_pdf_bytes(pdf_path: Path, start_page: int, end_page: int) -> bytes:
    """Extract a range of pages (0-based start_page to end_page inclusive) from PDF and return bytes."""
    with fitz.open(pdf_path) as src_doc:
        total_pages = len(src_doc)
        s_page = max(0, start_page)
        e_page = min(total_pages - 1, end_page)

        if s_page > e_page:
            raise ValueError(f"Invalid page range: {start_page} to {end_page} (Total pages: {total_pages})")

        with fitz.open() as dest_doc:
            dest_doc.insert_pdf(src_doc, from_page=s_page, to_page=e_page)
            return dest_doc.write()


def get_page_text_rects(pdf_path: Path, page_index: int) -> list[tuple[int, int, int, int]]:
    """Return bounding boxes of text blocks on a page, normalized to a 0-1000 grid.

    Each rect is ``(ymin, xmin, ymax, xmax)`` to match the ``box_2d`` convention.
    Empty/whitespace-only blocks are skipped. Returns ``[]`` for out-of-range
    pages or pages with no extractable text (e.g. text baked into a raster image).
    """
    with fitz.open(pdf_path) as doc:
        if page_index < 0 or page_index >= len(doc):
            return []
        page = doc[page_index]
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            return []
        rects: list[tuple[int, int, int, int]] = []
        for block in page.get_text("blocks"):
            x0, y0, x1, y1 = block[:4]
            text = block[4] if len(block) > 4 else ""
            if not str(text).strip():
                continue
            rects.append(
                (
                    int(round(y0 / rect.height * 1000)),
                    int(round(x0 / rect.width * 1000)),
                    int(round(y1 / rect.height * 1000)),
                    int(round(x1 / rect.width * 1000)),
                )
            )
        return rects


def render_image_crop_bytes(pdf_path: Path, page_index: int, box_2d: list[int], dpi: int = 300) -> bytes:
    """Render a normalized [0-1000] crop from a PDF page and return PNG bytes.

    box_2d is [ymin, xmin, ymax, xmax].
    """
    if len(box_2d) != 4:
        raise ValueError(f"box_2d must have exactly 4 values (got {box_2d})")

    ymin, xmin, ymax, xmax = box_2d

    with fitz.open(pdf_path) as doc:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"Page index {page_index} out of range for PDF of length {len(doc)}")

        page = doc[page_index]
        rect = page.rect

        # Convert normalized coordinates [0-1000] back to page points (1/72 inch)
        y0 = (ymin / 1000.0) * rect.height
        x0 = (xmin / 1000.0) * rect.width
        y1 = (ymax / 1000.0) * rect.height
        x1 = (xmax / 1000.0) * rect.width

        crop_rect = fitz.Rect(x0, y0, x1, y1)
        pix = page.get_pixmap(clip=crop_rect, dpi=dpi)
        return pix.tobytes("png")


def save_image_crop(pdf_path: Path, page_index: int, box_2d: list[int], dest_path: Path, dpi: int = 300) -> None:
    """Crops a specific portion of a page based on a normalized [0-1000] box and saves it.

    box_2d is [ymin, xmin, ymax, xmax].
    """
    png_bytes = render_image_crop_bytes(pdf_path, page_index, box_2d, dpi=dpi)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(png_bytes)
    logger.debug(f"Saved image crop from page {page_index + 1} to {dest_path}")
