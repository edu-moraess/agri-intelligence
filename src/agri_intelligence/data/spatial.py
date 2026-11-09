"""Dataset-level spatial metadata validation without performing coordinate transforms."""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real


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
        if self.crs is not None and (
            not isinstance(self.crs, str) or not self.crs.strip()
        ):
            raise ValueError("crs must be a non-empty string or None")
        if self.units is not None and (
            not isinstance(self.units, str) or not self.units.strip()
        ):
            raise ValueError("units must be a non-empty string or None")

        for name, value in (
            ("gsd_x_meters", self.gsd_x_meters),
            ("gsd_y_meters", self.gsd_y_meters),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(float(value))
                or value <= 0
            ):
                raise ValueError(f"{name} must be a finite positive number")

        for name, value in (("width", self.width), ("height", self.height)):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                raise ValueError(f"{name} must be a positive integer")

        if self.affine_transform is not None:
            transform = self.affine_transform
            if not isinstance(transform, (tuple, list)) or len(transform) != 6:
                raise ValueError("affine transform must contain six numeric coefficients")
            if any(
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(float(value))
                for value in transform
            ):
                raise ValueError("affine transform coefficients must be finite numbers")
            a, b, _, d, e, _ = (float(value) for value in transform)
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
