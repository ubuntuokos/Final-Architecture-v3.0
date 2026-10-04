"""FIFO-waiting Meshy / Runware batch with API Evangelist cross-intake dedup."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-MESHY-RUNWARE-API-EVANGELIST-2026-10-04.json"

SUBMITTED_URLS = [
    "https://github.com/topics/meshy?o=asc&s=updated",
    "https://github.com/topics/meshy?l=python&o=asc&s=updated",
    "https://github.com/meshy-dev/Meshy-guide",
    "https://github.com/topics/meshy?l=python",
    "https://github.com/meshy-dev",
    "https://github.com/topics/meshy?l=html",
    "https://github.com/topics/ai-3d-model-generator",
    "https://github.com/runware",
    "https://github.com/topics/runware?l=shell",
    "https://github.com/api-evangelist"
]

LOCAL_IDS = {
    "FA3-DONOR-GITHUB-TOPIC-MESHY-001",
    "FA3-DONOR-MESHY-DEV-MESHY-GUIDE-001",
    "FA3-DONOR-MESHY-DEV-ORG-001",
    "FA3-DONOR-GITHUB-TOPIC-AI-3D-MODEL-GENERATOR-001",
    "FA3-DONOR-RUNWARE-ORG-001",
    "FA3-DONOR-GITHUB-TOPIC-RUNWARE-001",
}

class WaitingDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_waiting_delta_is_bound_to_exact_parent(self):
        d = self.delta
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(d["parent_main"], "df24cb9d1fa2413b08c8d47461bdb2db799585f6")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_all_owner_marked_urls_are_preserved(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 10)
        self.assertEqual(d["submitted_urls"], SUBMITTED_URLS)
        self.assertEqual(d["cross_intake_reuse_count"], 1)
        self.assertEqual(d["mutation_submitted_url_count"], 9)
        self.assertEqual(d["canonical_alias_collapse_count"], 3)
        self.assertEqual(d["unique_source_count"], 6)
        self.assertEqual(d["new_source_count"], 6)
        self.assertEqual(d["proposed_entry_count"], 1433)

    def test_api_evangelist_is_reused_from_earlier_pr(self):
        reuse = self.delta["cross_intake_reuse"]
        self.assertEqual(len(reuse), 1)
        self.assertEqual(reuse[0]["url"], "https://github.com/api-evangelist")
        self.assertEqual(reuse[0]["donor_id"], "FA3-DONOR-API-EVANGELIST-ORG-001")
        self.assertEqual(reuse[0]["existing_pr"], 675)
        self.assertIn("NO_DUPLICATE_MUTATION", reuse[0]["disposition"])
        self.assertNotIn("https://github.com/api-evangelist", [row[0] for row in self.delta["sources"]])

    def test_meshy_filtered_views_share_one_identity(self):
        meshy = [row for row in self.delta["sources"] if "/topics/meshy" in row[0]]
        self.assertEqual(len(meshy), 4)
        self.assertEqual({row[1] for row in meshy}, {"FA3-DONOR-GITHUB-TOPIC-MESHY-001"})

    def test_waiting_records_are_not_prematurely_canonical(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertTrue(LOCAL_IDS.isdisjoint(current_ids))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.registry["entries"]))
        self.assertEqual(len(self.registry["entries"]), 1427)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.delta["boundaries"]["canonical_planning_visibility"])

    def test_no_runtime_or_authority_admission(self):
        b = self.delta["boundaries"]
        for key in (
            "automatic_fetch", "automatic_install", "automatic_activation",
            "automatic_code_import", "automatic_dependency",
            "automatic_provider_admission", "automatic_model_selection",
            "child_repository_auto_registration", "usage_edge_created",
            "capability_count_change", "authority_change", "runtime_change",
            "current_host_pass_claimed",
        ):
            self.assertFalse(b[key])
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

if __name__ == "__main__":
    unittest.main()
