"""Deterministic, model-independent detection postprocessing.

Tile-local boxes are mapped into parent-image coordinates, then class-aware
greedy NMS removes highly overlapping predictions from the same run/model.
No clipping is performed: malformed or out-of-bounds geometry is rejected.
"""
from __future__ import annotations

import math
from numbers import Real
from typing import Iterable, Sequence

from .contracts import CoordinateSpace, DetectionPrediction, TileRecord


def intersection_over_union(left: DetectionPrediction, right: DetectionPrediction) -> float:
    """Compute XYXY intersection-over-union for two image-space predictions."""
    a = left.bbox
    b = right.bbox
    if a.coordinate_space != CoordinateSpace.IMAGE or b.coordinate_space != CoordinateSpace.IMAGE:
        raise ValueError("IoU requires image-space bounding boxes")
    if a.frame_id != b.frame_id:
        raise ValueError("IoU requires boxes from the same image frame")

    x1 = max(a.x_min, b.x_min)
    y1 = max(a.y_min, b.y_min)
    x2 = min(a.x_max, b.x_max)
    y2 = min(a.y_max, b.y_max)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = (a.x_max - a.x_min) * (a.y_max - a.y_min)
    area_b = (b.x_max - b.x_min) * (b.y_max - b.y_min)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def _validate_threshold(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError("iou_threshold must be a finite number between 0 and 1")


def _to_image_space(
    prediction: DetectionPrediction,
    tiles_by_id: dict[str, TileRecord],
) -> DetectionPrediction:
    if prediction.bbox.coordinate_space == CoordinateSpace.IMAGE:
        if prediction.bbox.frame_id != prediction.image_id:
            raise ValueError("image-space prediction frame does not match image_id")
        if prediction.tile_id is not None:
            tile = tiles_by_id.get(prediction.tile_id)
            if tile is None or tile.image_id != prediction.image_id:
                raise ValueError("prediction tile provenance is missing or inconsistent")
        return prediction

    if prediction.tile_id is None:
        raise ValueError("tile-space prediction must include tile_id")
    tile = tiles_by_id.get(prediction.tile_id)
    if tile is None:
        raise ValueError(f"missing TileRecord for tile_id={prediction.tile_id!r}")
    if tile.image_id != prediction.image_id:
        raise ValueError("TileRecord image_id does not match prediction image_id")
    mapped = prediction.mapped_to_image(tile)
    box = mapped.bbox
    if (
        box.x_min < 0
        or box.y_min < 0
        or box.x_max > tile.image_width
        or box.y_max > tile.image_height
    ):
        raise ValueError("mapped prediction exceeds parent image bounds")
    return mapped


def postprocess_detections(
    predictions: Iterable[DetectionPrediction],
    tile_records: Sequence[TileRecord] = (),
    *,
    iou_threshold: float = 0.5,
) -> tuple[DetectionPrediction, ...]:
    """Map tile predictions to image space and apply deterministic class-aware NMS.

    NMS is isolated by image, class, model name/version, and run ID. The
    highest-scoring prediction is retained; a lower-scoring prediction is
    suppressed only when IoU is strictly greater than the threshold.
    Different classes and independent model runs never suppress one another.

    The function is dependency-free and does not modify input predictions.
    """
    _validate_threshold(iou_threshold)
    if isinstance(predictions, (str, bytes)):
        raise ValueError("predictions must be an iterable of DetectionPrediction values")
    if isinstance(tile_records, (str, bytes)):
        raise ValueError("tile_records must be a sequence of TileRecord values")

    records = tuple(tile_records)
    if any(not isinstance(item, TileRecord) for item in records):
        raise ValueError("all tile_records must be TileRecord instances")
    tiles_by_id: dict[str, TileRecord] = {}
    for record in records:
        if record.tile_id in tiles_by_id:
            raise ValueError(f"duplicate TileRecord tile_id={record.tile_id!r}")
        tiles_by_id[record.tile_id] = record

    items = tuple(predictions)
    if any(not isinstance(item, DetectionPrediction) for item in items):
        raise ValueError("all predictions must be DetectionPrediction instances")
    prediction_ids = [item.prediction_id for item in items]
    if len(prediction_ids) != len(set(prediction_ids)):
        raise ValueError("prediction_id values must be unique within one postprocessing call")

    mapped = tuple(_to_image_space(item, tiles_by_id) for item in items)
    groups: dict[tuple[str, str, str, str, str], list[DetectionPrediction]] = {}
    for item in mapped:
        key = (item.image_id, item.class_id, item.model_name, item.model_version, item.run_id)
        groups.setdefault(key, []).append(item)

    kept: list[DetectionPrediction] = []
    for key in sorted(groups):
        candidates = sorted(
            groups[key],
            key=lambda item: (
                -float(item.score),
                item.bbox.x_min,
                item.bbox.y_min,
                item.bbox.x_max,
                item.bbox.y_max,
                item.prediction_id,
            ),
        )
        selected: list[DetectionPrediction] = []
        for candidate in candidates:
            if all(
                intersection_over_union(candidate, prior) <= iou_threshold
                for prior in selected
            ):
                selected.append(candidate)
        kept.extend(selected)

    return tuple(
        sorted(
            kept,
            key=lambda item: (
                item.image_id,
                item.class_id,
                -float(item.score),
                item.bbox.x_min,
                item.bbox.y_min,
                item.prediction_id,
            ),
        )
    )
