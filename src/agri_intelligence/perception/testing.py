"""Deterministic fake perception backend for software tests only.

This module emits caller-supplied synthetic detections. It is not a trained
model, does not inspect pixels, and must never be used as performance evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Sequence

from .contracts import BoundingBox2D, CoordinateSpace, DetectionPrediction, ImageFrame


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class FakeDetection:
    """A synthetic detection fixture in the coordinate space of its input frame."""

    class_id: str
    score: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        _require_text("class_id", self.class_id)
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, Real)
            or not math.isfinite(float(self.score))
            or not 0 <= self.score <= 1
        ):
            raise ValueError("score must be finite and between 0 and 1")
        BoundingBox2D(
            self.x_min,
            self.y_min,
            self.x_max,
            self.y_max,
            "fixture-frame",
            CoordinateSpace.IMAGE,
        )


class FakePerceptionModel:
    """Return deterministic, caller-supplied detections without reading pixels."""

    backend = "fake"
    model_name = "synthetic-fixture-detector"
    model_version = "1"

    def __init__(self, detections: Sequence[FakeDetection] = ()) -> None:
        if isinstance(detections, (str, bytes)):
            raise ValueError("detections must be a sequence of FakeDetection values")
        self._detections = tuple(detections)
        if any(not isinstance(item, FakeDetection) for item in self._detections):
            raise ValueError("all detections must be FakeDetection instances")

    def predict(self, frame: ImageFrame, *, run_id: str) -> tuple[DetectionPrediction, ...]:
        if not isinstance(frame, ImageFrame):
            raise ValueError("frame must be an ImageFrame")
        _require_text("run_id", run_id)
        output = []
        for index, item in enumerate(self._detections):
            bbox = BoundingBox2D(
                item.x_min,
                item.y_min,
                item.x_max,
                item.y_max,
                frame.frame_id,
                frame.coordinate_space,
            )
            output.append(
                DetectionPrediction(
                    prediction_id=f"{run_id}:{frame.frame_id}:{index:06d}",
                    image_id=frame.image_id,
                    class_id=item.class_id,
                    score=float(item.score),
                    bbox=bbox,
                    model_name=self.model_name,
                    model_version=self.model_version,
                    run_id=run_id,
                    tile_id=frame.tile_id,
                )
            )
        return tuple(output)
