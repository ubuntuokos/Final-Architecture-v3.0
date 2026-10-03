import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

class GameCreationWP0Test(unittest.TestCase):
    def test_decision_and_assessment_are_fail_closed(self):
        d=load("canonical/decisions/FA3-DEC-GAME-CREATION-CAPABILITY-WP0-2026-10-01.json")
        a=load("canonical/assessments/FA3-GAME-CREATION-CAPABILITY-INTEGRATION-REUSE-ASSESSMENT-001.json")
        self.assertEqual(d["invariants"]["capability_baseline"],175)
        self.assertEqual(d["invariants"]["capability_delta"],0)
        self.assertEqual(d["invariants"]["architectural_authority_delta"],0)
        self.assertFalse(d["invariants"]["code_import_authorized"])
        self.assertFalse(d["invariants"]["runtime_activation_by_this_change"])
        self.assertFalse(a["adoption_authorized"])
        self.assertFalse(a["runtime_admission_authorized"])
        self.assertFalse(a["code_import_authorized"])
        self.assertEqual(a["donor_intake_state"]["active_intake_pr"],581)
        self.assertTrue(a["donor_intake_state"]["no_competing_registry_mutation"])
        self.assertGreaterEqual(len(a["analysis_source_locks"]),20)
        for source in a["analysis_source_locks"]:
            self.assertFalse(source["source_copy_authorized"])
            self.assertFalse(source["runtime_dependency_authorized"])
            self.assertIn(source["reuse_route"],{"A+B","A(partial)+B+C","A(partial)+B","B+C","C"})

    def test_current_host_claims_no_runtime_pass(self):
        c=load("canonical/FA3-GAME-CREATION-CAPABILITY-INTEGRATION-CURRENT-HOST-IMPACT-001.json")
        self.assertEqual(c["status"],"NO_RUNTIME_IMPACT")
        self.assertFalse(c["runtime_change"])
        self.assertFalse(c["physical_current_host_pass_claimed"])
        self.assertFalse(c["alignment_scope"]["donor_registry_mutated"])
        self.assertFalse(c["alignment_scope"]["usage_edge_added"])

if __name__=="__main__":
    unittest.main()
