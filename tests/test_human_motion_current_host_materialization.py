from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HumanMotionCurrentHostMaterializationTests(unittest.TestCase):
    def test_current_host_descriptor_is_fail_closed_and_non_authoritative(self):
        c = load("canonical/FA3-HUMAN-MOTION-CURRENT-HOST-CONFORMANCE-001.json"); g = load("canonical/FA3-GATE-HUMAN-MOTION-CURRENT-HOST-001.json"); e = load("canonical/human-motion-current-host-enforcement.json")
        self.assertEqual("PENDING_REAL_CURRENT_HOST_EXECUTION", c["status"]); self.assertFalse(c["production_admitted"]); self.assertEqual(143, c["capability_count_after"]); self.assertEqual(0, c["new_architectural_authorities"]); self.assertTrue(c["fail_closed"])
        self.assertEqual(28, g["rule_count"]); self.assertTrue(g["fail_closed"]); self.assertFalse(g["hosted_ci_may_promote_runtime"]); self.assertEqual(28, e["mandatory_rule_count"]); self.assertEqual(28, len(e["rules"]))

    def test_hardware_conformance_chain_is_mandatory_and_provider_neutral(self):
        c = load("canonical/FA3-HUMAN-MOTION-CURRENT-HOST-CONFORMANCE-001.json"); g = load("canonical/FA3-GATE-HUMAN-MOTION-CURRENT-HOST-001.json"); e = load("canonical/human-motion-current-host-enforcement.json")
        expected = ["HRB_COMPUTE_ROLE_ADMISSION", "NON_DISPLAY_GPU", "LIVE_UUID_PCI_BDF_IDENTITY", "NUMA_LOCALITY_EVIDENCE", "CUDA_EXECUTION", "NO_CPU_OR_CROSS_ACCELERATOR_FALLBACK"]
        self.assertEqual(expected, c["mandatory_hardware_conformance_chain"]); self.assertEqual(expected, g["mandatory_hardware_conformance_chain"])
        self.assertEqual("FA3-AUTH-HOST-RESOURCE-BROKER-001", c["hardware_authority_id"]); self.assertEqual("FA3-AUTH-HOST-RESOURCE-BROKER-001", g["hardware_authority_id"])
        self.assertTrue(g["exact_accelerator_sku_pin_forbidden"]); self.assertTrue(g["runtime_gpu_ordinal_as_identity_forbidden"])
        self.assertIn("hrb_compute_role_admission", e["rules"]); self.assertIn("selected_accelerator_non_display", e["rules"]); self.assertIn("hrb_numa_locality_placement_evidence", e["rules"]); self.assertIn("no_cpu_or_cross_accelerator_fallback", e["rules"])

    def test_parent_runtime_records_bind_current_host_gate_without_promoting(self):
        for path in ("canonical/FA3-GEM-X-RUNTIME-CONFORMANCE-001.json", "canonical/FA3-SOMA-X-RUNTIME-CONFORMANCE-001.json"):
            value = load(path); self.assertEqual("PENDING_CURRENT_HOST", value["status"]); self.assertFalse(value["production_admitted"]); self.assertEqual("FA3-HUMAN-MOTION-CURRENT-HOST-CONFORMANCE-001", value["current_host_conformance_id"]); self.assertEqual("FA3-GATE-HUMAN-MOTION-CURRENT-HOST-001", value["current_host_gate_id"]); self.assertTrue(value["runtime_promotion_requires_current_host_gate_pass"])

    def test_release_projection_preserves_143_and_no_runtime_claim(self):
        r = load("canonical/releases/FA3-RELEASE-PROJECTION-HUMAN-MOTION-2026-09-12.json"); self.assertEqual(143, r["capability_count_after"]); self.assertEqual(0, r["new_architectural_authorities"]); self.assertFalse(r["production_promotion_claimed"]); self.assertEqual("PENDING_CURRENT_HOST", r["current_host_runtime_status"]); self.assertEqual("FA3-GATE-HUMAN-MOTION-CURRENT-HOST-001", r["current_host_gate_id"])

    def test_dispatch_and_workflow_are_current_host_bounded(self):
        enforce = (ROOT / "bin/fa3-enforce").read_text(encoding="utf-8"); wf = (ROOT / ".github/workflows/fa3-human-motion-current-host.yml").read_text(encoding="utf-8")
        self.assertIn("human-motion-current-host", enforce); self.assertIn("runs-on: [self-hosted, linux, x64, fa3-current-host]", wf); self.assertIn("workflow_dispatch:", wf); self.assertIn("HF_HUB_OFFLINE: '1'", wf); self.assertIn("command -v bwrap", wf); self.assertIn("compute-role, non-display, UUID+BDF and NUMA-locality", wf); self.assertNotIn("curl ", wf); self.assertNotIn("wget ", wf)

    def test_no_concrete_current_gpu_sku_is_hardcoded(self):
        paths = [
            "canonical/FA3-HUMAN-MOTION-CURRENT-HOST-CONFORMANCE-001.json",
            "canonical/FA3-GATE-HUMAN-MOTION-CURRENT-HOST-001.json",
            "canonical/human-motion-current-host-enforcement.json",
            "src/fa3_human_motion_current_host.py",
            "evidence/collect-human-motion-current-host.py",
        ]
        text = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in paths).lower()
        self.assertNotIn("rtx 3090", text); self.assertNotIn("rtx3090", text); self.assertNotIn("a1000", text)

    def test_decision_preserves_architecture(self):
        d = load("canonical/decisions/FA3-DEC-HUMAN-MOTION-CURRENT-HOST-2026-09-12.json"); self.assertEqual(143, d["baseline_effect"]["capability_count_after"]); self.assertEqual(0, d["baseline_effect"]["new_architectural_authorities"]); self.assertFalse(d["security"]["runtime_network_fetch"]); self.assertFalse(d["security"]["automatic_model_download"])
        h = load("canonical/decisions/FA3-DEC-HUMAN-MOTION-HARDWARE-CONFORMANCE-2026-09-12.json"); self.assertEqual(143, h["baseline_effect"]["capability_count_after"]); self.assertEqual(0, h["baseline_effect"]["new_architectural_authorities"]); self.assertEqual("FA3-AUTH-HOST-RESOURCE-BROKER-001", h["placement_authority_id"])


if __name__ == "__main__": unittest.main()
