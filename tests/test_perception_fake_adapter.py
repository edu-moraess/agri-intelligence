import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agri_intelligence.perception.contracts import CoordinateSpace, ImageFrame, PerceptionModel
from agri_intelligence.perception.testing import FakeDetection, FakePerceptionModel


SHA = "c" * 64


def frame(**overrides):
    values = {
        "image_id": "field-image-01",
        "width": 100,
        "height": 80,
        "channels": 3,
        "dtype": "uint8",
        "color_space": "RGB",
        "source_sha256": SHA,
        "pixels": bytes(100 * 80 * 3),
    }
    values.update(overrides)
    return ImageFrame(**values)


class FakePerceptionAdapterTests(unittest.TestCase):
    def test_fake_backend_satisfies_model_protocol(self):
        model: PerceptionModel = FakePerceptionModel()
        self.assertEqual(model.predict(frame(), run_id="run-01"), ())

    def test_returns_typed_prediction_with_traceable_provenance(self):
        model = FakePerceptionModel([FakeDetection("seedling", 0.875, 10, 12, 22, 30)])
        results = model.predict(frame(), run_id="run-02")
        self.assertEqual(len(results), 1)
        prediction = results[0]
        self.assertEqual(prediction.prediction_id, "run-02:field-image-01:000000")
        self.assertEqual(prediction.image_id, "field-image-01")
        self.assertEqual(prediction.class_id, "seedling")
        self.assertEqual(prediction.score, 0.875)
        self.assertEqual(prediction.model_name, "synthetic-fixture-detector")
        self.assertEqual(prediction.model_version, "1")
        self.assertEqual(prediction.run_id, "run-02")
        self.assertIsNone(prediction.tile_id)
        self.assertEqual(prediction.bbox.frame_id, "field-image-01")
        self.assertEqual(prediction.bbox.coordinate_space, CoordinateSpace.IMAGE)

    def test_tile_predictions_use_tile_local_coordinates_and_keep_parent_id(self):
        tile = frame(tile_id="field-image-01::tile:000003", width=20, height=20)
        model = FakePerceptionModel([FakeDetection("seedling", 0.7, 1, 2, 8, 9)])
        prediction = model.predict(tile, run_id="run-tile")[0]
        self.assertEqual(prediction.image_id, "field-image-01")
        self.assertEqual(prediction.tile_id, tile.tile_id)
        self.assertEqual(prediction.bbox.frame_id, tile.tile_id)
        self.assertEqual(prediction.bbox.coordinate_space, CoordinateSpace.TILE)

    def test_output_order_and_ids_are_deterministic(self):
        model = FakePerceptionModel([
            FakeDetection("seedling", 0.9, 1, 1, 4, 4),
            FakeDetection("weed", 0.6, 5, 5, 9, 9),
        ])
        first = model.predict(frame(), run_id="run-stable")
        second = model.predict(frame(), run_id="run-stable")
        self.assertEqual(first, second)
        self.assertEqual([item.class_id for item in first], ["seedling", "weed"])

    def test_empty_fixture_returns_empty_tuple(self):
        self.assertEqual(FakePerceptionModel().predict(frame(), run_id="empty-run"), ())

    def test_invalid_scores_and_boxes_are_rejected(self):
        for score in (-0.1, 1.1, float("nan"), float("inf"), True):
            with self.subTest(score=score), self.assertRaises(ValueError):
                FakeDetection("seedling", score, 1, 1, 4, 4)
        for coords in ((1, 1, 1, 4), (1, 1, 4, 1), (float("nan"), 1, 4, 4)):
            with self.subTest(coords=coords), self.assertRaises(ValueError):
                FakeDetection("seedling", 0.5, *coords)

    def test_invalid_frame_and_run_id_are_rejected(self):
        model = FakePerceptionModel()
        with self.assertRaises(ValueError):
            model.predict(object(), run_id="run-01")
        with self.assertRaises(ValueError):
            model.predict(frame(), run_id=" ")

    def test_non_fake_detection_values_are_rejected(self):
        with self.assertRaises(ValueError):
            FakePerceptionModel([{"class_id": "seedling"}])

    def test_fixture_geometry_is_checked_against_actual_frame(self):
        model = FakePerceptionModel([FakeDetection("seedling", 0.5, 1, 1, 90, 70)])
        with self.assertRaises(ValueError):
            model.predict(frame(width=50, height=40), run_id="out-of-bounds")


if __name__ == "__main__":
    unittest.main()
