import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TestKritaAIImageEditingGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load("canonical/profiles/FA3-AI-IMAGE-EDITING-001.json")
        cls.contract = load("canonical/contracts/FA3-AI-IMAGE-EDITING-CONTRACTS-001.json")
        cls.hw = load("canonical/policies/FA3-AI-IMAGE-EDITING-HARDWARE-ADMISSION-001.json")
        cls.krita = load("canonical/providers/FA3-PROVIDER-KRITA-001.json")
        cls.ai = load("canonical/providers/FA3-PROVIDER-KRITA-AI-DIFFUSION-001.json")
        cls.vision = load("canonical/providers/FA3-PROVIDER-KRITA-VISION-TOOLS-001.json")
        cls.mcp = load("canonical/providers/FA3-PROVIDER-KRITA-MCP-001.json")
        cls.ref = load("canonical/references/FA3-KRITA-AI-IMAGE-EDITING-UPSTREAM-REFERENCE-2026-09-11.json")
        cls.decision = load("canonical/decisions/FA3-DEC-KRITA-AI-IMAGE-EDITING-2026-09-11.json")
        cls.enforcement = load("canonical/krita-ai-image-editing-enforcement.json")
        cls.gate = load("canonical/FA3-GATE-KRITA-AI-IMAGE-EDITING-001.json")

    def test_shared_profile_and_baseline_geometry(self):
        self.assertEqual(self.profile["relationship"], {"type": "SUBPROFILE-OF", "parent": "FA3-IMGGEN-001"})
        self.assertEqual(set(self.profile["scope"]["raster_frontends"]), {"GIMP 3.x", "Krita"})
        self.assertTrue(self.profile["scope"]["peer_frontend_model"])
        acc = self.profile["capability_accounting"]
        self.assertFalse(acc["adds_capability"])
        self.assertEqual(acc["capability_count_after"], 143)
        self.assertFalse(acc["adds_architectural_authority"])
        self.assertEqual(self.decision["new_capabilities"], 0)
        self.assertEqual(self.decision["new_architectural_authorities"], 0)

    def test_krita_authority_denials_and_base_provider(self):
        required = {"model_registry", "inference_runtime", "mcp_gateway", "hardware_resources", "workflow_orchestration", "secrets", "policy", "provenance"}
        self.assertTrue(required.issubset(set(self.profile["authority_constraints"]["krita_must_not_be_authority_for"])))
        self.assertFalse(self.krita["architectural_authority"])
        self.assertFalse(self.krita["new_architectural_authority"])
        self.assertEqual(self.krita["capability_count"], 143)
        self.assertIn("FA3-AI-IMAGE-EDITING-001", self.krita["additional_profiles"])

    def test_ai_diffusion_is_replaceable_non_authority(self):
        self.assertFalse(self.ai["architectural_authority"])
        self.assertFalse(self.ai["new_capability"])
        self.assertEqual(self.ai["capability_count"], 143)
        self.assertTrue(self.ai["backend_policy"]["provider_replacement_must_not_change_canonical_intent"])
        self.assertTrue(self.ai["backend_policy"]["model_artifacts_require_canonical_admission"])
        self.assertFalse(self.ai["backend_policy"]["automatic_custom_node_install_or_update"])
        self.assertIn("WORKFLOW_AUTHORITY", self.ai["forbidden_roles"])
        self.assertIn("MODEL_REGISTRY_AUTHORITY", self.ai["forbidden_roles"])

    def test_vision_models_are_admission_gated(self):
        policy = self.vision["model_asset_policy"]
        self.assertTrue(policy["canonical_model_admission_required"])
        self.assertTrue(policy["unadmitted_model_execution_forbidden_in_fa3_governed_mode"])
        self.assertTrue(policy["plugin_local_model_registry_is_non_authoritative"])

    def test_mcp_is_gateway_bounded_loopback_and_typed(self):
        policy = self.mcp["bridge_policy"]
        self.assertTrue(policy["fa3_governed_mode_requires_central_mcp_gateway"])
        self.assertTrue(policy["direct_global_mcp_authority_forbidden"])
        self.assertTrue(policy["authenticated_loopback_only"])
        self.assertTrue(policy["typed_operation_catalog_required"])
        self.assertTrue(policy["gui_mutation_main_thread_dispatch_required"])
        self.assertEqual(self.mcp["authority_boundaries"]["mcp_gateway"], "FA3-AUTH-MCP-GATEWAY-001")

    def test_hardware_is_dynamic_for_both_frontends(self):
        req = self.hw["requirements"]
        self.assertTrue(req["concrete_gpu_sku_must_not_be_architectural_dependency"])
        self.assertTrue(req["cuda_device_index_must_not_be_canonical_pin"])
        self.assertTrue(req["gpu_replacement_must_not_require_frontend_reconfiguration"])
        self.assertTrue(req["gpu_replacement_must_not_require_gimp_reconfiguration"])
        self.assertTrue(req["gpu_replacement_must_not_require_krita_reconfiguration"])
        self.assertFalse(self.hw["reference_baseline"]["binding"])

    def test_contract_is_frontend_and_provider_independent(self):
        execution = self.contract["execution_contract"]
        self.assertTrue(execution["provider_independent"])
        self.assertTrue(execution["backend_identity_must_not_be_required_by_frontend"])
        self.assertTrue(execution["backend_identity_must_not_be_required_by_gimp"])
        self.assertTrue(execution["backend_identity_must_not_be_required_by_krita"])
        self.assertTrue(execution["mcp_control_in_fa3_governed_mode_requires_existing_fa3_mcp_gateway"])
        self.assertEqual(set(self.contract["result_contract"]["nondestructive_default_targets"]), {"new_layer", "new_document"})

    def test_upstream_refs_are_pinned_and_licensed(self):
        self.assertEqual(len(self.ref["source_set"]), 4)
        for source in self.ref["source_set"]:
            self.assertRegex(source["revision"], r"^[0-9a-f]{40}$")
            self.assertRegex(source["observed_date"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["license"]["spdx"])
        self.assertEqual({source["repository"] for source in self.ref["source_set"]}, {"Acly/krita-ai-diffusion", "Acly/krita-vision-tools", "dcc-mcp/dcc-mcp-krita", "SanSaSane/krita-mcp"})

    def test_gate_is_closed_fail_closed_and_fully_linked(self):
        self.assertTrue(self.enforcement["fail_closed"])
        self.assertEqual(self.enforcement["baseline"]["capability_count_after"], 143)
        self.assertEqual(self.gate["status"], "CANONICAL_CLOSED")
        self.assertEqual(self.gate["priority"], "P0")
        self.assertTrue(self.gate["blocking"])
        self.assertEqual(self.gate["decision_id"], self.decision["id"])
        self.assertEqual(self.gate["enforcement_id"], self.enforcement["gate_id"])
        self.assertEqual(len(self.gate["checks"]), 15)
        self.assertEqual({check["id"] for check in self.gate["checks"]}, {f"KIE-{i:02d}" for i in range(1, 16)})
        self.assertTrue(all(check["failure"] == "BLOCK_PROMOTION" for check in self.gate["checks"]))

    def test_runtime_evidence_not_overclaimed(self):
        for provider in (self.ai, self.vision, self.mcp):
            self.assertEqual(provider["current_host_runtime_evidence"], "NOT_CLAIMED")
            self.assertFalse(provider["current_host_production_claim"])
        self.assertEqual(self.decision["current_host_runtime_evidence"], "NOT_CLAIMED")
        self.assertFalse(self.decision["current_host_runtime_promotion_claim"])
        self.assertFalse(self.ref["verification"]["runtime_execution_verified"])
        self.assertFalse(self.ref["verification"]["production_readiness_claim"])


if __name__ == "__main__":
    unittest.main()
