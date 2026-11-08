import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_environment import find_secret_indicators, run_python_compile

class ValidationTests(unittest.TestCase):
    def test_secret_scanner_detects_high_confidence_tokens(self):
        fake_token = "ghp_" + ("a" * 26) + "123456"
        self.assertIn("github_token", find_secret_indicators("token = " + fake_token))
        private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
        self.assertIn("private_key", find_secret_indicators(private_key_marker))

    def test_secret_scanner_ignores_documented_placeholders(self):
        self.assertEqual(find_secret_indicators('api_key = "your-token-here"'), [])

    def test_secret_scanner_detects_hardcoded_credential_assignment(self):
        sample = "client_" + "secret = " + '"not-a-placeholder-value"'
        self.assertIn("hardcoded_credential_assignment", find_secret_indicators(sample))

    def test_python_sources_compile_in_memory(self):
        passed, detail = run_python_compile()
        self.assertTrue(passed, detail)
        self.assertIn("Python files compiled", detail)

if __name__ == "__main__":
    unittest.main()
