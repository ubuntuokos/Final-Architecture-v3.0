import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_skill_fabric_v14 import (
    adversarial_review_allowed,
    artifact_binding_allowed,
    distributed_rate_limit_allowed,
    evaluate,
    ledger_update_allowed,
    positive_trigger_allowed,
    quality_floor_change_allowed,
    source_grounding_allowed,
)


class SkillFabricV14Tests(unittest.TestCase):
    def test_gate(self):
        report = evaluate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertGreaterEqual(report["regressions"]["total"], 24)

    def test_negated_trigger_is_not_positive_trigger(self):
        self.assertFalse(positive_trigger_allowed("Do not use when editing prose."))
        self.assertTrue(positive_trigger_allowed("Do not use when editing prose. Use when changing an API."))

    def test_quality_floor_rejects_rule_removal(self):
        before = {"capability_count": 175, "fail_closed": True, "mandatory_rules": ["A", "B"]}
        after = {"capability_count": 175, "fail_closed": True, "mandatory_rules": ["A"]}
        self.assertFalse(quality_floor_change_allowed(before, after))

    def test_rejected_change_ledger_is_append_only(self):
        before = {"append_only": True, "entries": [{"id": "R1"}]}
        self.assertTrue(ledger_update_allowed(before, {"append_only": True, "entries": [{"id": "R1"}, {"id": "R2"}]}))
        self.assertFalse(ledger_update_allowed(before, {"append_only": True, "entries": [{"id": "R2"}]}))

    def test_source_grounding_requires_runtime_verification(self):
        self.assertFalse(source_grounding_allowed({
            "claim": "x", "source_uri": "https://example.invalid", "immutable_source_ref": "v1",
            "claim_source_match": True, "verified": True, "source_is_authority": False,
            "implementation_affecting": True, "runtime_verification": {"required": True, "result": "PENDING"},
        }))

    def test_adversarial_review_cannot_self_select_provider(self):
        self.assertFalse(adversarial_review_allowed({
            "fresh_context": True, "original_conclusion_withheld": True, "artifact_ref": "a", "contract_ref": "c",
            "routes": {"model": "FA3-AUTH-MODEL-ROUTER-001", "resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001", "federation": "FA3-AGENT-FEDERATION-001"},
            "provider_self_selected": True, "reviewer_is_promotion_authority": False, "unresolved_critical_findings": 0,
        }))

    def test_artifact_binding_rejects_path_drift(self):
        self.assertFalse(artifact_binding_allowed({
            "artifact_id": "A", "schema_id": "S",
            "producer": {"component": "p", "path": "reports/a.json"},
            "consumers": [{"component": "c", "expected_path": "reports/b.json"}],
            "authority_owner": "FA3-AUTH-OBS-EVIDENCE-001",
        }))

    def test_multi_instance_rate_limit_requires_shared_store(self):
        self.assertFalse(distributed_rate_limit_allowed({
            "instance_count": 2, "shared_counter_store": False, "atomic_updates": True, "in_process_only": True,
        }))


if __name__ == "__main__":
    unittest.main()
