"""Deterministic image quality assessment for recipe photo crops."""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageFilter, ImageStat

from mexipes.config import ImageQualityConfig

# 3x3 Laplacian kernel for edge/sharpness detection
_LAPLACIAN_KERNEL = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0)

# Downscale bound for background/colorfulness statistics (keeps large crops fast).
_STATS_MAX_SIZE = (512, 512)

# Half-width of the luminance window around the modal peak counted as "background".
_BACKGROUND_PEAK_WINDOW = 16


@dataclass(frozen=True)
class ImageQualityMetrics:
    width: int
    height: int
    sharpness: float
    brightness: float
    background_fraction: float = 0.0
    colorfulness: float = 100.0


def _background_fraction(gray: Image.Image) -> float:
    """Fraction of pixels within a narrow luminance window around the modal peak.

    Scanned text pages are dominated by a single paper tone, so this fraction is
    high (~0.6-0.95); photographs spread luminance across the histogram.
    """
    hist = gray.histogram()
    total = sum(hist)
    if total == 0:
        return 0.0
    peak = max(range(256), key=hist.__getitem__)
    lo = max(0, peak - _BACKGROUND_PEAK_WINDOW)
    hi = min(255, peak + _BACKGROUND_PEAK_WINDOW)
    return sum(hist[lo : hi + 1]) / total


def _colorfulness(rgb: Image.Image) -> float:
    """Hasler & Suesstrunk colorfulness metric (0 = grayscale, food photos ~50+)."""
    r, g, b = rgb.split()
    rg = ImageChops.difference(r, g)
    half_rg = ImageChops.add(r, g, scale=2.0)
    yb = ImageChops.difference(half_rg, b)
    rg_stat = ImageStat.Stat(rg)
    yb_stat = ImageStat.Stat(yb)
    std_root = math.hypot(rg_stat.stddev[0], yb_stat.stddev[0])
    mean_root = math.hypot(rg_stat.mean[0], yb_stat.mean[0])
    return std_root + 0.3 * mean_root


def assess_image_quality(png_bytes: bytes) -> ImageQualityMetrics:
    """Compute sharpness, brightness, background dominance, and colorfulness from PNG bytes."""
    img = Image.open(io.BytesIO(png_bytes))
    width, height = img.size
    gray = img.convert("L")
    edges = gray.filter(_LAPLACIAN_KERNEL)
    sharpness = ImageStat.Stat(edges).var[0]
    brightness = ImageStat.Stat(gray).mean[0]

    stats_img = img.convert("RGB")
    stats_img.thumbnail(_STATS_MAX_SIZE)
    background_fraction = _background_fraction(stats_img.convert("L"))
    colorfulness = _colorfulness(stats_img)

    return ImageQualityMetrics(
        width=width,
        height=height,
        sharpness=sharpness,
        brightness=brightness,
        background_fraction=background_fraction,
        colorfulness=colorfulness,
    )


def is_low_quality(metrics: ImageQualityMetrics, cfg: ImageQualityConfig) -> tuple[bool, str]:
    """Return (True, reason) when the crop should be discarded."""
    if metrics.sharpness < cfg.min_sharpness:
        return True, f"sharpness {metrics.sharpness:.1f} < {cfg.min_sharpness}"
    if metrics.brightness < cfg.min_brightness:
        return True, f"brightness {metrics.brightness:.1f} < {cfg.min_brightness}"
    if metrics.brightness > cfg.max_brightness:
        return True, f"brightness {metrics.brightness:.1f} > {cfg.max_brightness}"
    if (
        cfg.reject_text_pages
        and metrics.background_fraction >= cfg.text_page_min_background
        and metrics.colorfulness <= cfg.text_page_max_colorfulness
    ):
        return True, (
            f"text-page crop (background {metrics.background_fraction:.2f} >= "
            f"{cfg.text_page_min_background}, colorfulness {metrics.colorfulness:.1f} <= "
            f"{cfg.text_page_max_colorfulness})"
        )
    return False, ""
