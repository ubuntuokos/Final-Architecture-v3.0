"""Owner-designated AI starter, learning and mark3labs donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-AI-STARTER-LEARNING-MARK3LABS-2026-10-03.json"

EXPECTED = {
    "github:topics/ai-starter-kit": ("FA3-DONOR-AI-STARTER-KIT-TOPIC-001", "GITHUB_TOPIC"),
    "github:mark3labs": ("FA3-DONOR-MARK3LABS-ORG-001", "GITHUB_ORGANIZATION"),
    "github:topics/ai-starter": ("FA3-DONOR-AI-STARTER-TOPIC-001", "GITHUB_TOPIC"),
    "github:topics/ai-for-beginners": ("FA3-DONOR-AI-FOR-BEGINNERS-TOPIC-001", "GITHUB_TOPIC"),
    "github:sixarm/ai-starter-guide": ("FA3-DONOR-SIXARM-AI-STARTER-GUIDE-001", "GITHUB_REPOSITORY"),
    "github:jbsoftware-io/gen-ai-starter": ("FA3-DONOR-JBSOFTWARE-GEN-AI-STARTER-001", "GITHUB_REPOSITORY"),
}
FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class AIStarterLearningMark3LabsDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.by_key = {e["source"]["normalized_key"]: e for e in cls.entries}

    def test_registry_integrity_and_fixed_baseline(self):
        self.assertEqual(len(self.entries), len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.entries), 1429)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1423)
        self.assertEqual(self.delta["proposed_entry_count"], 1429)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_exact_six_sources_are_reference_only(self):
        self.assertEqual(self.delta["source_count"], 6)
        self.assertEqual(self.delta["unique_source_key_count"], 6)
        for key, (donor_id, kind) in EXPECTED.items():
            row = self.by_key[key]
            self.assertEqual(row["donor_id"], donor_id)
            self.assertEqual(row["source"]["kind"], kind)
            self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
            self.assertEqual(row["submission_review"]["scope"], "REFERENCE_REGISTRATION_ONLY")
            self.assertTrue(row["discoverable_for_planning"])
            self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_indexes_do_not_recursively_admit_children(self):
        for key in (
            "github:topics/ai-starter-kit",
            "github:mark3labs",
            "github:topics/ai-starter",
            "github:topics/ai-for-beginners",
        ):
            self.assertIn("DISCOVERY_INDEX", self.by_key[key]["donor_modes"])
            self.assertEqual(self.by_key[key]["license"]["status"], "COLLECTION_INDEX")
        self.assertFalse(self.delta["boundaries"]["child_repository_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["child_service_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

    def test_repository_rights_boundaries_are_preserved(self):
        sixarm = self.by_key["github:sixarm/ai-starter-guide"]
        jb = self.by_key["github:jbsoftware-io/gen-ai-starter"]
        self.assertEqual(sixarm["license"]["declared"], "UNKNOWN")
        self.assertEqual(
            sixarm["source_snapshot"]["default_branch_commit"],
            "559354c0ac3e04188b5b7317cd77b372af7fceb3",
        )
        self.assertEqual(jb["license"]["declared"], "MIT")
        self.assertEqual(
            jb["source_snapshot"]["default_branch_commit"],
            "a274dee5f55670e1c63e2d8777baf9714ca287ce",
        )
        self.assertTrue(sixarm["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))
        self.assertTrue(jb["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_no_runtime_authority_or_current_host_claim(self):
        for key in (
            "automatic_fetch", "automatic_install", "automatic_activation",
            "automatic_code_import", "automatic_content_import", "automatic_dependency",
            "automatic_provider_admission", "automatic_model_selection",
            "usage_edge_created", "capability_count_change", "authority_change",
            "runtime_change", "current_host_pass_claimed",
        ):
            self.assertFalse(self.delta["boundaries"][key])

if __name__ == "__main__":
    unittest.main()
