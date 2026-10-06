import unittest

from fa3_context_budget_compaction import ContextBudgetError, compaction_receipt, plan_context_compaction
from fa3_llm_protocol_compat import (
    ProtocolCompatibilityError,
    canonical_usage_metadata,
    normalize_provider_error,
    normalize_tool_call_id,
    project_reasoning_intent,
    tool_schema_projection,
    validate_multimodal_payload,
    validate_stream_events,
)


class AntigravityRefreshProtocolTests(unittest.TestCase):
    def test_reasoning_projection_never_grants_adapter_authority(self):
        for protocol in ("OPENAI", "ANTHROPIC", "GEMINI"):
            row=project_reasoning_intent({"class":"HIGH","budget_tokens":2048},protocol)
            self.assertFalse(row["provider_or_model_selection_authority"])
            self.assertFalse(row["adapter_may_increase_reasoning"])
            self.assertFalse(row["silent_budget_clamp"])

    def test_security_schema_loss_fails_closed_without_treating_property_names_as_keywords(self):
        schema={"type":"object","properties":{"name":{"type":"string","pattern":"^[a-z]+$"}},"required":["name"],"additionalProperties":False}
        receipt=tool_schema_projection(
            schema,
            supported_keywords={"type","properties","required","additionalProperties"},
            security_relevant_keywords={"pattern","additionalProperties"},
        )
        self.assertEqual("UNSUPPORTED_FAIL_CLOSED",receipt["status"])
        self.assertIn("pattern",receipt["security_relevant_loss"])
        self.assertNotIn("name",receipt["observed_keywords"])

    def test_tool_call_id_projection_is_deterministic(self):
        a=normalize_tool_call_id("unsafe id with spaces")
        b=normalize_tool_call_id("unsafe id with spaces")
        self.assertEqual(a["canonical_id"],b["canonical_id"])
        self.assertTrue(a["transformed"])

    def test_stream_and_error_fidelity(self):
        receipt=validate_stream_events([{"type":"START"},{"type":"DELTA"},{"type":"HEARTBEAT"},{"type":"DONE"}])
        self.assertTrue(receipt["terminal_explicit"])
        with self.assertRaises(ProtocolCompatibilityError):
            validate_stream_events([{"type":"START"},{"type":"DONE"},{"type":"DELTA"}])
        err=normalize_provider_error(429,error_type="rate_limit",error_code="quota")
        self.assertEqual(429,err["http_status"])
        self.assertFalse(err["success"])
        with self.assertRaises(ProtocolCompatibilityError):
            normalize_provider_error(200,error_type="x",error_code="x")

    def test_multimodal_and_usage_bounds(self):
        ok=validate_multimodal_payload([
            {"kind":"TEXT"},
            {"kind":"INLINE_MEDIA","size_bytes":32},
            {"kind":"ARTIFACT_REF","artifact_ref":"artifact:1"},
        ],max_inline_bytes=64,max_parts=4)
        self.assertEqual(32,ok["inline_bytes"])
        with self.assertRaises(ProtocolCompatibilityError):
            validate_multimodal_payload([{"kind":"INLINE_MEDIA","size_bytes":65}],max_inline_bytes=64,max_parts=4)
        usage=canonical_usage_metadata({"input_tokens":10,"output_tokens":4,"reasoning_tokens":2,"vendor_extra":99})
        self.assertEqual(2,usage["usage"]["reasoning_tokens"])
        self.assertNotIn("vendor_extra",usage["usage"])


class AntigravityRefreshContextTests(unittest.TestCase):
    def setUp(self):
        self.segments=[
            {"segment_id":"p","classification":"PROTECTED","token_count":40,"provenance_ref":"src:p","ordinal":0},
            {"segment_id":"a","classification":"ACTIVE","token_count":30,"provenance_ref":"src:a","ordinal":1},
            {"segment_id":"r","classification":"RETRIEVABLE","token_count":30,"provenance_ref":"src:r","ordinal":2},
            {"segment_id":"s","classification":"SUMMARIZABLE","token_count":40,"provenance_ref":"src:s","ordinal":3},
            {"segment_id":"x","classification":"ARCHIVABLE","token_count":40,"provenance_ref":"src:x","ordinal":4},
        ]

    def test_compaction_preserves_protected_active_and_provenance(self):
        plan=plan_context_compaction(self.segments,max_context_tokens=150,target_context_tokens=100,min_headroom_tokens=20,min_growth_tokens=10)
        self.assertEqual("COMPACTION_REQUIRED",plan["status"])
        self.assertNotIn("p",plan["selected_segment_ids"])
        self.assertNotIn("a",plan["selected_segment_ids"])
        self.assertTrue(plan["provenance_preserved"])
        self.assertFalse(plan["silent_context_drop"])
        receipt=compaction_receipt(plan,summary_artifact_ref="artifact:summary")
        self.assertFalse(receipt["source_history_mutated"])
        self.assertTrue(receipt["retrieval_backreferences_required"])

    def test_anti_thrash_and_fail_closed(self):
        defer=plan_context_compaction(self.segments[:3],max_context_tokens=120,target_context_tokens=80,min_headroom_tokens=30,min_growth_tokens=50,last_compaction_total_tokens=95)
        self.assertEqual("DEFER_ANTI_THRASH",defer["status"])
        impossible=plan_context_compaction([
            {"segment_id":"p","classification":"PROTECTED","token_count":200,"provenance_ref":"src:p","ordinal":0}
        ],max_context_tokens=100,target_context_tokens=80,min_headroom_tokens=10,min_growth_tokens=10)
        self.assertEqual("FAIL_CLOSED_RESELECTION_REQUIRED",impossible["status"])

    def test_overhead_checkpoint_cooldown_and_hysteresis(self):
        plan=plan_context_compaction(
            [
                {"segment_id":"p","classification":"PROTECTED","token_count":60,"provenance_ref":"src:p","ordinal":0},
                {"segment_id":"s","classification":"SUMMARIZABLE","token_count":40,"provenance_ref":"src:s","ordinal":1},
            ],
            max_context_tokens=140,
            target_context_tokens=90,
            min_headroom_tokens=20,
            min_growth_tokens=10,
            tool_schema_overhead_tokens=10,
            multimodal_overhead_tokens=10,
            reserved_output_tokens=10,
            hysteresis_tokens=10,
            checkpoint_id="cp:2",
            parent_checkpoint_id="cp:1",
        )
        self.assertEqual("COMPACTION_REQUIRED",plan["status"])
        self.assertEqual(20,plan["overhead_tokens"])
        self.assertEqual("cp:2",plan["checkpoint_lineage"]["checkpoint_id"])
        self.assertTrue(plan["summarization_required"])
        self.assertEqual("SUMMARIZATION_CANDIDATE",plan["selected_actions"][0]["action"])
        receipt=compaction_receipt(plan,summary_artifact_ref="artifact:summary")
        self.assertEqual("cp:1",receipt["checkpoint_lineage"]["parent_checkpoint_id"])
        self.assertEqual(10,receipt["hysteresis_tokens"])

        cooldown=plan_context_compaction(
            self.segments[:3],
            max_context_tokens=120,
            target_context_tokens=80,
            min_headroom_tokens=30,
            min_growth_tokens=1,
            now_seconds=15,
            last_compaction_at_seconds=10,
            cooldown_seconds=10,
        )
        self.assertEqual("DEFER_COOLDOWN",cooldown["status"])
        self.assertGreater(cooldown["cooldown_remaining_seconds"],0)

    def test_invalid_segment_fails_closed(self):
        with self.assertRaises(ContextBudgetError):
            plan_context_compaction([{"segment_id":"x","classification":"ACTIVE","token_count":1}],max_context_tokens=10,target_context_tokens=8,min_headroom_tokens=1,min_growth_tokens=1)


if __name__=="__main__":
    unittest.main()
