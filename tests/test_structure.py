import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class StructureTests(unittest.TestCase):
    def test_required_documents_exist(self):
        for relative in ["README.md", "pyproject.toml", "docs/ARCHITECTURE.md", "docs/ARCHITECTURE_REVIEW.md", "configs/default.yaml", "scripts/validate_environment.py"]:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_no_ci_workflow_was_created(self):
        workflow_dir = ROOT / ".github" / "workflows"
        self.assertFalse(workflow_dir.exists())

if __name__ == "__main__":
    unittest.main()
