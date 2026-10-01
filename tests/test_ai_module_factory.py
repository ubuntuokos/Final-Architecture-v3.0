# SPDX-License-Identifier: Apache-2.0
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

class AIModuleFactoryStructureTest(unittest.TestCase):
    def test_profile_reuses_existing_capabilities(self):
        p=load("canonical/profiles/FA3-AI-MODULE-FACTORY-001.json")
        self.assertEqual(p["capability_count"],175)
        self.assertFalse(p["new_capability"])
        self.assertFalse(p["new_architectural_authority"])
        self.assertIn("CAP-095",p["capability_bindings"])
        self.assertFalse(p["routing"]["direct_provider_execution"])
        self.assertFalse(p["routing"]["direct_hardware_selection"])
        self.assertFalse(p["routing"]["silent_fallback"])

    def test_contract_is_fail_closed_and_draft_only(self):
        c=load("canonical/contracts/FA3-AI-MODULE-FACTORY-CONTRACTS-001.json")
        self.assertTrue(c["artifact_input"]["fail_closed_on_missing_or_unknown"])
        self.assertFalse(c["module_plan"]["execution_authorized"])
        self.assertFalse(c["module_plan"]["current_host_pass_claimed"])

    def test_application_and_gui_are_registered(self):
        a=load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
        app=next(x for x in a["applications"] if x["application_id"]=="fa3.ai-module-factory")
        self.assertEqual(app["lifecycle"],"PLANNED")
        shared=next(x for x in a["shared_capabilities"] if x["id"]=="FA3-SHARED-WORK-DERIVED-AI-001")
        self.assertIn("fa3.video-editor",shared["consumer_applications"])
        self.assertIn("fa3.story-screenplay",shared["consumer_applications"])
        g=load("canonical/FA3-GUI-SURFACE-REGISTRY-001.json")
        route=next(x for x in g["surfaces"] if x["route_id"]=="create.ai-module-factory")
        self.assertEqual(route["mutation"],"DRAFT_ONLY")
        self.assertFalse(route["direct_provider_execution"])
        self.assertFalse(route["direct_model_training"])

    def test_research_donors_not_claimed_registered(self):
        r=load("canonical/assessments/FA3-AI-MODULE-FACTORY-REUSE-ASSESSMENT-001.json")
        self.assertEqual(r["selected_existing_donor_ids"],[])
        self.assertFalse(r["donor_adoption_authorized"])
        self.assertFalse(r["donor_intake_status"]["new_research_batch_registered"])
        self.assertEqual(r["donor_intake_status"]["active_pr"],581)

    def test_current_host_remains_pending(self):
        h=load("canonical/FA3-AI-MODULE-FACTORY-CURRENT-HOST-IMPACT-001.json")
        self.assertFalse(h["physical_pass_claimed"])
        self.assertEqual(h["result"],"PENDING_PHYSICAL_CURRENT_HOST_REQUALIFICATION")

if __name__ == "__main__":
    unittest.main()
