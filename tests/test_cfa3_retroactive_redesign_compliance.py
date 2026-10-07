import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cfa3_retroactive_redesign_compliance import evaluate_record
from cfa3_retroactive_redesign_compliance_gate import GATE_ID, gate

POLICY = ROOT / "canonical/CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001.json"
DONOR = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"


def record(phase="REDESIGN_IN_PROGRESS"):
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    return {
        "schema": "cfa3.retroactive-redesign-record.v1",
        "component": {
            "id": "test.legacy",
            "kind": "APPLICATION",
            "designed_before_mandatory_donor_policy": True,
            "trigger_evidence_refs": ["test:legacy"]
        },
        "phase": phase,
        "legacy_source_discovery_complete": True,
        "legacy_sources": [],
        "current_rule_baseline": {
            "captured_from_canonical_main": True,
            "captured_main_sha": "b" * 40,
            "mandatory_rule_refs": ["test:current-rules"]
        },
        "rule_delta": [
            {"category": category, "status": "ALREADY_COMPLIANT", "rationale": "test", "evidence_refs": ["test:pass"]}
            for category in policy["current_rule_delta_review"]["required_categories"]
        ],
        "finalization_checks": {
            name: "PASS" for name in policy["finalization_gate"]["required_checks"]
        },
        "donor_registry_sha256": hashlib.sha256(DONOR.read_bytes()).hexdigest(),
        "capability_baseline": 175,
        "capability_delta": 0,
        "architectural_authority_delta": 0
    }


class RetroactiveRedesignComplianceTests(unittest.TestCase):
    def test_global_gate_passes(self):
        result = gate(ROOT)
        self.assertEqual(GATE_ID, result["gate_id"])
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(175, result["capability_count"])
        self.assertEqual(0, result["new_capabilities"])
        self.assertEqual(0, result["new_architectural_authorities"])

    def test_unregistered_legacy_source_allowed_during_planning(self):
        r = record()
        r["legacy_sources"] = [{
            "locator": "https://example.invalid/cfa3-test-legacy",
            "normalized_key": "https://example.invalid/cfa3-test-legacy",
            "origin_refs": ["test:old-plan"],
            "registry_status_at_discovery": "MISSING",
            "temporary_planning_use": True,
            "canonical_donor_id": None,
            "registration_evidence_refs": []
        }]
        self.assertEqual("PASS", evaluate_record(ROOT, r)["result"])

    def test_unregistered_legacy_source_blocks_finalization(self):
        r = record("REDESIGN_FINAL")
        r["legacy_sources"] = [{
            "locator": "https://example.invalid/cfa3-test-legacy",
            "normalized_key": "https://example.invalid/cfa3-test-legacy",
            "origin_refs": ["test:old-plan"],
            "registry_status_at_discovery": "MISSING",
            "temporary_planning_use": True,
            "canonical_donor_id": None,
            "registration_evidence_refs": []
        }]
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-013" for x in result["findings"]))

    def test_rule_delta_must_cover_every_category(self):
        r = record()
        r["rule_delta"] = r["rule_delta"][:-1]
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-027" for x in result["findings"]))

    def test_not_applicable_requires_rationale(self):
        r = record()
        r["rule_delta"][0]["status"] = "NOT_APPLICABLE"
        r["rule_delta"][0]["rationale"] = ""
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-025" for x in result["findings"]))

    def test_unresolved_rule_delta_blocks_finalization(self):
        r = record("REDESIGN_FINAL")
        r["rule_delta"][0]["status"] = "REQUIRES_CHANGE"
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-026" for x in result["findings"]))

    def test_finalization_requires_current_registry_digest(self):
        r = record("REDESIGN_FINAL")
        r["donor_registry_sha256"] = "0" * 64
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-030" for x in result["findings"]))

    def test_post_donor_policy_component_is_not_retroactive_case(self):
        r = record()
        r["component"]["designed_before_mandatory_donor_policy"] = False
        r["component"]["donor_policy_applicable_at_original_design"] = True
        result = evaluate_record(ROOT, r)
        self.assertEqual("PASS", result["result"])
        self.assertEqual("NOT_APPLICABLE_NORMAL_DONOR_RULES", result["disposition"])


if __name__ == "__main__":
    unittest.main()
