"""FIFO-waiting LocalAI ecosystem donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-LOCALAI-ECOSYSTEM-2026-10-04.json"

SUBMITTED_URLS = [
    "https://github.com/mudler/localai",
    "https://github.com/topics/local-ai",
    "https://github.com/topics/local-ai?l=c%2B%2B&o=asc&s=forks",
    "https://github.com/localai-org",
    "https://github.com/topics/local-ai?l=go&o=asc&s=updated",
    "https://github.com/topics/local-ai-agents?l=javascript",
    "https://github.com/topics/local-ai-models",
    "https://github.com/topics/localai",
    "https://github.com/topics/my-local-ai",
    "https://github.com/topics/self-hosted-ai",
]

LOCAL_IDS = {
    "FA3-DONOR-MUDLER-LOCALAI-001",
    "FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-001",
    "FA3-DONOR-LOCALAI-ORG-001",
    "FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-AGENTS-001",
    "FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-MODELS-001",
    "FA3-DONOR-GITHUB-TOPIC-LOCALAI-001",
    "FA3-DONOR-GITHUB-TOPIC-MY-LOCAL-AI-001",
    "FA3-DONOR-GITHUB-TOPIC-SELF-HOSTED-AI-001",
}


class WaitingLocalAIDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_waiting_delta_is_bound_to_exact_parent(self):
        d = self.delta
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(d["parent_main"], "9b328ff1582ba92d67562b10336b1ccaf8a8da84")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_submission_counts_and_alias_collapse(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 10)
        self.assertEqual(d["submitted_urls"], SUBMITTED_URLS)
        self.assertEqual(d["duplicate_submission_count"], 0)
        self.assertEqual(d["unique_submitted_url_count"], 10)
        self.assertEqual(d["matched_existing_count"], 0)
        self.assertEqual(d["published_registry_reuse_count"], 0)
        self.assertEqual(d["mutation_submitted_url_count"], 10)
        self.assertEqual(d["canonical_alias_collapse_count"], 2)
        self.assertEqual(d["unique_source_count"], 8)
        self.assertEqual(d["new_source_count"], 8)
        self.assertEqual(d["proposed_entry_count"], 1435)

    def test_filtered_local_ai_topic_views_share_one_identity(self):
        rows = [row for row in self.delta["sources"] if "/topics/local-ai" in row[0] and "/topics/local-ai-" not in row[0]]
        self.assertEqual(len(rows), 3)
        self.assertEqual({row[1] for row in rows}, {"FA3-DONOR-GITHUB-TOPIC-LOCAL-AI-001"})

    def test_waiting_records_are_not_prematurely_canonical(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertTrue(LOCAL_IDS.isdisjoint(current_ids))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.registry["entries"]))
        self.assertEqual(len(self.registry["entries"]), 1427)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.delta["boundaries"]["canonical_planning_visibility"])

    def test_no_runtime_provider_model_or_device_admission(self):
        b = self.delta["boundaries"]
        for key in (
            "automatic_fetch",
            "automatic_install",
            "automatic_activation",
            "automatic_code_import",
            "automatic_content_import",
            "automatic_dependency",
            "automatic_provider_admission",
            "automatic_model_selection",
            "automatic_device_selection",
            "child_repository_auto_registration",
            "usage_edge_created",
            "capability_count_change",
            "authority_change",
            "runtime_change",
            "current_host_pass_claimed",
        ):
            self.assertFalse(b[key])
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

    def test_localai_upstream_snapshot_is_reference_only(self):
        obs = self.delta["upstream_observations"]
        self.assertEqual(obs["mudler_localai_observed_head"], "ed4a3975be786682631d700f104255cc8b9000df")
        self.assertEqual(obs["mudler_localai_latest_release"], "v4.11.0")
        self.assertEqual(obs["mudler_localai_top_level_license"], "MIT")


if __name__ == "__main__":
    unittest.main()
