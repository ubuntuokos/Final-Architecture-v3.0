from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA=ROOT/"canonical/deltas/FA3-DONOR-AGENT-NATIVE-TOPICS-2026-10-01.json"
DEC=ROOT/"canonical/decisions/FA3-DEC-AGENT-NATIVE-RECONCILIATION-2026-10-01.json"
EXPECTED={
    "github:topics/agent-native?l=c&o=desc&s=updated": "FA3-DONOR-TOPICS-AGENT-NATIVE-L-C-O-DESC-S-UPDATED-001",
    "github:topics/agent-native?l=python&o=asc&s=stars": "FA3-DONOR-TOPICS-AGENT-NATIVE-L-PYTHON-O-ASC-S-STARS-001",
    "github:topics/agent-native-web": "FA3-DONOR-TOPICS-AGENT-NATIVE-WEB-001",
}
FLAGS=("authority","automatic_selection","automatic_fetch","automatic_install","automatic_activation","automatic_dependency","automatic_code_import","automatic_provider_admission","automatic_model_selection")

class AgentNativeDonorIntakeTests(unittest.TestCase):
    def test_exact_three_scoped_owner_references(self):
        reg=json.loads(REG.read_text())
        rows={r["source"]["normalized_key"]:r for r in reg["entries"]}
        self.assertEqual(reg["capability_count"],175)
        self.assertEqual(reg["backfill"]["entry_count"],len(reg["entries"]))
        for key,did in EXPECTED.items():
            row=rows[key]
            self.assertEqual(row["donor_id"],did)
            self.assertEqual(row["status"],"ACCEPTED_REFERENCE")
            self.assertEqual(row["submission_review"]["basis"],"OWNER_EXPLICIT_DONOR_LIST_COMMAND")
            self.assertTrue(row["discoverable_for_planning"])
            self.assertTrue(all(row[f] is False for f in FLAGS))
    def test_delta_and_decision_preserve_non_adoption_boundary(self):
        d=json.loads(DELTA.read_text()); dec=json.loads(DEC.read_text())
        self.assertEqual(d["parent_entry_count"],1307)
        self.assertEqual(d["proposed_entry_count"],1310)
        self.assertEqual(d["unique_source_key_count"],3)
        self.assertTrue(dec["explicit_user_approval"])
        self.assertFalse(dec["scoped_donor_registration"]["global_literal_donornak_rule_changed"])
        self.assertFalse(dec["scoped_donor_registration"]["adoption_authorized"])
        self.assertEqual(dec["new_capabilities"],0)
        self.assertEqual(dec["new_architectural_authorities"],0)

if __name__=="__main__":
    unittest.main()
