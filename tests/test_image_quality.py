import io
import random

from PIL import Image

from mexipes.config import ImageQualityConfig
from mexipes.image_quality import ImageQualityMetrics, assess_image_quality, is_low_quality

DEFAULT_CFG = ImageQualityConfig()


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _flat_image(luminance: int, size: tuple[int, int] = (200, 200)) -> bytes:
    return _png_bytes(Image.new("L", size, color=luminance))


def _noisy_sharp_image(size: tuple[int, int] = (200, 200)) -> bytes:
    rng = random.Random(0)
    img = Image.new("L", size)
    img.putdata([rng.randint(80, 220) for _ in range(size[0] * size[1])])
    return _png_bytes(img)


def _dark_blurry_image(size: tuple[int, int] = (400, 400)) -> bytes:
    """Simulates a low-res, dark publication photo (like embedded PDF raster crops)."""
    rng = random.Random(0)
    img = Image.new("L", size)
    img.putdata([rng.randint(30, 80) for _ in range(size[0] * size[1])])
    small = img.resize((size[0] // 8, size[1] // 8), Image.Resampling.LANCZOS)
    blurry = small.resize(size, Image.Resampling.LANCZOS)
    return _png_bytes(blurry)


def test_assess_image_quality_returns_dimensions_and_metrics() -> None:
    metrics = assess_image_quality(_flat_image(128, size=(100, 150)))

    assert metrics.width == 100
    assert metrics.height == 150
    assert metrics.brightness == 128.0
    assert metrics.sharpness >= 0.0


def test_is_low_quality_rejects_low_sharpness() -> None:
    metrics = ImageQualityMetrics(width=100, height=100, sharpness=50.0, brightness=150.0)

    low, reason = is_low_quality(metrics, DEFAULT_CFG)

    assert low is True
    assert "sharpness" in reason


def test_is_low_quality_rejects_low_brightness() -> None:
    metrics = ImageQualityMetrics(width=100, height=100, sharpness=200.0, brightness=70.0)

    low, reason = is_low_quality(metrics, DEFAULT_CFG)

    assert low is True
    assert "brightness" in reason


def test_is_low_quality_rejects_dark_flat_image() -> None:
    metrics = assess_image_quality(_flat_image(50))

    low, _ = is_low_quality(metrics, DEFAULT_CFG)

    assert low is True


def test_is_low_quality_rejects_dark_blurry_image() -> None:
    metrics = assess_image_quality(_dark_blurry_image())

    low, reason = is_low_quality(metrics, DEFAULT_CFG)

    assert low is True
    assert "sharpness" in reason or "brightness" in reason


def test_is_low_quality_accepts_sharp_bright_image() -> None:
    metrics = assess_image_quality(_noisy_sharp_image())

    low, reason = is_low_quality(metrics, DEFAULT_CFG)

    assert low is False
    assert reason == ""


def test_is_low_quality_rejects_overexposed_image() -> None:
    metrics = assess_image_quality(_flat_image(255))

    low, reason = is_low_quality(metrics, DEFAULT_CFG)

    assert low is True
    assert "brightness" in reason


def test_real_bad_crop_would_be_discarded() -> None:
    """Regression: a real publication crop measured sharpness=106.5, brightness=70.6.

    Pinned to the measured metrics rather than a live file under ``data/`` so the
    check stays deterministic across pipeline re-runs (which repopulate that path
    with arbitrary, often perfectly good, images).
    """
    metrics = ImageQualityMetrics(width=300, height=300, sharpness=106.5, brightness=70.6)

    low, reason = is_low_quality(metrics, DEFAULT_CFG)

    assert low is True
    assert "sharpness" in reason or "brightness" in reason
