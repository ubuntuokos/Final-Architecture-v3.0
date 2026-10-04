"""Owner-marked auto-rigging topic and UEBridgeMCP donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-AUTO-RIGGING-UEBRIDGEMCP-2026-10-04.json"

TOPIC_KEY = "github:topics/auto-rigging"
TOPIC_URL = "https://github.com/topics/auto-rigging"
TOPIC_ID = "FA3-DONOR-AUTO-RIGGING-TOPIC-001"

UE_KEY = "github:uuuuzz/uebridgemcp"
UE_URL = "https://github.com/uuuuzz/UEBridgeMCP"
UE_ID = "FA3-DONOR-UEBRIDGEMCP-001"

FLAGS = (
    "authority", "automatic_selection", "automatic_fetch", "automatic_install",
    "automatic_activation", "automatic_dependency", "automatic_code_import",
    "automatic_provider_admission", "automatic_model_selection",
)

class AutoRiggingUEBridgeMcpDonorTests(unittest.TestCase):
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
        self.assertEqual(self.delta["parent_entry_count"], 1427)
        self.assertEqual(self.delta["proposed_entry_count"], 1429)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_auto_rigging_topic_is_discovery_only(self):
        row = self.by_key[TOPIC_KEY]
        self.assertEqual(row["donor_id"], TOPIC_ID)
        self.assertEqual(row["source"]["locator"], TOPIC_URL)
        self.assertEqual(row["source"]["kind"], "GITHUB_TOPIC")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["license"]["status"], "COLLECTION_INDEX")
        self.assertIn("DISCOVERY_INDEX", row["donor_modes"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))
        self.assertFalse(self.delta["boundaries"]["topic_child_repository_auto_registration"])

    def test_uebridgemcp_is_reference_only_and_rights_gated(self):
        row = self.by_key[UE_KEY]
        self.assertEqual(row["donor_id"], UE_ID)
        self.assertEqual(row["source"]["locator"], UE_URL)
        self.assertEqual(row["source"]["kind"], "GITHUB")
        self.assertEqual(row["status"], "ACCEPTED_REFERENCE")
        self.assertEqual(row["license"]["declared"], "GPL-3.0")
        self.assertIn("UNREAL_EDITOR_INTEGRATION_REFERENCE", row["donor_modes"])
        self.assertIn("UNREAL_COMPATIBILITY_REVIEW", row["code_reuse_policy"])
        self.assertEqual(
            row["upstream_observation"]["observed_head"],
            "51c7a0c2288fc00a36aa6b11b73e2789a58ea68e",
        )
        self.assertTrue(all(row[flag] is False for flag in FLAGS))
        self.assertFalse(self.delta["boundaries"]["uebridgemcp_runtime_admission"])
        self.assertFalse(self.delta["boundaries"]["uebridgemcp_source_copy"])

    def test_intake_has_no_runtime_capability_or_usage_effect(self):
        self.assertEqual(self.delta["source_count"], 2)
        self.assertEqual(self.delta["new_source_count"], 2)
        self.assertEqual(self.delta["matched_existing_count"], 0)
        self.assertFalse(self.delta["boundaries"]["runtime_change"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])
        self.assertFalse(self.delta["boundaries"]["authority_change"])
        self.assertFalse(self.delta["boundaries"]["capability_count_change"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

if __name__ == "__main__":
    unittest.main()
