import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TestMultimodalGenerationContextIR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load("canonical/profiles/FA3-VIDEO-001.json")
        cls.video = load("canonical/contracts/FA3-VIDEO-CONTRACTS-001.json")
        cls.mmg = load("canonical/contracts/FA3-MMG-CONTEXT-IR-CONTRACTS-001.json")
        cls.decision = load("canonical/decisions/FA3-DEC-MMG-CONTEXT-IR-2026-09-08.json")
        cls.enforcement = load("canonical/mmg-context-ir-enforcement.json")
        cls.video_enforcement = load("canonical/video-enforcement.json")
        cls.h3 = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")

    def test_baseline_geometry_is_unchanged(self):
        self.assertFalse(self.mmg["canonical_root"])
        self.assertFalse(self.mmg["new_capability"])
        self.assertFalse(self.mmg["new_architectural_authority"])
        self.assertEqual(self.mmg["capability_count"], 143)
        self.assertEqual(self.decision["new_capabilities"], 0)
        self.assertEqual(self.decision["new_architectural_authorities"], 0)
        self.assertEqual(self.decision["capability_count_after"], 143)
        self.assertTrue(self.decision["authority_boundaries_unchanged"])

    def test_mmg_ir_is_provider_neutral_child_of_video_generation_ir(self):
        self.assertTrue(self.mmg["provider_neutral"])
        self.assertEqual(self.mmg["parent_contract"], "FA3-VIDEO-CONTRACTS-001/VideoGenerationIR")
        self.assertEqual(self.mmg["canonical_type"], "MultimodalGenerationContextIR")
        self.assertIn("FA3-MMG-CONTEXT-IR-CONTRACTS-001", self.profile["contracts"])
        self.assertEqual(
            self.profile["multimodal_generation_context_ir"]["embedding"],
            "TYPED_CHILD_OF_VideoGenerationIR",
        )
        chain = self.profile["mandatory_execution_chain"]
        self.assertLess(chain.index("video_context_compiler"), chain.index("MultimodalGenerationContextIR"))
        self.assertLess(chain.index("MultimodalGenerationContextIR"), chain.index("VideoGenerationIR"))

    def test_artifact_entity_binding_are_distinct(self):
        ref = self.mmg["reference_model"]
        self.assertEqual(ref["separation_rule"], "ReferenceArtifact != SemanticEntity != ReferenceBinding")
        self.assertTrue(ref["one_artifact_may_define_multiple_entities"])
        self.assertTrue(ref["one_entity_may_use_multiple_artifacts"])
        self.assertTrue(ref["one_artifact_may_have_multiple_binding_roles"])

    def test_reference_content_is_non_instructional_by_default(self):
        self.assertFalse(self.mmg["reference_model"]["reference_embedded_text_instruction_eligible_by_default"])
        self.assertTrue(self.video["rules"]["reference_content_non_instructional_by_default"])
        self.assertIn("REFERENCE_CONTENT_IS_NON_INSTRUCTIONAL_BY_DEFAULT", self.enforcement["p0_invariants"])

    def test_inference_is_typed_provenanced_and_bounded(self):
        self.assertEqual(
            set(self.mmg["inference_origins"]),
            {"DECLARED", "AUTHORITY_DERIVED", "ARTIFACT_DERIVED", "INFERRED", "DEFAULTED"},
        )
        rules = self.mmg["inference_rules"]
        self.assertTrue(rules["origin_required"])
        self.assertTrue(rules["confidence_required_for_inferred_or_defaulted"])
        self.assertTrue(rules["hard_constraint_override_forbidden"])
        self.assertTrue(rules["silent_dialogue_rewrite_forbidden"])
        self.assertTrue(rules["silent_visible_text_rewrite_forbidden"])
        self.assertTrue(rules["rights_or_license_inference_forbidden"])
        self.assertTrue(rules["security_or_policy_decision_inference_forbidden"])

    def test_temporal_model_is_rational_and_provider_independent(self):
        temporal = self.mmg["temporal_model"]
        self.assertEqual(temporal["time_type"], "RationalTime")
        self.assertEqual(temporal["duration_type"], "RationalDuration")
        self.assertFalse(temporal["floating_point_time_as_canonical_semantics"])
        self.assertEqual(
            set(temporal["frame_anchor_types"]),
            {"FIRST_FRAME", "LAST_FRAME", "KEYFRAME", "COMPOSITION_ANCHOR", "INTERMEDIATE_STATE"},
        )

    def test_projection_loss_is_fail_closed_for_hard_constraints(self):
        self.assertEqual(
            set(self.mmg["projection_loss_states"]),
            {"PRESERVED", "APPROXIMATED", "DROPPED", "UNSUPPORTED"},
        )
        projection = self.mmg["projection_rules"]
        self.assertEqual(projection["hard_dropped"], "FAIL")
        self.assertEqual(projection["hard_unsupported"], "PROVIDER_INELIGIBLE")
        self.assertEqual(projection["soft_approximated"], "ALLOW_WITH_EVIDENCE")
        self.assertTrue(projection["loss_report_required"])
        self.assertTrue(self.video["rules"]["provider_projection_loss_report_required"])
        self.assertTrue(self.video["rules"]["hard_projection_loss_fail_closed"])

    def test_regeneration_preserves_lineage_and_declares_delta(self):
        regen = self.mmg["regeneration_context"]
        required = set(regen["required_fields"])
        self.assertTrue(
            {
                "base_generation_ir_ref",
                "previous_result_ref",
                "parent_provenance_ref",
                "frozen_constraints",
                "mutable_constraints",
                "allowed_delta",
                "iteration_index",
            }.issubset(required)
        )
        self.assertTrue(regen["parent_lineage_required"])
        self.assertTrue(regen["frozen_and_mutable_constraints_required"])

    def test_authority_boundaries_are_explicit(self):
        auth = self.mmg["authority_boundaries"]
        self.assertEqual(auth["story"], "FA3-STORY-001")
        self.assertEqual(auth["voice_identity"], "FA3-VOICE-001")
        self.assertEqual(auth["scene_spatial_camera"], "FA3-DCC-RT3D-001")
        self.assertEqual(auth["provider_routing"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(auth["security_license_policy"], "FA3-AUTH-SECURITY-GOV-001")
        self.assertEqual(auth["evidence"], "FA3-AUTH-OBS-EVIDENCE-001")
        self.assertEqual(auth["context_compiler"], "NON_AUTHORITY_TRANSFORMATION")

    def test_provider_native_semantics_do_not_leak_upstream(self):
        forbidden = set(self.mmg["forbidden_canonical_content"])
        self.assertIn("provider_native_prompt_syntax", forbidden)
        self.assertIn("provider_specific_reference_count_limits", forbidden)
        self.assertIn("provider_specific_resolution_or_duration_limits", forbidden)
        self.assertIn("hosted_H3_Context_IR_as_dependency", forbidden)
        self.assertTrue(self.video["rules"]["provider_native_prompt_syntax_forbidden_upstream"])
        self.assertTrue(self.video["rules"]["fixed_provider_reference_limits_forbidden"])
        self.assertTrue(self.video["rules"]["fixed_provider_resolution_limits_forbidden"])

    def test_h3_remains_pattern_source_not_context_authority(self):
        policy = self.h3["context_ir_policy"]
        self.assertEqual(policy["provider_context_ir"], "REFERENCE_PATTERN_ONLY")
        self.assertFalse(policy["hosted_context_ir_required_for_fa3"])
        self.assertEqual(policy["canonical_contract"], "FA3-MMG-CONTEXT-IR-CONTRACTS-001")
        self.assertEqual(policy["canonical_type"], "MultimodalGenerationContextIR")
        self.assertTrue(policy["provider_native_context_ir_downstream_projection_only"])
        self.assertFalse(self.h3["architectural_authority"])
        self.assertFalse(self.h3["prompt_knowledge_adapter"]["canonical_ir"])

    def test_video_gate_embeds_mmg_subgate(self):
        mmg = self.video_enforcement["mmg_context_ir"]
        self.assertEqual(mmg["subgate_id"], "FA3-MMG-CONTEXT-IR-GATESET-001")
        self.assertEqual(mmg["contract_id"], "FA3-MMG-CONTEXT-IR-CONTRACTS-001")
        self.assertEqual(mmg["typed_child_of"], "VideoGenerationIR")
        self.assertFalse(mmg["hosted_h3_context_ir_required"])
        self.assertEqual(self.enforcement["parent_gate_id"], "FA3-VIDEO-GATESET-001")
        self.assertTrue(self.enforcement["fail_closed"])

    def test_contract_projection_and_inference_types_are_registered(self):
        required = {
            "MultimodalGenerationContextIR",
            "SemanticContextGraph",
            "SemanticEntity",
            "SemanticRelation",
            "ReferenceFidelityPolicy",
            "TemporalContextGraph",
            "ContextConstraint",
            "ContextInferenceRecord",
            "ContextAmbiguityRecord",
            "ContextConflictRecord",
            "ContextCompilerReceipt",
            "ProviderProjectionLossReport",
            "ContextRevisionPatch",
            "ContextAwareRegenerationContext",
        }
        self.assertTrue(required.issubset(set(self.video["contracts"])))
        self.assertTrue(required.issubset(set(self.mmg["contracts"])))


if __name__ == "__main__":
    unittest.main()
