"""Safe, optional-backend image decoding for agricultural perception."""
from __future__ import annotations

from pathlib import Path

from agri_intelligence.data.inventory import sha256_file
from .contracts import ImageFrame


class ImageDecodeError(ValueError):
    """Raised when an image cannot be safely decoded into the core contract."""


def read_image(path: Path, *, image_id: str | None = None, max_pixels: int = 100_000_000) -> ImageFrame:
    """Decode an image as immutable RGB uint8 bytes without modifying its source.

    Pillow is an optional runtime adapter. Importing this module does not require
    Pillow; callers receive a clear error if it is unavailable.
    """
    source = Path(path).expanduser()
    if source.is_symlink():
        raise ImageDecodeError("image source must not be a symlink")
    try:
        source = source.resolve(strict=True)
    except OSError as exc:
        raise ImageDecodeError(f"image source is unavailable: {source}") from exc
    if not source.is_file():
        raise ImageDecodeError("image source must be a regular file")
    if isinstance(max_pixels, bool) or not isinstance(max_pixels, int) or max_pixels <= 0:
        raise ValueError("max_pixels must be a positive integer")

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for file decoding; install the optional image extra"
        ) from exc

    try:
        with Image.open(source) as probe:
            probe.verify()
        with Image.open(source) as opened:
            oriented = ImageOps.exif_transpose(opened)
            width, height = oriented.size
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise ImageDecodeError("image dimensions are invalid or exceed max_pixels")
            rgb = oriented.convert("RGB")
            pixels = rgb.tobytes()
    except ImageDecodeError:
        raise
    except Exception as exc:
        raise ImageDecodeError(f"image could not be decoded: {type(exc).__name__}") from exc

    expected = width * height * 3
    if len(pixels) != expected:
        raise ImageDecodeError("decoded pixel buffer has an unexpected length")
    return ImageFrame(
        image_id=image_id or source.stem,
        width=width,
        height=height,
        channels=3,
        dtype="uint8",
        color_space="RGB",
        source_sha256=sha256_file(source),
        pixels=pixels,
    )
