import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_naming_compatibility_gate import EXPECTED_ALIASES, evaluate
from fa3_release_baseline import active_capability_count

class NamingCompatibilityGateTests(unittest.TestCase):
    def test_repository_policy_passes(self):
        report = evaluate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual("CFA3", report["canonical_product_name"])
        self.assertEqual(active_capability_count(ROOT), report["capability_count"])

    def test_alias_set_is_exact(self):
        self.assertEqual({"CFA3", "FA3", "FA3/CFA3", "CFA3/FA3"}, EXPECTED_ALIASES)

    def test_no_capability_or_authority_delta(self):
        report = evaluate(ROOT)
        checks = {row["name"]: row["status"] for row in report["checks"]}
        self.assertEqual("PASS", checks["baseline-preserved"])
        self.assertEqual(active_capability_count(ROOT), report["capability_count"])

    def test_history_and_machine_identifiers_are_protected(self):
        report = evaluate(ROOT)
        checks = {row["name"]: row["status"] for row in report["checks"]}
        self.assertEqual("PASS", checks["history-preserved"])
        self.assertEqual("PASS", checks["machine-identifiers-not-auto-renamed"])

if __name__ == "__main__":
    unittest.main()
