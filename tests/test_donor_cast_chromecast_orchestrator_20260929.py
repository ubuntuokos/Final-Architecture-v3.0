import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-CAST-CHROMECAST-ORCHESTRATOR-2026-09-29.json"
FLAGS = ("authority","automatic_selection","automatic_fetch","automatic_install","automatic_activation","automatic_dependency","automatic_code_import","automatic_provider_admission","automatic_model_selection")

class DonorCastChromecastOrchestratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REG.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.by_id = {e["donor_id"]: e for e in cls.reg["entries"]}

    def test_source_counts_and_uniqueness(self):
        d, reg = self.delta, self.reg
        self.assertEqual((d["source_count"], d["unique_source_key_count"], d["new_candidate_count"]), (9,8,8))
        self.assertEqual(reg["capability_count"],175)
        self.assertEqual(reg["backfill"]["entry_count"],len(reg["entries"]))
        self.assertEqual(len(self.by_id),len(reg["entries"]))
        self.assertEqual(len({e["source"]["normalized_key"] for e in reg["entries"]}),len(reg["entries"]))

    def test_new_candidates_fail_closed_and_original_urls_preserved(self):
        for row in self.delta["sources"]:
            e = self.by_id[row["donor_id"]]
            self.assertEqual(e["source"]["normalized_key"],row["normalized_source_key"])
            self.assertEqual(e["status"],"CANDIDATE")
            self.assertTrue(all(e.get(flag) is False for flag in FLAGS))
            for url in row["urls"]:
                self.assertIn("User-supplied discovery URL: "+url,e["notes"])
        topics = [x for x in self.delta["sources"] if x["normalized_source_key"]=="github:topics/orchestrator"]
        self.assertEqual(len(topics),1)
        self.assertEqual(len(topics[0]["urls"]),2)

if __name__=="__main__": unittest.main()
