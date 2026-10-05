from __future__ import annotations

import json
import unittest
from pathlib import Path

from fa3_license_rights import evaluate_descriptor, evaluate_release_receipt
from fa3_license_rights_gate import gate

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "canonical/license-rights-policy.json").read_text(encoding="utf-8"))


class LicenseRightsTests(unittest.TestCase):
    def descriptor(self):
        return {
            "schema": "fa3.license-rights-descriptor.v1",
            "subject": {"id": "x", "type": "CODE"},
            "source": {"locator": "example/repo", "revision": "a" * 40},
            "license": {
                "declared": "Apache-2.0",
                "detected": ["Apache-2.0"],
                "concluded": "Apache-2.0",
                "effective": "Apache-2.0",
            },
            "rights": {
                "modification_allowed": True,
                "redistribution_allowed": True,
                "commercial_use_allowed": True,
            },
            "obligations": {
                "attribution_required": True,
                "source_offer_required": False,
                "entitlement_required": False,
                "unresolved": [],
            },
            "disposition": "ALLOW_WITH_OBLIGATIONS",
            "evidence": ["fixture"],
        }

    def test_static_gate(self):
        result = gate(ROOT)
        self.assertEqual("PASS", result["result"])
        self.assertFalse(result["release_eligible"])
        self.assertIn(result["retroactive_audit_status"], {"PENDING_RETROACTIVE_AUDIT", "IN_PROGRESS_RETROACTIVE_AUDIT"})

    def test_valid_descriptor(self):
        result = evaluate_descriptor(self.descriptor(), POLICY)
        self.assertEqual("PASS", result["result"])
        self.assertTrue(result["admitted_for_release"])

    def test_unknown_license_fails_closed(self):
        d = self.descriptor()
        d["license"]["effective"] = "UNKNOWN"
        self.assertEqual("FAIL", evaluate_descriptor(d, POLICY)["result"])

    def test_required_entitlement_needs_reference(self):
        d = self.descriptor()
        d["obligations"]["entitlement_required"] = True
        self.assertEqual("FAIL", evaluate_descriptor(d, POLICY)["result"])

    def test_reference_only_is_valid_but_not_releasable(self):
        d = self.descriptor()
        d["disposition"] = "REFERENCE_ONLY"
        result = evaluate_descriptor(d, POLICY)
        self.assertEqual("PASS", result["result"])
        self.assertFalse(result["admitted_for_release"])

    def test_release_receipt_requires_completed_retroactive_audit(self):
        r = {
            "schema": "fa3.release-license-compliance-receipt.v1",
            "release": {"id": "r"},
            "repository_audit": {"status": "PENDING"},
            "sbom": {"spdx_status": "GENERATED", "cyclonedx_status": "GENERATED"},
            "notices": {"third_party_notice_status": "GENERATED"},
            "obligations": {
                "attribution_resolved": True,
                "source_offer_resolved": True,
                "entitlements_resolved": True,
            },
            "counts": {"unknown_license_count": 0, "unresolved_conflict_count": 0},
        }
        self.assertEqual("FAIL", evaluate_release_receipt(r, POLICY)["result"])
        r["repository_audit"]["status"] = "PASS"
        self.assertEqual("PASS", evaluate_release_receipt(r, POLICY)["result"])


if __name__ == "__main__":
    unittest.main()
