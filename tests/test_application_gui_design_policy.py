from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_application_gui_design_gate import gate


class ApplicationGuiDesignPolicyTests(unittest.TestCase):
    def test_canonical_policy_gate_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertTrue(report["retroactive"])
        self.assertGreater(report["application_review_count"], 0)
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_policy_is_retroactive_change_synced_and_design_system_locked(self) -> None:
        policy = json.loads(
            (ROOT / "canonical/FA3-APPLICATION-GUI-DESIGN-POLICY-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(policy["scope"]["retroactive"])
        self.assertFalse(policy["scope"]["grandfathering_allowed"])
        self.assertTrue(policy["scope"]["continuous_change_sync"])
        self.assertEqual(policy["design_system"]["mode"], "FA3_DESIGN_SYSTEM_LOCKED")
        self.assertTrue(
            policy["placement"]["exact_final_application_local_placement_requires_owner_approval"]
        )
        self.assertTrue(
            policy["change_synchronization"]["functional_delta_requires_gui_impact_assessment"]
        )
        self.assertTrue(
            policy["change_synchronization"]["removed_function_may_not_leave_orphan_gui"]
        )

    def test_lifecycle_binding_is_fail_closed(self) -> None:
        lifecycle = json.loads(
            (ROOT / "canonical/FA3-APP-LIFECYCLE-001.json").read_text(encoding="utf-8")
        )
        gui = lifecycle["application_gui_governance"]
        self.assertEqual(gui["policy_id"], "FA3-APPLICATION-GUI-DESIGN-POLICY-001")
        self.assertTrue(gui["retroactive"])
        self.assertFalse(gui["grandfathering_allowed"])
        self.assertTrue(gui["fa3_design_system_required"])
        self.assertTrue(gui["functional_delta_gui_impact_assessment_required"])
        self.assertTrue(gui["exact_application_local_placement_owner_approval_required"])

    def test_missing_design_system_lock_fails(self) -> None:
        required = [
            "canonical/FA3-APPLICATION-GUI-DESIGN-POLICY-001.json",
            "canonical/FA3-APP-LIFECYCLE-001.json",
            "canonical/FA3-APPLICATION-GUI-RETROACTIVE-AUDIT-001.json",
            "canonical/contracts/FA3-APPLICATION-GUI-DESIGN-RECORD-001.schema.json",
            "canonical/FA3-GATE-APPLICATION-GUI-DESIGN-001.json",
            "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
            "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json",
            "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
            "canonical/FA3-GATE-REGISTRY-001.json",
            "canonical/enforcement-policy.json",
            "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json",
            "docs/FA3-APPLICATION-GUI-DESIGN-POLICY-001.md",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in required:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, target)
            policy_path = root / "canonical/FA3-APPLICATION-GUI-DESIGN-POLICY-001.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["design_system"]["mode"] = "APPLICATION_LOCAL"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            report = gate(root)
            codes = {row["code"] for row in report["findings"]}
            self.assertIn("GUI-POLICY-007", codes)


if __name__ == "__main__":
    unittest.main()
