"""Owner-marked AI Voice Cloning Gist donor intake and reference-plan regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-AI-VOICE-CLONING-GIST-2026-10-03.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-VOICE-TRANSFORMATION-REFERENCE-PLAN-2026-10-03.json"
PROFILE = ROOT / "canonical/profiles/FA3-VOICE-001.json"
ENGINE = ROOT / "canonical/FA3-ENGINE-REGISTRY-001.json"

KEY = "gist:0xdevalias/bb618bba1f0c9038e4bf740de884ac99"
URL = "https://gist.github.com/0xdevalias/bb618bba1f0c9038e4bf740de884ac99"
DONOR_ID = "FA3-DONOR-0XDEVALIAS-AI-VOICE-CLONING-GIST-001"
FLAGS = ("authority","automatic_selection","automatic_fetch","automatic_install","automatic_activation","automatic_dependency","automatic_code_import","automatic_provider_admission","automatic_model_selection")

class VoiceCloningGistDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta=json.loads(DELTA.read_text(encoding="utf-8"))
        cls.decision=json.loads(DECISION.read_text(encoding="utf-8"))
        cls.profile=json.loads(PROFILE.read_text(encoding="utf-8"))
        cls.engine=json.loads(ENGINE.read_text(encoding="utf-8"))
        cls.entries=cls.registry["entries"]
        cls.by_key={e["source"]["normalized_key"]:e for e in cls.entries}

    def test_registry_integrity_and_fixed_baseline(self):
        self.assertEqual(len(self.entries),len(self.by_key))
        self.assertEqual(self.registry["backfill"]["entry_count"],len(self.entries))
        self.assertEqual(len(self.entries),1423)
        self.assertEqual(self.registry["capability_count"],175)
        self.assertEqual(self.delta["parent_entry_count"],1422)
        self.assertEqual(self.delta["proposed_entry_count"],1423)
        self.assertEqual(self.delta["capability_delta"],0)
        self.assertEqual(self.delta["authority_delta"],0)

    def test_exact_owner_marked_gist_is_discovery_reference_only(self):
        row=self.by_key[KEY]
        self.assertEqual(row["donor_id"],DONOR_ID)
        self.assertEqual(row["source"]["locator"],URL)
        self.assertEqual(row["source"]["kind"],"GIST")
        self.assertEqual(row["status"],"ACCEPTED_REFERENCE")
        self.assertEqual(row["submission_review"]["scope"],"REFERENCE_REGISTRATION_ONLY")
        self.assertIn("DISCOVERY_INDEX",row["donor_modes"])
        self.assertTrue(all(row[flag] is False for flag in FLAGS))
        self.assertTrue(row["code_reuse_policy"].startswith("SOURCE_COPY_BLOCKED"))

    def test_child_sources_are_not_recursively_admitted(self):
        self.assertEqual(self.delta["source_count"],1)
        self.assertFalse(self.delta["boundaries"]["child_repository_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["child_service_auto_registration"])
        self.assertFalse(self.delta["boundaries"]["automatic_provider_admission"])
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])

    def test_existing_voice_authority_is_preserved(self):
        self.assertEqual(self.profile["id"],"FA3-VOICE-001")
        self.assertEqual(self.profile["capability_count"],175)
        self.assertFalse(self.profile["architectural_authority"])
        self.assertIn("VOICE",self.engine["engine_classes"])
        self.assertEqual(self.engine["capability_count"],175)
        self.assertEqual(self.decision["profile_id"],"FA3-VOICE-001")
        self.assertEqual(self.decision["new_capabilities"],0)
        self.assertEqual(self.decision["new_architectural_authorities"],0)
        self.assertEqual(self.decision["capability_count_after"],175)

    def test_reference_plan_does_not_claim_runtime_or_current_host(self):
        self.assertFalse(self.decision["runtime_materialization"])
        self.assertFalse(self.decision["provider_admission"])
        self.assertFalse(self.decision["model_admission"])
        self.assertFalse(self.decision["usage_edge_created"])
        self.assertEqual(self.decision["current_host_impact"],"NO_RUNTIME_IMPACT")
        self.assertFalse(self.delta["boundaries"]["runtime_change"])
        self.assertFalse(self.delta["boundaries"]["current_host_pass_claimed"])

if __name__ == "__main__":
    unittest.main()
