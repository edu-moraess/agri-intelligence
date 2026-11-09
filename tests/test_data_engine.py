import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agri_intelligence.data.annotations import audit_detection_records
from agri_intelligence.data.contracts import (
    AnnotationSchema, AuditFinding, AuditState, DatasetAsset, DatasetAuditResult,
    DatasetLicense, DatasetManifest, DatasetSource, DatasetSplit, DatasetVersion,
    LicenseStatus,
)
from agri_intelligence.data.inventory import inventory_paths
from agri_intelligence.data.leakage import audit_split_leakage
from agri_intelligence.data.manifest import manifest_to_dict, write_manifest
from agri_intelligence.data.spatial import SpatialDatasetMetadata


class DataEngineTests(unittest.TestCase):
    def manifest(self, license_status=LicenseStatus.VERIFIED):
        license_obj = DatasetLicense("CC-BY-4.0", license_status) if license_status == LicenseStatus.VERIFIED else DatasetLicense(None, license_status)
        audit_state = AuditState.PASS if license_status == LicenseStatus.VERIFIED else AuditState.BLOCKED
        return DatasetManifest(
            dataset_id="synthetic",
            version=DatasetVersion("1"),
            source=DatasetSource("https://example.invalid/source"),
            license=license_obj,
            annotation_schema=AnnotationSchema("coco", "object_detection", ("single", "double")),
            splits=(DatasetSplit("train"), DatasetSplit("test")),
            audit=DatasetAuditResult(audit_state),
        )

    def test_valid_manifest_is_serializable(self):
        payload = manifest_to_dict(self.manifest())
        self.assertEqual(payload["dataset_id"], "synthetic")
        self.assertEqual(payload["license"]["status"], "verified")

    def test_unknown_license_is_blocked(self):
        manifest = self.manifest(LicenseStatus.UNKNOWN)
        self.assertTrue(manifest.license.adoption_blocked)
        self.assertEqual(manifest.adoption_state, AuditState.BLOCKED)
        with self.assertRaises(ValueError):
            DatasetLicense("CC-BY-4.0", LicenseStatus.UNKNOWN, rights_verified=True)

    def test_checksum_and_missing_file_behavior(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "sample.bin"
            image.write_bytes(b"synthetic")
            assets = inventory_paths(root)
            self.assertEqual(len(assets), 1)
            self.assertEqual(len(assets[0].sha256), 64)
            image.unlink()
            with self.assertRaises(FileNotFoundError):
                inventory_paths(root, [image])

    def test_png_dimensions_are_observed_without_loading_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (640).to_bytes(4, "big") + (480).to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
            (root / "sample.png").write_bytes(header)
            asset = inventory_paths(root)[0]
            self.assertEqual((asset.width, asset.height, asset.channels), (640, 480, 3))

    def test_annotation_validation_catches_invalid_boxes_and_classes(self):
        audit = audit_detection_records([
            {"id": "a1", "image_id": "img", "bbox": [0, 0, 10, 10], "category": "unknown"},
            {"id": "a1", "image_id": "missing", "bbox": [0, 0, 0, 4], "category": "single"},
        ], {"img": (8, 8)}, {"single"})
        codes = {finding.code for finding in audit.findings}
        self.assertIn("unknown_class", codes)
        self.assertIn("bbox_out_of_bounds", codes)
        self.assertIn("duplicate_annotation_id", codes)
        self.assertIn("annotation_without_image", codes)

    def test_images_without_annotations_are_warnings(self):
        audit = audit_detection_records([], {"img": (10, 10)}, {"single"})
        self.assertEqual(audit.findings[0].severity, "warning")
        self.assertEqual(audit.findings[0].code, "image_without_annotations")

    def test_exact_hash_and_related_group_leakage_are_reported(self):
        audit = audit_split_leakage([
            {"sha256": "abc", "split": "train", "source_video": "v1"},
            {"sha256": "abc", "split": "test", "source_video": "v1"},
        ])
        codes = {finding.code for finding in audit.findings}
        self.assertIn("exact_hash_across_splits", codes)
        self.assertIn("related_group_across_splits", codes)

    def test_spatial_metadata_is_not_fabricated(self):
        manifest = self.manifest()
        self.assertEqual(manifest.spatial_reference, {})
        self.assertEqual(manifest.limitations, ())

    def test_spatial_contract_rejects_invalid_reference_data(self):
        with self.assertRaises(ValueError):
            SpatialDatasetMetadata(gsd_x_meters=0)
        with self.assertRaises(ValueError):
            SpatialDatasetMetadata(affine_transform=(1, 0, 0, 0, 0, 0))
        valid = SpatialDatasetMetadata(crs="EPSG:32623", gsd_x_meters=0.1, width=100, height=80)
        self.assertTrue(valid.has_ground_reference)
        self.assertFalse(valid.geographic_coordinates_available)

    def test_manifest_write_is_json_and_does_not_download(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            write_manifest(self.manifest(), path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"]["version"], "1")
            self.assertFalse((Path(temp) / "download").exists())


if __name__ == "__main__":
    unittest.main()
