"""Shared Voice Studio / Quick Video GUI materialization regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "canonical/profiles/FA3-VOICE-001.json"
CONTRACTS = ROOT / "canonical/contracts/FA3-VOICE-CONTRACTS-001.json"
APPS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
SHARED = ROOT / "canonical/FA3-SHARED-MODULE-PATTERN-CATALOGUE-001.json"
PRODUCT_FAMILY = ROOT / "canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json"
DECISION = ROOT / "canonical/decisions/FA3-DEC-SHARED-VOICE-STUDIO-QUICKVIDEO-2026-10-03.json"
INTENT = ROOT / "canonical/intents/FA3-SHARED-VOICE-STUDIO-QUICKVIDEO-APPLICATION-INTENT-2026-10-03.json"
VOICE_STUDIO = ROOT / "apps/fa3-control-center/qml/VoiceStudioPage.qml"
PLUGIN = ROOT / "apps/shared/voice/qml/VoicePluginPanel.qml"
PROFILES = ROOT / "apps/shared/voice/qml/VoiceProfileManagerPanel.qml"
OVERLAY = ROOT / "apps/shared/voice/qml/VoiceActivityOverlay.qml"
MAIN = ROOT / "apps/fa3-control-center/qml/Main.qml"
CMAKE = ROOT / "apps/fa3-control-center/CMakeLists.txt"

class SharedVoiceStudioQuickVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        cls.contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
        cls.apps = json.loads(APPS.read_text(encoding="utf-8"))
        cls.shared = json.loads(SHARED.read_text(encoding="utf-8"))
        cls.product_family = json.loads(PRODUCT_FAMILY.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        cls.intent = json.loads(INTENT.read_text(encoding="utf-8"))

    def test_baseline_and_authority(self):
        self.assertEqual(self.profile["capability_count"], 175)
        self.assertEqual(self.contracts["capability_count"], 175)
        self.assertEqual(self.decision["capability_count_after"], 175)
        self.assertEqual(self.decision["new_capabilities"], 0)
        self.assertEqual(self.decision["new_architectural_authorities"], 0)
        self.assertFalse(self.decision["surfaces"]["voice_studio"]["authority"])
        self.assertFalse(self.decision["surfaces"]["shared_voice_plugin"]["direct_provider_execution"])

    def test_voice_studio_application_and_shared_component(self):
        app = next(x for x in self.apps["applications"] if x["application_id"] == "fa3.voice-studio")
        self.assertEqual(app["kind"], "INTERNAL_APPLICATION")
        self.assertIn(app["lifecycle"], {"PLANNED", "MATERIALIZED"})
        placement = next(x for x in self.product_family["application_placements"] if x["application_id"] == "fa3.voice-studio")
        self.assertEqual(placement["primary_family"], "FA3-FAMILY-CREATIVE-MEDIA-001")
        self.assertIn("FA3-FAMILY-STUDIO-FILM-001", placement["secondary_families"])
        target = next(x for x in self.shared["shared_module_targets"] if x["id"] == "FA3-SHARED-VOICE-PLUGIN-PATTERN-001")
        self.assertIn("fa3.quickclip", target["consumer_application_ids"])
        self.assertEqual(target["materialization_profile_id"], "FA3-VOICE-001")
        self.assertEqual(target["materialization_contract_id"], "FA3-VOICE-CONTRACTS-001")
        self.assertEqual(target["materialization_status"], "GUI_HOST_CONTRACT_MATERIALIZED_RUNTIME_ADAPTER_GATED")
        self.assertFalse(any(x["id"] == "FA3-SHARED-VOICE-PLUGIN-001" for x in self.shared["materialized_shared_components"]))

    def test_plugin_contract_and_hardware_boundary(self):
        c = self.contracts["contracts"]["shared_voice_plugin_host"]
        self.assertEqual(set(c["projection_modes"]), {"QUICK", "STANDARD", "ADVANCED"})
        self.assertFalse(c["direct_provider_execution"])
        self.assertFalse(c["direct_device_selection"])
        self.assertTrue(c["model_router_required"])
        self.assertTrue(c["hrb_required_for_accelerator"])
        self.assertTrue(self.profile["shared_voice_surfaces"]["cpu_only_path_required"])

    def test_gui_surfaces(self):
        studio = VOICE_STUDIO.read_text(encoding="utf-8")
        for token in ["FA3 Voice Studio", "Generate", "Voices", "Capture", "Transform", "Stories", "Dubbing", "Effects", "Models", "Providers", "Jobs", "Settings"]:
            self.assertIn(token, studio)
        plugin = PLUGIN.read_text(encoding="utf-8")
        for token in ["Quick Dub", "Fit to Clip", "Generate & Insert", "Generate editable captions", "Duck background music", "Build Editable Dub"]:
            self.assertIn(token, plugin)
        profiles = PROFILES.read_text(encoding="utf-8")
        self.assertIn("Voice Profile Manager", profiles)
        self.assertIn("consent", profiles.lower())
        overlay = OVERLAY.read_text(encoding="utf-8")
        self.assertIn("activityState", overlay)
        self.assertIn("privacyState", overlay)

    def test_control_center_wiring(self):
        main = MAIN.read_text(encoding="utf-8")
        cmake = CMAKE.read_text(encoding="utf-8")
        for token in ['"create.voice-studio": 42', 'routeId: "create.voice-studio"', "VoiceStudioPage", "VoiceActivityOverlay"]:
            self.assertIn(token, main)
        for token in ["VoiceStudioPage.qml", "VoicePluginPanel.qml", "VoiceProfileManagerPanel.qml", "VoiceActivityOverlay.qml"]:
            self.assertIn(token, cmake)

    def test_voicebox_pending_donor_is_not_fabricated_usage(self):
        b = self.decision["donor_boundary"]
        self.assertEqual(b["status"], "OWNER_MARKED_PENDING_CANONICAL_INTAKE_NOT_REQUIRED_FOR_NATIVE_MATERIALIZATION")
        self.assertFalse(b["usage_edge_created"])
        self.assertFalse(b["code_imported"])
        self.assertFalse(b["runtime_dependency"])
        usage = self.apps.get("donor_usage_records", [])
        self.assertFalse(any("VOICEBOX" in x.get("id", "").upper() for x in usage))

    def test_no_direct_provider_or_device_literals_in_plugin(self):
        plugin = PLUGIN.read_text(encoding="utf-8").lower()
        for forbidden in ["cuda:0", "http://localhost", "127.0.0.1:", "directml:0", "rocm:0"]:
            self.assertNotIn(forbidden, plugin)

if __name__ == "__main__":
    unittest.main()
