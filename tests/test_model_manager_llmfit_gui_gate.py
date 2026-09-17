from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_model_manager_llmfit_gui_gate import gate, validate_provider, workload_draft_semantics  # noqa: E402


class ModelManagerLlmfitGuiGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = json.loads(
            (ROOT / "canonical/providers/FA3-PROVIDER-LLMFIT-001.json").read_text(encoding="utf-8")
        )

    def test_reference_materialization_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_provider_cannot_become_authority(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["architectural_authority"] = True
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-003", codes)

    def test_fit_estimate_cannot_be_runtime_evidence(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["model_fit_estimate"] = "RUNTIME_EVIDENCE"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-008", codes)

    def test_floating_upstream_release_is_rejected(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["upstream_release"] = "latest"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-005", codes)

    def test_placement_authority_remains_hrb(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["accelerator_placement"] = "LLMFIT"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-009", codes)

    def test_provider_hardware_observation_is_non_authoritative(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["hardware_detection"] = "ADMISSION_AUTHORITY"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-010", codes)

    def test_resource_classes_must_be_workload_derived(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["resource_class_derivation"] = "FROM_DETECTED_GPU"
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-011", codes)

    def test_cpu_only_does_not_require_accelerator(self) -> None:
        draft = workload_draft_semantics(False)
        self.assertEqual(draft["requested_resource_classes"], ["CPU", "MEMORY"])
        self.assertFalse(draft["accelerator_required"])
        self.assertFalse(draft["accelerator_discovery_required"])
        self.assertFalse(draft["accelerator_lease_required"])
        self.assertFalse(draft["accelerator_guard_required"])
        self.assertTrue(draft["hrb_authorization_required"])

    def test_accelerator_workload_is_hrb_and_guard_bound(self) -> None:
        draft = workload_draft_semantics(True)
        self.assertIn("ACCELERATOR", draft["requested_resource_classes"])
        self.assertTrue(draft["accelerator_required"])
        self.assertTrue(draft["accelerator_discovery_required"])
        self.assertTrue(draft["accelerator_lease_required"])
        self.assertTrue(draft["accelerator_guard_required"])
        self.assertTrue(draft["hrb_authorization_required"])

    def test_generic_hardware_baseline_cannot_be_redefined_by_provider(self) -> None:
        provider = copy.deepcopy(self.provider)
        provider["fa3_usage_policy"]["generic_global_nvidia_cuda_requirement"] = True
        codes = {row["code"] for row in validate_provider(provider)}
        self.assertIn("LLMFIT-GUI-015", codes)


if __name__ == "__main__":
    unittest.main()
