from __future__ import annotations

import json
import unittest
from pathlib import Path

from fa3_license_rights import evaluate_descriptor
from fa3_license_rights_retro_audit import run_audit

ROOT = Path(__file__).resolve().parents[1]


class RetroLicenseRightsAuditTests(unittest.TestCase):
    def test_audit_control_passes_without_faking_completion(self):
        report = run_audit(ROOT)
        self.assertEqual("PASS", report["control_result"])
        self.assertFalse(report["repository_audit_complete"])
        self.assertFalse(report["release_eligible"])
        self.assertEqual("PENDING_RETROACTIVE_AUDIT", report["repository_audit_status"])

    def test_jev_snapshot_has_exact_pinned_license_evidence(self):
        policy = json.loads((ROOT / "canonical/license-rights-policy.json").read_text(encoding="utf-8"))
        descriptor = json.loads(
            (ROOT / "canonical/descriptors/FA3-RIGHTS-THIRD-PARTY-RADAR-SNAPSHOT-001.json").read_text(encoding="utf-8")
        )
        result = evaluate_descriptor(descriptor, policy)
        self.assertEqual("PASS", result["result"])
        self.assertTrue(result["admitted_for_release"])
        self.assertEqual("MIT", descriptor["license"]["effective"])
        self.assertEqual(
            "a27922ad457389775f4fe4eadcf688afc9d36d83",
            descriptor["source"]["revision"],
        )

    def test_no_external_subject_is_currently_in_product_bundle(self):
        manifest = json.loads((ROOT / "canonical/distribution-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(0, manifest["included_external_count"])
        self.assertEqual([], manifest["third_party_notices"])

    def test_historical_status_remains_fail_closed(self):
        status = json.loads((ROOT / "canonical/license-rights-audit-status.json").read_text(encoding="utf-8"))
        self.assertEqual("PENDING_RETROACTIVE_AUDIT", status["status"])
        self.assertFalse(status["release_eligible"])
        self.assertFalse(status["global_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
