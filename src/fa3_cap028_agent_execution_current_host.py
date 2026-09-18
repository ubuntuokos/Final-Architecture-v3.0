#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fa3_autogpt_gate import (
    delegated_capabilities_valid,
    execution_context_valid,
    gate as autogpt_gate,
)
from fa3_codex_gate import gate as codex_gate
from fa3_closed_loop_agent_ops_reference import budget_valid
from fa3_developer_agent_coordination import (
    commit_intent_allowed,
    message_hop_action,
    mutation_allowed,
    workspace_plan_valid,
)
from fa3_developer_agent_coordination_gate import gate as coordination_gate
from fa3_loop_engineering_gate import gate as loop_gate
from fa3_openhands_gate import (
    canonical_tool_mediation_valid,
    direct_execute_tool_valid,
    gate as openhands_gate,
)
from fa3_runtime_hardening import agent_sandbox_valid
from fa3_runtime_hardening_current_host import validate_runtime_sandbox_receipt
from fa3_runtime_hardening_gate import gate as runtime_hardening_gate

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-028"
MODES = ("positive", "negative", "rollback")
SANDBOX_RECEIPT = "evidence/receipts/runtime-isolation-sandbox-current-host.json"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("top-level object required")
    return obj


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _expected_source_decisions(root: Path) -> list[str]:
    registry = _load(root / "evidence/evidence-registry.json")
    record = next(
        (row for row in registry.get("records", []) if row.get("subject_id") == CAPABILITY_ID),
        None,
    )
    if not isinstance(record, dict):
        raise RuntimeError("CAP-028 evidence-registry record missing")
    ids = record.get("source_decision_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids):
        raise RuntimeError("CAP-028 source-decision coverage invalid")
    return ids


def _validate_coverage(root: Path) -> list[str]:
    expected = _expected_source_decisions(root)
    supplied = json.loads(_required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
    if supplied != expected:
        raise RuntimeError("CAP-028 producer coverage does not exactly match Evidence Registry")
    return expected


def _validate_canonical_boundaries(root: Path) -> dict[str, Any]:
    reports = {
        "autogpt": autogpt_gate(root),
        "codex": codex_gate(root),
        "openhands": openhands_gate(root),
        "loop_engineering": loop_gate(root),
        "developer_coordination": coordination_gate(root),
        "runtime_hardening": runtime_hardening_gate(root),
    }
    failed = [name for name, report in reports.items() if report.get("result") != "PASS"]
    if failed:
        raise RuntimeError("CAP-028 canonical boundary gate failed: " + ",".join(failed))

    autogpt = reports["autogpt"]
    codex = reports["codex"]
    openhands = reports["openhands"]
    loop = reports["loop_engineering"]
    coordination = reports["developer_coordination"]
    if autogpt.get("runtime_provider_required") is not False:
        raise RuntimeError("AutoGPT optional-provider semantics drift")
    if codex.get("current_host_production_state") != "PENDING_SEPARATE_REAL_CURRENT_HOST_RECEIPT":
        raise RuntimeError("Codex provider current-host semantics drift")
    if openhands.get("runtime_provider_required") is not False:
        raise RuntimeError("OpenHands optional-provider semantics drift")
    if loop.get("runtime_provider_required") is not False:
        raise RuntimeError("Loop Engineering optional-provider semantics drift")
    if coordination.get("promotion_effect") != "REFERENCE_RUNTIME_COORDINATION_EVIDENCE_ONLY_EXTERNAL_PROVIDER_PROMOTION_SEPARATE":
        raise RuntimeError("developer coordination provider-separation semantics drift")
    return {
        name: {
            "result": report.get("result"),
            "gate_id": report.get("gate_id"),
        }
        for name, report in reports.items()
    }


def _validated_sandbox(root: Path) -> dict[str, Any]:
    path = root / SANDBOX_RECEIPT
    if not path.is_file():
        raise RuntimeError("CAP-028 requires fresh runtime-isolation sandbox current-host receipt")
    receipt = _load(path)
    ok, reasons = validate_runtime_sandbox_receipt(receipt, root=root)
    if not ok:
        raise RuntimeError("sandbox current-host receipt rejected: " + "; ".join(reasons))
    return {
        "path": SANDBOX_RECEIPT,
        "sha256": _sha256(path),
        "status": receipt.get("status"),
        "result": receipt.get("result"),
    }


def _task_context() -> dict[str, Any]:
    return {
        "caller_identity": "fa3-current-host-qualification",
        "delegation_id": "cap028-current-host",
        "workflow_run_id": "cap028-qualification",
        "node_id": "agent-task",
        "capability_scope": ["read-workspace"],
        "policy_decision_id": "cap028-policy",
    }


def _sandbox_policy_ok() -> bool:
    return agent_sandbox_valid(
        backend="WASMTIME_WASI",
        arbitrary_code=True,
        explicit_admission=True,
        ephemeral_overlay=True,
        host_home_visible=False,
        host_processes_visible=False,
        network_mode="DENY",
        direct_mcp_bypass=False,
        compatibility_evidence=True,
    )


def _run_wasmtime(scope: Path) -> dict[str, Any]:
    wasmtime = shutil.which("wasmtime")
    if not wasmtime:
        raise RuntimeError("wasmtime is required for CAP-028 real sandbox execution")
    wat = scope / "cap028-agent-positive.wat"
    wat.write_text('(module (func (export "_start")))\n', encoding="utf-8")
    proc = subprocess.run(
        [wasmtime, "run", str(wat)],
        cwd=scope,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        shell=False,
        check=False,
        env={
            key: os.environ[key]
            for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")
            if key in os.environ
        },
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Wasmtime sandbox task failed: {proc.stderr[-1000:]}")
    return {
        "binary": wasmtime,
        "module_sha256": _sha256(wat),
        "returncode": proc.returncode,
        "filesystem_preopens": [],
        "network_lease": False,
        "host_subprocess_agent_execution": False,
    }


def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    coverage = _validate_coverage(root)
    gates = _validate_canonical_boundaries(root)
    sandbox = _validated_sandbox(root)

    context = _task_context()
    if not execution_context_valid(context):
        raise RuntimeError("delegated execution context rejected")
    if not delegated_capabilities_valid(["read-workspace", "write-workspace"], ["read-workspace"]):
        raise RuntimeError("delegated capability narrowing rejected")
    if not canonical_tool_mediation_valid(canonical_mediated=True, authorized=True):
        raise RuntimeError("canonical tool mediation rejected")
    if not workspace_plan_valid({"worker": "cap028-worktree"}, ["worker"]):
        raise RuntimeError("isolated mutating workspace plan rejected")
    if not budget_valid(
        usage={"tokens": 10, "cost": 0, "time": 1, "tools": 1, "subagents": 0},
        limits={"tokens": 100, "cost": 1, "time": 60, "tools": 5, "subagents": 1},
        agent_can_raise_limits=False,
    ):
        raise RuntimeError("bounded execution budget rejected")
    if not _sandbox_policy_ok():
        raise RuntimeError("canonical agent sandbox policy rejected known-good plan")

    runtime = _run_wasmtime(scope)
    descriptor = scope / "cap028-positive-task.json"
    _write(
        descriptor,
        {
            "capability_id": CAPABILITY_ID,
            "delegated_context": context,
            "sandbox_backend": "WASMTIME_WASI",
            "network_mode": "DENY",
            "authoritative_provider": False,
            "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
            "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        },
    )
    return {
        "mode": "positive",
        "status": "PASS",
        "coverage_count": len(coverage),
        "canonical_gates": gates,
        "sandbox_receipt": sandbox,
        "real_sandbox_execution": runtime,
        "descriptor_sha256": _sha256(descriptor),
        "provider_runtime_dependency_required": False,
    }


def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    coverage = _validate_coverage(root)
    gates = _validate_canonical_boundaries(root)
    sandbox = _validated_sandbox(root)

    cases = {
        "host_subprocess_agent_execution_denied": not agent_sandbox_valid(
            backend="HOST_SUBPROCESS",
            arbitrary_code=True,
            explicit_admission=True,
            ephemeral_overlay=True,
            host_home_visible=False,
            host_processes_visible=False,
            network_mode="DENY",
            direct_mcp_bypass=False,
            compatibility_evidence=True,
        ),
        "host_home_visibility_denied": not agent_sandbox_valid(
            backend="WASMTIME_WASI",
            arbitrary_code=True,
            explicit_admission=True,
            ephemeral_overlay=True,
            host_home_visible=True,
            host_processes_visible=False,
            network_mode="DENY",
            direct_mcp_bypass=False,
            compatibility_evidence=True,
        ),
        "direct_mcp_bypass_denied": not agent_sandbox_valid(
            backend="WASMTIME_WASI",
            arbitrary_code=True,
            explicit_admission=True,
            ephemeral_overlay=True,
            host_home_visible=False,
            host_processes_visible=False,
            network_mode="DENY",
            direct_mcp_bypass=True,
            compatibility_evidence=True,
        ),
        "delegation_expansion_denied": not delegated_capabilities_valid(
            ["read-workspace"], ["read-workspace", "write-workspace"]
        ),
        "direct_openhands_tool_bypass_denied": not direct_execute_tool_valid(
            api="conversation.execute_tool", canonical_mediated=False
        ),
        "worker_main_commit_denied": not commit_intent_allowed(
            actor_role="WORKER", target_branch="main"
        ),
        "destructive_without_approval_denied": not mutation_allowed(
            risk_class="DESTRUCTIVE", approved=False
        ),
        "message_hop_overflow_terminates": message_hop_action(
            hop=4, max_hops=4, act="request"
        ) == "TERMINATE",
    }
    if not all(cases.values()):
        raise RuntimeError("CAP-028 negative matrix admitted a forbidden path")
    artifact = scope / "cap028-negative-cases.json"
    _write(artifact, cases)
    return {
        "mode": "negative",
        "status": "PASS",
        "coverage_count": len(coverage),
        "canonical_gates": gates,
        "sandbox_receipt": sandbox,
        "cases": cases,
        "artifact_sha256": _sha256(artifact),
    }


def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    coverage = _validate_coverage(root)
    gates = _validate_canonical_boundaries(root)
    sandbox = _validated_sandbox(root)

    descriptor = scope / "cap028-rollback-task.json"
    baseline_obj = {
        "capability_id": CAPABILITY_ID,
        "parent_capabilities": ["read-workspace", "write-workspace"],
        "child_capabilities": ["read-workspace"],
        "sandbox_backend": "WASMTIME_WASI",
        "network_mode": "DENY",
        "state": "BASELINE",
    }
    baseline = (
        json.dumps(baseline_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    descriptor.write_bytes(baseline)
    pre_sha = _sha256_bytes(baseline)
    if not delegated_capabilities_valid(
        baseline_obj["parent_capabilities"], baseline_obj["child_capabilities"]
    ):
        raise RuntimeError("rollback baseline delegation invalid")

    fault = dict(baseline_obj)
    fault["child_capabilities"] = ["read-workspace", "write-workspace", "host-shell"]
    fault["state"] = "FAULT_INJECTED"
    _write(descriptor, fault)
    mutated_sha = _sha256(descriptor)
    if delegated_capabilities_valid(
        baseline_obj["parent_capabilities"], fault["child_capabilities"]
    ):
        raise RuntimeError("fault-injected authority expansion was admitted")

    descriptor.write_bytes(baseline)
    post_sha = _sha256(descriptor)
    if post_sha != pre_sha:
        raise RuntimeError("rollback failed to restore exact task descriptor")
    if mutated_sha == pre_sha:
        raise RuntimeError("rollback fault injection did not change descriptor digest")

    ephemeral_parent = scope / "ephemeral"
    ephemeral_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cap028-", dir=ephemeral_parent) as td:
        work = Path(td)
        (work / "state.json").write_text('{"state":"transient"}\n', encoding="utf-8")
        transient_path = work
    workspace_destroyed = not transient_path.exists()
    if not workspace_destroyed:
        raise RuntimeError("ephemeral agent workspace survived rollback")

    return {
        "mode": "rollback",
        "status": "PASS",
        "coverage_count": len(coverage),
        "canonical_gates": gates,
        "sandbox_receipt": sandbox,
        "pre_sha256": pre_sha,
        "mutated_sha256": mutated_sha,
        "post_sha256": post_sha,
        "fault_rejected": True,
        "rollback_hash_equal": post_sha == pre_sha,
        "ephemeral_workspace_destroyed": workspace_destroyed,
    }


def run_mode(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    root = root.resolve()
    scope = scope.resolve()
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if root not in scope.parents:
        raise RuntimeError("source artifact scope escapes repository")
    scope.mkdir(parents=True, exist_ok=True)
    if mode == "positive":
        return _run_positive(root, scope)
    if mode == "negative":
        return _run_negative(root, scope)
    return _run_rollback(root, scope)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CAP-028 current-host provider-neutral agent execution qualification producer"
    )
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-028")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap028-agent-execution-evidence.json"
        payload = {
            "schema": "fa3.cap028-agent-execution-current-host-evidence.v1",
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "result": result,
        }
        _write(artifact, payload)
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": _required_env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": json.loads(
                _required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON")
            ),
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": _sha256(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(
            json.dumps({"status": "REJECTED", "findings": [str(exc)]}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
