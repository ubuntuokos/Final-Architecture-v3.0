import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cfa3_retroactive_redesign_compliance import (
    REAL_RECORD_ROOT,
    _published_main_sha,
    _published_registry,
    evaluate_record,
)
from cfa3_retroactive_redesign_compliance_gate import GATE_ID, gate, real_record_paths

POLICY = ROOT / "canonical/CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001.json"


def record(phase="REDESIGN_IN_PROGRESS"):
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    published_main = _published_main_sha(ROOT)
    _registry, registry_raw = _published_registry(ROOT, published_main)
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
            "captured_main_sha": published_main,
            "mandatory_rule_refs": ["test:current-rules"]
        },
        "rule_delta": [
            {"category": category, "status": "ALREADY_COMPLIANT", "rationale": "test", "evidence_refs": ["test:pass"]}
            for category in policy["current_rule_delta_review"]["required_categories"]
        ],
        "finalization_checks": {
            name: "PASS" for name in policy["finalization_gate"]["required_checks"]
        },
        "donor_registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
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

    def test_legacy_sources_inventory_must_be_explicit(self):
        r = record()
        del r["legacy_sources"]
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-032" for x in result["findings"]))

    def test_locator_must_derive_recorded_normalized_key(self):
        r = record()
        r["legacy_sources"] = [{
            "locator": "https://example.invalid/unrelated",
            "normalized_key": "github:someone/else",
            "origin_refs": ["test:mismatch"],
            "registry_status_at_discovery": "PRESENT",
            "temporary_planning_use": False,
            "canonical_donor_id": None,
            "registration_evidence_refs": []
        }]
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-033" for x in result["findings"]))

    def test_temporary_use_is_limited_to_policy_allowlist(self):
        r = record("LEGACY_COMPONENT_IDENTIFIED")
        r["legacy_sources"] = [{
            "locator": "https://example.invalid/cfa3-test-legacy",
            "normalized_key": "https://example.invalid/cfa3-test-legacy",
            "origin_refs": ["test:phase"],
            "registry_status_at_discovery": "MISSING",
            "temporary_planning_use": True,
            "canonical_donor_id": None,
            "registration_evidence_refs": []
        }]
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-034" for x in result["findings"]))

    def test_finalization_requires_exact_published_main_sha(self):
        r = record("REDESIGN_FINAL")
        r["current_rule_baseline"]["captured_main_sha"] = "a" * 40
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] in {"RR-035", "RR-036"} for x in result["findings"]))

    def test_canonical_source_requires_exact_donor_id(self):
        registry, _raw = _published_registry(ROOT, _published_main_sha(ROOT))
        donor = next(
            row for row in registry["entries"]
            if row.get("status") in {"ACCEPTED_REFERENCE", "ANALYZED"}
            and isinstance(row.get("source", {}).get("locator"), str)
            and row["source"]["locator"].startswith("https://")
        )
        r = record("REDESIGN_FINAL")
        r["legacy_sources"] = [{
            "locator": donor["source"]["locator"],
            "normalized_key": donor["source"]["normalized_key"],
            "origin_refs": ["test:canonical"],
            "registry_status_at_discovery": "PRESENT",
            "temporary_planning_use": False,
            "canonical_donor_id": None,
            "registration_evidence_refs": ["test:registry"]
        }]
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] in {"RR-015", "RR-033"} for x in result["findings"]))

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

    def test_not_applicable_path_preserves_prior_failures(self):
        r = record()
        r["schema"] = "invalid.schema"
        r["component"]["designed_before_mandatory_donor_policy"] = False
        r["component"]["donor_policy_applicable_at_original_design"] = True
        result = evaluate_record(ROOT, r)
        self.assertEqual("FAIL", result["result"])
        self.assertTrue(any(x["code"] == "RR-001" for x in result["findings"]))

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

    def test_real_record_discovery_uses_canonical_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record_root = root / REAL_RECORD_ROOT
            record_root.mkdir(parents=True)
            (record_root / "one.json").write_text("{}", encoding="utf-8")
            (root / "outside.json").write_text("{}", encoding="utf-8")
            self.assertEqual([record_root / "one.json"], real_record_paths(root))


if __name__ == "__main__":
    unittest.main()
