"""Core evidence contracts; intentionally independent of ML frameworks."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

@dataclass(frozen=True)
class Provenance:
    source: str
    method: str
    version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        if not self.source.strip() or not self.method.strip():
            raise ValueError("provenance source and method are required")

@dataclass(frozen=True)
class Uncertainty:
    kind: str
    value: float | None = None
    unit: str | None = None
    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("uncertainty kind is required")
        if self.value is not None and self.value < 0:
            raise ValueError("uncertainty value cannot be negative")

@dataclass(frozen=True)
class Observation:
    id: str
    observed_at: datetime
    provenance: Provenance
    value: Any
    spatial_reference: str | None = None
    uncertainty: Uncertainty | None = None
    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("observation id is required")

@dataclass(frozen=True)
class Prediction:
    id: str
    model: str
    value: Any
    provenance: Provenance
    confidence: float | None = None
    uncertainty: Uncertainty | None = None
    def __post_init__(self) -> None:
        if not self.id.strip() or not self.model.strip():
            raise ValueError("prediction id and model are required")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

@dataclass(frozen=True)
class DerivedMeasurement:
    id: str
    value: float
    unit: str
    provenance: Provenance
    inputs: tuple[str, ...]
    uncertainty: Uncertainty | None = None
    def __post_init__(self) -> None:
        if not self.id.strip() or not self.unit.strip() or not self.inputs:
            raise ValueError("measurement id, unit and inputs are required")
