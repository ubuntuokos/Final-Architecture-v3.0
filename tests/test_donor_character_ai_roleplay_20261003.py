"""Owner-marked Character AI / Roleplay / Avatar donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-CHARACTER-AI-ROLEPLAY-2026-10-03.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

EXPECTED = {
    "github:character-ai": ("FA3-DONOR-CHARACTER-AI-ORG-001", "GITHUB_ORGANIZATION"),
    "github:topics/characterai": ("FA3-DONOR-CHARACTERAI-TOPIC-001", "GITHUB_TOPIC"),
    "github:topics/character-engine": ("FA3-DONOR-CHARACTER-ENGINE-TOPIC-001", "GITHUB_TOPIC"),
    "github:harmony-ai-solutions": ("FA3-DONOR-HARMONY-AI-SOLUTIONS-PROFILE-001", "GITHUB_PROFILE"),
    "github:topics/ai-roleplay": ("FA3-DONOR-AI-ROLEPLAY-TOPIC-001", "GITHUB_TOPIC"),
    "github:devanik21": ("FA3-DONOR-DEVANIK21-PROFILE-001", "GITHUB_PROFILE"),
    "github:kontextso": ("FA3-DONOR-KONTEXTSO-PROFILE-001", "GITHUB_PROFILE"),
    "github:topics/ai-character": ("FA3-DONOR-AI-CHARACTER-TOPIC-001", "GITHUB_TOPIC"),
    "github:topics/ai-avatar": ("FA3-DONOR-AI-AVATAR-TOPIC-001", "GITHUB_TOPIC"),
    "github:topics/roleplay-ai": ("FA3-DONOR-ROLEPLAY-AI-TOPIC-001", "GITHUB_TOPIC"),
    "github:samuraigpt": ("FA3-DONOR-SAMURAIGPT-PROFILE-001", "GITHUB_PROFILE"),
    "github:mixar-ai": ("FA3-DONOR-MIXAR-AI-PROFILE-001", "GITHUB_PROFILE"),
    "github:topics/character-platform": ("FA3-DONOR-CHARACTER-PLATFORM-TOPIC-001", "GITHUB_TOPIC"),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class CharacterAIRoleplayDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertGreaterEqual(len(self.entries), 1370)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1357)
        self.assertEqual(self.delta["submitted_url_count"], 15)
        self.assertEqual(self.delta["unique_source_key_count"], 13)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertEqual(self.delta["proposed_entry_count"], 1370)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_normalized_sources_are_reference_only(self):
        self.assertEqual(set(EXPECTED), {x["normalized_key"] for x in self.delta["sources"]})
        for key, (donor_id, kind) in EXPECTED.items():
            with self.subTest(key=key):
                row = self.by_key[key]
                self.assertEqual(row["donor_id"], donor_id)
                self.assertEqual(row["source"]["kind"], kind)
                self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
                self.assertEqual(row["submission_review"]["basis"], "OWNER_EXPLICIT_DONORNAK_MARKER")
                self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
                self.assertFalse(row["submission_review"]["second_registry_approval_required"])
                self.assertTrue(row["discoverable_for_planning"])
                self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_characterai_filtered_views_are_one_identity_and_preserved(self):
        row = self.by_key["github:topics/characterai"]
        expected_urls = {
            "https://github.com/topics/characterai?o=desc&s=updated",
            "https://github.com/topics/characterai?l=javascript&o=asc&s=forks",
            "https://github.com/topics/characterai?l=typescript&o=asc&s=stars",
        }
        self.assertEqual(set(row["source"]["discovery_urls"]), expected_urls)
        delta_rows = [x for x in self.delta["sources"] if x["normalized_key"] == "github:topics/characterai"]
        self.assertEqual(len(delta_rows), 3)

    def test_no_automatic_usage_or_runtime_admission(self):
        serialized = json.dumps(self.links, sort_keys=True)
        for donor_id, _kind in EXPECTED.values():
            self.assertNotIn(donor_id, serialized)
        self.assertTrue(all(v is False for v in self.delta["boundaries"].values()))

if __name__ == "__main__":
    unittest.main()
