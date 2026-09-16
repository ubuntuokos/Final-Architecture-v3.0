from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hardware_fabric_gate import current_host_claim_valid, evaluate  # noqa: E402
from fa3_hardware_fabric_current_host_gate import validate_receipt  # noqa: E402


class HardwareFabricGateTests(unittest.TestCase):
    def test_repository_hardware_fabric_materialization(self):
        report = evaluate(ROOT)
        self.assertEqual(report["result"], "PASS", json.dumps(report, indent=2))
        self.assertEqual(report["capability_delta"], 0)
        self.assertEqual(report["authority_delta"], 0)

    def test_authority_model_uses_existing_hw_root(self):
        hw = json.loads((ROOT / "canonical/profiles/FA3-HW-001.json").read_text(encoding="utf-8"))
        compute = json.loads((ROOT / "canonical/FA3-COMPUTE-PROFILE-001.json").read_text(encoding="utf-8"))
        reconciliation = json.loads((ROOT / "canonical/FA3-HARDWARE-FABRIC-RECONCILIATION-001.json").read_text(encoding="utf-8"))
        self.assertTrue(hw["canonical_root"])
        self.assertEqual(hw["id"], "FA3-HW-001")
        self.assertEqual(compute["purpose"], "DESCRIBE_MEASURED_RESOURCE_CAPABILITY_WITHOUT_NAMED_HARDWARE_ADMISSION")
        self.assertEqual(reconciliation["authority_resolution"]["hardware_capability_root"]["repository_presence"], "VERIFIED_PRESENT")
        self.assertFalse(reconciliation["authority_resolution"]["hardware_capability_root"]["retraction_required"])

    def test_no_false_current_host_pass(self):
        self.assertFalse(current_host_claim_valid("PASS", None))
        invalid = {
            "schema": "fa3.hardware-fabric-current-host-receipt.v1",
            "executed": False,
            "result": "PASS",
            "guard_default_mode": "RECOMMEND",
            "destructive_action_performed": False,
        }
        self.assertFalse(current_host_claim_valid("PASS", invalid))
        self.assertTrue(current_host_claim_valid("RUNTIME_EVIDENCE_PENDING", None))

    def test_valid_executed_receipt_contract(self):
        receipt = {
            "schema": "fa3.hardware-fabric-current-host-receipt.v1",
            "executed": True,
            "result": "PASS",
            "hardware_root": "FA3-HW-001",
            "compute_profile": "FA3-COMPUTE-PROFILE-001",
            "guard": "FA3-ACCEL-GUARD-001",
            "guard_default_mode": "RECOMMEND",
            "destructive_action_performed": False,
            "automatic_external_process_preemption_performed": False,
            "decision": {
                "mode": "RECOMMEND",
                "automatic_resolution": False,
                "destructive_action_authorized": False,
            },
            "baseline": {"observable": True},
            "current": {"observable": True},
            "contention_state": "NO_CONTENTION",
        }
        self.assertEqual(validate_receipt(receipt), [])
        self.assertTrue(current_host_claim_valid("PASS", receipt))


if __name__ == "__main__":
    unittest.main()
