import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text())


class LTX2ProviderTests(unittest.TestCase):
    def setUp(self):
        self.profile = load("canonical/profiles/FA3-VIDEO-001.json")
        self.provider = load("canonical/providers/FA3-PROVIDER-LTX2-001.json")
        self.decision = load("canonical/decisions/FA3-DEC-VIDEO-LTX2-2026-09-12.json")
        self.reference = load("canonical/references/FA3-LTX2-UPSTREAM-REFERENCE-2026-09-12.json")
        self.enforcement = load("canonical/video-enforcement.json")
        self.evidence = load("evidence/reference/ltx2-provider-policy-ci-2026-09-12.json")

    def test_provider_is_registered_without_new_authority_or_capability(self):
        self.assertIn("FA3-PROVIDER-LTX2-001", self.profile["providers"])
        self.assertFalse(self.provider["canonical_root"])
        self.assertFalse(self.provider["architectural_authority"])
        self.assertFalse(self.provider["new_capability"])
        self.assertFalse(self.provider["new_architectural_authority"])
        self.assertEqual(self.provider["capability_count"], 143)
        self.assertEqual(self.profile["capability_count"], 143)

    def test_provider_projects_existing_video_ir(self):
        projection = self.provider["canonical_ir_projection"]
        self.assertEqual(projection["input"], "VideoGenerationIR")
        self.assertFalse(projection["provider_native_fields_in_canonical_ir"])
        self.assertTrue(projection["projection_loss_report_required"])
        self.assertTrue(projection["hard_projection_loss_fail_closed"])
        self.assertEqual(
            projection["retake_maps_to"],
            ["VideoRegenerationIntent", "TemporalEditDescriptor"],
        )
        self.assertEqual(
            projection["audio_video_maps_to"],
            ["AudioDialoguePlan", "AudioSceneDescriptor", "AVSyncConstraint"],
        )

    def test_admitted_video_capabilities_cover_current_ltx2_pipeline_surface(self):
        capabilities = set(self.provider["video_capabilities"])
        for capability in {
            "TEXT_TO_VIDEO",
            "IMAGE_TO_VIDEO",
            "VIDEO_TO_VIDEO_IC_LORA",
            "KEYFRAME_INTERPOLATION",
            "TEMPORAL_RETAKE_REGENERATION",
            "AUDIO_TO_VIDEO",
            "SYNCHRONIZED_AUDIO_VIDEO",
            "LIP_DUB_REVOICING",
            "SPATIAL_UPSCALE",
            "TEMPORAL_UPSCALE",
        }:
            self.assertIn(capability, capabilities)

    def test_audio_only_pipeline_is_not_claimed_by_video_authority(self):
        excluded = self.provider["excluded_from_video_provider_claims"]
        self.assertEqual(
            excluded["audio_only_t2a_one_stage"],
            "DEFER_TO_AUDIO_DOMAIN_AUTHORITY",
        )
        self.assertNotIn("TEXT_TO_AUDIO", self.provider["video_capabilities"])

    def test_legacy_ltx_video_is_not_duplicate_canonical_provider(self):
        excluded = self.provider["excluded_from_video_provider_claims"]
        self.assertEqual(
            excluded["legacy_ltx_video_0_9_8"],
            "REFERENCE_OR_COMPATIBILITY_ONLY_NOT_SEPARATE_CANONICAL_PROVIDER",
        )
        self.assertNotIn("FA3-PROVIDER-LTX-VIDEO-001", self.profile["providers"])
        self.assertFalse(self.decision["legacy_policy"]["separate_canonical_provider_record"])

    def test_unverified_video_extension_is_not_claimed(self):
        excluded = self.provider["excluded_from_video_provider_claims"]
        self.assertEqual(
            excluded["video_extension"],
            "NOT_VERIFIED_IN_CURRENT_LTX2_PIPELINE_SURFACE",
        )
        self.assertNotIn("VIDEO_EXTENSION", self.provider["video_capabilities"])

    def test_multi_gpu_is_latency_not_memory_aggregation(self):
        mgpu = self.provider["memory_execution_policy"]["multi_gpu"]
        self.assertEqual(mgpu["purpose"], "LATENCY_REDUCTION_NOT_MODEL_FIT")
        self.assertTrue(mgpu["single_machine_only"])
        self.assertTrue(mgpu["requires_p2p_access"])
        self.assertTrue(mgpu["full_mutable_transformer_copy_per_gpu"])
        self.assertTrue(mgpu["memory_expansion_claim_forbidden"])
        self.assertFalse(self.provider["memory_execution_policy"]["vram_aggregation_across_gpus"])

    def test_memory_fallback_is_explicit_and_fp8_is_not_assumed(self):
        memory = self.provider["memory_execution_policy"]
        self.assertEqual(memory["cpu_offload"], "PREFERRED_WHEN_VRAM_CONSTRAINED")
        self.assertEqual(memory["disk_offload"], "FALLBACK_ONLY")
        self.assertIn("CONDITIONAL", memory["fp8"])
        self.assertFalse(memory["ampere_legacy_fp8_kernel_support_assumed"])

    def test_license_admission_is_version_sensitive_and_fail_closed(self):
        license_policy = self.provider["license_admission"]
        self.assertEqual(license_policy["mode"], "FAIL_CLOSED")
        self.assertTrue(license_policy["license_family_must_match_exact_model_version"])
        self.assertEqual(
            license_policy["ltx_2_through_2_3"]["commercial_entity_threshold_usd_annual_revenue"],
            10000000,
        )
        self.assertTrue(
            license_policy["ltx_2_through_2_3"]["at_or_above_threshold_requires_paid_commercial_use_license"]
        )
        self.assertFalse(
            license_policy["ltx_2_5_and_future_2_x"]["automatic_inheritance_from_ltx_2_3_admission"]
        )
        self.assertEqual(license_policy["unknown_version_or_eligibility"], "DENY_RUNTIME_PROMOTION")

    def test_integration_targets_do_not_create_parallel_authority(self):
        native = self.provider["integration_targets"]["native_ltx_pipelines"]
        comfy = self.provider["integration_targets"]["comfyui"]
        self.assertEqual(native["status"], "PRODUCTION_INTEGRATION_TARGET")
        self.assertEqual(comfy["status"], "PRODUCTION_INTEGRATION_TARGET")
        self.assertTrue(comfy["must_route_through_existing_fa3_comfyui_integration"])
        self.assertTrue(comfy["parallel_workflow_authority_forbidden"])
        for forbidden in (
            "VIDEO_SEMANTIC_AUTHORITY",
            "MODEL_ROUTING_AUTHORITY",
            "HOST_RESOURCE_AUTHORITY",
            "WORKFLOW_AUTHORITY",
            "VOICE_IDENTITY_AUTHORITY",
            "EVIDENCE_AUTHORITY",
        ):
            self.assertIn(forbidden, self.provider["prohibited_authority_roles"])

    def test_runtime_promotion_remains_pending_real_current_host_e2e(self):
        runtime = self.provider["runtime_admission"]
        self.assertEqual(runtime["mode"], "FAIL_CLOSED")
        self.assertTrue(runtime["promotion_requires_real_current_host_e2e"])
        self.assertFalse(runtime["current_host_runtime_promotion_claim"])
        self.assertIn("PENDING_CURRENT_HOST", runtime["non_pass_states"])
        self.assertEqual(
            self.decision["promotion_state"],
            "PROVIDER_POLICY_CANONICAL_RUNTIME_PENDING_CURRENT_HOST_E2E",
        )
        self.assertFalse(self.decision["provider_runtime_execution_claim"])

    def test_upstream_reference_is_pinned_and_rejects_floating_promotion(self):
        self.assertEqual(
            self.reference["observed_commit"],
            "a95ab856bf29407b6b066ede0abe1846050db56c",
        )
        self.assertFalse(self.reference["floating_main_for_promotion_evidence"])
        self.assertTrue(self.reference["fa3_interpretation"]["license_admission_is_version_sensitive"])
        self.assertFalse(self.reference["fa3_interpretation"]["multi_gpu_vram_aggregation_allowed"])
        self.assertFalse(self.reference["fa3_interpretation"]["video_extension_current_ltx2_claim_verified"])

    def test_enforcement_registers_ltx2_fail_closed_policy(self):
        self.assertIn("FA3-PROVIDER-LTX2-001", self.enforcement["provider_ids"])
        policy = self.enforcement["ltx2_provider_policy"]
        self.assertTrue(policy["fail_closed"])
        self.assertTrue(policy["provider_projection_only"])
        self.assertFalse(policy["multi_gpu_memory_aggregation_allowed"])
        self.assertTrue(policy["exact_version_license_resolution_required"])
        self.assertFalse(policy["ltx_2_5_license_auto_inherited_from_ltx_2_3"])
        self.assertTrue(policy["runtime_promotion_requires_real_current_host_e2e"])
        self.assertFalse(policy["current_host_runtime_promotion_claim"])

    def test_decision_preserves_fa3_baseline_semantics(self):
        self.assertFalse(self.decision["canonical_semantics_changed"])
        self.assertEqual(self.decision["new_capabilities"], 0)
        self.assertEqual(self.decision["new_architectural_authorities"], 0)
        self.assertEqual(self.decision["capability_count_after"], 143)

    def test_policy_evidence_is_static_pass_not_runtime_pass(self):
        self.assertEqual(self.evidence["status"], "PASS")
        self.assertEqual(self.evidence["passed"], self.evidence["total"])
        self.assertEqual(
            self.evidence["evidence_class"],
            "CANONICAL_POLICY_STATIC_EXECUTABLE_CONFORMANCE_ONLY",
        )
        self.assertFalse(self.evidence["current_host_runtime_promotion_claim"])
        self.assertFalse(self.evidence["provider_runtime_execution_claim"])
        self.assertEqual(self.evidence["runtime_state"], "PENDING_CURRENT_HOST")


if __name__ == "__main__":
    unittest.main()
