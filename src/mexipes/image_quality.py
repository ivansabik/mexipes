"""Deterministic image quality assessment for recipe photo crops."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageStat

from mexipes.config import ImageQualityConfig

# 3x3 Laplacian kernel for edge/sharpness detection
_LAPLACIAN_KERNEL = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=0)


@dataclass(frozen=True)
class ImageQualityMetrics:
    width: int
    height: int
    sharpness: float
    brightness: float


def assess_image_quality(png_bytes: bytes) -> ImageQualityMetrics:
    """Compute sharpness (Laplacian variance) and brightness (mean luminance) from PNG bytes."""
    gray = Image.open(io.BytesIO(png_bytes)).convert("L")
    width, height = gray.size
    edges = gray.filter(_LAPLACIAN_KERNEL)
    sharpness = ImageStat.Stat(edges).var[0]
    brightness = ImageStat.Stat(gray).mean[0]
    return ImageQualityMetrics(
        width=width,
        height=height,
        sharpness=sharpness,
        brightness=brightness,
    )


def is_low_quality(metrics: ImageQualityMetrics, cfg: ImageQualityConfig) -> tuple[bool, str]:
    """Return (True, reason) when the crop should be discarded."""
    if metrics.sharpness < cfg.min_sharpness:
        return True, f"sharpness {metrics.sharpness:.1f} < {cfg.min_sharpness}"
    if metrics.brightness < cfg.min_brightness:
        return True, f"brightness {metrics.brightness:.1f} < {cfg.min_brightness}"
    if metrics.brightness > cfg.max_brightness:
        return True, f"brightness {metrics.brightness:.1f} > {cfg.max_brightness}"
    return False, ""
