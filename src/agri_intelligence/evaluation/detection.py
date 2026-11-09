"""Deterministic, dependency-free image-space detection evaluation.

Ground truth is intentionally represented separately from model predictions.
All geometry is expressed in source-image pixels; this module has no spatial
or agronomic interpretation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Iterable

from agri_intelligence.perception.contracts import (
    BoundingBox2D,
    CoordinateSpace,
    DetectionPrediction,
)


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_unit_interval(name: str, value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError(f"{name} must be finite and between 0 and 1")


@dataclass(frozen=True)
class GroundTruthBox:
    """One audited reference object in IMAGE pixel coordinates."""

    annotation_id: str
    image_id: str
    class_id: str
    bbox: BoundingBox2D

    def __post_init__(self) -> None:
        for name, value in (
            ("annotation_id", self.annotation_id),
            ("image_id", self.image_id),
            ("class_id", self.class_id),
        ):
            _require_text(name, value)
        if not isinstance(self.bbox, BoundingBox2D):
            raise ValueError("bbox must be a BoundingBox2D")
        if self.bbox.coordinate_space != CoordinateSpace.IMAGE:
            raise ValueError("ground-truth bbox must use IMAGE coordinate space")
        if self.bbox.frame_id != self.image_id:
            raise ValueError("ground-truth bbox frame_id must match image_id")


@dataclass(frozen=True)
class EvaluationConfig:
    """Explicit detection-evaluation protocol.

    AP uses every prediction score (ranked from highest to lowest), while
    precision/recall/TP/FP/FN use confidence_threshold at operating_iou.
    AP is 101-point interpolated average precision.
    """

    classes: tuple[str, ...]
    confidence_threshold: float = 0.25
    iou_thresholds: tuple[float, ...] = (0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95)
    operating_iou: float = 0.5
    matching_policy: str = "greedy_score"
    ap_method: str = "interpolated_101_point"

    def __post_init__(self) -> None:
        if not isinstance(self.classes, tuple) or not self.classes:
            raise ValueError("classes must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.classes):
            raise ValueError("classes must contain non-empty strings")
        if len(set(self.classes)) != len(self.classes):
            raise ValueError("classes must be unique")
        _require_unit_interval("confidence_threshold", self.confidence_threshold)
        if not isinstance(self.iou_thresholds, tuple) or not self.iou_thresholds:
            raise ValueError("iou_thresholds must be a non-empty tuple")
        for value in self.iou_thresholds:
            _require_unit_interval("IoU threshold", value)
        if tuple(sorted(set(self.iou_thresholds))) != self.iou_thresholds:
            raise ValueError("iou_thresholds must be unique and sorted ascending")
        _require_unit_interval("operating_iou", self.operating_iou)
        if self.operating_iou not in self.iou_thresholds:
            raise ValueError("operating_iou must be included in iou_thresholds")
        if self.matching_policy != "greedy_score":
            raise ValueError("matching_policy must be 'greedy_score'")
        if self.ap_method != "interpolated_101_point":
            raise ValueError("ap_method must be 'interpolated_101_point'")


@dataclass(frozen=True)
class ClassEvaluation:
    class_id: str
    ground_truth_count: int
    prediction_count: int
    tp: int
    fp: int
    fn: int
    precision: float | None
    recall: float | None
    average_precision: tuple[tuple[float, float | None], ...]


@dataclass(frozen=True)
class EvaluationResult:
    config: EvaluationConfig
    image_ids: tuple[str, ...]
    per_class: tuple[ClassEvaluation, ...]
    map_by_iou: tuple[tuple[float, float | None], ...]

    @property
    def map_50(self) -> float | None:
        return dict(self.map_by_iou).get(0.5)

    @property
    def mean_average_precision(self) -> float | None:
        values = [value for _, value in self.map_by_iou if value is not None]
        return sum(values) / len(values) if values else None


def _validate_inputs(
    ground_truth: tuple[GroundTruthBox, ...],
    predictions: tuple[DetectionPrediction, ...],
    config: EvaluationConfig,
) -> None:
    if not isinstance(config, EvaluationConfig):
        raise ValueError("config must be an EvaluationConfig")
    if any(not isinstance(item, GroundTruthBox) for item in ground_truth):
        raise ValueError("all ground_truth values must be GroundTruthBox instances")
    if any(not isinstance(item, DetectionPrediction) for item in predictions):
        raise ValueError("all predictions must be DetectionPrediction instances")
    gt_ids = [item.annotation_id for item in ground_truth]
    pred_ids = [item.prediction_id for item in predictions]
    if len(gt_ids) != len(set(gt_ids)):
        raise ValueError("annotation_id values must be unique within one evaluation")
    if len(pred_ids) != len(set(pred_ids)):
        raise ValueError("prediction_id values must be unique within one evaluation")
    allowed = set(config.classes)
    for item in ground_truth:
        if item.class_id not in allowed:
            raise ValueError(f"ground truth contains unconfigured class {item.class_id!r}")
    for item in predictions:
        if item.class_id not in allowed:
            raise ValueError(f"predictions contain unconfigured class {item.class_id!r}")
        if item.bbox.coordinate_space != CoordinateSpace.IMAGE:
            raise ValueError("predictions must be postprocessed into IMAGE coordinate space")
        if item.bbox.frame_id != item.image_id:
            raise ValueError("prediction bbox frame_id must match image_id")


def _match(
    ground_truth: tuple[GroundTruthBox, ...],
    predictions: tuple[DetectionPrediction, ...],
    iou_threshold: float,
    confidence_threshold: float | None,
) -> tuple[int, int, int]:
    """Greedy score-ordered, one-to-one matching, scoped by image and class."""
    gt_by_key: dict[tuple[str, str], list[GroundTruthBox]] = {}
    for item in ground_truth:
        gt_by_key.setdefault((item.image_id, item.class_id), []).append(item)
    for values in gt_by_key.values():
        values.sort(key=lambda item: item.annotation_id)

    candidates = [
        item for item in predictions
        if confidence_threshold is None or item.score >= confidence_threshold
    ]
    candidates.sort(key=lambda item: (-float(item.score), item.image_id, item.prediction_id))
    matched: dict[tuple[str, str], set[str]] = {}
    tp = 0
    fp = 0
    for prediction in candidates:
        key = (prediction.image_id, prediction.class_id)
        available = [
            item for item in gt_by_key.get(key, ())
            if item.annotation_id not in matched.setdefault(key, set())
        ]
        best: GroundTruthBox | None = None
        best_iou = -1.0
        for reference in available:
            overlap = _bbox_iou(prediction.bbox, reference.bbox)
            if overlap > best_iou:
                best = reference
                best_iou = overlap
        if best is not None and best_iou >= iou_threshold:
            matched[key].add(best.annotation_id)
            tp += 1
        else:
            fp += 1
    fn = len(ground_truth) - tp
    return tp, fp, fn


def _bbox_iou(left: BoundingBox2D, right: BoundingBox2D) -> float:
    if left.coordinate_space != CoordinateSpace.IMAGE or right.coordinate_space != CoordinateSpace.IMAGE:
        raise ValueError("IoU requires IMAGE coordinate space")
    if left.frame_id != right.frame_id:
        raise ValueError("IoU requires boxes from the same image")
    x1 = max(left.x_min, right.x_min)
    y1 = max(left.y_min, right.y_min)
    x2 = min(left.x_max, right.x_max)
    y2 = min(left.y_max, right.y_max)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_left = (left.x_max - left.x_min) * (left.y_max - left.y_min)
    area_right = (right.x_max - right.x_min) * (right.y_max - right.y_min)
    union = area_left + area_right - intersection
    return intersection / union if union > 0 else 0.0


def _average_precision(
    ground_truth: tuple[GroundTruthBox, ...],
    predictions: tuple[DetectionPrediction, ...],
    iou_threshold: float,
) -> float | None:
    support = len(ground_truth)
    if support == 0:
        return None
    if not predictions:
        return 0.0

    gt_by_key: dict[tuple[str, str], list[GroundTruthBox]] = {}
    for item in ground_truth:
        gt_by_key.setdefault((item.image_id, item.class_id), []).append(item)
    for values in gt_by_key.values():
        values.sort(key=lambda item: item.annotation_id)

    ranked = sorted(
        predictions,
        key=lambda item: (-float(item.score), item.image_id, item.prediction_id),
    )
    matched: dict[tuple[str, str], set[str]] = {}
    tp_flags: list[int] = []
    fp_flags: list[int] = []
    for prediction in ranked:
        key = (prediction.image_id, prediction.class_id)
        used = matched.setdefault(key, set())
        available = [item for item in gt_by_key.get(key, ()) if item.annotation_id not in used]
        best: GroundTruthBox | None = None
        best_iou = -1.0
        for reference in available:
            overlap = _bbox_iou(prediction.bbox, reference.bbox)
            if overlap > best_iou:
                best = reference
                best_iou = overlap
        if best is not None and best_iou >= iou_threshold:
            used.add(best.annotation_id)
            tp_flags.append(1)
            fp_flags.append(0)
        else:
            tp_flags.append(0)
            fp_flags.append(1)

    cumulative_tp = 0
    cumulative_fp = 0
    recalls: list[float] = []
    precisions: list[float] = []
    for tp_flag, fp_flag in zip(tp_flags, fp_flags):
        cumulative_tp += tp_flag
        cumulative_fp += fp_flag
        recalls.append(cumulative_tp / support)
        precisions.append(cumulative_tp / (cumulative_tp + cumulative_fp))

    # 101-point interpolated AP: mean of maximum precision at recall >= r.
    interpolated = []
    for index in range(101):
        recall_level = index / 100
        eligible = [
            precision for recall, precision in zip(recalls, precisions)
            if recall >= recall_level
        ]
        interpolated.append(max(eligible, default=0.0))
    return sum(interpolated) / 101


def evaluate_detections(
    ground_truth: Iterable[GroundTruthBox],
    predictions: Iterable[DetectionPrediction],
    config: EvaluationConfig,
) -> EvaluationResult:
    """Evaluate detections with explicit operating-point and ranked AP metrics."""
    gt = tuple(ground_truth)
    pred = tuple(predictions)
    _validate_inputs(gt, pred, config)

    image_ids = tuple(sorted({item.image_id for item in gt} | {item.image_id for item in pred}))
    per_class: list[ClassEvaluation] = []
    map_by_iou: list[tuple[float, float | None]] = []

    for class_id in config.classes:
        class_gt = tuple(item for item in gt if item.class_id == class_id)
        class_pred = tuple(item for item in pred if item.class_id == class_id)
        tp, fp, fn = _match(
            class_gt, class_pred, config.operating_iou, config.confidence_threshold
        )
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        aps = tuple(
            (
                threshold,
                _average_precision(class_gt, class_pred, threshold),
            )
            for threshold in config.iou_thresholds
        )
        per_class.append(ClassEvaluation(
            class_id=class_id,
            ground_truth_count=len(class_gt),
            prediction_count=sum(
                item.score >= config.confidence_threshold for item in class_pred
            ),
            tp=tp,
            fp=fp,
            fn=fn,
            precision=precision,
            recall=recall,
            average_precision=aps,
        ))

    for threshold in config.iou_thresholds:
        supported = [
            dict(item.average_precision)[threshold]
            for item in per_class
            if item.ground_truth_count > 0
        ]
        values = [value for value in supported if value is not None]
        map_by_iou.append((
            threshold,
            sum(values) / len(values) if values else None,
        ))

    return EvaluationResult(
        config=config,
        image_ids=image_ids,
        per_class=tuple(per_class),
        map_by_iou=tuple(map_by_iou),
    )
