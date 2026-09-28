import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from fa3_nested_tool_guard import (
    NestedToolPolicyError, compile_nested_tool_run, static_regression_pair,
)


class NestedToolGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fa3-nested-tool-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "scratch"
        self.workspace.mkdir()
        self.profile = self.root / "seccomp.json"
        self.profile.write_text('{"defaultAction":"SCMP_ACT_ERRNO"}', encoding="utf-8")
        self.request = {
            "schema": "fa3.nested-tool-request.v1",
            "task_id": "work-123",
            "image": "registry.invalid/tool@sha256:" + "b" * 64,
            "command": ["/bin/true"],
            "workspace_target": "/workspace/task",
        }
        self.admission = {
            "scope_task_id": self.request["task_id"],
            "security_authority": "FA3-AUTH-SECURITY-GOV-001",
            "action_authority": "FA3-UNIFIED-ACTION-FABRIC-001",
            "tool_authority": "FA3-AUTH-MCP-GATEWAY-001",
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "runner_backend": "GVISOR",
            "rootless": True,
            "runtime_compatibility_evidence": "PASS",
            "explicit_runtime_admission": True,
            "ephemeral_workspace": True,
            "network_mode": "DENY",
            "egress": [],
            "direct_mcp_bypass": False,
            "podman_socket_visible": False,
            "host_processes_visible": False,
            "host_home_visible": False,
            "secret_delivery": "NONE",
            "image": self.request["image"],
            "workspace_target": self.request["workspace_target"],
            "rootfs_readonly": True,
            "cap_drop": "ALL",
            "no_new_privileges": True,
            "privileged": False,
            "namespace_policy": "PRIVATE",
            "hrb_lease_ref": "lease-work-123",
            "cpu_quota": 1,
            "memory_bytes": 128 * 1024 * 1024,
            "pids_limit": 64,
            "approved_ephemeral_root": str(self.root),
            "workspace_source": str(self.workspace),
            "seccomp_path": str(self.profile),
            "seccomp_sha256": hashlib.sha256(self.profile.read_bytes()).hexdigest(),
        }

    def test_reference_static_regressions(self):
        self.assertEqual((True, True), static_regression_pair())

    def test_safe_launch_is_gvisor_only_and_does_not_execute(self):
        result = compile_nested_tool_run(self.request, self.admission)
        self.assertEqual("GVISOR", result["backend"])
        self.assertFalse(result["current_host_production_promotion_claim"])
        self.assertEqual("DENY", result["network"])
        self.assertFalse(result["direct_runtime_socket"])
        argv = result["argv"]
        self.assertIn("--runtime=runsc", argv)
        self.assertIn("--network=none", argv)
        self.assertIn("--cap-drop=ALL", argv)
        self.assertIn("--read-only", argv)
        self.assertIn("--pull=never", argv)
        self.assertIn("--security-opt=no-new-privileges", argv)
        self.assertFalse(any(arg.startswith("--device") for arg in argv))
        self.assertFalse(any(arg.startswith("--env") for arg in argv))
        self.assertEqual(self.request["image"], argv[-2])
        self.assertEqual(self.request["command"][0], argv[-1])

    def test_policy_mutations_fail_closed(self):
        mutations = (
            ("scope_task_id", "other-task"),
            ("security_authority", "OTHER"),
            ("action_authority", "DIRECT"),
            ("tool_authority", "OTHER"),
            ("resource_authority", "OTHER"),
            ("runner_backend", "HARDENED_ROOTLESS_OCI"),
            ("rootless", False),
            ("runtime_compatibility_evidence", "PENDING"),
            ("explicit_runtime_admission", False),
            ("ephemeral_workspace", False),
            ("network_mode", "ALLOW"),
            ("egress", [{"host": "example.com", "port": 443}]),
            ("direct_mcp_bypass", True),
            ("podman_socket_visible", True),
            ("host_processes_visible", True),
            ("host_home_visible", True),
            ("secret_delivery", "ENV"),
            ("image", "another-image"),
            ("workspace_target", "/"),
            ("rootfs_readonly", False),
            ("cap_drop", "NONE"),
            ("no_new_privileges", False),
            ("privileged", True),
            ("namespace_policy", "HOST"),
            ("hrb_lease_ref", ""),
            ("cpu_quota", 0),
            ("memory_bytes", -1),
            ("pids_limit", 0),
            ("seccomp_sha256", "a" * 64),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                with self.assertRaises(NestedToolPolicyError):
                    compile_nested_tool_run(self.request, {**self.admission, key: value})

    def test_untrusted_docker_or_podman_flags_not_admitted(self):
        for added in (
            {"privileged": True},
            {"cap_add": ["SYS_ADMIN"]},
            {"mounts": [{"source": "/home", "target": "/home"}]},
            {"podman_flags": ["--network=host"]},
            {"env": {"API_KEY": "should-not-appear"}},
        ):
            with self.subTest(added=added):
                with self.assertRaises(NestedToolPolicyError):
                    compile_nested_tool_run({**self.request, **added}, self.admission)

    def test_unpinned_image_and_bad_task_rejected(self):
        for k, v in (("image", "ubuntu:latest"),
                     ("image", "repo@sha256:123"),
                     ("task_id", "../escape"),
                     ("workspace_target", "/proc")):
            with self.subTest(k=k, v=v), self.assertRaises(NestedToolPolicyError):
                compile_nested_tool_run({**self.request, k: v}, self.admission)

    def test_ephemeral_workspace_cannot_escape_root(self):
        outside = self.root.parent
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(
                self.request, {**self.admission, "workspace_source": str(outside)}
            )
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(
                self.request, {**self.admission, "workspace_source": str(self.root)}
            )

    def test_unverified_or_missing_seccomp_rejected(self):
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(
                self.request,
                {**self.admission, "seccomp_path": str(self.root / "missing.json")},
            )
        self.profile.write_text('{"defaultAction":"SCMP_ACT_ALLOW"}', encoding="utf-8")
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(self.request, self.admission)

    def test_reject_nonmapping_and_boolean_resource_injection(self):
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(None, self.admission)
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(self.request, {**self.admission, "cpu_quota": True})
        with self.assertRaises(NestedToolPolicyError):
            compile_nested_tool_run(self.request, {**self.admission, "memory_bytes": True})


if __name__ == "__main__":
    unittest.main()
