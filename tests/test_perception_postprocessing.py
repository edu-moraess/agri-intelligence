import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agri_intelligence.perception.contracts import (
    BoundingBox2D,
    CoordinateSpace,
    DetectionPrediction,
    TileRecord,
)
from agri_intelligence.perception.postprocessing import (
    intersection_over_union,
    postprocess_detections,
)


def tile(tile_id, x, width=60, image_id="field-01"):
    return TileRecord(
        tile_id=tile_id,
        image_id=image_id,
        x=x,
        y=0,
        width=width,
        height=40,
        image_width=100,
        image_height=40,
        tile_index=0 if x == 0 else 1,
    )


def prediction(
    prediction_id,
    *,
    tile_id=None,
    coords=(10, 10, 20, 20),
    class_id="seedling",
    score=0.8,
    run_id="run-01",
    image_id="field-01",
):
    space = CoordinateSpace.TILE if tile_id else CoordinateSpace.IMAGE
    frame_id = tile_id or image_id
    return DetectionPrediction(
        prediction_id=prediction_id,
        image_id=image_id,
        class_id=class_id,
        score=score,
        bbox=BoundingBox2D(*coords, frame_id, space),
        model_name="detector",
        model_version="1",
        run_id=run_id,
        tile_id=tile_id,
    )


class DetectionPostprocessingTests(unittest.TestCase):
    def test_maps_tile_local_coordinates_to_parent_image(self):
        record = tile("tile-a", 30)
        item = prediction("p1", tile_id="tile-a", coords=(2, 3, 12, 13))
        result = postprocess_detections([item], [record])
        self.assertEqual(len(result), 1)
        self.assertEqual(
            (result[0].bbox.x_min, result[0].bbox.y_min,
             result[0].bbox.x_max, result[0].bbox.y_max),
            (32, 3, 42, 13),
        )
        self.assertEqual(result[0].bbox.coordinate_space, CoordinateSpace.IMAGE)
        self.assertEqual(result[0].bbox.frame_id, "field-01")
        self.assertEqual(result[0].tile_id, "tile-a")

    def test_suppresses_duplicate_object_across_overlapping_tiles(self):
        records = [tile("tile-left", 0), tile("tile-right", 40)]
        left = prediction("left", tile_id="tile-left", coords=(45, 10, 55, 20), score=0.91)
        right = prediction("right", tile_id="tile-right", coords=(5, 10, 15, 20), score=0.82)
        result = postprocess_detections([right, left], records, iou_threshold=0.5)
        self.assertEqual([item.prediction_id for item in result], ["left"])

    def test_keeps_distinct_same_class_objects_below_iou_threshold(self):
        first = prediction("first", coords=(0, 0, 10, 10))
        second = prediction("second", coords=(12, 0, 22, 10))
        self.assertEqual(len(postprocess_detections([first, second])), 2)

    def test_nms_is_class_aware(self):
        first = prediction("seedling", coords=(0, 0, 10, 10), class_id="seedling")
        second = prediction("weed", coords=(0, 0, 10, 10), class_id="weed")
        self.assertEqual(len(postprocess_detections([first, second])), 2)

    def test_nms_does_not_mix_independent_runs(self):
        first = prediction("run-a", coords=(0, 0, 10, 10), run_id="run-a")
        second = prediction("run-b", coords=(0, 0, 10, 10), run_id="run-b")
        self.assertEqual(len(postprocess_detections([first, second])), 2)

    def test_image_space_predictions_pass_through(self):
        item = prediction("image-pred", coords=(1, 2, 8, 9))
        result = postprocess_detections([item])
        self.assertEqual(result, (item,))

    def test_empty_input_returns_empty_tuple(self):
        self.assertEqual(postprocess_detections([]), ())

    def test_iou_is_computed_for_image_space_boxes(self):
        first = prediction("a", coords=(0, 0, 10, 10))
        second = prediction("b", coords=(5, 0, 15, 10))
        self.assertAlmostEqual(intersection_over_union(first, second), 1 / 3)

    def test_missing_or_inconsistent_tile_provenance_is_rejected(self):
        item = prediction("orphan", tile_id="missing")
        with self.assertRaises(ValueError):
            postprocess_detections([item])
        wrong_image = tile("tile-a", 0, image_id="other-image")
        with self.assertRaises(ValueError):
            postprocess_detections([item], [wrong_image])

    def test_duplicate_tile_ids_and_prediction_ids_are_rejected(self):
        record = tile("tile-a", 0)
        with self.assertRaises(ValueError):
            postprocess_detections([], [record, record])
        item = prediction("duplicate")
        with self.assertRaises(ValueError):
            postprocess_detections([item, item])

    def test_invalid_inputs_and_iou_threshold_are_rejected(self):
        for threshold in (-0.1, 1.1, float("nan"), float("inf"), True):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                postprocess_detections([], iou_threshold=threshold)
        with self.assertRaises(ValueError):
            postprocess_detections([object()])
        with self.assertRaises(ValueError):
            postprocess_detections([], [object()])

    def test_equal_scores_have_deterministic_tie_breaking(self):
        first = prediction("z-id", coords=(0, 0, 10, 10), score=0.8)
        second = prediction("a-id", coords=(0, 0, 10, 10), score=0.8)
        one = postprocess_detections([first, second])
        two = postprocess_detections([second, first])
        self.assertEqual(one, two)
        self.assertEqual([item.prediction_id for item in one], ["a-id"])


if __name__ == "__main__":
    unittest.main()
