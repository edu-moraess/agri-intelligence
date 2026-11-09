import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agri_intelligence.perception.contracts import (
    BoundingBox2D,
    CoordinateSpace,
    DetectionPrediction,
    ImageFrame,
    PerceptionModel,
    TileRecord,
    VisionRunManifest,
)


SHA = "a" * 64


def image_frame(**overrides):
    values = {
        "image_id": "image-1",
        "width": 100,
        "height": 80,
        "channels": 3,
        "dtype": "uint8",
        "color_space": "RGB",
        "source_sha256": SHA,
        "pixels": object(),
    }
    values.update(overrides)
    return ImageFrame(**values)


def tile_record(**overrides):
    values = {
        "tile_id": "tile-1",
        "image_id": "image-1",
        "x": 20,
        "y": 10,
        "width": 40,
        "height": 30,
        "image_width": 100,
        "image_height": 80,
        "tile_index": 0,
    }
    values.update(overrides)
    return TileRecord(**values)


class PerceptionContractTests(unittest.TestCase):
    def test_image_frame_requires_valid_metadata_and_pixels(self):
        frame = image_frame()
        self.assertEqual(frame.frame_id, "image-1")
        self.assertEqual(frame.coordinate_space, CoordinateSpace.IMAGE)
        self.assertIsNotNone(frame.pixels)

        with self.assertRaises(ValueError):
            image_frame(width=True)
        with self.assertRaises(ValueError):
            image_frame(height=0)
        with self.assertRaises(ValueError):
            image_frame(image_id=" ")
        with self.assertRaises(ValueError):
            image_frame(pixels=None)
        with self.assertRaises(ValueError):
            image_frame(source_sha256="not-a-checksum")

    def test_tile_frame_declares_tile_coordinate_space(self):
        frame = image_frame(tile_id="tile-1", width=40, height=30)
        self.assertEqual(frame.frame_id, "tile-1")
        self.assertEqual(frame.coordinate_space, CoordinateSpace.TILE)

    def test_bounding_box_rejects_invalid_values_and_dimensions(self):
        with self.assertRaises(ValueError):
            BoundingBox2D(0, 0, 0, 10, "image-1", CoordinateSpace.IMAGE)
        with self.assertRaises(ValueError):
            BoundingBox2D(0, 0, float("nan"), 10, "image-1", CoordinateSpace.IMAGE)
        with self.assertRaises(ValueError):
            BoundingBox2D(0, 0, 10, 10, "image-1", "image")

    def test_tile_window_must_fit_inside_parent_image(self):
        with self.assertRaises(ValueError):
            tile_record(x=80, width=30)
        with self.assertRaises(ValueError):
            tile_record(y=70, height=20)
        with self.assertRaises(ValueError):
            tile_record(tile_index=-1)

    def test_tile_bbox_maps_to_parent_image_coordinates(self):
        tile = tile_record()
        local = BoundingBox2D(
            2, 3, 12, 13, "tile-1", CoordinateSpace.TILE
        )
        mapped = tile.to_image_bbox(local)
        self.assertEqual(
            (mapped.x_min, mapped.y_min, mapped.x_max, mapped.y_max),
            (22, 13, 32, 23),
        )
        self.assertEqual(mapped.frame_id, "image-1")
        self.assertEqual(mapped.coordinate_space, CoordinateSpace.IMAGE)

    def test_tile_bbox_rejects_wrong_frame_and_out_of_bounds(self):
        tile = tile_record()
        wrong_frame = BoundingBox2D(
            0, 0, 10, 10, "tile-other", CoordinateSpace.TILE
        )
        out_of_bounds = BoundingBox2D(
            0, 0, 41, 10, "tile-1", CoordinateSpace.TILE
        )
        with self.assertRaises(ValueError):
            tile.to_image_bbox(wrong_frame)
        with self.assertRaises(ValueError):
            tile.to_image_bbox(out_of_bounds)

    def test_detection_prediction_requires_matching_coordinate_reference(self):
        bbox = BoundingBox2D(1, 2, 10, 12, "image-1", CoordinateSpace.IMAGE)
        prediction = DetectionPrediction(
            "pred-1", "image-1", "plant", 0.9, bbox,
            "fake", "1", "run-1",
        )
        self.assertEqual(prediction.class_id, "plant")
        with self.assertRaises(ValueError):
            DetectionPrediction(
                "pred-2", "image-1", "plant", 1.1, bbox,
                "fake", "1", "run-1",
            )
        with self.assertRaises(ValueError):
            DetectionPrediction(
                "pred-3", "image-1", "plant", 0.9,
                BoundingBox2D(1, 2, 10, 12, "wrong-image", CoordinateSpace.IMAGE),
                "fake", "1", "run-1",
            )

    def test_tile_prediction_maps_to_image_and_keeps_tile_provenance(self):
        tile = tile_record()
        local = BoundingBox2D(2, 3, 12, 13, "tile-1", CoordinateSpace.TILE)
        prediction = DetectionPrediction(
            "pred-1", "image-1", "plant", 0.8, local,
            "fake", "1", "run-1", tile_id="tile-1",
        )
        mapped = prediction.mapped_to_image(tile)
        self.assertEqual(mapped.bbox.frame_id, "image-1")
        self.assertEqual(mapped.bbox.coordinate_space, CoordinateSpace.IMAGE)
        self.assertEqual(mapped.tile_id, "tile-1")
        self.assertEqual(mapped.run_id, "run-1")

    def test_tile_prediction_rejects_mismatched_tile(self):
        local = BoundingBox2D(2, 3, 12, 13, "tile-1", CoordinateSpace.TILE)
        prediction = DetectionPrediction(
            "pred-1", "image-1", "plant", 0.8, local,
            "fake", "1", "run-1", tile_id="tile-1",
        )
        with self.assertRaises(ValueError):
            prediction.mapped_to_image(tile_record(tile_id="tile-other"))

    def test_run_manifest_requires_checksums_and_utc_timestamp(self):
        manifest = VisionRunManifest(
            run_id="run-1",
            started_at_utc="2026-11-09T01:00:00Z",
            backend="fake",
            model_name="fixture-detector",
            model_version="1",
            config_sha256=SHA,
            input_manifest_sha256=SHA,
        )
        self.assertEqual(manifest.run_id, "run-1")
        with self.assertRaises(ValueError):
            VisionRunManifest(
                "run-1", "2026-11-09T01:00:00", "fake", "model", "1",
                SHA, SHA,
            )
        with self.assertRaises(ValueError):
            VisionRunManifest(
                "run-1", "2026-11-09T03:00:00+02:00", "fake", "model", "1",
                SHA, SHA,
            )
        with self.assertRaises(ValueError):
            VisionRunManifest(
                "run-1", "2026-11-09T01:00:00Z", "fake", "model", "1",
                "invalid", SHA,
            )

    def test_fake_detector_satisfies_model_protocol(self):
        class FakeDetector:
            def predict(self, frame, *, run_id):
                bbox = BoundingBox2D(
                    1, 1, 5, 5, frame.frame_id, frame.coordinate_space
                )
                return [
                    DetectionPrediction(
                        "pred-1", frame.image_id, "plant", 0.5, bbox,
                        "fake", "1", run_id,
                        tile_id=frame.tile_id,
                    )
                ]

        detector: PerceptionModel = FakeDetector()
        results = detector.predict(image_frame(), run_id="run-1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].run_id, "run-1")


if __name__ == "__main__":
    unittest.main()
