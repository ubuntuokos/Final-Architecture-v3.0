"""FIFO-waiting Cloudflare Clef-Flash donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-CLOUDFLARE-CLEF-FLASH-2026-10-04.json"

SOURCE = "https://huggingface.co/Cloudflare/clef-flash"
DONOR_ID = "FA3-DONOR-CLOUDFLARE-CLEF-FLASH-001"


class WaitingCloudflareClefFlashDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_waiting_delta_is_bound_to_exact_parent(self):
        d = self.delta
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(d["parent_main"], "07518f8a55c49fec5efa010ea285ff0a736e9524")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_single_source_identity(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 1)
        self.assertEqual(d["submitted_urls"], [SOURCE])
        self.assertEqual(d["unique_source_count"], 1)
        self.assertEqual(d["new_source_count"], 1)
        self.assertEqual(d["proposed_entry_count"], 1428)
        self.assertEqual(d["sources"], [[SOURCE, DONOR_ID]])
        identity = d["canonical_identities"][0]
        self.assertEqual(identity["donor_id"], DONOR_ID)
        self.assertEqual(identity["normalized_key"], "https://huggingface.co/cloudflare/clef-flash")
        self.assertEqual(identity["kind"], "HUGGINGFACE_MODEL")
        self.assertEqual(identity["status"], "ACCEPTED_REFERENCE")

    def test_waiting_record_is_not_prematurely_canonical(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertNotIn(DONOR_ID, current_ids)
        self.assertEqual(len(self.registry["entries"]), 1427)
        self.assertEqual(self.registry["backfill"]["entry_count"], 1427)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.delta["boundaries"]["canonical_planning_visibility"])

    def test_no_runtime_or_authority_admission(self):
        d = self.delta
        self.assertEqual(d["capability_baseline"], 175)
        self.assertEqual(d["capability_delta"], 0)
        self.assertEqual(d["authority_delta"], 0)
        self.assertEqual(d["usage_edges_created"], 0)
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
            "usage_edge_created",
            "capability_count_change",
            "authority_change",
            "runtime_change",
            "current_host_pass_claimed",
        ):
            self.assertFalse(d["boundaries"][key])

    def test_model_specific_safety_boundaries(self):
        obs = self.delta["upstream_observations"]
        self.assertEqual(obs["parameter_count"], "9B")
        self.assertEqual(obs["base_model"], "Qwen/Qwen3.5-9B")
        self.assertEqual(obs["declared_license"], "Apache-2.0")
        self.assertTrue(obs["jev_compatible"])
        self.assertTrue(obs["system_one_compatible"])
        self.assertFalse(obs["cpu_only_runtime_proven"])
        self.assertTrue(obs["custom_executable_model_code_present"])
        requirements = "\n".join(self.delta["requirements"])
        self.assertIn("FA3-DECISION-FABRIC-001", requirements)
        self.assertIn("FA3-SYSTEM-ONE-REFLEX-001", requirements)
        self.assertIn("fa3-decision-system-one", requirements)
        self.assertIn("CPU-only viability is mandatory", requirements)
        self.assertIn("Cloudflare Workers AI is not admitted", requirements)


if __name__ == "__main__":
    unittest.main()
