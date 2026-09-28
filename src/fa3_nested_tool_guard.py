#!/usr/bin/env python3
"""FA3-native, fail-closed pre-launch compiler for mediated nested OCI tools.

Inspired by publicly documented Clampdown containment patterns. No upstream
Clampdown source is copied. This compiles a bounded plan; it does not execute
Podman, attest the host, create an egress lease, or promote a runner.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")
TASK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
TARGET = re.compile(r"^/workspace/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
HEX = re.compile(r"^[0-9a-f]{64}$")
REQUEST_FIELDS = frozenset({"schema", "task_id", "image", "command", "workspace_target"})


class NestedToolPolicyError(ValueError):
    """A request cannot cross the existing FA3 sandbox admission boundary."""


def _required(condition: bool, code: str) -> None:
    if not condition:
        raise NestedToolPolicyError(code)


def _safe_path(path: object, code: str) -> Path:
    _required(isinstance(path, str) and path.startswith("/")
              and not any(c in path for c in ",\n\r\0"), code)
    try:
        value = Path(path).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise NestedToolPolicyError(code) from exc
    _required(value.is_dir() and not value.is_symlink()
              and not any(c in str(value) for c in ",\n\r\0"), code)
    return value


def compile_nested_tool_run(request: dict[str, Any], admission: dict[str, Any]) -> dict[str, Any]:
    """Compile argv from trusted admission, never from arbitrary Podman flags.

    The UAF/runner must validate authenticity, freshness, scope and signatures
    of *admission* before calling this function. Production execution remains
    disabled until separate current-host kernel/runtime evidence passes.
    """
    _required(isinstance(request, dict) and set(request) == REQUEST_FIELDS,
              "NTO-001_UNRECOGNIZED_OR_MISSING_REQUEST_FIELDS")
    _required(request.get("schema") == "fa3.nested-tool-request.v1"
              and isinstance(request.get("task_id"), str)
              and TASK.fullmatch(request["task_id"]) is not None,
              "NTO-002_INVALID_TASK")
    image = request.get("image")
    _required(isinstance(image, str) and IMAGE.fullmatch(image) is not None,
              "NTO-003_UNPINNED_IMAGE")
    command = request.get("command")
    _required(isinstance(command, list) and bool(command)
              and all(isinstance(x, str) and x and "\0" not in x for x in command),
              "NTO-004_INVALID_COMMAND")
    target = request.get("workspace_target")
    _required(isinstance(target, str) and TARGET.fullmatch(target) is not None,
              "NTO-005_INVALID_WORKSPACE_TARGET")

    # Admission is produced by the existing FA3 authorities, never the agent.
    _required(isinstance(admission, dict)
              and admission.get("scope_task_id") == request["task_id"]
              and admission.get("security_authority") == "FA3-AUTH-SECURITY-GOV-001"
              and admission.get("action_authority") == "FA3-UNIFIED-ACTION-FABRIC-001"
              and admission.get("tool_authority") == "FA3-AUTH-MCP-GATEWAY-001"
              and admission.get("resource_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001",
              "NTO-006_AUTHORITY_SCOPE_MISMATCH")
    _required(admission.get("runner_backend") == "GVISOR"
              and admission.get("rootless") is True
              and admission.get("runtime_compatibility_evidence") == "PASS"
              and admission.get("explicit_runtime_admission") is True
              and admission.get("ephemeral_workspace") is True,
              "NTO-007_ISOLATION_OR_ADMISSION_MISSING")
    _required(admission.get("network_mode") == "DENY"
              and admission.get("egress") == []
              and admission.get("direct_mcp_bypass") is False
              and admission.get("podman_socket_visible") is False
              and admission.get("host_processes_visible") is False
              and admission.get("host_home_visible") is False
              and admission.get("secret_delivery") == "NONE",
              "NTO-008_NETWORK_SOCKET_OR_SECRET_EXPOSURE")
    _required(admission.get("image") == image
              and admission.get("workspace_target") == target
              and admission.get("rootfs_readonly") is True
              and admission.get("cap_drop") == "ALL"
              and admission.get("no_new_privileges") is True
              and admission.get("privileged") is False
              and admission.get("namespace_policy") == "PRIVATE",
              "NTO-009_UNSAFE_CONTAINER_POLICY")
    lease = admission.get("hrb_lease_ref")
    _required(isinstance(lease, str) and bool(lease.strip()),
              "NTO-010_MISSING_HRB_LEASE")
    cpu = admission.get("cpu_quota")
    memory = admission.get("memory_bytes")
    pids = admission.get("pids_limit")
    _required(isinstance(cpu, (int, float)) and not isinstance(cpu, bool)
              and 0 < cpu <= 1024 and isinstance(memory, int) and not isinstance(memory, bool)
              and 16 * 1024 * 1024 <= memory <= 2**50
              and isinstance(pids, int) and not isinstance(pids, bool)
              and 1 <= pids <= 4096,
              "NTO-011_INVALID_HRB_RESOURCE_PROJECTION")

    # Re-resolve immediately before launch; trusted UAF must own this root and
    # prevent a path swap between validation and Podman's bind-mount operation.
    root = _safe_path(admission.get("approved_ephemeral_root"), "NTO-012_INVALID_ROOT")
    source = _safe_path(admission.get("workspace_source"), "NTO-013_INVALID_WORKSPACE")
    _required(source != root and os.path.commonpath((str(source), str(root))) == str(root),
              "NTO-014_WORKSPACE_OUTSIDE_APPROVED_ROOT")
    seccomp = admission.get("seccomp_path")
    expected_hash = admission.get("seccomp_sha256")
    _required(isinstance(seccomp, str) and seccomp.startswith("/")
              and isinstance(expected_hash, str) and HEX.fullmatch(expected_hash) is not None,
              "NTO-015_SECCOMP_PROFILE_UNPINNED")
    seccomp_path = Path(seccomp)
    _required(seccomp_path.is_file() and not seccomp_path.is_symlink()
              and seccomp_path.resolve(strict=True) == seccomp_path
              and hashlib.sha256(seccomp_path.read_bytes()).hexdigest() == expected_hash,
              "NTO-016_SECCOMP_PROFILE_MISMATCH")
    try:
        seccomp_data = json.loads(seccomp_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise NestedToolPolicyError("NTO-016_INVALID_SECCOMP_JSON") from exc
    _required(isinstance(seccomp_data, dict)
              and seccomp_data.get("defaultAction") in
              {"SCMP_ACT_ERRNO", "SCMP_ACT_KILL", "SCMP_ACT_KILL_PROCESS"},
              "NTO-016_SECCOMP_DEFAULT_ALLOW_FORBIDDEN")
    _required(not any(c in str(seccomp_path) for c in ",\n\r\0"),
              "NTO-017_UNSAFE_SECCOMP_PATH")

    argv = [
        "podman", "run", "--rm", "--pull=never", "--runtime=runsc",
        "--userns=keep-id", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--security-opt=seccomp=" + str(seccomp_path),
        "--read-only", "--network=none", "--pid=private", "--ipc=private",
        "--uts=private", "--cgroupns=private",
        "--pids-limit=" + str(pids), "--memory=" + str(memory),
        "--cpus=" + str(cpu), "--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=64m",
        "--mount=type=bind,src=" + str(source) + ",dst=" + target + ",rw",
        "--workdir=" + target, "--", image, *command,
    ]
    plan_digest = hashlib.sha256(
        json.dumps(argv, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return {
        "schema": "fa3.nested-tool-launch-plan.v1",
        "task_id": request["task_id"],
        "backend": "GVISOR",
        "argv": argv,
        "hrb_lease_ref": lease,
        "plan_sha256": plan_digest,
        "network": "DENY",
        "direct_runtime_socket": False,
        "secret_delivery": "NONE",
        "non_authoritative": True,
        "current_host_production_promotion_claim": False,
    }


def static_regression_pair() -> tuple[bool, bool]:
    """Pure reference-gate cases, not host sandbox/LSM evidence."""
    with tempfile.TemporaryDirectory(prefix="fa3-nto-") as folder:
        root = Path(folder)
        ws = root / "task-workspace"
        ws.mkdir()
        profile = root / "seccomp.json"
        profile.write_text('{"defaultAction":"SCMP_ACT_ERRNO"}', encoding="utf-8")
        request = {
            "schema": "fa3.nested-tool-request.v1",
            "task_id": "task-1",
            "image": "example.invalid/tool@sha256:" + "a" * 64,
            "command": ["/bin/true"],
            "workspace_target": "/workspace/project",
        }
        admission = {
            "scope_task_id": "task-1",
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
            "image": request["image"],
            "workspace_target": request["workspace_target"],
            "rootfs_readonly": True,
            "cap_drop": "ALL",
            "no_new_privileges": True,
            "privileged": False,
            "namespace_policy": "PRIVATE",
            "hrb_lease_ref": "reference-only-hrb-lease",
            "cpu_quota": 1,
            "memory_bytes": 128 * 1024 * 1024,
            "pids_limit": 64,
            "approved_ephemeral_root": str(root),
            "workspace_source": str(ws),
            "seccomp_path": str(profile),
            "seccomp_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
        }
        positive = (compile_nested_tool_run(request, admission)["backend"] == "GVISOR")
        rejected = True
        for key, value in (
            ("network_mode", "ALLOW"),
            ("podman_socket_visible", True),
            ("privileged", True),
            ("runner_backend", "HARDENED_ROOTLESS_OCI"),
            ("seccomp_sha256", "0" * 64),
        ):
            try:
                compile_nested_tool_run(request, {**admission, key: value})
            except NestedToolPolicyError:
                pass
            else:
                rejected = False
        try:
            compile_nested_tool_run({**request, "podman_flags": ["--privileged"]}, admission)
        except NestedToolPolicyError:
            pass
        else:
            rejected = False
    return positive, rejected
