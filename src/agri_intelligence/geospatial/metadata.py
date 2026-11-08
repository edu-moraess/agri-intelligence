"""Geospatial metadata with explicit CRS and affine-transform validation."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class SpatialMetadata:
    crs: str | None = None
    gsd_meters: float | None = None
    transform_available: bool = False
    affine_transform: tuple[float, float, float, float, float, float] | None = None
    def __post_init__(self) -> None:
        if self.crs is not None and not self.crs.strip():
            raise ValueError("crs cannot be blank")
        if self.gsd_meters is not None and (not math.isfinite(self.gsd_meters) or self.gsd_meters <= 0):
            raise ValueError("gsd_meters must be finite and positive")
        if self.transform_available:
            if not self.crs:
                raise ValueError("a spatial transform requires a declared CRS")
            if self.affine_transform is None:
                raise ValueError("transform_available requires affine coefficients")
        if self.affine_transform is not None:
            if len(self.affine_transform) != 6:
                raise ValueError("affine_transform must contain six coefficients")
            if not all(math.isfinite(v) for v in self.affine_transform):
                raise ValueError("affine coefficients must be finite")
            if not self.crs:
                raise ValueError("affine coefficients require a declared CRS")
            a, b, _, d, e, _ = self.affine_transform
            if math.isclose(a * e - b * d, 0.0, abs_tol=1e-15):
                raise ValueError("affine transform is singular")
