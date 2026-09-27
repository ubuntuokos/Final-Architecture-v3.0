#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_mcp_unix_client import request as unix_request  # noqa: E402
from fa3_os_runtime import default_journal_path, ingest_event, read_journal_events  # noqa: E402

CAPABILITY = "fa3.memory.retrieve"
PROVIDER = "FA3-OS-REFERENCE-RUNTIME-001"
ADAPTER = "fa3.adapter.fa3-os.memory.retrieve"
PROJECT = "FA3-OS-AGENT-EXPOSURE-ADMISSION"
WORKSTREAM = "FA3-OS-MCP-AGENT-EXPOSURE"


def _head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _binding(registry: dict[str, Any]) -> dict[str, Any]:
    cap = next(x for x in registry["capabilities"] if x.get("capability_id") == CAPABILITY)
    return next(x for x in cap["providers"] if x.get("provider_id") == PROVIDER)


def _wait_socket(socket_path: Path, timeout: float = 12.0) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            hs, health = unix_request(str(socket_path), "GET", "/healthz")
            rs, ready = unix_request(str(socket_path), "GET", "/readyz")
            if hs == 200 and rs == 200 and ready.get("ready") is True:
                return health, ready
            last = f"health={hs} ready={rs} {ready}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.2)
    raise RuntimeError("gateway did not become ready: " + last)


def _agent_invoke(socket_path: Path, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as fh:
        json.dump(payload, fh)
        request_file = fh.name
    try:
        cmd = [
            "systemd-run", "--user", "--wait", "--collect", "--pipe", "--quiet",
            "--slice=fa3-agent.slice",
            sys.executable, str(SRC / "fa3_mcp_unix_client.py"),
            "--socket", str(socket_path), "--method", "POST", "--path", "/invoke",
            "--request-file", request_file,
        ]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=20)
        if proc.returncode != 0:
            raise RuntimeError(f"agent service invocation failed rc={proc.returncode}: {proc.stderr[-500:]}")
        line = next((x for x in reversed(proc.stdout.splitlines()) if x.strip().startswith("{")), "")
        result = json.loads(line)
        return int(result["http_status"]), result["body"]
    finally:
        Path(request_file).unlink(missing_ok=True)


def _payload(
    *,
    actor: str = "FA3-AGENT-CURRENT-HOST-TEST",
    scoped: bool = True,
    project_id: str = PROJECT,
    workstream_id: str = WORKSTREAM,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {"limit": 20}
    if scoped:
        arguments.update({"project_id": project_id, "workstream_id": workstream_id})
    return {
        "actor_id": actor,
        "client_id": "fa3-agent-runtime",
        "session_id": "FA3-OS-MCP-CURRENT-HOST-SESSION",
        "capability_id": CAPABILITY,
        "arguments": arguments,
        "policy_request": {"purpose": "current-host agent context admission"},
    }


def collect(output: Path) -> dict[str, Any]:
    registry_path = ROOT / "canonical/mcp-capability-registry.json"
    registry_bytes = registry_path.read_bytes()
    registry_sha = hashlib.sha256(registry_bytes).hexdigest()
    registry = json.loads(registry_bytes.decode("utf-8"))
    canonical_binding = _binding(registry)
    source_state = canonical_binding.get("state")
    if source_state not in {"PENDING_CURRENT_HOST", "CONNECTED"}:
        raise RuntimeError(f"unsupported canonical binding state: {source_state}")

    runtime_registry = json.loads(json.dumps(registry))
    candidate = _binding(runtime_registry)
    candidate["state"] = "CONNECTED"
    candidate["evidence_ref"] = candidate.get("evidence_ref") or "CURRENT_HOST_ADMISSION_TRANSIENT"

    journal = default_journal_path()
    journal.parent.mkdir(parents=True, exist_ok=True)
    run_scope = f"{time.time_ns():x}-{os.getpid():x}"
    project_id = f"{PROJECT}-{run_scope}"
    workstream_id = f"{WORKSTREAM}-{run_scope}"
    event = ingest_event(
        {
            "source_kind": "FA3_NATIVE",
            "capture_kind": "APPLICATION_EVENT",
            "action": "AGENT_EXPOSURE_ADMISSION",
            "subject": {"kind": "WORKSTREAM", "reference": workstream_id},
            "application_id": "FA3 Current Host Admission",
            "project_id": project_id,
            "session_id": "FA3-OS-MCP-ADMISSION",
            "workstream_id": workstream_id,
            "artifact_id": "FA3-OS-MCP-ADMISSION-EVENT",
            "provenance": {"source_class": "FA3_NATIVE", "source_reference": "agent-exposure-collector"},
            "confidence": 1.0,
            "tags": ["CURRENT_HOST", "MCP_AGENT_EXPOSURE"],
        },
        journal,
    )
    event_id = event["event_id"]

    with tempfile.TemporaryDirectory(prefix="fa3-os-mcp-admission-") as tmp:
        temp_registry = Path(tmp) / "registry.json"
        temp_registry.write_text(json.dumps(runtime_registry, indent=2) + "\n", encoding="utf-8")
        install_registry = registry_path if source_state == "CONNECTED" else temp_registry
        subprocess.run(
            ["bash", str(ROOT / "bin/fa3-os-mcp-agent-exposure-install"), "--registry", str(install_registry), "--start"],
            cwd=ROOT, check=True, timeout=30,
        )

    state_root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "fa3/mcp-gateway"
    install_receipt = json.loads((state_root / "install-success-receipt.json").read_text(encoding="utf-8"))
    ownership_transition = install_receipt.get("ownership_transition")
    install_control_ok = (
        install_receipt.get("schema") == "fa3.mcp-gateway-install-success-receipt.v1"
        and install_receipt.get("component_id") == "FA3-MCP-GATEWAY-001"
        and ownership_transition in {"NO_ADOPTION", "LEGACY_BYTE_EQUIVALENT_ADOPTION"}
        and install_receipt.get("previous_state_captured") is True
        and install_receipt.get("conflict_detection") == "FAIL_CLOSED"
        and install_receipt.get("legacy_adoption_policy") == "BYTE_EQUIVALENT_ONLY"
        and install_receipt.get("rollback_mechanism") is True
        and install_receipt.get("recovery_evidence_materialized") is True
        and install_receipt.get("upstream_resources_modified") is False
    )

    socket_path = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "fa3/mcp-gateway.sock"
    health, readiness = _wait_socket(socket_path)
    socket_mode = stat.S_IMODE(socket_path.stat().st_mode)

    direct_status, direct_body = unix_request(
        str(socket_path), "POST", "/invoke",
        _payload(project_id=project_id, workstream_id=workstream_id),
    )
    wrong_status, wrong_body = _agent_invoke(
        socket_path,
        _payload(actor="NOT-AN-FA3-AGENT", project_id=project_id, workstream_id=workstream_id),
    )
    scope_status, scope_body = _agent_invoke(socket_path, _payload(scoped=False))
    ok_status, ok_body = _agent_invoke(
        socket_path,
        _payload(project_id=project_id, workstream_id=workstream_id),
    )

    result = ok_body.get("result", {}) if isinstance(ok_body, dict) else {}
    audit_id = str(result.get("audit_event_id", ""))
    rows = read_journal_events(journal)
    audit_ok = any(
        row.get("id") == audit_id
        and row.get("event_type") == "AUDIT"
        and "MCP_GATEWAY_MEDIATED" in row.get("tags", [])
        for row in rows
    )

    subprocess.run(["systemctl", "--user", "restart", "fa3-mcp-gateway.service"], check=True, timeout=15)
    health_after, ready_after = _wait_socket(socket_path)
    service_active = subprocess.run(["systemctl", "--user", "is-active", "--quiet", "fa3-mcp-gateway.service"]).returncode == 0
    service_enabled = subprocess.run(["systemctl", "--user", "is-enabled", "--quiet", "fa3-mcp-gateway.service"]).returncode == 0

    checks = {
        "persistent_service_active": service_active,
        "persistent_service_enabled": service_enabled,
        "service_restart_verified": ready_after.get("ready") is True,
        "unix_socket_0600_verified": socket_mode == 0o600,
        "gateway_authority_verified": health.get("authority") == "FA3-AUTH-MCP-GATEWAY-001",
        "gateway_readiness_verified": readiness.get("ready") is True,
        "non_agent_cgroup_denied": direct_status == 403 and direct_body.get("reason_code") == "POLICY_DENY",
        "wrong_actor_denied": wrong_status == 403 and wrong_body.get("reason_code") == "POLICY_DENY",
        "unscoped_retrieval_denied": scope_status == 403 and scope_body.get("reason_code") == "POLICY_DENY",
        "scoped_agent_retrieval_passed": ok_status == 200 and ok_body.get("result_status") == "success",
        "provider_binding_verified": ok_body.get("provider_id") == PROVIDER and ok_body.get("adapter_id") == ADAPTER,
        "source_event_retrieved": event_id in result.get("source_event_refs", []),
        "journal_audit_verified": audit_ok,
        "minimized_projection_verified": result.get("projection_mode") == "MINIMIZED_AGENT_CONTEXT",
        "global_promotion_not_claimed": ok_body.get("global_promotion_claim") is False,
        "canonical_registry_unchanged": hashlib.sha256(registry_path.read_bytes()).hexdigest() == registry_sha,
        "installer_coexistence_controls_verified": install_control_ok,
        "legacy_unit_adoption_safe": ownership_transition in {"NO_ADOPTION", "LEGACY_BYTE_EQUIVALENT_ADOPTION"},
    }
    passed = all(checks.values())

    receipt = {
        "schema": "fa3.os-mcp-agent-exposure-current-host-evidence.v1",
        "conformance_id": "FA3-OS-MCP-AGENT-EXPOSURE-CONFORMANCE-001",
        "gate_id": "FA3-OS-MCP-AGENT-EXPOSURE-GATESET-001",
        "result": "PASS" if passed else "FAIL",
        "status": "CURRENT_HOST_PASS" if passed and source_state == "CONNECTED" else "CANDIDATE_PASS" if passed else "FAIL",
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "repository_head": _head(),
        "canonical_binding_state": source_state,
        "service_left_enabled": source_state == "CONNECTED" and passed,
        "host": {"node": os.uname().nodename, "system": os.uname().sysname, "release": os.uname().release, "machine": os.uname().machine},
        "socket_path": str(socket_path),
        "installer_ownership_transition": ownership_transition,
        "installer_recovery_receipt": str(state_root / "install-success-receipt.json"),
        "checks": checks,
        "gateway_health": health_after,
        "gateway_readiness": ready_after,
        "invocation_receipt": ok_body,
        "global_promotion_claim": False,
        "agent_exposure_scope": {"actor_prefix": "FA3-AGENT-", "client_id": "fa3-agent-runtime", "cgroup": "fa3-agent.slice"},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if source_state != "CONNECTED":
        subprocess.run(["bash", str(ROOT / "bin/fa3-os-mcp-agent-exposure-install"), "--stop"], cwd=ROOT, check=False)

    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/fa3-os-mcp-agent-exposure/current-host.json")
    args = parser.parse_args()
    receipt = collect(Path(args.output))
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
