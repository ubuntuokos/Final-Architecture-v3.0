"""Metadata-only FA3 donor media intake assertions: never runtime acceptance."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "canonical/deltas/FA3-DONOR-MEDIA-INTAKE-2026-09-29.json"

class DonorMediaIntakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.sources = cls.data["sources"]

    def test_is_unique_pending_intake_not_parallel_registry(self):
        d = self.data
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(d["target_registry"], "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json")
        self.assertEqual(d["status"], "PENDING_DONOR_RECONCILIATION")
        self.assertEqual(d["merge_mode"], "SERIAL_LOSSLESS_UPSERT_BY_NORMALIZED_SOURCE_KEY")
        self.assertTrue(d["planning_and_finalization_blocked_until_donor_registry_integrity_verified"])
        self.assertEqual(d["source_count"], 58)
        self.assertEqual(len(self.sources), 58)
        keys = [x["normalized_source_key"] for x in self.sources]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len({x["url"] for x in self.sources}), len(keys))
        self.assertEqual(sum(x["repository_identity_checked"] for x in self.sources), 22)

    def test_no_admission_or_scope_expansion(self):
        d = self.data
        self.assertEqual(d["canonical_capability_baseline"], 175)
        self.assertEqual(d["capability_delta"], 0)
        self.assertEqual(d["authority_delta"], 0)
        for row in [d, *self.sources]:
            for flag in ("automatic_dependency", "automatic_fetch", "automatic_install",
                         "automatic_code_import", "automatic_model_selection",
                         "automatic_provider_admission", "automatic_activation"):
                self.assertIs(row[flag], False, (row.get("url"), flag))
        for row in self.sources:
            self.assertFalse(row["authority"])
            self.assertFalse(row["source_copy_allowed"])
            self.assertEqual(row["lifecycle_status"], "CANDIDATE")
            self.assertEqual(row["upstream_license"], "UNREVIEWED")

    def test_pinned_overlap_and_exact_filter_distinction(self):
        d = self.data
        match = [x for x in self.sources if x["normalized_source_key"] == "github:rikorose/deepfilternet"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["overlap_pending_pr"], 528)
        self.assertEqual({x["normalized_source_key"] for x in self.sources
                          if x["url"].startswith("https://github.com/topics/video-codec?")},
                         {"github:topics/video-codec?l=c", "github:topics/video-codec?l=python",
                          "github:topics/video-codec?l=c&o=desc&s=updated",
                          "github:topics/video-codec?l=python&o=desc&s=updated",
                          "github:topics/video-codec?l=rust&o=desc&s=forks"})
        self.assertTrue(d["pending_concurrent_donor_prs"])

if __name__ == "__main__":
    unittest.main()
