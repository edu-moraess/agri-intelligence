"""Typed, model-independent contracts for image-space perception.

Pixel payloads are intentionally opaque: adapters may use NumPy, Pillow, Torch,
or another optional backend without making that dependency part of the core.
Adapters must treat the supplied pixel payload as read-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
import math
from numbers import Real
import re
from typing import Protocol, Sequence


_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class CoordinateSpace(str, Enum):
    IMAGE = "image"
    TILE = "tile"


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{name} must be a 64-character hexadecimal SHA-256")


def _require_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class ImageFrame:
    """A validated image plus an opaque, read-only pixel payload.

    For a source image, frame_id is image_id and coordinate_space is IMAGE.
    For a tile, set tile_id; coordinates are then local to that tile.
    """

    image_id: str
    width: int
    height: int
    channels: int
    dtype: str
    color_space: str
    source_sha256: str
    pixels: object = field(repr=False, compare=False)
    tile_id: str | None = None

    def __post_init__(self) -> None:
        _require_text("image_id", self.image_id)
        _require_positive_int("width", self.width)
        _require_positive_int("height", self.height)
        _require_positive_int("channels", self.channels)
        _require_text("dtype", self.dtype)
        _require_text("color_space", self.color_space)
        _require_sha256("source_sha256", self.source_sha256)
        if self.pixels is None:
            raise ValueError("pixels must not be None")
        if self.tile_id is not None:
            _require_text("tile_id", self.tile_id)

    @property
    def frame_id(self) -> str:
        return self.tile_id or self.image_id

    @property
    def coordinate_space(self) -> CoordinateSpace:
        return CoordinateSpace.TILE if self.tile_id is not None else CoordinateSpace.IMAGE


@dataclass(frozen=True)
class BoundingBox2D:
    """Axis-aligned XYXY box in pixel coordinates of one explicit frame."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float
    frame_id: str
    coordinate_space: CoordinateSpace

    def __post_init__(self) -> None:
        _require_text("frame_id", self.frame_id)
        if not isinstance(self.coordinate_space, CoordinateSpace):
            raise ValueError("coordinate_space must be a CoordinateSpace")
        values = (self.x_min, self.y_min, self.x_max, self.y_max)
        if any(
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("bounding box coordinates must be finite real numbers")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("bounding box must have positive width and height")


@dataclass(frozen=True)
class TileRecord:
    """A tile window expressed in the parent image's pixel coordinates."""

    tile_id: str
    image_id: str
    x: int
    y: int
    width: int
    height: int
    image_width: int
    image_height: int
    tile_index: int

    def __post_init__(self) -> None:
        _require_text("tile_id", self.tile_id)
        _require_text("image_id", self.image_id)
        for name, value in (
            ("x", self.x),
            ("y", self.y),
            ("tile_index", self.tile_index),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name, value in (
            ("width", self.width),
            ("height", self.height),
            ("image_width", self.image_width),
            ("image_height", self.image_height),
        ):
            _require_positive_int(name, value)
        if self.x + self.width > self.image_width:
            raise ValueError("tile exceeds parent image width")
        if self.y + self.height > self.image_height:
            raise ValueError("tile exceeds parent image height")

    def to_image_bbox(self, bbox: BoundingBox2D) -> BoundingBox2D:
        """Map a tile-local XYXY box into the parent image pixel frame."""
        if bbox.coordinate_space != CoordinateSpace.TILE or bbox.frame_id != self.tile_id:
            raise ValueError("bbox must reference this tile in TILE coordinate space")
        if (
            bbox.x_min < 0
            or bbox.y_min < 0
            or bbox.x_max > self.width
            or bbox.y_max > self.height
        ):
            raise ValueError("tile-local bbox exceeds tile bounds")
        return BoundingBox2D(
            x_min=bbox.x_min + self.x,
            y_min=bbox.y_min + self.y,
            x_max=bbox.x_max + self.x,
            y_max=bbox.y_max + self.y,
            frame_id=self.image_id,
            coordinate_space=CoordinateSpace.IMAGE,
        )


@dataclass(frozen=True)
class DetectionPrediction:
    prediction_id: str
    image_id: str
    class_id: str
    score: float
    bbox: BoundingBox2D
    model_name: str
    model_version: str
    run_id: str
    tile_id: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("prediction_id", self.prediction_id),
            ("image_id", self.image_id),
            ("class_id", self.class_id),
            ("model_name", self.model_name),
            ("model_version", self.model_version),
            ("run_id", self.run_id),
        ):
            _require_text(name, value)
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, Real)
            or not math.isfinite(float(self.score))
            or not 0 <= self.score <= 1
        ):
            raise ValueError("score must be finite and between 0 and 1")
        if not isinstance(self.bbox, BoundingBox2D):
            raise ValueError("bbox must be a BoundingBox2D")
        if self.tile_id is not None:
            _require_text("tile_id", self.tile_id)
        if self.bbox.coordinate_space == CoordinateSpace.TILE:
            if self.tile_id is None or self.bbox.frame_id != self.tile_id:
                raise ValueError("tile-space bbox must reference prediction tile_id")
        elif self.bbox.frame_id != self.image_id:
            raise ValueError("image-space bbox must reference prediction image_id")

    def mapped_to_image(self, tile: TileRecord) -> "DetectionPrediction":
        """Return an image-space prediction while retaining tile provenance."""
        if self.tile_id != tile.tile_id or self.image_id != tile.image_id:
            raise ValueError("tile does not belong to this prediction")
        mapped = tile.to_image_bbox(self.bbox)
        return replace(self, bbox=mapped)


@dataclass(frozen=True)
class VisionRunManifest:
    run_id: str
    started_at_utc: str
    backend: str
    model_name: str
    model_version: str
    config_sha256: str
    input_manifest_sha256: str
    dataset_manifest_sha256: str | None = None
    model_sha256: str | None = None
    source_revision: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("run_id", self.run_id),
            ("backend", self.backend),
            ("model_name", self.model_name),
            ("model_version", self.model_version),
        ):
            _require_text(name, value)
        _require_sha256("config_sha256", self.config_sha256)
        _require_sha256("input_manifest_sha256", self.input_manifest_sha256)
        for name, value in (
            ("dataset_manifest_sha256", self.dataset_manifest_sha256),
            ("model_sha256", self.model_sha256),
        ):
            if value is not None:
                _require_sha256(name, value)
        if self.source_revision is not None:
            _require_text("source_revision", self.source_revision)
        if not isinstance(self.started_at_utc, str) or not self.started_at_utc.strip():
            raise ValueError("started_at_utc must be an ISO-8601 timestamp")
        try:
            timestamp = datetime.fromisoformat(self.started_at_utc.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("started_at_utc must be an ISO-8601 timestamp") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("started_at_utc must include a timezone")
        if timestamp.utcoffset().total_seconds() != 0:
            raise ValueError("started_at_utc must use UTC")
        

class PerceptionModel(Protocol):
    """Backend adapter contract; implementation dependencies remain optional."""

    def predict(self, frame: ImageFrame, *, run_id: str) -> Sequence[DetectionPrediction]:
        """Return detections in the coordinate space of the supplied frame."""
        ...
