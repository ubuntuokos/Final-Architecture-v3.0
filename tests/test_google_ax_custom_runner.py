from __future__ import annotations

import copy
import unittest

from fa3_google_ax_custom_runner import AxCustomRunnerError, compile_custom_runner_plan


class GoogleAxCustomRunnerTests(unittest.TestCase):
    def fixtures(self):
        task={
            "schema":"fa3.agent-workload-task.v1","task_id":"agent-task-1","root_task_id":"agent-task-1",
            "action_ref":"orchestration.execute","agent_definition_ref":"agent:def:1","workspace_refs":["workspace-1"],
            "resource_requirements":{"cpu_physical_cores":1},"network_envelope_ref":"net:1",
            "model_intent":{"capability":"coding","locality":"prefer_local"},"authorized_ai_participants":["agent:def:1"],
            "fanout_limits":{"max_children":2,"max_depth":1,"max_concurrent_children":1,"max_runtime_seconds":300,
                             "max_retries":1,"max_tool_calls":10,"max_model_requests":10}
        }
        workspace={"schema":"fa3.agent-workspace.v1","workspace_id":"workspace-1",
                   "sources":[{"kind":"GIT","repo":"https://github.com/example/repo.git","commit":"a"*40}],
                   "bootstrap_mode":"NONE"}
        envelope={"schema":"fa3.execution-network-envelope.v1","default":"DENY",
                  "egress":[{"host":"github.com","port":443}],"ingress":[],
                  "direct_model_provider_access":False,"direct_external_tool_access":False,"authority":False}
        binding={
            "schema":"fa3.google-ax-provider-binding.v1","provider_id":"FA3-PROVIDER-GOOGLE-AX-001","atespace":"fa3",
            "runner_image":"registry.example/fa3-ax-runner@sha256:"+"b"*64,
            "command":["fa3-google-ax-runner","execute"],"workspace_order":["workspace-1"],
            "workspace_paths":{"workspace-1":"/workspace/workspace-1"},"gateway_name":"agent-task-1-gateway",
            "resources":{"requests":{"cpu":"1","memory":"1Gi"}},"hrb_admission_ref":"hrb-auth:1",
            "resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","model_router_binding_ref":"model-route:1",
            "model_router_authority":"FA3-AUTH-MODEL-ROUTER-001","mcp_gateway_binding_ref":"mcp-session:1",
            "mcp_gateway_authority":"FA3-AUTH-MCP-GATEWAY-001","network_envelope_ref":"net:1","debug":False
        }
        return task,workspace,envelope,binding

    def test_immutable_git_materializes_inside_runner(self):
        task,workspace,envelope,binding=self.fixtures()
        plan=compile_custom_runner_plan(task,[workspace],envelope,binding)
        item=plan["workspace_materializations"][0]
        self.assertEqual(item["mode"],"IMMUTABLE_GIT_COMMIT")
        self.assertTrue(item["detached_checkout"])
        self.assertEqual(item["steps"][-1]["op"],"git_verify_head")
        self.assertFalse(plan["cluster_apply_ready"])
        self.assertFalse(plan["google_ax_runtime_promotion_claim"])

    def test_git_host_requires_explicit_egress(self):
        task,workspace,envelope,binding=self.fixtures()
        envelope["egress"]=[]
        with self.assertRaises(AxCustomRunnerError):
            compile_custom_runner_plan(task,[workspace],envelope,binding)

    def test_embedded_git_credentials_rejected(self):
        task,workspace,envelope,binding=self.fixtures()
        workspace["sources"][0]["repo"]="https://user:secret@github.com/example/repo.git"
        with self.assertRaises(AxCustomRunnerError):
            compile_custom_runner_plan(task,[workspace],envelope,binding)

    def test_skill_or_mcp_workspace_source_cannot_bypass_fabrics(self):
        task,workspace,envelope,binding=self.fixtures()
        for kind in ("SKILL","MCP_CAPABILITY"):
            bad=copy.deepcopy(workspace)
            bad["sources"]=[{"kind":kind,"ref":"x"}]
            with self.assertRaises(Exception):
                compile_custom_runner_plan(task,[bad],envelope,binding)

    def test_binding_authorities_remain_fa3_owned(self):
        task,workspace,envelope,binding=self.fixtures()
        plan=compile_custom_runner_plan(task,[workspace],envelope,binding)
        self.assertEqual(plan["authority_bindings"]["resources"],"FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertEqual(plan["authority_bindings"]["model_routing"],"FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(plan["authority_bindings"]["tool_mediation"],"FA3-AUTH-MCP-GATEWAY-001")


if __name__=="__main__":
    unittest.main()
