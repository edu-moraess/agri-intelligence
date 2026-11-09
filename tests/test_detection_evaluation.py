import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agri_intelligence.evaluation.detection import (
    EvaluationConfig,
    GroundTruthBox,
    evaluate_detections,
)
from agri_intelligence.perception.contracts import (
    BoundingBox2D,
    CoordinateSpace,
    DetectionPrediction,
)


def box(image_id, x1=0, y1=0, x2=10, y2=10, space=CoordinateSpace.IMAGE):
    return BoundingBox2D(x1, y1, x2, y2, image_id, space)


def gt(annotation_id="gt-1", image_id="image-1", class_id="seedling", bbox=None):
    return GroundTruthBox(annotation_id, image_id, class_id, bbox or box(image_id))


def pred(
    prediction_id="pred-1",
    image_id="image-1",
    class_id="seedling",
    score=0.9,
    bbox=None,
    tile_id=None,
):
    return DetectionPrediction(
        prediction_id=prediction_id,
        image_id=image_id,
        class_id=class_id,
        score=score,
        bbox=bbox or box(image_id),
        model_name="fixture",
        model_version="1",
        run_id="run-1",
        tile_id=tile_id,
    )


class DetectionEvaluationTests(unittest.TestCase):
    def test_perfect_detection_has_unit_metrics(self):
        result = evaluate_detections(
            [gt()], [pred()], EvaluationConfig(classes=("seedling",))
        )
        metrics = result.per_class[0]
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (1, 0, 0))
        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.recall, 1.0)
        self.assertEqual(dict(metrics.average_precision)[0.5], 1.0)
        self.assertEqual(result.map_50, 1.0)

    def test_duplicate_predictions_can_match_ground_truth_only_once(self):
        result = evaluate_detections(
            [gt()],
            [pred("p1", score=0.9), pred("p2", score=0.8)],
            EvaluationConfig(classes=("seedling",)),
        )
        metrics = result.per_class[0]
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (1, 1, 0))
        self.assertEqual(metrics.precision, 0.5)
        self.assertEqual(metrics.recall, 1.0)

    def test_false_positive_ranked_before_true_positive_reduces_ap(self):
        false_positive = pred(
            "fp", score=0.9, bbox=box("image-1", 30, 30, 40, 40)
        )
        true_positive = pred("tp", score=0.8)
        result = evaluate_detections(
            [gt()],
            [true_positive, false_positive],
            EvaluationConfig(classes=("seedling",)),
        )
        self.assertAlmostEqual(
            dict(result.per_class[0].average_precision)[0.5], 0.5
        )

    def test_matching_is_scoped_to_image(self):
        result = evaluate_detections(
            [gt(image_id="image-a")],
            [pred(image_id="image-b")],
            EvaluationConfig(classes=("seedling",)),
        )
        metrics = result.per_class[0]
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (0, 1, 1))
        self.assertEqual(result.image_ids, ("image-a", "image-b"))

    def test_matching_is_class_aware(self):
        result = evaluate_detections(
            [gt(class_id="seedling")],
            [pred(class_id="weed")],
            EvaluationConfig(classes=("seedling", "weed")),
        )
        self.assertEqual((result.per_class[0].tp, result.per_class[0].fn), (0, 1))
        self.assertEqual((result.per_class[1].tp, result.per_class[1].fp), (0, 1))

    def test_no_predictions_with_ground_truth_has_zero_recall_and_ap(self):
        result = evaluate_detections(
            [gt()], [], EvaluationConfig(classes=("seedling",))
        )
        metrics = result.per_class[0]
        self.assertIsNone(metrics.precision)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(dict(metrics.average_precision)[0.5], 0.0)

    def test_unsupported_class_is_explicit_and_excluded_from_map(self):
        result = evaluate_detections(
            [gt(class_id="seedling")],
            [pred(class_id="weed")],
            EvaluationConfig(classes=("seedling", "weed")),
        )
        weed = result.per_class[1]
        self.assertEqual(weed.ground_truth_count, 0)
        self.assertIsNone(weed.precision)
        self.assertIsNone(weed.recall)
        self.assertIsNone(dict(weed.average_precision)[0.5])
        self.assertEqual(result.map_50, 0.0)

    def test_no_ground_truth_or_predictions_returns_undefined_map(self):
        result = evaluate_detections(
            [], [], EvaluationConfig(classes=("seedling",))
        )
        self.assertEqual(result.image_ids, ())
        self.assertIsNone(result.map_50)
        self.assertIsNone(result.mean_average_precision)

    def test_operating_confidence_threshold_does_not_truncate_ranked_ap(self):
        result = evaluate_detections(
            [gt()],
            [pred(score=0.2)],
            EvaluationConfig(
                classes=("seedling",),
                confidence_threshold=0.5,
            ),
        )
        metrics = result.per_class[0]
        self.assertEqual((metrics.tp, metrics.fp, metrics.fn), (0, 0, 1))
        self.assertEqual(metrics.prediction_count, 0)
        self.assertEqual(dict(metrics.average_precision)[0.5], 1.0)

    def test_configurable_iou_thresholds_produce_separate_map_values(self):
        partial = box("image-1", 0, 0, 7, 10)
        result = evaluate_detections(
            [gt()],
            [pred(bbox=partial)],
            EvaluationConfig(
                classes=("seedling",),
                iou_thresholds=(0.5, 0.75),
            ),
        )
        values = dict(result.map_by_iou)
        self.assertEqual(values[0.5], 1.0)
        self.assertEqual(values[0.75], 0.0)

    def test_tiled_predictions_must_be_postprocessed_first(self):
        tiled = box("tile-1", space=CoordinateSpace.TILE)
        with self.assertRaisesRegex(ValueError, "IMAGE coordinate"):
            evaluate_detections(
                [gt()],
                [pred(bbox=tiled, tile_id="tile-1")],
                EvaluationConfig(classes=("seedling",)),
            )

    def test_duplicate_annotation_and_prediction_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "annotation_id"):
            evaluate_detections(
                [gt("same"), gt("same", image_id="image-2")],
                [],
                EvaluationConfig(classes=("seedling",)),
            )
        with self.assertRaisesRegex(ValueError, "prediction_id"):
            evaluate_detections(
                [],
                [pred("same"), pred("same", image_id="image-2")],
                EvaluationConfig(classes=("seedling",)),
            )

    def test_unknown_classes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unconfigured class"):
            evaluate_detections(
                [gt(class_id="weed")],
                [],
                EvaluationConfig(classes=("seedling",)),
            )

    def test_invalid_configurations_are_rejected(self):
        invalid = (
            {"classes": ()},
            {"classes": ("seedling", "seedling")},
            {"classes": ("seedling",), "confidence_threshold": 1.1},
            {"classes": ("seedling",), "iou_thresholds": (0.75, 0.5)},
            {"classes": ("seedling",), "iou_thresholds": (0.5, 0.5)},
            {"classes": ("seedling",), "iou_thresholds": (0.75,), "operating_iou": 0.5},
            {"classes": ("seedling",), "matching_policy": "hungarian"},
            {"classes": ("seedling",), "ap_method": "voc_2007"},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                EvaluationConfig(**values)

    def test_ground_truth_requires_image_space_and_matching_frame(self):
        with self.assertRaisesRegex(ValueError, "IMAGE coordinate"):
            gt(bbox=box("image-1", space=CoordinateSpace.TILE))
        with self.assertRaisesRegex(ValueError, "frame_id"):
            gt(bbox=box("other-image"))


if __name__ == "__main__":
    unittest.main()
