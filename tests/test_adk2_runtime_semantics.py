import unittest
from pathlib import Path
from src.fa3_adk2_runtime_gate import gate,regression_cases
from src.fa3_agent_runtime_semantics import RuntimeSemanticsError,consume_budget,make_execution_ledger,normalize_mcp_result,plan_resume,validate_artifact_write,validate_session_append,validate_tool_confirmation
ROOT=Path(__file__).resolve().parents[1]
class Adk2DerivedRuntimeSemanticsTests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        r=gate(ROOT); self.assertEqual("PASS",r["result"],r.get("findings"))
    def test_regressions_pass(self): self.assertEqual("PASS",regression_cases()["result"])
    def test_truthy_confirmation_is_not_authorization(self):
        r={"schema":"fa3.tool-confirmation.v1","tool_id":"x","tool_args_digest":"sha256:x","required":1,"approved":True,"approval_receipt_ref":"a","authority":"FA3-AUTH-SECURITY-GOV-001_OR_AUTH-HUMAN"}
        with self.assertRaises(RuntimeSemanticsError): validate_tool_confirmation(r)
    def test_budget_exhaustion_fails_closed(self):
        l=make_execution_ledger({"max_model_requests":0,"max_tool_calls":1,"max_retries":0},max_transfer_hops=0)
        with self.assertRaises(RuntimeSemanticsError): consume_budget(l,"model_calls")
    def test_completed_resume_requires_digest_match(self):
        with self.assertRaises(RuntimeSemanticsError): plan_resume({"side_effecting":False},"COMPLETED",receipt_spec_digest="sha256:a",current_spec_digest="sha256:b")
    def test_mcp_unknown_top_level_extension_fails(self):
        with self.assertRaises(RuntimeSemanticsError): normalize_mcp_result({"content":[],"vendorExtension":True})
    def test_cross_thread_session_append_fails(self):
        with self.assertRaises(RuntimeSemanticsError): validate_session_append({"session_id":"s","thread_id":"t","state":"ACTIVE"},{"event_id":"e","session_id":"s","thread_id":"other"},set())
    def test_artifact_version_cannot_skip(self):
        with self.assertRaises(RuntimeSemanticsError): validate_artifact_write("out/a.bin",1,2,previous_version=1,requested_version=3)
if __name__=="__main__": unittest.main()
