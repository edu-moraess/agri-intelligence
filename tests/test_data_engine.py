import json
import math
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
from agri_intelligence.data.inventory import inventory_paths, sha256_file
from agri_intelligence.data.leakage import audit_split_integrity, audit_split_leakage
from agri_intelligence.data.manifest import manifest_to_dict, write_manifest
from agri_intelligence.data.spatial import SpatialDatasetMetadata


class DataEngineTests(unittest.TestCase):
    def verified_license(self, **overrides):
        values = {
            "name": "CC-BY-4.0",
            "status": LicenseStatus.VERIFIED,
            "rights_verified": True,
            "commercial_use_verified": True,
            "attribution_required": True,
            "attribution_verified": True,
        }
        values.update(overrides)
        return DatasetLicense(**values)

    def manifest(self, license_status=LicenseStatus.VERIFIED):
        license_obj = (
            self.verified_license()
            if license_status == LicenseStatus.VERIFIED
            else DatasetLicense(None, license_status)
        )
        audit_state = AuditState.PASS if not license_obj.adoption_blocked else AuditState.BLOCKED
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
        self.assertEqual(self.manifest().adoption_state, AuditState.PASS)

    def test_unknown_license_is_blocked(self):
        manifest = self.manifest(LicenseStatus.UNKNOWN)
        self.assertTrue(manifest.license.adoption_blocked)
        self.assertEqual(manifest.adoption_state, AuditState.BLOCKED)
        with self.assertRaises(ValueError):
            DatasetLicense("CC-BY-4.0", LicenseStatus.UNKNOWN, rights_verified=True)

    def test_license_name_alone_does_not_allow_adoption(self):
        license_obj = DatasetLicense("CC-BY-4.0", LicenseStatus.VERIFIED)
        self.assertTrue(license_obj.adoption_blocked)

    def test_license_requires_rights_commercial_and_attribution_review(self):
        cases = [
            {"rights_verified": False},
            {"commercial_use_verified": False},
            {"attribution_verified": False},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                license_obj = self.verified_license(**changes)
                self.assertTrue(license_obj.adoption_blocked)

    def test_verified_license_allows_adoption_only_when_all_requirements_met(self):
        self.assertFalse(self.verified_license().adoption_blocked)

    def test_license_rejects_malformed_attribution_metadata(self):
        with self.assertRaises(ValueError):
            self.verified_license(attribution_required="yes")

    def test_checksum_and_missing_file_behavior(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "sample.bin"
            image.write_bytes(b"synthetic")
            assets = inventory_paths(root)
            self.assertEqual(len(assets), 1)
            self.assertEqual(len(assets[0].sha256), 64)
            self.assertEqual(sha256_file(image, chunk_size=2), assets[0].sha256)
            with self.assertRaises(ValueError):
                sha256_file(image, chunk_size=0)
            image.unlink()
            with self.assertRaises(FileNotFoundError):
                inventory_paths(root, [image])

    def test_inventory_requires_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                inventory_paths(Path(temp) / "missing")
            file_path = Path(temp) / "file"
            file_path.write_text("x")
            with self.assertRaises(NotADirectoryError):
                inventory_paths(file_path)

    def test_inventory_relative_paths_are_relative_to_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "nested").mkdir()
            (root / "nested" / "asset.bin").write_bytes(b"data")
            assets = inventory_paths(root, [Path("nested/asset.bin")])
            self.assertEqual(assets[0].path, "nested/asset.bin")

    def test_inventory_rejects_paths_outside_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            root.mkdir()
            outside = Path(temp) / "outside.bin"
            outside.write_bytes(b"outside")
            with self.assertRaises(ValueError):
                inventory_paths(root, [outside])

    def test_inventory_rejects_symlink_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            root.mkdir()
            target = Path(temp) / "target.bin"
            target.write_bytes(b"target")
            link = root / "link.bin"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are not supported in this environment")
            with self.assertRaises(ValueError):
                inventory_paths(root, [link])

    def test_png_dimensions_are_observed_without_loading_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            header = (
                bytes([137]) + b"PNG\r\n\x1a\n" + bytes([0, 0, 0, 13]) + b"IHDR"
                + (640).to_bytes(4, "big") + (480).to_bytes(4, "big")
                + bytes([8, 2])
            )
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

    def test_annotation_rejects_non_numeric_and_non_finite_bbox_values(self):
        for bbox in ([0, 0, "bad", 4], [0, 0, math.nan, 4], [0, 0, math.inf, 4], [0, 0, True, 4]):
            with self.subTest(bbox=bbox):
                audit = audit_detection_records(
                    [{"id": "a", "image_id": "img", "bbox": bbox, "category": "single"}],
                    {"img": (10, 10)}, {"single"}
                )
                self.assertIn("invalid_bbox_values", {item.code for item in audit.findings})

    def test_annotation_rejects_invalid_image_dimensions_without_crashing(self):
        audit = audit_detection_records(
            [{"id": "a", "image_id": "img", "bbox": [0, 0, 1, 1], "category": "single"}],
            {"img": (0, 10)}, {"single"}
        )
        codes = {item.code for item in audit.findings}
        self.assertIn("invalid_image_dimensions", codes)
        self.assertIn("annotation_without_image", codes)

    def test_annotation_coordinate_modes_are_applied(self):
        normalized = audit_detection_records(
            [{"id": "n", "image_id": "img", "bbox": [0.1, 0.1, 0.5, 0.5], "category": "single"}],
            {"img": (100, 100)}, {"single"}, coordinate_mode="normalized_xywh"
        )
        xyxy = audit_detection_records(
            [{"id": "p", "image_id": "img", "bbox": [10, 10, 60, 60], "category": "single"}],
            {"img": (100, 100)}, {"single"}, coordinate_mode="absolute_xyxy"
        )
        self.assertNotIn("bbox_out_of_bounds", {item.code for item in normalized.findings})
        self.assertNotIn("bbox_out_of_bounds", {item.code for item in xyxy.findings})

    def test_annotation_rejects_unsupported_coordinate_mode(self):
        for mode in ("unknown", ["absolute_xywh"]):
            with self.subTest(mode=mode):
                audit = audit_detection_records([], {}, set(), coordinate_mode=mode)
                self.assertEqual(audit.findings[0].code, "unsupported_coordinate_mode")

    def test_schema_rejects_non_string_coordinate_mode(self):
        with self.assertRaises(ValueError):
            AnnotationSchema("coco", "detection", ("plant",), coordinate_mode=["xywh"])

    def test_annotation_rejects_non_mapping_records(self):
        audit = audit_detection_records([None], {"img": (10, 10)}, {"single"})
        self.assertIn("invalid_annotation_record", {item.code for item in audit.findings})

    def test_images_without_annotations_are_warnings(self):
        audit = audit_detection_records([], {"img": (10, 10)}, {"single"})
        self.assertEqual(audit.findings[0].severity, "warning")
        self.assertEqual(audit.findings[0].code, "image_without_annotations")

    def test_exact_hash_and_related_group_leakage_are_reported(self):
        digest = "a" * 64
        audit = audit_split_leakage([
            {"sha256": digest, "split": "train", "source_video": "v1"},
            {"sha256": digest, "split": "test", "source_video": "v1"},
        ])
        codes = {finding.code for finding in audit.findings}
        self.assertIn("exact_hash_across_splits", codes)
        self.assertIn("related_group_across_splits", codes)

    def test_split_integrity_detects_unknown_and_repeated_assets(self):
        audit = audit_split_integrity(
            [{"asset_id": "a"}, {"asset_id": "b"}],
            [
                {"name": "train", "asset_ids": ["a", "missing"]},
                {"name": "test", "asset_ids": ["a", "b"]},
            ],
        )
        codes = {finding.code for finding in audit.findings}
        self.assertIn("unknown_split_asset", codes)
        self.assertIn("asset_in_multiple_splits", codes)

    def test_split_integrity_detects_duplicate_ids_and_split_names(self):
        audit = audit_split_integrity(
            [{"asset_id": "a"}, {"asset_id": "a"}],
            [{"name": "train", "asset_ids": ["a"]}, {"name": "train", "asset_ids": []}],
        )
        codes = {finding.code for finding in audit.findings}
        self.assertIn("duplicate_asset_id", codes)
        self.assertIn("duplicate_split_name", codes)

    def test_manifest_rejects_duplicate_asset_ids_and_paths(self):
        asset = DatasetAsset("a", "a.png", 1)
        with self.assertRaises(ValueError):
            DatasetManifest("x", DatasetVersion("1"), DatasetSource("local:x"),
                            self.verified_license(), assets=(asset, asset))
        with self.assertRaises(ValueError):
            DatasetManifest("x", DatasetVersion("1"), DatasetSource("local:x"),
                            self.verified_license(),
                            assets=(asset, DatasetAsset("b", "a.png", 1)))

    def test_manifest_rejects_unknown_and_cross_split_asset_assignments(self):
        asset = DatasetAsset("a", "a.png", 1)
        args = ("x", DatasetVersion("1"), DatasetSource("local:x"), self.verified_license())
        with self.assertRaises(ValueError):
            DatasetManifest(*args, assets=(asset,), splits=(DatasetSplit("train", ("missing",)),))
        with self.assertRaises(ValueError):
            DatasetManifest(*args, assets=(asset,), splits=(
                DatasetSplit("train", ("a",)), DatasetSplit("test", ("a",))
            ))

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

    def test_manifest_write_is_json_and_atomic_temp_is_cleaned(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            write_manifest(self.manifest(), path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"]["version"], "1")
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])

    def test_manifest_write_requires_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing" / "manifest.json"
            with self.assertRaises(FileNotFoundError):
                write_manifest(self.manifest(), path)


if __name__ == "__main__":
    unittest.main()
