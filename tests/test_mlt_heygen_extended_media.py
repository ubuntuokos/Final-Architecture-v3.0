import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_mlt_extended_media import MediaPlanError, plan_hyperframes, plan_heygen, timeline_binding
from fa3_mlt_heygen_gate import gate

class MLTHeyGenExtendedMediaTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        report=gate()
        self.assertEqual(report["result"],"PASS",report["findings"])
        self.assertEqual(report["capability_count"],175)

    def test_hyperframes_plan_is_non_executing_and_preserves_source(self):
        plan=plan_hyperframes({
            "project_id":"project:test",
            "composition":{"source_revision":"b41ef425","source_hash":"sha256:test"}
        })
        self.assertFalse(plan["execution_requested"])
        self.assertTrue(plan["editable_source_preserved"])
        self.assertEqual(plan["donor_id"],"FA3-DONOR-HYPERFRAMES-001")
        self.assertTrue(plan["runtime_admission_required"])

    def test_reference_planner_rejects_direct_execution(self):
        with self.assertRaises(MediaPlanError):
            plan_hyperframes({
                "project_id":"project:test","execute":True,
                "composition":{"source_revision":"x","source_hash":"y"}
            })

    def test_heygen_plan_requires_rights_and_secret_broker_reference(self):
        with self.assertRaises(MediaPlanError):
            plan_heygen({"project_id":"project:test","operation":"digital_human.attach"})
        plan=plan_heygen({
            "project_id":"project:test","operation":"digital_human.attach",
            "rights_decision_ref":"rights:approved","secret_ref":"secret-broker://heygen/api",
            "cloud_execution_approved":True,"billable_execution_approved":True
        })
        self.assertEqual(plan["status"],"BLOCKED_RUNTIME_NOT_ADMITTED")
        self.assertFalse(plan["provider_runtime_admitted"])
        self.assertEqual(plan["provider_model_routing_authority"],"FA3-AUTH-MODEL-ROUTER-001")

    def test_raw_secret_is_rejected(self):
        with self.assertRaises(MediaPlanError):
            plan_heygen({
                "project_id":"project:test","operation":"digital_human.attach",
                "rights_decision_ref":"rights:approved","secret_ref":"secret-broker://heygen/api",
                "api_key":"should-never-be-here"
            })

    def test_generated_media_binding_never_mutates_kdenlive_xml_directly(self):
        binding=timeline_binding({"sha256":"abc","provider_id":"FA3-PROVIDER-HEYGEN-001"},project_id="p",track_id="v2")
        self.assertFalse(binding["direct_kdenlive_project_xml_mutation"])
        self.assertIn("DRY_RUN_DIFF_APPROVAL",binding["mutation_path"])

    def test_engine_registry_exposes_parallel_choices_without_readiness_claim(self):
        registry=json.loads((ROOT/"canonical/FA3-ENGINE-REGISTRY-001.json").read_text())
        by_id={x["engine_id"]:x for x in registry["engine_records"]}
        self.assertTrue(by_id["FA3-ENGINE-MLT-001"]["permanent_parallel_option"])
        self.assertTrue(by_id["FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001"]["permanent_parallel_option"])
        self.assertEqual(by_id["FA3-ENGINE-HYPERFRAMES-001"]["health_state"],"CURRENT_HOST_NOT_ADMITTED")
        self.assertEqual(by_id["FA3-ENGINE-HEYGEN-001"]["health_state"],"CURRENT_HOST_NOT_ADMITTED")

    def test_hyperframes_donor_usage_is_explicit(self):
        links=json.loads((ROOT/"canonical/FA3-APPLICATION-DONOR-LINKS-001.json").read_text())
        usage=next(x for x in links["donor_usage_records"] if x["id"]=="FA3-USAGE-HYPERFRAMES-MLT-EXTENDED-MEDIA-001")
        self.assertEqual(usage["donor_id"],"FA3-DONOR-HYPERFRAMES-001")
        self.assertEqual(usage["usage_kind"],"ARCHITECTURE_PATTERN")
        self.assertFalse(usage["code_imported"])
        self.assertFalse(usage["runtime_dependency"])

if __name__=="__main__":
    unittest.main()
