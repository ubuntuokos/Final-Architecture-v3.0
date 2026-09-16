import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_intel_accel_gate import CAPABILITY_COUNT, classify_fixture, dedup_aliases, evaluate


class IntelAccelGateTests(unittest.TestCase):
    def test_repository_gate_passes(self):
        result = evaluate(ROOT)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(CAPABILITY_COUNT, result["capability_count"])
        self.assertFalse(result["current_host_runtime_promotion_claim"])
        self.assertEqual([], result["repository_audit"]["blocking_hits"])

    def test_absent_intel_accelerator_is_not_failure(self):
        state = classify_fixture({})
        self.assertTrue(state["not_applicable"])
        self.assertFalse(state["intel_gpu"])
        self.assertFalse(state["intel_npu"])

    def test_openvino_cpu_fixture(self):
        state = classify_fixture({"intel_cpu": True, "openvino_devices": ["CPU"]})
        self.assertTrue(state["openvino_cpu_ready"])
        self.assertFalse(state["not_applicable"])

    def test_gpu_openvino_and_torch_xpu_fixture(self):
        state = classify_fixture({
            "intel_gpu": True,
            "openvino_devices": ["GPU"],
            "torch_xpu_available": True,
        })
        self.assertTrue(state["openvino_gpu_ready"])
        self.assertTrue(state["torch_xpu_ready"])
        self.assertEqual("READY", state["device_states"]["GPU"])

    def test_npu_openvino_fixture(self):
        state = classify_fixture({"intel_npu": True, "openvino_devices": ["NPU"]})
        self.assertTrue(state["openvino_npu_ready"])
        self.assertEqual("READY", state["device_states"]["NPU"])

    def test_external_contention_precedes_ready(self):
        state = classify_fixture({
            "intel_gpu": True,
            "openvino_devices": ["GPU"],
            "external_busy": ["GPU"],
        })
        self.assertEqual("BUSY_EXTERNAL", state["device_states"]["GPU"])

    def test_fa3_lease_is_reported(self):
        state = classify_fixture({
            "intel_npu": True,
            "openvino_devices": ["NPU"],
            "fa3_leased": ["NPU"],
        })
        self.assertEqual("LEASED_FA3", state["device_states"]["NPU"])

    def test_runtime_aliases_dedup_to_physical_device(self):
        aliases = dedup_aliases([
            {"pci_bdf": "0000:03:00.0", "alias": "OPENVINO:GPU.0"},
            {"pci_bdf": "0000:03:00.0", "alias": "LEVEL_ZERO:0"},
            {"pci_bdf": "0000:03:00.0", "alias": "TORCH_XPU:0"},
        ])
        self.assertEqual(["0000:03:00.0"], list(aliases))
        self.assertEqual(3, len(aliases["0000:03:00.0"]))

    def test_alias_without_physical_identity_fails_closed(self):
        with self.assertRaises(ValueError):
            dedup_aliases([{"alias": "TORCH_XPU:0"}])


if __name__ == "__main__":
    unittest.main()
