import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-ODBC-SQL-VECTOR-MEDIA-2026-09-29.json"
FLAGS = ("authority", "automatic_selection", "automatic_fetch", "automatic_install", "automatic_activation", "automatic_dependency", "automatic_code_import", "automatic_provider_admission", "automatic_model_selection")

class DonorOdbcSqlVectorMediaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.ids = {row["donor_id"]: row for row in cls.reg["entries"]}

    def test_source_intake_counts_and_identity(self):
        self.assertEqual(self.delta["source_count"], 56)
        self.assertEqual(self.delta["unique_source_key_count"], 50)
        self.assertEqual(len(self.delta["new_ids"]), 48)
        self.assertEqual(len(self.delta["updated_existing"]), 2)
        self.assertEqual(self.reg["backfill"]["entry_count"], len(self.reg["entries"]))
        self.assertEqual(self.reg["capability_count"], 175)
        self.assertEqual(len(self.ids), len(self.reg["entries"]))
        keys = [row["source"]["normalized_key"] for row in self.reg["entries"]]
        self.assertEqual(len(set(keys)), len(keys))

    def test_intake_entries_fail_closed_and_urls_retained(self):
        for row in self.delta["new_ids"]:
            entry = self.ids[row["id"]]
            self.assertEqual(entry["source"]["normalized_key"], row["key"])
            self.assertEqual(entry["status"], "CANDIDATE")
            self.assertTrue(all(entry.get(flag) is False for flag in FLAGS))
        for source in self.delta["sources"]:
            key = source["normalized_source_key"]
            entry = next((r for r in self.reg["entries"] if r["source"]["normalized_key"] == key), None)
            if entry is None:
                candidate_ids = [r["id"] for r in self.delta["updated_existing"] if r["key"] == key]
                self.assertEqual(len(candidate_ids), 1)
                entry = self.ids[candidate_ids[0]]
            notes = entry.get("notes", [])
            for url in source["urls"]:
                self.assertIn("User-supplied discovery URL: " + url, notes)

if __name__ == "__main__":
    unittest.main()
