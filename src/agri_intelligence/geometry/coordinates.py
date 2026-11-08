"""Explicit coordinate spaces and safe physical-distance prerequisites."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math

class CoordinateSpace(str, Enum):
    IMAGE = "image"
    TILE = "tile"
    ORTHOMOSAIC = "orthomosaic"
    PROJECTED = "projected_metric"
    GEOGRAPHIC = "geographic"

@dataclass(frozen=True)
class Point:
    x: float
    y: float
    space: CoordinateSpace
    def __post_init__(self) -> None:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("point coordinates must be finite")

@dataclass(frozen=True)
class GroundSamplingDistance:
    """Ground resolution in metres per pixel for the x and y image axes."""
    meters_per_pixel: float
    meters_per_pixel_y: float | None = None
    def __post_init__(self) -> None:
        values = (self.meters_per_pixel, self.meters_per_pixel_y)
        if any(v is not None and (not math.isfinite(v) or v <= 0) for v in values):
            raise ValueError("GSD values must be finite and positive")
    @property
    def x(self) -> float:
        return self.meters_per_pixel
    @property
    def y(self) -> float:
        return self.meters_per_pixel_y or self.meters_per_pixel

def euclidean_distance(a: Point, b: Point, *, gsd: GroundSamplingDistance | None = None) -> float:
    """Return metres for pixel coordinates or native units for a metric CRS."""
    if a.space != b.space:
        raise ValueError("points must share a coordinate space")
    dx, dy = a.x - b.x, a.y - b.y
    if a.space in {CoordinateSpace.IMAGE, CoordinateSpace.TILE, CoordinateSpace.ORTHOMOSAIC}:
        if gsd is None:
            raise ValueError("pixel-space distance requires a validated GSD")
        return math.hypot(dx * gsd.x, dy * gsd.y)
    if a.space == CoordinateSpace.PROJECTED:
        return math.hypot(dx, dy)
    raise ValueError("geographic degrees require a geodesic transformation")
