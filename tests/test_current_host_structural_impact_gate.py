from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_current_host_structural_impact_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]
POLICY = "canonical/FA3-CURRENT-HOST-STRUCTURAL-CHANGE-POLICY-001.json"


class CurrentHostStructuralImpactGateTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        dst = root / POLICY
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / POLICY, dst)
        return td, root

    def test_non_structural_change_needs_no_record(self):
        td, root = self._root()
        try:
            report = evaluate(root, ["docs/example.md", "tests/test_example.py"])
            self.assertEqual("PASS", report["result"], report)
            self.assertEqual([], report["structural_changes"])
        finally:
            td.cleanup()

    def test_structural_change_without_impact_record_fails_closed(self):
        td, root = self._root()
        try:
            report = evaluate(root, ["src/fa3_model_router.py"])
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(report["findings"])
        finally:
            td.cleanup()

    def test_reconciled_structural_change_requires_real_current_host_companion(self):
        td, root = self._root()
        try:
            record_path = "canonical/current-host-impact/FA3-CH-IMPACT-TEST-001.json"
            record = {
                "schema": "fa3.current-host-structural-impact.v1",
                "id": "FA3-CH-IMPACT-TEST-001",
                "status": "RECONCILED",
                "structural_changes": ["src/fa3_model_router.py"],
                "current_host_changes": ["src/fa3_model_router_current_host_gate.py"],
                "physical_requalification_required": True,
                "historical_evidence_reused": False,
                "rationale": "Model routing semantics changed and require fresh physical host requalification.",
            }
            path = root / record_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record), encoding="utf-8")
            report = evaluate(
                root,
                [
                    "src/fa3_model_router.py",
                    "src/fa3_model_router_current_host_gate.py",
                    record_path,
                ],
            )
            self.assertEqual("PASS", report["result"], report)
        finally:
            td.cleanup()

    def test_no_runtime_impact_requires_explicit_rationale_and_no_requalification(self):
        td, root = self._root()
        try:
            record_path = "canonical/current-host-impact/FA3-CH-IMPACT-TEST-002.json"
            record = {
                "schema": "fa3.current-host-structural-impact.v1",
                "id": "FA3-CH-IMPACT-TEST-002",
                "status": "NO_RUNTIME_IMPACT",
                "structural_changes": ["canonical/contracts/FA3-EXAMPLE-CONTRACTS-001.json"],
                "current_host_changes": [],
                "physical_requalification_required": False,
                "historical_evidence_reused": False,
                "rationale": "The change is schema documentation only and does not alter runtime behavior or evidence semantics.",
            }
            path = root / record_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record), encoding="utf-8")
            report = evaluate(
                root,
                ["canonical/contracts/FA3-EXAMPLE-CONTRACTS-001.json", record_path],
            )
            self.assertEqual("PASS", report["result"], report)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
