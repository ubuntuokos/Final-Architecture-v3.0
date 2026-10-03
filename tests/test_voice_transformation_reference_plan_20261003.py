"""Voice transformation donor-reference materialization regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "canonical/profiles/FA3-VOICE-001.json"
CONTRACTS = ROOT / "canonical/contracts/FA3-VOICE-CONTRACTS-001.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-VOICE-TRANSFORMATION-REFERENCE-PLAN-2026-10-03.json"
ASSESSMENT = ROOT / "canonical/assessments/FA3-VOICE-TRANSFORMATION-GIST-REUSE-ASSESSMENT-2026-10-03.json"
PANEL = ROOT / "apps/shared/voice/qml/VoiceTransformationPanel.qml"

DONOR = "FA3-DONOR-0XDEVALIAS-AI-VOICE-CLONING-GIST-001"
USAGE = "FA3-USAGE-AI-VOICE-CLONING-GIST-VOICE-TRANSFORMATION-001"
MODES = {
    "VOICE_CONVERSION",
    "REALTIME_VOICE_CONVERSION",
    "SINGING_VOICE_CONVERSION",
    "STYLE_TRANSFER",
    "SPEECH_REPRESENTATION",
}

class VoiceTransformationReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        cls.contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))

    def test_baseline_and_authority_invariants(self):
        self.assertEqual(self.profile["id"], "FA3-VOICE-001")
        self.assertEqual(self.profile["capability_count"], 175)
        self.assertFalse(self.profile["architectural_authority"])
        self.assertEqual(self.contracts["capability_count"], 175)
        self.assertEqual(self.contracts["new_capabilities"], 0)
        self.assertEqual(self.contracts["new_architectural_authorities"], 0)
        self.assertEqual(self.decision["capability_count_after"], 175)
        self.assertEqual(self.decision["new_capabilities"], 0)
        self.assertEqual(self.decision["new_architectural_authorities"], 0)

    def test_provider_neutral_transformation_contracts(self):
        self.assertTrue(MODES.issubset(set(self.profile["transformation_modes"])))
        req = self.contracts["contracts"]["transformation_request"]
        self.assertTrue(MODES.issubset(set(req["mode_enum"])))
        self.assertIn("realtime_session", self.contracts["contracts"])
        self.assertIn("speech_representation", self.contracts["contracts"])
        self.assertTrue(self.contracts["security"]["cuda_requires_hrb_lease"])

    def test_explicit_usage_edge_and_no_runtime_adoption(self):
        row = next(x for x in self.links["donor_usage_records"] if x["id"] == USAGE)
        self.assertEqual(row["donor_id"], DONOR)
        self.assertEqual(row["usage_kind"], "ARCHITECTURE_PATTERN")
        self.assertFalse(row["code_imported"])
        self.assertFalse(row["runtime_dependency"])
        self.assertFalse(row["provider_admission"])
        self.assertFalse(row["model_admission"])
        self.assertEqual(row["primary_consumer"]["id"], "FA3-VOICE-001")
        app_ids = {a["application_id"] for a in self.links["applications"]}
        for consumer in row["consumers"]:
            if consumer["kind"] == "APPLICATION":
                self.assertIn(consumer["id"], app_ids)

    def test_published_donor_snapshot_and_child_boundary(self):
        self.assertEqual(self.assessment["donor_id"], DONOR)
        self.assertEqual(self.assessment["donor_snapshot"]["registry_entry_count"], 1423)
        self.assertEqual(
            self.assessment["donor_snapshot"]["published_main_commit"],
            "fd8adf5ab2ef12882c47250ecb5d5f22ff8e796b",
        )
        self.assertFalse(self.decision["gui_projection"]["authority"])
        self.assertIn("provider or model admission", " ".join(self.assessment["excluded"]).lower())

    def test_shared_panel_is_non_executing_until_admission(self):
        qml = PANEL.read_text(encoding="utf-8")
        self.assertIn("FA3-VOICE-001", qml)
        self.assertIn("Reference-only donor engines are never selectable", qml)
        self.assertIn('Button { text: "Apply"; enabled: false }', qml)

if __name__ == "__main__":
    unittest.main()
