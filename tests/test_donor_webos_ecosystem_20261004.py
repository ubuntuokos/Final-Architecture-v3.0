"""FIFO-waiting webOS / web-based OS donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-WEBOS-ECOSYSTEM-2026-10-04.json"

SUBMITTED_URLS = [
    "https://github.com/webosose",
    "https://github.com/topics/webos",
    "https://github.com/topics/web-based-os",
    "https://github.com/topics/webos-application?o=asc&s=updated",
]

LOCAL_IDS = {
    "FA3-DONOR-WEBOSOSE-ORG-001",
    "FA3-DONOR-GITHUB-TOPIC-WEBOS-001",
    "FA3-DONOR-GITHUB-TOPIC-WEB-BASED-OS-001",
    "FA3-DONOR-GITHUB-TOPIC-WEBOS-APPLICATION-001",
}

class WaitingWebOSDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_waiting_delta_is_bound_to_exact_parent(self):
        d = self.delta
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(d["parent_main"], "9e795a2a6bf3417b60bc52179edcd31d8e53d8a9")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_all_owner_marked_urls_are_preserved(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 4)
        self.assertEqual(d["submitted_urls"], SUBMITTED_URLS)
        self.assertEqual(d["duplicate_submission_count"], 0)
        self.assertEqual(d["matched_existing_count"], 0)
        self.assertEqual(d["matched_pending_intake_count"], 0)
        self.assertEqual(d["unique_source_count"], 4)
        self.assertEqual(d["new_source_count"], 4)
        self.assertEqual(d["proposed_entry_count"], 1431)

    def test_topic_query_is_provenance_only(self):
        source_map = dict(self.delta["sources"])
        self.assertEqual(
            source_map["https://github.com/topics/webos-application?o=asc&s=updated"],
            "FA3-DONOR-GITHUB-TOPIC-WEBOS-APPLICATION-001",
        )
        identities = {row["donor_id"]: row for row in self.delta["canonical_identities"]}
        self.assertEqual(
            identities["FA3-DONOR-GITHUB-TOPIC-WEBOS-APPLICATION-001"]["normalized_key"],
            "github:topics/webos-application",
        )

    def test_all_records_are_discovery_indexes(self):
        identities = self.delta["canonical_identities"]
        self.assertEqual(len(identities), 4)
        self.assertEqual({row["status"] for row in identities}, {"ACCEPTED_REFERENCE"})
        self.assertEqual({row["mode"] for row in identities}, {"DISCOVERY_INDEX"})
        self.assertEqual(
            {row["kind"] for row in identities},
            {"GITHUB_ORGANIZATION", "GITHUB_TOPIC"},
        )

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
