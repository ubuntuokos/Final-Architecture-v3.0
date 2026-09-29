import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
AUD=ROOT/"canonical/deltas/FA3-DONOR-LEGACY-OPEN-PR-RECONCILIATION-2026-09-29.json"
class LegacyReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(REG.read_text());cls.a=json.loads(AUD.read_text());cls.e={x["source"]["normalized_key"]:x for x in cls.r["entries"]}
    def test_cardinality_baseline_and_sources(self):
        self.assertEqual(self.r["capability_count"],175)
        self.assertEqual(self.r["backfill"]["entry_count"],1189)
        self.assertEqual(len(self.r["entries"]),1189)
        self.assertEqual(len(self.a["additions"]),17)
        self.assertEqual(len(self.a["rekeys"]),3)
        self.assertEqual(len(self.a["enriched"]),7)
        self.assertEqual(len(self.a["held_prs"]),14)
        self.assertEqual(len({x["head_sha"] for x in self.a["held_prs"]}),13)
    def test_new_candidates_are_denied_automatic_admission(self):
        flags=["authority","automatic_selection","automatic_fetch","automatic_install","automatic_activation","automatic_dependency","automatic_code_import","automatic_provider_admission","automatic_model_selection"]
        for x in self.a["additions"]:
            e=self.e[x["key"]]
            self.assertEqual(e["donor_id"],x["id"])
            self.assertEqual(e["status"],"CANDIDATE")
            self.assertTrue(all(e[f] is False for f in flags))
    def test_legacy_aliases_preserved_in_place(self):
        for x in self.a["rekeys"]:
            e=self.e[x["new_key"]]
            self.assertEqual(e["donor_id"],x["id"])
            self.assertIn(x["old_key"],e["legacy_source_keys"])
            self.assertNotIn(x["old_key"],self.e)
    def test_held_workflow_is_not_a_donor_change(self):
        self.assertTrue(all(x["donor_workflow_line_changes"] is False for x in self.a["held_prs"]))
        self.assertTrue(all(x["feature_changes"]=="HOLD_NOT_MERGED" for x in self.a["held_prs"]))
        self.assertFalse(self.a["release_ready"])
if __name__=="__main__": unittest.main()
