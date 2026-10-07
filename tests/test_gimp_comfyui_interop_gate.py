import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TestGimpComfyUIInteropGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load("canonical/contracts/FA3-CREATIVE-DESKTOP-GENERATIVE-INTEROP-CONTRACTS-001.json")
        cls.provider = load("canonical/providers/FA3-PROVIDER-GIMP-COMFYUI-INTEROP-001.json")
        cls.decision = load("canonical/decisions/FA3-DEC-GIMP-COMFYUI-INTEROP-2026-09-09.json")
        cls.enforcement = load("canonical/gimp-comfyui-interop-enforcement.json")
        cls.gate = load("canonical/FA3-GATE-GIMP-COMFYUI-INTEROP-001.json")
        cls.reference = load("canonical/references/FA3-GIMP-COMFYUI-UPSTREAM-REFERENCE-2026-09-09.json")
        cls.mmg = load("canonical/contracts/FA3-MMG-CONTEXT-IR-CONTRACTS-001.json")
        cls.imggen = load("canonical/contracts/FA3-IMGGEN-CONTRACTS-001.json")
        cls.lifecycle = load("canonical/contracts/FA3-LOCAL-GENERATIVE-MEDIA-LIFECYCLE-CONTRACTS-001.json")

    def test_baseline_geometry_is_unchanged(self):
        self.assertFalse(self.contract["canonical_root"])
        self.assertFalse(self.contract["new_capability"])
        self.assertFalse(self.contract["new_architectural_authority"])
        self.assertEqual(self.contract["capability_count"], 143)
        self.assertFalse(self.provider["architectural_authority"])
        self.assertFalse(self.provider["new_capability"])
        self.assertFalse(self.provider["new_architectural_authority"])
        self.assertEqual(self.decision["new_capabilities"], 0)
        self.assertEqual(self.decision["new_architectural_authorities"], 0)
        self.assertEqual(self.decision["capability_count_after"], 143)

    def test_existing_mmg_context_ir_is_reused(self):
        bridge = self.contract["mmg_context_ir_bridge"]
        self.assertEqual(bridge["canonical_contract"], "FA3-MMG-CONTEXT-IR-CONTRACTS-001")
        self.assertEqual(bridge["canonical_type"], "MultimodalGenerationContextIR")
        self.assertTrue(bridge["editor_context_is_projection_source_not_new_ir_authority"])
        self.assertEqual(self.mmg["canonical_id"], "FA3-MMG-CONTEXT-IR-001")
        self.assertIn("EXISTING_MMG_CONTEXT_IR_REUSED_NOT_DUPLICATED", self.enforcement["p0_invariants"])

    def test_editor_semantics_cover_document_layer_selection_mask_alpha_and_color(self):
        required = set(self.contract["editor_context"]["required_semantics"])
        self.assertTrue({
            "document_identity", "canvas_geometry", "active_layer", "ordered_layer_set",
            "selection", "mask_and_alpha", "color_space_and_profile", "generation_intent",
            "result_placement_policy"
        }.issubset(required))
        self.assertTrue(self.contract["editor_context"]["rgba_alpha_semantics_must_be_preserved"])
        self.assertTrue(self.contract["editor_context"]["selection_and_mask_must_not_be_conflated"])

    def test_operation_surface_is_complete_without_provider_lockin(self):
        operations = set(self.contract["supported_operation_classes"])
        expected = {
            "TEXT_TO_IMAGE", "IMAGE_TO_IMAGE", "INPAINT", "OUTPAINT", "UPSCALE",
            "SELECTION_EDIT", "LAYER_COMPOSITE", "MASK_TRANSFER",
            "REFERENCE_OR_CONTROL_IMAGE", "RESULT_TO_NEW_LAYER", "RESULT_TO_NEW_DOCUMENT"
        }
        self.assertTrue(expected.issubset(operations))
        self.assertTrue(self.contract["provider_neutral"])

    def test_provider_native_workflow_is_downstream_projection_only(self):
        bridge = self.contract["mmg_context_ir_bridge"]
        self.assertTrue(bridge["provider_native_prompt_or_workflow_syntax_upstream_forbidden"])
        self.assertTrue(bridge["projection_loss_report_required"])
        self.assertEqual(bridge["hard_constraint_loss"], "FAIL_CLOSED")
        self.assertEqual(bridge["provider_specific_limits"], "DOWNSTREAM_PROJECTION_ONLY")

    def test_endpoint_and_device_are_not_canonical_constants(self):
        runtime = self.contract["runtime_interop"]
        self.assertEqual(runtime["endpoint"], "DISCOVERED_OR_OPERATOR_CONFIGURED_PROVIDER_LOCAL_ENDPOINT")
        self.assertFalse(runtime["hardcoded_host_port_as_canonical_requirement"])
        self.assertTrue(self.enforcement["provider_admission"]["runtime_endpoint_must_be_discovered_or_operator_configured"])
        self.assertTrue(self.enforcement["provider_admission"]["fixed_gpu_identity_forbidden"])
        self.assertIn("NO_HARDCODED_GPU_MODEL_COUNT_OR_DEVICE", self.enforcement["p0_invariants"])

    def test_document_mutation_is_nondestructive_and_fail_safe(self):
        policy = self.contract["result_policy"]
        self.assertEqual(policy["default_placement"], "NEW_LAYER_OR_NEW_DOCUMENT")
        self.assertFalse(policy["destructive_overwrite_by_default"])
        self.assertTrue(policy["source_document_preservation_on_provider_failure"])
        self.assertEqual(policy["partial_or_ambiguous_result"], "DO_NOT_MUTATE_SOURCE_DOCUMENT")
        self.assertTrue(self.enforcement["document_safety"]["validated_result_before_mutation"])
        self.assertTrue(self.enforcement["document_safety"]["source_document_unchanged_on_provider_failure"])

    def test_workflow_custom_nodes_models_and_dependencies_are_admission_gated(self):
        security = self.contract["security_and_supply_chain"]
        self.assertTrue(security["plugin_code_admission_required"])
        self.assertTrue(security["workflow_and_custom_node_inventory_required"])
        self.assertTrue(security["workflow_and_custom_node_revision_hash_required"])
        self.assertTrue(security["model_artifact_security_gate_required"])
        self.assertFalse(security["automatic_custom_node_install_or_update"])
        self.assertTrue(security["bundled_dependency_license_inventory_required"])

    def test_upstream_references_are_revision_pinned(self):
        refs = self.provider["upstream_references"]
        self.assertGreaterEqual(len(refs), 4)
        for ref in refs:
            self.assertRegex(ref["observed_revision"], r"^[0-9a-f]{40}$")
            self.assertRegex(ref["observed_date"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(ref["repository"])
            self.assertTrue(ref["license"])

    def test_license_policy_separates_gpl_pattern_source_from_code_intake(self):
        refs = {r["repository"]: r for r in self.provider["upstream_references"]}
        gpl = refs["nchenevey1/gimp-comfy-tools"]
        self.assertEqual(gpl["license"], "GPL-3.0")
        self.assertEqual(gpl["role"], "REFERENCE_PATTERN_ONLY_UNDER_PERMISSIVE_CODE_ADMISSION")
        self.assertEqual(
            self.provider["selection_policy"]["gpl_reference_code_copy_into_permissive_fa3_components"],
            "FORBIDDEN_WITHOUT_EXPLICIT_LICENSE_POLICY_CHANGE",
        )
        self.assertTrue(self.contract["security_and_supply_chain"]["non_permissive_reference_code_may_be_pattern_source_only"])

    def test_no_upstream_plugin_is_required_or_authoritative(self):
        selection = self.provider["selection_policy"]
        self.assertTrue(selection["no_single_upstream_is_required"])
        self.assertFalse(selection["live_transceiver_required"])
        self.assertTrue(selection["provider_replacement_must_not_change_canonical_intent"])
        forbidden = set(self.provider["forbidden_roles"])
        self.assertTrue({
            "GLOBAL_ORCHESTRATION_AUTHORITY", "WORKFLOW_AUTHORITY", "MODEL_REGISTRY_AUTHORITY",
            "MODEL_ROUTER_AUTHORITY", "HOST_RESOURCE_AUTHORITY", "EVIDENCE_AUTHORITY",
            "GENERATION_CONTEXT_IR_AUTHORITY"
        }.issubset(forbidden))

    def test_live_transport_is_optional_non_authority(self):
        self.assertEqual(self.contract["runtime_interop"]["live_transport"], "OPTIONAL_NON_AUTHORITY_TRANSPORT")
        self.assertFalse(self.contract["runtime_interop"]["cloud_dependency_required"])
        self.assertTrue(self.contract["runtime_interop"]["local_first"])
        self.assertIn("LIVE_TRANSPORT_OPTIONAL_AND_NON_AUTHORITY", self.enforcement["p0_invariants"])

    def test_required_existing_contracts_are_materialized(self):
        for contract_id in self.enforcement["required_existing_contracts"]:
            path = ROOT / "canonical" / "contracts" / f"{contract_id}.json"
            self.assertTrue(path.exists(), contract_id)
        self.assertEqual(self.imggen["status"], "CANONICAL")
        self.assertEqual(self.lifecycle["status"], "CANONICAL")

    def test_gate_is_fail_closed_and_current_host_runtime_is_not_overclaimed(self):
        self.assertTrue(self.enforcement["fail_closed"])
        self.assertEqual(self.provider["current_host_runtime_evidence"], "NOT_CLAIMED")
        self.assertFalse(self.provider["current_host_production_claim"])
        self.assertEqual(self.decision["current_host_runtime_evidence"], "NOT_CLAIMED")
        self.assertFalse(self.decision["current_host_runtime_promotion_claim"])

    def test_explicit_gate_record_is_closed_blocking_and_fully_linked(self):
        self.assertEqual(self.gate["status"], "CANONICAL_CLOSED")
        self.assertEqual(self.gate["priority"], "P0")
        self.assertTrue(self.gate["blocking"])
        self.assertEqual(self.gate["decision_id"], self.decision["id"])
        self.assertEqual(self.decision["gate_record_id"], self.gate["id"])
        self.assertEqual(self.enforcement["gate_record_id"], self.gate["id"])
        self.assertEqual(self.gate["enforcement_id"], self.enforcement["gate_id"])
        self.assertEqual(len(self.gate["checks"]), 15)
        self.assertEqual({c["id"] for c in self.gate["checks"]}, {f"GDG-{i:02d}" for i in range(1, 16)})
        self.assertTrue(all(c["failure"] == "BLOCK_PROMOTION" for c in self.gate["checks"]))

    def test_upstream_reference_snapshot_is_non_authoritative_pinned_and_linked(self):
        mapping = self.reference["fa3_mapping"]
        self.assertFalse(mapping["canonical_root"])
        self.assertFalse(mapping["architectural_authority"])
        self.assertFalse(mapping["required_runtime_dependency"])
        self.assertEqual(self.provider["upstream_reference_id"], self.reference["id"])
        self.assertEqual(self.decision["upstream_reference_id"], self.reference["id"])
        self.assertEqual(self.enforcement["upstream_reference_id"], self.reference["id"])
        self.assertEqual(self.gate["upstream_reference_id"], self.reference["id"])
        self.assertFalse(self.reference["verification"]["runtime_execution_verified"])
        self.assertFalse(self.reference["verification"]["production_readiness_claim"])
        for source in self.reference["source_set"]:
            self.assertRegex(source["revision"], r"^[0-9a-f]{40}$")
            self.assertRegex(source["observed_date"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["repository"])
            self.assertTrue(source["license"]["spdx"])


if __name__ == "__main__":
    unittest.main()
