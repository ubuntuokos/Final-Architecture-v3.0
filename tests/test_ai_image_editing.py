import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class AIImageEditingCanonicalGate(unittest.TestCase):
    def setUp(self):
        self.profile = load("canonical/profiles/FA3-AI-IMAGE-EDITING-001.json")
        self.contracts = load("canonical/contracts/FA3-AI-IMAGE-EDITING-CONTRACTS-001.json")
        self.hw = load("canonical/policies/FA3-AI-IMAGE-EDITING-HARDWARE-ADMISSION-001.json")
        self.providers = load("canonical/providers/FA3-PROVIDER-GIMP-AI-LOCAL-001.json")
        self.decision = load("canonical/decisions/FA3-DEC-GIMP-LOCAL-AI-2026-09-08.json")

    def test_projection_does_not_create_capability_or_authority(self):
        self.assertEqual(self.profile["relationship"], {"type": "SUBPROFILE-OF", "parent": "FA3-IMGGEN-001"})
        acc = self.profile["capability_accounting"]
        self.assertFalse(acc["adds_capability"])
        self.assertEqual(acc["capability_count_before"], 143)
        self.assertEqual(acc["capability_count_after"], 143)
        self.assertFalse(acc["adds_architectural_authority"])
        self.assertEqual(self.decision["invariants"]["capability_count"], 143)
        self.assertEqual(self.decision["invariants"]["new_architectural_authorities"], 0)

    def test_modes_and_intents(self):
        self.assertEqual(set(self.profile["scope"]["operation_modes"]), {"standalone", "fa3_governed"})
        required = {"generate", "image_edit", "inpaint", "outpaint", "generative_fill", "background_remove", "upscale", "control_guidance", "reference_image", "segmentation", "relight"}
        self.assertTrue(required.issubset(set(self.contracts["request_contract"]["allowed_intents"])))

    def test_gimp_never_becomes_architectural_authority(self):
        denied = set(self.profile["authority_constraints"]["gimp_must_not_be_authority_for"])
        required = {"model_registry", "inference_runtime", "mcp_gateway", "hardware_resources", "workflow_orchestration", "secrets", "policy", "provenance"}
        self.assertTrue(required.issubset(denied))
        self.assertTrue(self.providers["constraints"]["gimp_is_frontend_not_authority"])

    def test_hardware_is_discovered_not_sku_pinned(self):
        req = self.hw["requirements"]
        self.assertTrue(req["concrete_gpu_sku_must_not_be_architectural_dependency"])
        self.assertTrue(req["cuda_device_index_must_not_be_canonical_pin"])
        self.assertTrue(req["fixed_vram_amount_must_not_be_global_profile_pin"])
        self.assertEqual(req["gpu_replacement_lifecycle"], ["rediscover", "revalidate_runtime", "readmit_model", "reroute_workload"])
        self.assertTrue(req["gpu_replacement_must_not_require_gimp_reconfiguration"])
        self.assertFalse(self.hw["reference_baseline"]["binding"])
        self.assertIn("free_vram", self.hw["discovery_dimensions"])
        self.assertIn("current_load", self.hw["discovery_dimensions"])

    def test_provider_interchange_and_standalone_mode(self):
        self.assertEqual(set(self.providers["backend_interchange"]), {"COMFYUI", "FORGE", "STABLE_DIFFUSION_CPP"})
        self.assertTrue(self.providers["constraints"]["all_backends_replaceable"])
        self.assertTrue(self.providers["constraints"]["standalone_mode_must_not_require_fa3"])
        self.assertTrue(self.contracts["execution_contract"]["provider_independent"])
        self.assertTrue(self.contracts["execution_contract"]["backend_identity_must_not_be_required_by_gimp"])


if __name__ == "__main__":
    unittest.main()
