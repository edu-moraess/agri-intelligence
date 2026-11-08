"""Geospatial metadata without depending on a GIS library in Phase 0."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SpatialMetadata:
    crs: str | None = None
    gsd_meters: float | None = None
    transform_available: bool = False
    def __post_init__(self) -> None:
        if self.gsd_meters is not None and self.gsd_meters <= 0:
            raise ValueError("gsd_meters must be positive")
        if self.transform_available and not self.crs:
            raise ValueError("a spatial transform requires a declared CRS")
