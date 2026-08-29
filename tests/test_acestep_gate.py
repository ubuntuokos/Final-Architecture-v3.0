import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_acestep_gate import (
    api_boundary_valid,
    gate,
    hrb_admission_valid,
    kv_cache_invariance_valid,
    lm_reinit_policy_valid,
    lossless_master_valid,
    non_turbo_dcw_valid,
    requested_model_identity_valid,
    run_regressions,
    sft_promotion_valid,
    text2music_state_hygiene_valid,
)


class AceStepGateTests(unittest.TestCase):
    def test_reference_gate_and_regressions_pass(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["regressions"]["result"], "PASS")
        self.assertTrue(report["runtime_provider_required"])

    def test_provider_is_required_but_not_authority(self):
        provider = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-ACE-STEP-001.json").read_text())
        self.assertEqual(provider["status"], "ACCEPTED_REQUIRED_PRIMARY_REFERENCE")
        self.assertTrue(provider["global_runtime_promotion_required"])
        self.assertFalse(provider["architectural_authority"])
        self.assertFalse(provider["device_selection_authority"])
        self.assertFalse(provider["model_routing_authority"])
        self.assertFalse(provider["orchestration_authority"])
        self.assertEqual(provider["capability_count"], 143)

    def test_text2music_cover_state_leak_is_rejected(self):
        self.assertTrue(text2music_state_hygiene_valid("text2music", 1.0, 0.0))
        self.assertFalse(text2music_state_hygiene_valid("text2music", 1.0, 0.2))

    def test_non_turbo_dcw_and_sft_promotion_are_gated(self):
        self.assertTrue(non_turbo_dcw_valid("xl_sft", False))
        self.assertFalse(non_turbo_dcw_valid("xl_sft", True))
        self.assertTrue(sft_promotion_valid(dcw_off_pass=True, quality_pass=True, negative_regression_pass=True))
        self.assertFalse(sft_promotion_valid(dcw_off_pass=True, quality_pass=False, negative_regression_pass=True))

    def test_requested_model_cannot_silently_fallback(self):
        self.assertTrue(requested_model_identity_valid("m1", "m1", silent_fallback=False))
        self.assertFalse(requested_model_identity_valid("m1", "m2", silent_fallback=True))

    def test_hrb_and_api_boundaries_fail_closed(self):
        self.assertTrue(hrb_admission_valid(accelerator=True, hrb_lease="lease", provider_self_placed=False))
        self.assertFalse(hrb_admission_valid(accelerator=True, hrb_lease=None, provider_self_placed=False))
        self.assertTrue(api_boundary_valid(bind_address="127.0.0.1", authenticated=True, central_gateway=True))
        self.assertFalse(api_boundary_valid(bind_address="0.0.0.0", authenticated=False, central_gateway=False))

    def test_reinit_memory_safety_is_enforced(self):
        self.assertTrue(kv_cache_invariance_valid(2.95, 2.96))
        self.assertFalse(kv_cache_invariance_valid(2.95, 3.77))
        self.assertTrue(lm_reinit_policy_valid(in_process_reinit=True, clean_teardown_pass=False, process_recycle=True))
        self.assertFalse(lm_reinit_policy_valid(in_process_reinit=True, clean_teardown_pass=False, process_recycle=False))

    def test_lossless_master_is_required(self):
        self.assertTrue(lossless_master_valid("wav"))
        self.assertTrue(lossless_master_valid("flac"))
        self.assertFalse(lossless_master_valid("mp3"))

    def test_regression_suite_passes(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], report["total"])
        self.assertGreaterEqual(report["total"], 10)


if __name__ == "__main__":
    unittest.main()
