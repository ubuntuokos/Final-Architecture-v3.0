from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_tutorial_reuse_planner import plan_tutorial, self_check

DONOR_ID = "FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001"


def tutorial(feature: dict, donor_id: str = DONOR_ID) -> dict:
    return {
        "schema": "fa3.tutorial-reference-input.v1",
        "reference_class": "TUTORIAL_REFERENCE",
        "donor_id": donor_id,
        "title": "Synthetic registered tutorial fixture",
        "provenance": {
            "source": "fixture:synthetic-tutorial",
            "rights_status": "REFERENCE_ONLY",
            "reuse_allowance": "FUNCTIONAL_ANALYSIS_ONLY",
            "product": "fixture",
            "version": "1",
        },
        "feature_units": [feature],
    }


def run(payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tutorial.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return plan_tutorial(ROOT, path)


class TutorialReusePlannerTests(unittest.TestCase):
    def test_self_check_preserves_baseline_and_zero_runtime_delta(self):
        report = self_check(ROOT)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertEqual(report["capability_baseline"], 175)
        self.assertEqual(report["runtime_delta"], "NONE")

    def test_existing_multi_app_function_routes_to_shared_core(self):
        report = run(tutorial({
            "feature_id": "TFU-SHARED-001",
            "name": "Existing shared function",
            "intent": "Exercise shared placement",
            "capability_hints": ["CAP-001"],
            "application_hints": ["fa3.video-editor", "fa3.quickclip"],
            "requested_placement": "AUTO",
        }))
        self.assertEqual(report["result"], "PASS", report["findings"])
        feature = report["features"][0]
        self.assertEqual(feature["capability_match_state"], "EXISTING_CAPABILITY")
        self.assertTrue(feature["shared_core_required"])
        self.assertEqual(feature["placement"], "SHARED_LAYER_REQUIRED")
        self.assertIn("fa3.video-editor", feature["matched_application_ids"])
        self.assertIn("fa3.quickclip", feature["matched_application_ids"])
        self.assertTrue(all(x["manual_update_required"] for x in feature["impact"]))
        self.assertTrue(all(not x["capability_loss_allowed"] for x in feature["impact"]))

    def test_missing_function_is_real_gap_not_automatic_implementation(self):
        report = run(tutorial({
            "feature_id": "TFU-GAP-001",
            "name": "Synthetic unmapped function",
            "intent": "Exercise real-gap path",
            "capability_hints": ["NOT-A-CANONICAL-CAPABILITY"],
            "application_hints": ["fa3.video-editor"],
        }))
        self.assertEqual(report["result"], "PASS", report["findings"])
        feature = report["features"][0]
        self.assertEqual(feature["capability_match_state"], "REAL_GAP")
        self.assertFalse(feature["implementation_authorized_by_planner"])
        self.assertEqual(feature["impact"][0]["action"], "BLOCKED_BY_PENDING_IMPLEMENTATION")

    def test_unregistered_source_and_capability_growth_fail_closed(self):
        report = run(tutorial({
            "feature_id": "TFU-GUARD-001",
            "name": "Forbidden growth",
            "intent": "Exercise donor and 175 guards",
            "capability_hints": ["NOT-A-CANONICAL-CAPABILITY"],
            "application_hints": ["fa3.video-editor"],
            "requested_top_level_capability": True,
        }, donor_id="FA3-DONOR-DOES-NOT-EXIST"))
        self.assertEqual(report["result"], "BLOCKED")
        codes = {x["code"] for x in report["findings"]}
        self.assertIn("TUT-REG-001", codes)
        self.assertIn("TUT-CAP-175-GUARD", codes)
        self.assertEqual(report["capability_baseline"], 175)

    def test_manual_and_runtime_promotion_claims_fail_closed(self):
        report = run(tutorial({
            "feature_id": "TFU-CLAIM-001",
            "name": "Invalid claims",
            "intent": "Exercise documentation/runtime guards",
            "capability_hints": ["CAP-001"],
            "application_hints": ["fa3.video-editor"],
            "manual_claim_available": True,
            "runtime_promotion_claimed": True,
        }))
        self.assertEqual(report["result"], "BLOCKED")
        codes = {x["code"] for x in report["findings"]}
        self.assertIn("TUT-MANUAL-001", codes)
        self.assertIn("TUT-RUNTIME-001", codes)

    def test_structural_runtime_change_routes_to_current_host_requalification(self):
        report = run(tutorial({
            "feature_id": "TFU-HOST-001",
            "name": "Structural shared runtime change",
            "intent": "Exercise Current Host routing",
            "capability_hints": ["CAP-001"],
            "application_hints": ["fa3.video-editor", "fa3.quickclip"],
            "structural_runtime_change": True,
        }))
        self.assertEqual(report["result"], "PASS", report["findings"])
        host = report["features"][0]["current_host"]
        self.assertEqual(host["alignment"], "CURRENT_HOST_REQUALIFICATION_REQUIRED_AFTER_IMPLEMENTATION")
        self.assertTrue(host["physical_non_simulated_evidence_required_for_runtime_promotion"])
        self.assertFalse(host["runtime_promotion_claimed"])


if __name__ == "__main__":
    unittest.main()
