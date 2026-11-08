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

@dataclass(frozen=True)
class GroundSamplingDistance:
    meters_per_pixel: float
    def __post_init__(self) -> None:
        if not math.isfinite(self.meters_per_pixel) or self.meters_per_pixel <= 0:
            raise ValueError("GSD must be a finite positive value")

def euclidean_distance(a: Point, b: Point, *, gsd: GroundSamplingDistance | None = None) -> float:
    if a.space != b.space:
        raise ValueError("points must share a coordinate space")
    pixels = math.hypot(a.x - b.x, a.y - b.y)
    if a.space in {CoordinateSpace.IMAGE, CoordinateSpace.TILE, CoordinateSpace.ORTHOMOSAIC}:
        if gsd is None:
            raise ValueError("pixel-space distance requires a validated GSD")
        return pixels * gsd.meters_per_pixel
    if a.space == CoordinateSpace.PROJECTED:
        return pixels
    raise ValueError("geographic degrees require a geodesic transformation")
