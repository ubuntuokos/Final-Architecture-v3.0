from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class ChangeHistoryProfileTests(unittest.TestCase):
    def test_profile_is_shared_derived_non_authority(self):
        p=load("canonical/profiles/FA3-CHANGE-HISTORY-INTELLIGENCE-001.json")
        self.assertEqual(p["parent_profile_id"],"FA3-JOURNAL-001")
        self.assertEqual(p["capability_count"],175)
        self.assertFalse(p["new_capability"])
        self.assertFalse(p["new_architectural_authority"])
        self.assertFalse(p["storage"]["source_of_truth"])
        self.assertTrue(p["storage"]["rebuildable"])
        self.assertTrue(p["storage"]["source_mutation_forbidden"])

    def test_reuse_is_published_main_bound_and_has_usage_edges(self):
        a=load("canonical/assessments/FA3-CHANGE-HISTORY-INTELLIGENCE-REUSE-ASSESSMENT-001.json")
        links=load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
        snap=a["donor_planning_snapshot"]
        self.assertEqual(snap["published_main_commit"],"d65215e75867d71605093ae8f46a0dfbd6c6f471")
        self.assertEqual(snap["donor_registry_entry_count"],1344)
        expected=set(a["selected_existing_donor_ids"])
        active={r["donor_id"] for r in links["donor_usage_records"] if r["status"]!="REMOVED"}
        self.assertTrue(expected <= active)

    def test_current_host_remains_pending(self):
        h=load("canonical/FA3-CHANGE-HISTORY-CURRENT-HOST-IMPACT-001.json")
        self.assertFalse(h["physical_pass_claimed"])
        self.assertEqual(h["result"],"PENDING_PHYSICAL_CURRENT_HOST_REQUALIFICATION")
        self.assertEqual(h["central_current_host_reconciliation"]["active_pr"],559)

if __name__=="__main__": unittest.main()
