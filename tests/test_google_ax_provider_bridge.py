from __future__ import annotations

import copy
import unittest

from src.fa3_google_ax_provider import AxProviderBridgeError, compile_ax_provider_bridge


def task() -> dict:
    return {
        "schema": "fa3.agent-workload-task.v1",
        "task_id": "agent-task-1",
        "root_task_id": "agent-task-1",
        "action_ref": "orchestration.execute",
        "agent_definition_ref": "agent-def-1",
        "workspace_refs": ["workspace-1"],
        "resource_requirements": {"cpu_physical_cores": 1, "memory_gib": 1},
        "network_envelope_ref": "net-1",
        "model_intent": {"capability": "coding", "locality": "prefer_local"},
        "authorized_ai_participants": ["agent-def-1"],
        "fanout_limits": {
            "max_children": 2, "max_depth": 1, "max_concurrent_children": 1,
            "max_runtime_seconds": 300, "max_retries": 1, "max_tool_calls": 10, "max_model_requests": 10,
        },
    }


def workspace() -> dict:
    return {"schema": "fa3.agent-workspace.v1", "workspace_id": "workspace-1", "sources": [], "bootstrap_mode": "NONE"}


def network() -> dict:
    return {
        "schema": "fa3.execution-network-envelope.v1",
        "default": "DENY",
        "egress": [{"host": "router.fa3.internal", "port": 443}],
        "ingress": [],
        "direct_model_provider_access": False,
        "direct_external_tool_access": False,
        "authority": False,
    }


def binding() -> dict:
    return {
        "schema": "fa3.google-ax-provider-binding.v1",
        "provider_id": "FA3-PROVIDER-GOOGLE-AX-001",
        "atespace": "fa3",
        "runner_image": "registry.example/fa3-ax-runner@sha256:" + "a" * 64,
        "command": ["fa3-agent-runner", "--execute"],
        "workspace_order": ["workspace-1"],
        "workspace_paths": {"workspace-1": "/workspace/workspace-1"},
        "gateway_name": "agent-task-1-gateway",
        "resources": {"requests": {"cpu": "1", "memory": "1Gi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "hrb_admission_ref": "hrb-auth:1",
        "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "model_router_binding_ref": "model-route:1",
        "model_router_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "mcp_gateway_binding_ref": "mcp-session:1",
        "mcp_gateway_authority": "FA3-AUTH-MCP-GATEWAY-001",
        "network_envelope_ref": "net-1",
        "debug": False,
    }


class GoogleAxProviderBridgeTests(unittest.TestCase):
    def test_safe_subset_compiles_to_upstream_v1alpha1_without_model(self) -> None:
        result = compile_ax_provider_bridge(task(), [workspace()], network(), binding())
        self.assertEqual(result["schema"], "fa3.google-ax-provider-projection.v1")
        self.assertFalse(result["cluster_apply_ready"])
        self.assertEqual([m["kind"] for m in result["manifests"]], ["Workspace", "Gateway", "Task"])
        self.assertTrue(all(m["apiVersion"] == "ax.io/v1alpha1" for m in result["manifests"]))
        self.assertNotIn("Model", [m["kind"] for m in result["manifests"]])
        task_manifest = result["manifests"][-1]
        self.assertIn("@sha256:", task_manifest["spec"]["image"])
        self.assertFalse(task_manifest["spec"]["debug"])

    def test_immutable_git_commit_gap_fails_closed(self) -> None:
        ws = workspace()
        ws["sources"] = [{"kind": "GIT", "repo": "https://example.invalid/repo.git", "commit": "a" * 40}]
        with self.assertRaisesRegex(AxProviderBridgeError, "IMMUTABLE_GIT_COMMIT_UNREPRESENTABLE"):
            compile_ax_provider_bridge(task(), [ws], network(), binding())

    def test_ax_native_mcp_and_skill_discovery_are_not_authority_bypasses(self) -> None:
        for source in (
            {"kind": "SKILL", "skill_ref": "skill:x", "admission_profile": "FA3-SKILL-FABRIC-001"},
            {"kind": "MCP_CAPABILITY", "gateway_authority": "FA3-AUTH-MCP-GATEWAY-001"},
        ):
            ws = workspace()
            ws["sources"] = [source]
            with self.assertRaises(AxProviderBridgeError):
                compile_ax_provider_bridge(task(), [ws], network(), binding())

    def test_debug_and_floating_image_are_rejected(self) -> None:
        b = binding()
        b["debug"] = True
        with self.assertRaisesRegex(AxProviderBridgeError, "AX_DEBUG"):
            compile_ax_provider_bridge(task(), [workspace()], network(), b)
        b = binding()
        b["runner_image"] = "registry.example/fa3-ax-runner:latest"
        with self.assertRaisesRegex(AxProviderBridgeError, "IMMUTABLE_DIGEST"):
            compile_ax_provider_bridge(task(), [workspace()], network(), b)

    def test_network_wildcard_and_accelerator_projection_fail_closed(self) -> None:
        net = network()
        net["egress"] = [{"host": "*", "port": 443}]
        with self.assertRaisesRegex(AxProviderBridgeError, "WILDCARD"):
            compile_ax_provider_bridge(task(), [workspace()], net, binding())
        t = copy.deepcopy(task())
        t["resource_requirements"]["gpu.vram_gib"] = 8
        with self.assertRaisesRegex(AxProviderBridgeError, "ACCELERATOR_RESOURCE_UNREPRESENTABLE"):
            compile_ax_provider_bridge(t, [workspace()], network(), binding())


if __name__ == "__main__":
    unittest.main()
