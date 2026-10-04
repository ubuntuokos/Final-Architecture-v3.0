import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_naming_compatibility_gate import (
    DECISION,
    EXPECTED_ALIASES,
    POLICY,
    evaluate,
)
from fa3_release_baseline import BASELINE_PATH, active_capability_count


class NamingCompatibilityGateTests(unittest.TestCase):
    def _sandbox(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for rel in (BASELINE_PATH, POLICY, DECISION):
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)
        return td, root

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

    def test_contradictory_decision_fails_closed(self):
        td, root = self._sandbox()
        try:
            path = root / DECISION
            decision = json.loads(path.read_text(encoding="utf-8"))
            decision["destructive_history_rewrite"] = True
            decision["automatic_machine_identifier_rename"] = True
            decision["owner_directive"] = []
            path.write_text(json.dumps(decision), encoding="utf-8")
            report = evaluate(root)
            self.assertEqual("FAIL", report["result"], report)
            checks = {row["name"]: row["status"] for row in report["checks"]}
            self.assertEqual("FAIL", checks["decision-equivalence-bound"])
            self.assertEqual("FAIL", checks["decision-nondestructive-bound"])
        finally:
            td.cleanup()

    def test_failure_report_exposes_observed_policy_values(self):
        td, root = self._sandbox()
        try:
            path = root / POLICY
            policy = json.loads(path.read_text(encoding="utf-8"))
            policy["semantic_aliases"] = ["CFA3"]
            policy["capability_baseline"] = active_capability_count(ROOT) + 1
            path.write_text(json.dumps(policy), encoding="utf-8")
            report = evaluate(root)
            self.assertEqual("FAIL", report["result"], report)
            self.assertEqual(["CFA3"], report["semantic_aliases"])
            self.assertEqual(active_capability_count(ROOT) + 1, report["capability_count"])
            self.assertEqual(active_capability_count(ROOT), report["expected_active_capability_count"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
