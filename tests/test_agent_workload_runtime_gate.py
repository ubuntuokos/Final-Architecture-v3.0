import copy
import unittest
from pathlib import Path

from src.fa3_agent_workload import WorkloadContractError, project_to_ax, resume_requirements, validate_task
from src.fa3_agent_workload_gate import gate, regression_cases

ROOT=Path(__file__).resolve().parents[1]

class AgentWorkloadRuntimeTests(unittest.TestCase):
    def test_reference_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual("PASS",report["result"],report.get("findings"))

    def test_regressions_pass(self):
        self.assertEqual("PASS",regression_cases()["result"])

    def test_direct_physical_model_pin_is_rejected(self):
        task={"schema":"fa3.agent-workload-task.v1","task_id":"t","root_task_id":"t","action_ref":"orchestration.execute",
              "agent_definition_ref":"a","resource_requirements":{},"network_envelope_ref":"n",
              "model_intent":{"provider_id":"direct"},"authorized_ai_participants":["a"],
              "fanout_limits":{"max_children":1,"max_depth":1,"max_concurrent_children":1,"max_runtime_seconds":60,"max_retries":0,"max_tool_calls":1,"max_model_requests":1}}
        with self.assertRaises(WorkloadContractError):
            validate_task(task)

if __name__=="__main__":
    unittest.main()
