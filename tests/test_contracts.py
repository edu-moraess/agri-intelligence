import unittest
from datetime import datetime, timezone
from agri_intelligence.core.contracts import Observation, Prediction, Provenance, Uncertainty, DerivedMeasurement
from agri_intelligence.geometry.coordinates import CoordinateSpace, GroundSamplingDistance, Point, euclidean_distance
from agri_intelligence.geospatial.metadata import SpatialMetadata

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.provenance = Provenance("test", "fixture")

    def test_observation_and_prediction_keep_provenance(self):
        obs = Observation("o1", datetime.now(timezone.utc), self.provenance, {"plant": 1})
        pred = Prediction("p1", "future-model", {"label": "seedling"}, self.provenance, confidence=0.8)
        self.assertEqual(obs.provenance.source, "test")
        self.assertEqual(pred.model, "future-model")

    def test_pixel_distance_requires_gsd(self):
        a, b = Point(0, 0, CoordinateSpace.IMAGE), Point(3, 4, CoordinateSpace.IMAGE)
        with self.assertRaises(ValueError):
            euclidean_distance(a, b)
        self.assertAlmostEqual(euclidean_distance(a, b, gsd=GroundSamplingDistance(0.1)), 0.5)

    def test_anisotropic_gsd_is_applied_per_axis(self):
        a, b = Point(0, 0, CoordinateSpace.IMAGE), Point(3, 4, CoordinateSpace.IMAGE)
        gsd = GroundSamplingDistance(0.1, meters_per_pixel_y=0.2)
        self.assertAlmostEqual(euclidean_distance(a, b, gsd=gsd), (0.3**2 + 0.8**2) ** 0.5)

    def test_geographic_distance_is_not_naively_euclidean(self):
        a = Point(0, 0, CoordinateSpace.GEOGRAPHIC)
        with self.assertRaises(ValueError):
            euclidean_distance(a, Point(1, 1, CoordinateSpace.GEOGRAPHIC))

    def test_non_finite_coordinates_and_gsd_are_rejected(self):
        with self.assertRaises(ValueError):
            Point(float("nan"), 0, CoordinateSpace.IMAGE)
        with self.assertRaises(ValueError):
            GroundSamplingDistance(float("inf"))

    def test_spatial_transform_requires_crs_and_affine_coefficients(self):
        with self.assertRaises(ValueError):
            SpatialMetadata(crs="EPSG:32623", transform_available=True)
        valid = SpatialMetadata(crs="EPSG:32623", transform_available=True,
                                affine_transform=(0.1, 0.0, 100.0, 0.0, -0.1, 200.0))
        self.assertTrue(valid.transform_available)

    def test_invalid_uncertainty_and_measurement_values_are_rejected(self):
        with self.assertRaises(ValueError):
            Uncertainty("stddev", float("nan"), "m")
        with self.assertRaises(ValueError):
            DerivedMeasurement("m1", float("inf"), "m", self.provenance, ("p1",))

if __name__ == "__main__":
    unittest.main()
