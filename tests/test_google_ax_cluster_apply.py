from __future__ import annotations

import copy
import unittest

from src.fa3_google_ax_cluster_apply import AxClusterApplyError, compile_cluster_apply_plan


def projection() -> dict:
    return {
        "schema": "fa3.google-ax-provider-projection.v1",
        "provider_id": "FA3-PROVIDER-GOOGLE-AX-001",
        "upstream_commit": "e6211f84a9e30dd309304167b8f1d51cbdaf8dab",
        "google_ax_runtime_promotion_claim": False,
        "authority_bindings": {
            "resources": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
            "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        },
        "manifests": [
            {"apiVersion": "ax.io/v1alpha1", "kind": "Workspace", "metadata": {"name": "workspace-1"}, "spec": {}},
            {"apiVersion": "ax.io/v1alpha1", "kind": "Gateway", "metadata": {"name": "gateway-1"}, "spec": {}},
            {"apiVersion": "ax.io/v1alpha1", "kind": "Task", "metadata": {"name": "task-1"}, "spec": {"image": "registry.example/fa3-ax-runner@sha256:" + "a" * 64}},
        ],
    }


def runner_plan() -> dict:
    return {
        "schema": "fa3.google-ax-custom-runner-plan.v1",
        "provider_id": "FA3-PROVIDER-GOOGLE-AX-001",
        "upstream_commit": "e6211f84a9e30dd309304167b8f1d51cbdaf8dab",
        "runner_image": "registry.example/fa3-ax-runner@sha256:" + "a" * 64,
        "google_ax_runtime_promotion_claim": False,
        "authority_bindings": {
            "resources": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
            "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        },
    }


def evidence() -> dict:
    return {
        "schema": "fa3.google-ax-runner-image-evidence.v1",
        "runner_image": "registry.example/fa3-ax-runner@sha256:" + "a" * 64,
        "evidence_ref": "evidence:ax-runner-image:1",
        "build_verified": True,
        "digest_verified": True,
        "current_host_runtime_promotion_claim": False,
    }


def cluster() -> dict:
    return {
        "schema": "fa3.google-ax-cluster-binding.v1",
        "cluster_scope_ref": "cluster-scope:ax-test",
        "kubernetes_context_ref": "k8s-context:ax-test",
        "agent_substrate_ref": "agent-substrate:ax-test",
        "security_approval_ref": "security-approval:ax-test",
        "namespace": "fa3",
        "scope_bound": True,
        "debug_guest_services_authorized": False,
    }


class GoogleAxClusterApplyTests(unittest.TestCase):
    def test_plan_is_scope_bound_and_not_promotion(self) -> None:
        result = compile_cluster_apply_plan(projection(), runner_plan(), evidence(), cluster())
        self.assertTrue(result["cluster_apply_adapter_materialized"])
        self.assertFalse(result["runtime_promotion_eligible"])
        self.assertEqual(result["apply_order"], ["Workspace", "Gateway", "Task"])
        self.assertTrue(result["dry_run_required_before_apply"])
        self.assertFalse(result["google_ax_runtime_promotion_claim"])

    def test_missing_runner_evidence_fails_closed(self) -> None:
        bad = evidence()
        bad["build_verified"] = False
        with self.assertRaisesRegex(AxClusterApplyError, "EVIDENCE_NOT_VERIFIED"):
            compile_cluster_apply_plan(projection(), runner_plan(), bad, cluster())

    def test_raw_cluster_credentials_fail_closed(self) -> None:
        bad = cluster()
        bad["token"] = "secret"
        with self.assertRaisesRegex(AxClusterApplyError, "RAW_CREDENTIAL"):
            compile_cluster_apply_plan(projection(), runner_plan(), evidence(), bad)

    def test_model_resource_or_authority_drift_fails_closed(self) -> None:
        bad = projection()
        bad["manifests"][0]["kind"] = "Model"
        with self.assertRaises(AxClusterApplyError):
            compile_cluster_apply_plan(bad, runner_plan(), evidence(), cluster())
        bad = projection()
        bad["authority_bindings"]["model_routing"] = "AX"
        with self.assertRaisesRegex(AxClusterApplyError, "AUTHORITY_BINDING_MISMATCH"):
            compile_cluster_apply_plan(bad, runner_plan(), evidence(), cluster())


if __name__ == "__main__":
    unittest.main()
