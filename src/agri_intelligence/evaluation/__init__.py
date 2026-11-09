"""Image-space object-detection evaluation contracts and metrics."""

from .detection import (
    ClassEvaluation,
    EvaluationConfig,
    EvaluationResult,
    GroundTruthBox,
    evaluate_detections,
)

__all__ = [
    "ClassEvaluation",
    "EvaluationConfig",
    "EvaluationResult",
    "GroundTruthBox",
    "evaluate_detections",
]
