import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text())


class VideoRegistryTests(unittest.TestCase):
    def test_video_profile_is_canonical_without_new_capability_or_authority(self):
        profile = load("canonical/profiles/FA3-VIDEO-001.json")
        self.assertEqual(profile["status"], "CANONICAL")
        self.assertEqual(profile["priority"], "P0")
        self.assertEqual(profile["requirement"], "MUST")
        self.assertFalse(profile["new_capability"])
        self.assertFalse(profile["new_architectural_authority"])
        self.assertEqual(profile["capability_count"], 143)

    def test_contract_set_is_provider_neutral(self):
        contracts = load("canonical/contracts/FA3-VIDEO-CONTRACTS-001.json")
        self.assertTrue(contracts["provider_neutral"])
        self.assertIn("VideoGenerationIR", contracts["contracts"])
        self.assertIn("ContextAwareRegenerationRequest", contracts["contracts"])
        self.assertTrue(contracts["rules"]["provider_native_prompt_syntax_forbidden_upstream"])

    def test_all_video_providers_are_non_authoritative(self):
        for path in [
            "canonical/providers/FA3-PROVIDER-KLING-001.json",
            "canonical/providers/FA3-PROVIDER-SEEDANCE-001.json",
            "canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json",
        ]:
            provider = load(path)
            self.assertFalse(provider["canonical_root"])
            self.assertFalse(provider["architectural_authority"])
            self.assertFalse(provider["new_capability"])
            self.assertEqual(provider["capability_count"], 143)

    def test_kling_mcp_cannot_bypass_central_gateway(self):
        kling = load("canonical/providers/FA3-PROVIDER-KLING-001.json")
        self.assertEqual(
            kling["mcp_boundary"],
            "MUST_ROUTE_THROUGH_FA3_CENTRAL_MCP_GATEWAY",
        )

    def test_h3_context_ir_is_not_canonical_dependency(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        self.assertEqual(h3["context_ir_policy"]["provider_context_ir"], "REFERENCE_PATTERN_ONLY")
        self.assertFalse(h3["context_ir_policy"]["hosted_context_ir_required_for_fa3"])

    def test_h3_local_admission_is_fail_closed(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        self.assertEqual(h3["license_admission"]["mode"], "FAIL_CLOSED")
        self.assertEqual(h3["license_admission"]["local_deployment"], "CONDITIONAL")
        self.assertIn("deployment_authorization_evidence", h3["license_admission"]["requires"])

    def test_h3_diffusers_and_comfyui_are_targets_not_promoted(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        self.assertEqual(h3["integration_targets"]["diffusers"]["status"], "PRODUCTION_INTEGRATION_TARGET")
        self.assertEqual(h3["integration_targets"]["comfyui"]["status"], "PRODUCTION_INTEGRATION_TARGET")
        self.assertIn("NOT_YET_CURRENT_HOST_PROMOTED", h3["implementation_status"])

    def test_decision_preserves_baseline_semantics(self):
        decision = load("canonical/decisions/FA3-DEC-VIDEO-H3-2026-08-30.json")
        self.assertFalse(decision["canonical_semantics_changed"])
        self.assertEqual(decision["new_capabilities"], 0)
        self.assertEqual(decision["new_architectural_authorities"], 0)
        self.assertEqual(decision["capability_count_after"], 143)

    def test_enforcement_declares_h3_promotion_evidence(self):
        gate = load("canonical/video-enforcement.json")
        self.assertTrue(gate["fail_closed"])
        self.assertIn("video_execution_e2e_pass", gate["h3_promotion_requirements"])
        self.assertIn("qc_and_provenance_evidence_pass", gate["h3_promotion_requirements"])


if __name__ == "__main__":
    unittest.main()
