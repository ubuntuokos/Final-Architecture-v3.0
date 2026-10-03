"""Renoise interaction/theme owner-marked donor batch regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-RENOISE-INTERACTION-SOURCES-2026-10-03.json"

SOURCES = {
    "github:renoise-ai": ("FA3-DONOR-RENOISE-AI-ORG-001", "GITHUB_ORGANIZATION"),
    "github:nickcent/renoise-ai-assistant": ("FA3-DONOR-NICKCENT-RENOISE-AI-ASSISTANT-001", "GITHUB_REPOSITORY"),
    "github:renoise": ("FA3-DONOR-RENOISE-ORG-001", "GITHUB_ORGANIZATION"),
    "github:arcocodes": ("FA3-DONOR-ARCOCODES-ORG-001", "GITHUB_ORGANIZATION"),
    "github:catppuccin/renoise": ("FA3-DONOR-CATPPUCCIN-RENOISE-001", "GITHUB_REPOSITORY"),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class RenoiseInteractionDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"].lower(): e for e in cls.entries}

    def test_registry_integrity_and_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.entries), 1427)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1422)
        self.assertEqual(self.delta["source_count"], 5)
        self.assertEqual(self.delta["unique_source_key_count"], 5)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["proposed_entry_count"], 1427)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_owner_marked_sources_are_reference_only(self):
        for key, (donor_id, kind) in SOURCES.items():
            row = self.by_key[key]
            self.assertEqual(row["donor_id"], donor_id)
            self.assertEqual(row["source"]["kind"], kind)
            self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
            self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
            self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
            self.assertFalse(row["submission_review"]["second_registry_approval_required"])
            self.assertTrue(row["discoverable_for_planning"])
            self.assertTrue(all(row[flag] is False for flag in FLAGS))
            self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_org_records_do_not_auto_admit_children(self):
        for key in ("github:renoise-ai", "github:renoise", "github:arcocodes"):
            row = self.by_key[key]
            self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
            self.assertEqual(row["license"], {"declared": "NOT_APPLICABLE", "status": "COLLECTION_INDEX"})
        self.assertFalse(self.delta["boundaries"]["child_repository_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

    def test_repository_provenance_and_unsafe_execution_boundary(self):
        nick = self.by_key["github:nickcent/renoise-ai-assistant"]
        cat = self.by_key["github:catppuccin/renoise"]
        self.assertEqual(nick["license"]["declared"], "MIT")
        self.assertEqual(nick["source_snapshot"]["commit"], "cfce8d10434b9a69a88f767d99fe98d07cf1056c")
        self.assertEqual(cat["license"]["declared"], "MIT")
        self.assertEqual(cat["source_snapshot"]["commit"], "47d7b7ba9f282ae0b310b2b6186bed95466fecac")
        self.assertFalse(self.delta["boundaries"]["arbitrary_generated_code_execution"])
        self.assertFalse(self.delta["boundaries"]["generic_ai_auto_execute"])
        self.assertFalse(self.delta["boundaries"]["automatic_provider_admission"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])

if __name__ == "__main__":
    unittest.main()
