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
            "canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json",
        ]:
            provider = load(path)
            self.assertFalse(provider["canonical_root"])
            self.assertFalse(provider["architectural_authority"])
            self.assertFalse(provider["new_capability"])
            self.assertEqual(provider["capability_count"], 143)

    def test_stability_sgm_is_specialized_multiview_reference_not_geometry(self):
        profile = load("canonical/profiles/FA3-VIDEO-001.json")
        provider = load("canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json")
        self.assertIn("FA3-PROVIDER-STABILITY-SGM-001", profile["providers"])
        self.assertIn("FA3-GENERATIVE-PIPELINE-MULTIVIEW-CONTRACTS-001", profile["contracts"])
        self.assertFalse(provider["output_semantics"]["canonical_geometry"])
        self.assertEqual(
            provider["output_semantics"]["geometry_admission"],
            "FA3-3D-GEOM-001_VALIDATION_AND_MATERIALIZATION_REQUIRED",
        )

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

    def test_h3_execution_framework_projection_distinguishes_full_dit_serving(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        for name in ("sglang", "diffusers", "comfyui"):
            self.assertEqual(
                h3["integration_targets"][name]["status"],
                "PRODUCTION_INTEGRATION_TARGET",
            )
        self.assertEqual(
            h3["integration_targets"]["vllm"]["status"],
            "RESTRICTED_NOT_END_TO_END_H3_TARGET",
        )
        self.assertFalse(h3["integration_targets"]["vllm"]["end_to_end_h3_dit_serving"])
        self.assertFalse(h3["integration_targets"]["vllm"]["production_h3_target"])
        self.assertEqual(
            h3["integration_targets"]["vllm_omni"]["status"],
            "DISCOVERED_NOT_ADMITTED",
        )
        self.assertFalse(h3["integration_targets"]["vllm_omni"]["automatic_promotion"])
        self.assertIn("NOT_YET_CURRENT_HOST_PROMOTED", h3["implementation_status"])

    def test_h3_prompt_skill_is_reference_knowledge_only(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        prompt = h3["prompt_knowledge_adapter"]
        self.assertEqual(prompt["status"], "REFERENCE_KNOWLEDGE_ADAPTER")
        self.assertFalse(prompt["architectural_authority"])
        self.assertFalse(prompt["canonical_ir"])
        self.assertFalse(prompt["context_compiler_authority"])
        self.assertFalse(prompt["execution_authority"])
        self.assertEqual(
            prompt["skills_lock_computed_hash"],
            "3d01859464bc9438585c8fdbf7fcd4b4c54404fadd3f1a64ab7970ae8877d086",
        )

    def test_h3_runtime_targets_require_immutable_version_pin(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        for name in ("sglang", "diffusers", "comfyui", "vllm_omni"):
            self.assertTrue(
                h3["integration_targets"][name]["immutable_runtime_version_pin_required"]
            )

    def test_h3_comfyui_promotion_is_compatibility_gated(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        comfy = h3["integration_targets"]["comfyui"]
        self.assertTrue(comfy["adapter_compatibility_regression_required"])
        self.assertTrue(comfy["audio_path_regression_required"])
        self.assertTrue(comfy["current_host_e2e_required"])
        self.assertIn("Comfy-Org/ComfyUI#15960", comfy["known_open_compatibility_risks"])
        self.assertIn("Comfy-Org/ComfyUI#15970", comfy["known_open_compatibility_risks"])

    def test_h3_projection_decision_preserves_baseline(self):
        decision = load(
            "canonical/decisions/FA3-DEC-MINIMAX-H3-PROJECTION-2026-08-30.json"
        )
        self.assertFalse(decision["canonical_semantics_changed"])
        self.assertEqual(decision["new_capabilities"], 0)
        self.assertEqual(decision["new_architectural_authorities"], 0)
        self.assertEqual(decision["capability_count_after"], 143)
        self.assertEqual(
            decision["promotion_state"],
            "INTEGRATION_TARGETS_REGISTERED_NOT_CURRENT_HOST_PROMOTED",
        )

    def test_h3_upstream_reference_is_immutable_and_skill_locked(self):
        ref = load(
            "canonical/references/FA3-MINIMAX-H3-UPSTREAM-REFERENCE-2026-08-30.json"
        )
        self.assertEqual(
            ref["observed_commit"],
            "d21241f0a4b3acbb34c97dae47fa417b7065e438",
        )
        self.assertFalse(ref["rules"]["floating_main_for_promotion_evidence"])
        self.assertEqual(
            ref["prompt_skill"]["skills_lock_computed_hash"],
            "3d01859464bc9438585c8fdbf7fcd4b4c54404fadd3f1a64ab7970ae8877d086",
        )

    def test_h3_local_and_hosted_service_admission_are_separate(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        service = h3["service_access_policy"]
        self.assertEqual(service["local_open_weight"]["deployment_class"], "LOCAL_H3_BASE")
        self.assertFalse(service["local_open_weight"]["hosted_platform_credential_required"])
        self.assertEqual(
            service["hosted_open_platform"]["deployment_class"],
            "REMOTE_OR_HYBRID_MINIMAX_OPEN_PLATFORM",
        )
        self.assertTrue(h3["license_admission"]["hosted_service_terms_evaluated_separately"])

    def test_h3_payg_and_subscription_credentials_are_not_interchangeable(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        creds = h3["service_access_policy"]["hosted_open_platform"]["credential_modes"]
        self.assertFalse(creds["payg_api_key"]["interchangeable_with_subscription_key"])
        self.assertFalse(creds["token_plan_subscription_key"]["interchangeable_with_payg_api_key"])
        self.assertNotEqual(
            creds["payg_api_key"]["credential_class"],
            creds["token_plan_subscription_key"]["credential_class"],
        )

    def test_h3_commercial_plan_state_is_discovered_not_hardcoded(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        service = h3["service_access_policy"]
        self.assertTrue(service["entitlement_discovery"]["required"])
        self.assertTrue(service["entitlement_discovery"]["commercial_plan_availability_is_dynamic"])
        self.assertEqual(
            service["hosted_open_platform"]["team_subscription"]["availability"],
            "DISCOVER_AT_ADMISSION",
        )
        self.assertTrue(
            service["hosted_open_platform"]["team_subscription"]["hard_dependency_forbidden"]
        )

    def test_h3_billing_fallback_requires_explicit_policy(self):
        h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        fallback = h3["service_access_policy"]["fallback_policy"]
        self.assertTrue(fallback["credential_class_auto_substitution_forbidden"])
        self.assertTrue(fallback["billing_mode_auto_switch_forbidden"])
        self.assertTrue(fallback["subscription_to_payg_requires_explicit_policy_and_admitted_secret"])
        self.assertTrue(fallback["payg_to_subscription_requires_explicit_policy_and_admitted_secret"])

    def test_h3_service_access_reference_rejects_stale_plan_assumptions(self):
        ref = load(
            "canonical/references/FA3-MINIMAX-H3-SERVICE-REFERENCE-2026-09-07.json"
        )
        self.assertIn(
            "DO_NOT_CANONICALIZE_COMMERCIAL_PLAN_AVAILABILITY",
            ref["canonicalization_rules"],
        )
        self.assertIn(
            "TEAM_PLAN_AVAILABILITY_MUST_NOT_BE_INFERRED_FROM_UNVERIFIED_OR_HISTORICAL_NOTICE",
            ref["canonicalization_rules"],
        )
        self.assertFalse(ref["current_host_runtime_promotion_claim"])

    def test_h3_service_access_decision_preserves_baseline(self):
        decision = load(
            "canonical/decisions/FA3-DEC-MINIMAX-H3-SERVICE-ACCESS-2026-09-07.json"
        )
        self.assertFalse(decision["canonical_semantics_changed"])
        self.assertEqual(decision["new_capabilities"], 0)
        self.assertEqual(decision["new_architectural_authorities"], 0)
        self.assertEqual(decision["capability_count_after"], 143)
        self.assertEqual(
            decision["promotion_state"],
            "PROVIDER_POLICY_CANONICAL_RUNTIME_NOT_PROMOTED",
        )

    def test_h3_service_access_reference_evidence_is_policy_only_pass(self):
        evidence = load("evidence/reference/minimax-h3-service-access-ci-2026-09-07.json")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["passed"], evidence["total"])
        self.assertFalse(evidence["current_host_runtime_promotion_claim"])
        self.assertFalse(evidence["provider_runtime_execution_claim"])


if __name__ == "__main__":
    unittest.main()
