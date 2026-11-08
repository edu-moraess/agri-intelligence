import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import validate_environment as validator


class ValidationSecurityTests(unittest.TestCase):
    def temp_repo(self):
        context = tempfile.TemporaryDirectory()
        root = Path(context.name)
        (root / "artifacts").mkdir()
        return context, root

    def test_secret_scanner_detects_synthetic_credentials(self):
        fake_token = "ghp_" + ("a" * 30)
        self.assertIn("github_token", validator.find_secret_indicators(fake_token))
        private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
        self.assertIn("private_key", validator.find_secret_indicators(private_key_marker))
        aws_key = "AKIA" + "1234567890ABCDEF"
        self.assertIn("aws_access_key", validator.find_secret_indicators(aws_key))

    def test_placeholders_do_not_create_false_positive(self):
        self.assertEqual(validator.find_secret_indicators('api_key = "your-token-here"'), [])
        self.assertEqual(validator.find_secret_indicators('password: "${PASSWORD}"'), [])

    def test_hidden_file_is_scanned(self):
        context, root = self.temp_repo()
        with context:
            (root / ".hidden-config").write_text("token = 'ghp_" + ("b" * 30) + "'", encoding="utf-8")
            status, detail = validator.run_secret_scan(root)
            self.assertEqual(status, "failed")
            self.assertIn(".hidden-config", detail)

    def test_binary_file_is_handled_without_decoding(self):
        context, root = self.temp_repo()
        with context:
            (root / "sample.bin").write_bytes(b"\x00\xff\x00binary")
            self.assertEqual(validator.run_secret_scan(root)[0], "passed")

    def test_read_error_is_a_failure(self):
        context, root = self.temp_repo()
        with context:
            target = root / "readme.txt"
            target.write_text("safe", encoding="utf-8")
            with patch.object(Path, "read_text", side_effect=OSError("synthetic read failure")):
                status, detail = validator.run_secret_scan(root)
            self.assertEqual(status, "failed")
            self.assertIn("read_error", detail)

    def test_large_file_is_not_read_unboundedly(self):
        context, root = self.temp_repo()
        with context:
            (root / "large.txt").write_bytes(b"x" * (validator.MAX_SCANNABLE_BYTES + 1))
            status, detail = validator.run_secret_scan(root)
            self.assertEqual(status, "failed")
            self.assertIn("file_too_large", detail)

    def test_external_symlink_is_rejected_without_following(self):
        context, root = self.temp_repo()
        with context:
            outside = Path(context.name).parent / (Path(context.name).name + "-outside")
            outside.write_text("ghp_" + ("c" * 30), encoding="utf-8")
            link = root / "linked-secret.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            status, detail = validator.run_artifact_scan(root)
            self.assertEqual(status, "failed")
            self.assertIn("symlink:linked-secret.txt", detail)

    def test_path_traversal_report_destination_is_rejected(self):
        context, root = self.temp_repo()
        with context:
            payload = {"gate": "PASS"}
            with self.assertRaises(ValueError):
                validator.write_report(root / "artifacts" / ".." / "outside.json", payload, root=root)

    def test_report_symlink_is_not_overwritten(self):
        context, root = self.temp_repo()
        with context:
            target = root / "outside.json"
            target.write_text("original", encoding="utf-8")
            report = root / "artifacts" / "phase_0_validation_report.json"
            try:
                report.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaises(OSError):
                validator.write_report(report, {"gate": "PASS"}, root=root)
            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_report_is_valid_json_and_only_designated_file_changes(self):
        context, root = self.temp_repo()
        with context:
            report = root / "artifacts" / "phase_0_validation_report.json"
            validator.write_report(report, {"gate": "PASS", "checks": []}, root=root)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["gate"], "PASS")
            self.assertEqual(list((root / "artifacts").iterdir()), [report])

    def test_non_serializable_report_payload_is_rejected(self):
        context, root = self.temp_repo()
        with context:
            report = root / "artifacts" / "phase_0_validation_report.json"
            with self.assertRaises(TypeError):
                validator.write_report(report, {"invalid": object()}, root=root)
            self.assertFalse(report.exists())

    def test_report_write_error_is_propagated(self):
        context, root = self.temp_repo()
        with context:
            report = root / "artifacts" / "phase_0_validation_report.json"
            with patch.object(validator.tempfile, "NamedTemporaryFile", side_effect=PermissionError("synthetic permission failure")):
                with self.assertRaises(PermissionError):
                    validator.write_report(report, {"gate": "PASS"}, root=root)

    def test_git_metadata_is_explicitly_excluded_from_worktree_scan(self):
        context, root = self.temp_repo()
        with context:
            (root / ".git").mkdir()
            (root / ".git" / "historical-secret.txt").write_text("ghp_" + ("d" * 30), encoding="utf-8")
            self.assertEqual(validator.run_secret_scan(root)[0], "passed")

    def test_prohibited_artifacts_are_rejected(self):
        context, root = self.temp_repo()
        with context:
            (root / "weights.onnx").write_bytes(b"synthetic")
            (root / ".env").write_text("safe-looking placeholder", encoding="utf-8")
            status, detail = validator.run_artifact_scan(root)
            self.assertEqual(status, "failed")
            self.assertIn("weights.onnx", detail)
            self.assertIn(".env", detail)

    def test_subprocess_failure_is_reported(self):
        context, root = self.temp_repo()
        with context:
            completed = type("Completed", (), {"returncode": 7, "stdout": "", "stderr": "synthetic failure"})()
            with patch.object(validator.subprocess, "run", return_value=completed):
                status, detail = validator.run_structural_tests(root)
            self.assertEqual(status, "failed")
            self.assertIn("synthetic failure", detail)

    def test_subprocess_timeout_is_reported(self):
        context, root = self.temp_repo()
        with context:
            with patch.object(validator.subprocess, "run", side_effect=validator.subprocess.TimeoutExpired("test", 30)):
                status, detail = validator.run_structural_tests(root)
            self.assertEqual(status, "failed")
            self.assertIn("timeout", detail)

    def test_gate_rejects_skipped_or_failed_required_checks(self):
        context, root = self.temp_repo()
        with context:
            with patch.object(validator, "run_structural_tests", return_value=("failed", "synthetic")):
                report = validator.build_report(root, root / "artifacts" / "report.json")
            self.assertEqual(report["gate"], "FAIL")


if __name__ == "__main__":
    unittest.main()
