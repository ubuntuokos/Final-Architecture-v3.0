import unittest
from pathlib import Path
from src.fa3_adk2_runtime_gate import gate,regression_cases
from src.fa3_agent_runtime_semantics import RuntimeSemanticsError,consume_budget,make_execution_ledger,normalize_mcp_result,plan_resume,validate_artifact_write,validate_session_append,validate_tool_confirmation
from src.fa3_agent_workload import WorkloadContractError, compile_execution_plan
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
    def test_execution_plan_compiler_binds_task_graph_model_and_budget(self):
        task={"schema":"fa3.agent-workload-task.v1","task_id":"t","root_task_id":"t","action_ref":"orchestration.execute","agent_definition_ref":"a","workspace_refs":[],"resource_requirements":{},"network_envelope_ref":"n","model_intent":{"required_capabilities":["tools"]},"authorized_ai_participants":["a"],"fanout_limits":{"max_children":1,"max_depth":1,"max_concurrent_children":1,"max_runtime_seconds":60,"max_retries":1,"max_tool_calls":2,"max_model_requests":2},"provenance_refs":[]}
        graph={"schema":"fa3.agent-workflow-graph.v1","graph_id":"g","entry_node":"n1","yaml_is_canonical":False,"nodes":[{"node_id":"n1","kind":"AGENT","side_effecting":False}],"edges":[]}
        model={"schema":"fa3.model-capability-descriptor.v1","logical_model_id":"default","source":"PROVIDER_DECLARED","router_authority":"FA3-AUTH-MODEL-ROUTER-001","model_id_heuristic":False,"capabilities":{"tools":True,"structured_output":False,"media_input":False,"media_output":False,"streaming":True}}
        plan=compile_execution_plan(task,graph,model,task_spec_digest="sha256:t",max_transfer_hops=2)
        self.assertEqual("fa3.agent-execution-plan.v1",plan["schema"])
        self.assertEqual(2,plan["ledger"]["limits"]["transfer_hops"])
if __name__=="__main__": unittest.main()
