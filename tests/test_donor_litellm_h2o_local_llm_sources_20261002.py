"""Exact owner-marked LiteLLM/H2O/local-LLM source donor intake regression tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-LITELLM-H2O-LOCAL-LLM-SOURCES-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

EXPECTED = {
    "github:berriai": ("FA3-DONOR-BERRIAI-ORG-001", "https://github.com/BerriAI", "GITHUB_ORGANIZATION"),
    "github:topics/litellm": ("FA3-DONOR-LITELLM-TOPIC-001", "https://github.com/topics/litellm", "GITHUB_TOPIC"),
    "github:topics/litellm-ai-gateway?l=go": (
        "FA3-DONOR-LITELLM-AI-GATEWAY-GO-TOPIC-001",
        "https://github.com/topics/litellm-ai-gateway?l=go",
        "GITHUB_TOPIC",
    ),
    "github:h2oai": ("FA3-DONOR-H2OAI-ORG-001", "https://github.com/h2oai", "GITHUB_ORGANIZATION"),
    "github:litellm-labs": (
        "FA3-DONOR-LITELLM-LABS-ORG-001",
        "https://github.com/LiteLLM-Labs",
        "GITHUB_ORGANIZATION",
    ),
    "github:topics/local-llm": (
        "FA3-DONOR-LOCAL-LLM-TOPIC-001",
        "https://github.com/topics/local-llm",
        "GITHUB_TOPIC",
    ),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class LiteLLMH2OLocalLLMDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1339)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1333)
        self.assertEqual(self.delta["proposed_entry_count"], 1339)
        self.assertEqual(self.delta["source_count"], 6)
        self.assertEqual(self.delta["unique_source_key_count"], 6)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_sources_are_reference_only(self):
        self.assertEqual(
            set(EXPECTED),
            {x["normalized_key"] for x in self.delta["sources"]},
        )
        for key, (donor_id, url, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["locator"], url)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(
                    row["submission_review"]["basis"],
                    "OWNER_EXPLICIT_DONORNAK_MARKER",
                )
                self.assertEqual(
                    row["submission_review"]["scope"],
                    "REFERENCE_REGISTRATION_ONLY",
                )
                self.assertFalse(
                    row["submission_review"]["second_registry_approval_required"]
                )
                self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
                self.assertEqual(
                    row["license"],
                    {"declared": "NOT_APPLICABLE", "status": "COLLECTION_INDEX"},
                )
                self.assertTrue(row["discoverable_for_planning"])
                self.assertTrue(all(row[flag] is False for flag in FLAGS))
                self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_go_filtered_topic_view_is_preserved(self):
        row = self.by_key["github:topics/litellm-ai-gateway?l=go"]
        self.assertEqual(row["discovery_filter"]["language"], "go")
        self.assertEqual(
            row["discovery_filter"]["observed_url"],
            "https://github.com/topics/litellm-ai-gateway?l=go",
        )

    def test_batch_does_not_create_usage_edges(self):
        serialized = json.dumps(self.links, sort_keys=True)
        for donor_id, _url, _kind in EXPECTED.values():
            self.assertNotIn(donor_id, serialized)
        boundaries = self.delta["boundaries"]
        for field in (
            "child_repository_auto_registration",
            "automatic_fetch",
            "automatic_install",
            "automatic_activation",
            "automatic_code_import",
            "automatic_dependency",
            "automatic_provider_admission",
            "automatic_model_selection",
            "hosted_service_activation",
            "usage_edge_created",
            "capability_count_change",
            "authority_change",
        ):
            self.assertFalse(boundaries[field])

if __name__ == "__main__":
    unittest.main()
