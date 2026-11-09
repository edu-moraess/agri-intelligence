"""Dataset-level spatial metadata validation without performing coordinate transforms."""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class SpatialDatasetMetadata:
    crs: str | None = None
    gsd_x_meters: float | None = None
    gsd_y_meters: float | None = None
    affine_transform: tuple[float, float, float, float, float, float] | None = None
    width: int | None = None
    height: int | None = None
    units: str | None = None

    def __post_init__(self) -> None:
        if self.crs is not None and not self.crs.strip():
            raise ValueError("crs cannot be blank")
        for value in (self.gsd_x_meters, self.gsd_y_meters):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError("GSD values must be finite and positive")
        if self.width is not None and self.width <= 0 or self.height is not None and self.height <= 0:
            raise ValueError("spatial dimensions must be positive")
        if self.affine_transform is not None:
            if len(self.affine_transform) != 6 or not all(math.isfinite(v) for v in self.affine_transform):
                raise ValueError("affine transform must contain six finite coefficients")
            a, b, _, d, e, _ = self.affine_transform
            if math.isclose(a * e - b * d, 0.0, abs_tol=1e-15):
                raise ValueError("affine transform is singular")
            if not self.crs:
                raise ValueError("affine transform requires CRS")

    @property
    def has_ground_reference(self) -> bool:
        return bool(self.crs and (self.affine_transform or self.gsd_x_meters))

    @property
    def geographic_coordinates_available(self) -> bool:
        return bool(self.crs and self.affine_transform)
