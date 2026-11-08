import unittest
from datetime import datetime, timezone
from agri_intelligence.core.contracts import Observation, Prediction, Provenance
from agri_intelligence.geometry.coordinates import CoordinateSpace, GroundSamplingDistance, Point, euclidean_distance

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.provenance = Provenance("test", "fixture")

    def test_observation_and_prediction_keep_provenance(self):
        obs = Observation("o1", datetime.now(timezone.utc), self.provenance, {"plant": 1})
        pred = Prediction("p1", "future-model", {"label": "seedling"}, self.provenance, confidence=0.8)
        self.assertEqual(obs.provenance.source, "test")
        self.assertEqual(pred.model, "future-model")

    def test_pixel_distance_requires_gsd(self):
        a = Point(0, 0, CoordinateSpace.IMAGE)
        b = Point(3, 4, CoordinateSpace.IMAGE)
        with self.assertRaises(ValueError):
            euclidean_distance(a, b)
        self.assertEqual(euclidean_distance(a, b, gsd=GroundSamplingDistance(0.1)), 0.5)

    def test_geographic_distance_is_not_naively_euclidean(self):
        a = Point(0, 0, CoordinateSpace.GEOGRAPHIC)
        with self.assertRaises(ValueError):
            euclidean_distance(a, Point(1, 1, CoordinateSpace.GEOGRAPHIC))

if __name__ == "__main__":
    unittest.main()
