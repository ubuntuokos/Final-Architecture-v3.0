import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_python_import_audit import audit


class PythonImportAuditTests(unittest.TestCase):
    def test_repository_uses_single_fa3_module_namespace(self):
        result = audit(ROOT)
        self.assertEqual(result["result"], "PASS", result["findings"][:20])

    def test_src_package_import_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "tests").mkdir()
            (root / "tests/test_bad.py").write_text("from src.fa3_decision_fabric import DecisionError\n")
            result = audit(root)
            self.assertEqual(result["result"], "FAIL")
            self.assertEqual(result["findings"][0]["code"], "PYIMPORT-001")

    def test_voice_router_and_decision_fabric_share_exception_identity(self):
        decision = importlib.import_module("fa3_decision_fabric")
        voice = importlib.import_module("fa3_voice_quality_router")
        self.assertIs(voice.DecisionError, decision.DecisionError)
        self.assertNotIn("src.fa3_decision_fabric", sys.modules)
        self.assertNotIn("src.fa3_voice_quality_router", sys.modules)


if __name__ == "__main__":
    unittest.main()
