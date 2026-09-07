import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_stability_matrix_lifecycle_gate as sm


class StabilityMatrixLifecycleGateTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        report = sm.gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual((report["regressions"]["passed"], report["regressions"]["total"]), (23, 23))
        self.assertFalse(report["current_host_production_claim"])

    def test_regression_matrix(self):
        report = sm.run_regressions()
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual((report["passed"], report["total"]), (23, 23))

    def test_hardcoded_device_route_is_rejected(self):
        self.assertFalse(sm.device_routing_valid(discovered=False, pci_slot="", gpu_uuid="", hrb_lease=False, hardcoded_model=True))

    def test_public_direct_bind_is_rejected(self):
        self.assertFalse(sm.network_valid(bind_host="0.0.0.0", proxy_approved=False))

    def test_gui_is_not_a_production_worker(self):
        self.assertFalse(sm.native_worker_valid(gui_process=True, native_unit=False, ai_media_target=False))

    def test_failed_validation_requires_completed_rollback(self):
        self.assertFalse(sm.rollback_valid(validation_pass=False, rollback_available=True, rolled_back=False))

    def test_provider_cannot_take_workflow_authority(self):
        authorities = {"workflow": "StabilityMatrix", "events": "NATS", "resources": "HostResourceBroker", "security": "SecurityGovernance", "evidence": "ObservabilityEvidence"}
        self.assertFalse(sm.authority_retention_valid(authorities))


if __name__ == "__main__":
    unittest.main()
