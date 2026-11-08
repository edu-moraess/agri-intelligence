import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_environment import find_secret_indicators, run_python_compile

class ValidationTests(unittest.TestCase):
    def test_secret_scanner_detects_high_confidence_tokens(self):
        self.assertIn("github_token", find_secret_indicators("token = ghp_abcdefghijklmnopqrstuvwxyz123456"))
        self.assertIn("private_key", find_secret_indicators("-----BEGIN PRIVATE KEY-----"))

    def test_secret_scanner_ignores_documented_placeholders(self):
        self.assertEqual(find_secret_indicators('api_key = "your-token-here"'), [])

    def test_python_sources_compile_in_memory(self):
        passed, detail = run_python_compile()
        self.assertTrue(passed, detail)
        self.assertIn("Python files compiled", detail)

if __name__ == "__main__":
    unittest.main()
