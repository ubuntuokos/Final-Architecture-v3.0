from __future__ import annotations
import unittest
from fa3_change_impact import evidence_currentness

class EvidenceCurrentnessTests(unittest.TestCase):
    def test_identity_drift_marks_evidence_stale(self):
        state=evidence_currentness(
            {"subject_identity":{"source_sha":"a","config_sha":"b"}},
            {"source_sha":"a","config_sha":"c"},
        )
        self.assertFalse(state["current"])
        self.assertEqual(state["stale_fields"],["config_sha"])
        self.assertTrue(state["requires_requalification"])

    def test_matching_identity_stays_current(self):
        state=evidence_currentness({"subject_identity":{"source_sha":"a"}},{"source_sha":"a"})
        self.assertTrue(state["current"])

if __name__=="__main__": unittest.main()
