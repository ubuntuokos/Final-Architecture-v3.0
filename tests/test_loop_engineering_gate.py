import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_closed_loop_agent_ops_reference as refimpl
import fa3_loop_engineering_gate as loopgate


class LoopEngineeringGateTests(unittest.TestCase):
    def _copy(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return td, root

    def test_baseline_gate_passes(self):
        report = loopgate.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual((36, 36), (report["regressions"]["passed"], report["regressions"]["total"]))

    def test_all_36_rules_have_positive_and_negative_cases(self):
        report = loopgate.run_regressions()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(36, len(report["cases"]))
        self.assertEqual(36, len({case["rule_id"] for case in report["cases"]}))
        self.assertTrue(all(case["positive_case"] for case in report["cases"]))
        self.assertTrue(all(case["negative_case_rejected"] for case in report["cases"]))

    def test_maker_checker_fail_closed(self):
        self.assertFalse(refimpl.maker_checker_valid(
            level="L3_UNATTENDED", maker_session="same", verifier_session="same",
            verifier_restricted=True, verifier_self_repairs=False,
        ))
        self.assertFalse(refimpl.maker_checker_valid(
            level="L2_ASSISTED", maker_session="m", verifier_session="v",
            verifier_restricted=False, verifier_self_repairs=True,
        ))

    def test_budget_and_circuit_breaker_fail_closed(self):
        self.assertFalse(refimpl.budget_valid(
            usage={"tokens": 100}, limits={"tokens": 1000},
            self_raise=True, extension_human_approved=False,
        ))
        self.assertTrue(refimpl.circuit_breaker_stop(
            {"same_error_repeats": 3},
            {"same_error_repeat_limit": 3},
        ))

    def test_workspace_policy_and_human_gate_fail_closed(self):
        self.assertFalse(refimpl.workspace_valid(
            level="L3_UNATTENDED", mutating=True, isolated=True, lease=False, single_writer=False,
        ))
        self.assertFalse(refimpl.auto_merge_valid(
            enabled=True, explicit_allowlist=False, low_risk=True, verifier_pass=True,
        ))
        self.assertFalse(refimpl.high_risk_gate_valid(high_risk=True, human_approved=False))

    def test_drift_and_compaction_fail_closed(self):
        self.assertFalse(refimpl.drift_preflight_valid(level="L3_UNATTENDED", hashes_match=False))
        self.assertFalse(refimpl.compaction_valid(
            required_provenance_ids={"a", "b"}, retained_provenance_ids={"a"},
        ))

    def test_portable_hardware_floor_is_not_model_pinned(self):
        self.assertFalse(refimpl.hardware_admission_valid(
            live_discovery=False, hrb_lease=False, static_cpu_ids=True,
            reference_as_portable_default=True, accelerator_required=False,
            gpu_uuid=None, pci_bdf=None, ordinal_only=False,
        ))
        self.assertFalse(refimpl.hardware_admission_valid(
            live_discovery=True, hrb_lease=False, static_cpu_ids=False,
            reference_as_portable_default=False, accelerator_required=True,
            gpu_uuid=None, pci_bdf=None, ordinal_only=True,
        ))
        self.assertTrue(refimpl.portable_hardware_floor_valid(
            cpu_packages=1, physical_cores_per_package=8,
            cpu_vendor_pinned=False, cpu_model_pinned=False,
            gpu_count=1, gpu_rtx_equivalent_series=30,
            gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,
            gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True,
        ))
        self.assertTrue(refimpl.portable_hardware_floor_valid(
            cpu_packages=2, physical_cores_per_package=24,
            cpu_vendor_pinned=False, cpu_model_pinned=False,
            gpu_count=1, gpu_rtx_equivalent_series=50,
            gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,
            gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True,
        ))
        self.assertFalse(refimpl.portable_hardware_floor_valid(
            cpu_packages=1, physical_cores_per_package=7,
            cpu_vendor_pinned=False, cpu_model_pinned=False,
            gpu_count=1, gpu_rtx_equivalent_series=20,
            gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,
            gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True,
        ))

    def test_provider_authority_drift_fails(self):
        td, root = self._copy()
        try:
            path = root / loopgate.PATHS["provider"]
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["architectural_authority"] = True
            path.write_text(json.dumps(obj) + "\n", encoding="utf-8")
            self.assertEqual("FAIL", loopgate.gate(root)["result"])
        finally:
            td.cleanup()

    def test_reference_evidence_cannot_claim_current_host(self):
        evidence = json.loads((ROOT / loopgate.PATHS["evidence"]).read_text(encoding="utf-8"))
        self.assertEqual("PASS", evidence["status"])
        self.assertFalse(evidence["current_host_provider_runtime_evidence"])
        self.assertFalse(evidence["current_host_runtime_promotion_claim"])
        self.assertFalse(evidence["production_provider_admission_claim"])


if __name__ == "__main__":
    unittest.main()
