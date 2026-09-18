#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_os_context_policy import (  # noqa: E402
    AuthorizationError,
    effective_events,
    record_mcp_gateway_retrieval_audit,
    selective_erase,
    validate_mcp_gateway_receipt,
)
from fa3_os_runtime import (  # noqa: E402
    PolicyViolation,
    build_derived_projection,
    default_journal_path,
    ingest_event,
    normalize_capture_request,
    read_journal_events,
    utc_now,
)
from fa3_os_runtime_gate import gate as reference_gate  # noqa: E402

CONFORMANCE_ID = "FA3-OS-RUNTIME-CONFORMANCE-001"
EVIDENCE_SCHEMA = "fa3.os-runtime-current-host-evidence.v1"
TEST_PROJECT = "FA3-OS-CURRENT-HOST-ADMISSION"


def _git_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def _negative_privacy_tests(base: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    cases = [
        ("KEYLOGGER", {"capture_kind": "KEYLOGGER"}),
        ("CLIPBOARD", {"capture_kind": "CLIPBOARD"}),
        ("SCREENSHOT", {"capture_kind": "SCREENSHOT"}),
        ("TERMINAL_CONTENT", {"source_kind": "TERMINAL", "command": "cat ~/.ssh/id_rsa"}),
        ("PASSWORD_MANAGER", {"application_id": "keepassxc"}),
    ]
    for label, patch in cases:
        candidate = dict(base)
        candidate.update(patch)
        try:
            normalize_capture_request(candidate)
            failures.append(label)
        except PolicyViolation:
            pass
    return not failures, failures


def _control_center_smoke(binary: Path | None) -> tuple[bool, str]:
    candidates: list[Path] = []
    if binary is not None:
        candidates.append(binary)
    env_binary = os.environ.get("FA3_CONTROL_CENTER_BINARY")
    if env_binary:
        candidates.append(Path(env_binary))
    candidates.extend([
        ROOT / "build/fa3-control-center/fa3-control-center",
        ROOT / "build/fa3-os-current-host/fa3-control-center",
    ])
    which = shutil.which("fa3-control-center")
    if which:
        candidates.append(Path(which))
    selected = next((path for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)
    if selected is None:
        return False, "CONTROL_CENTER_BINARY_NOT_FOUND"

    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("QT_QUICK_BACKEND", "software")
    env.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    process = subprocess.Popen(
        [str(selected)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(2.0)
    rc = process.poll()
    if rc is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        return True, f"STARTED:{selected}"
    stdout, stderr = process.communicate(timeout=2)
    detail = (stderr or stdout or "").strip().replace("\n", " ")[:400]
    return rc == 0, f"EXIT={rc}:{detail}"


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _url_json(url: str, *, timeout: float = 1.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise RuntimeError(f"Non-object response from {url}")
    return value


def _post_json(url: str, payload: dict[str, Any], *, timeout: float = 3.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.load(exc)
        except Exception:
            detail = {"http_status": exc.code}
        raise RuntimeError(f"Gateway invocation denied: {detail}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Gateway invocation returned non-object receipt")
    return value


def _gateway_retrieval_e2e(
    *,
    project_id: str,
    workstream_id: str,
    session_id: str,
    run_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry_path = ROOT / "canonical/mcp-capability-registry.json"
    canonical_bytes_before = registry_path.read_bytes()
    canonical_sha_before = hashlib.sha256(canonical_bytes_before).hexdigest()
    registry = json.loads(canonical_bytes_before.decode("utf-8"))
    capability = next(
        (
            item
            for item in registry.get("capabilities", [])
            if isinstance(item, dict) and item.get("capability_id") == "fa3.memory.retrieve"
        ),
        None,
    )
    if capability is None:
        raise RuntimeError("Canonical MCP registry has no fa3.memory.retrieve capability")

    projected = json.loads(json.dumps(registry))
    projected_capability = next(
        item
        for item in projected["capabilities"]
        if item.get("capability_id") == "fa3.memory.retrieve"
    )
    providers = [
        item
        for item in projected_capability.get("providers", [])
        if not (
            isinstance(item, dict)
            and item.get("provider_id") == "FA3-OS-REFERENCE-RUNTIME-001"
            and item.get("adapter_id") == "fa3.adapter.fa3-os.memory.retrieve"
        )
    ]
    providers.append(
        {
            "provider_id": "FA3-OS-REFERENCE-RUNTIME-001",
            "adapter_id": "fa3.adapter.fa3-os.memory.retrieve",
            "state": "CONNECTED",
            "priority": 1,
            "transport": "native",
            "approval_override": "policy",
            "evidence_ref": "EPHEMERAL_CURRENT_HOST_ADMISSION_ONLY",
            "gate_id": "FA3-OS-RUNTIME-CURRENT-HOST-GATESET-001",
        }
    )
    projected_capability["providers"] = providers

    port = _free_loopback_port()
    with tempfile.TemporaryDirectory(prefix="fa3-os-mcp-admission-") as tmp:
        temp_registry = Path(tmp) / "mcp-capability-registry.json"
        temp_registry.write_text(json.dumps(projected, indent=2) + "\n", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env["FA3_MCP_ADAPTER_FACTORIES"] = "fa3_os_mcp_adapter:create_adapters"
        process = subprocess.Popen(
            [
                sys.executable,
                str(SRC / "fa3_mcp_gateway_server.py"),
                "--registry",
                str(temp_registry),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            health: dict[str, Any] | None = None
            readiness: dict[str, Any] | None = None
            last_error = ""
            for _ in range(60):
                if process.poll() is not None:
                    stdout, stderr = process.communicate(timeout=1)
                    raise RuntimeError(
                        "MCP gateway exited during admission startup: "
                        + (stderr or stdout or f"exit={process.returncode}")[-600:]
                    )
                try:
                    health = _url_json(base_url + "/healthz")
                    readiness = _url_json(base_url + "/readyz")
                    if readiness.get("ready") is True:
                        break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    time.sleep(0.1)
            else:
                raise RuntimeError(f"MCP gateway did not become ready: {last_error}")

            if health is None or health.get("authority") != "FA3-AUTH-MCP-GATEWAY-001":
                raise RuntimeError(f"Unexpected MCP gateway health authority: {health}")
            if readiness is None or readiness.get("ready") is not True:
                raise RuntimeError(f"MCP gateway admission projection not ready: {readiness}")

            request_id = f"FA3-OS-MCP-{run_id}"
            invocation = {
                "actor_id": "FA3-OS-CURRENT-HOST-ADMISSION",
                "client_id": "fa3-os-current-host-collector",
                "session_id": session_id,
                "capability_id": "fa3.memory.retrieve",
                "arguments": {
                    "project_id": project_id,
                    "workstream_id": workstream_id,
                    "limit": 20,
                },
                "policy_decision": {
                    "authority": registry.get("policy_authority"),
                    "status": "ALLOW",
                    "capability_id": "fa3.memory.retrieve",
                    "decision_id": request_id,
                },
            }
            receipt = _post_json(base_url + "/invoke", invocation)
            validate_mcp_gateway_receipt(receipt)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    canonical_bytes_after = registry_path.read_bytes()
    canonical_sha_after = hashlib.sha256(canonical_bytes_after).hexdigest()
    if canonical_bytes_after != canonical_bytes_before:
        raise RuntimeError("Canonical MCP registry changed during ephemeral admission projection")

    return receipt, {
        "mode": "CENTRAL_MCP_GATEWAY_EPHEMERAL_ADMISSION_BINDING",
        "authority": receipt.get("authority"),
        "capability": receipt.get("capability_id"),
        "provider_id": receipt.get("provider_id"),
        "adapter_id": receipt.get("adapter_id"),
        "result_status": receipt.get("result_status"),
        "reason_code": receipt.get("reason_code"),
        "request_sha256": receipt.get("request_sha256"),
        "canonical_registry_mutated": False,
        "canonical_registry_sha256_before": canonical_sha_before,
        "canonical_registry_sha256_after": canonical_sha_after,
        "global_gateway_promotion_claim": False,
    }



def _journal_contract_retention_ok() -> bool:
    path = ROOT / "canonical/contracts/FA3-JOURNAL-CONTRACTS-001.json"
    try:
        contracts = json.loads(path.read_text(encoding="utf-8"))["contracts"]["delete"]
    except Exception:
        return False
    return (
        contracts.get("event_delete") == "TOMBSTONE"
        and contracts.get("archive_delete") == "RETENTION_TRASH"
        and contracts.get("physical_purge") == "POLICY_OR_ADMIN_ONLY"
    )


def collect(*, output: Path, control_center_binary: Path | None) -> dict[str, Any]:
    journal = default_journal_path()
    run_id = str(uuid.uuid4()).upper()
    workstream_id = f"FA3-OS-ADMISSION-WS-{run_id}"
    session_id = f"FA3-OS-ADMISSION-SESSION-{run_id}"
    artifact_id = f"FA3-OS-ADMISSION-ARTIFACT-{run_id}"
    base: dict[str, Any] = {
        "source_kind": "FA3_NATIVE",
        "capture_kind": "FA3_ADMISSION_EVENT",
        "action": "CURRENT_HOST_ADMISSION_PROBE",
        "subject": {"kind": "VIRTUAL_ARTIFACT", "reference": f"fa3://admission/{artifact_id}"},
        "application_id": "FA3 OS Current Host Admission",
        "project_id": TEST_PROJECT,
        "session_id": session_id,
        "workstream_id": workstream_id,
        "artifact_id": artifact_id,
        "provenance": {"source_class": "FA3_NATIVE", "source_reference": "fa3-os-current-host-collector"},
        "confidence": 1.0,
        "tags": ["CURRENT_HOST_ADMISSION", "RETENTION:EPHEMERAL_TEST"],
        "summary": "FA3 OS harmless current-host admission probe",
    }

    checks: dict[str, bool] = {
        "reference_runtime_gate_pass": False,
        "actual_journal_append_verified": False,
        "privacy_negative_tests_passed": False,
        "deterministic_projection_verified": False,
        "control_center_smoke_passed": False,
        "selective_erasure_retention_verified": False,
        "gateway_authorization_verified": False,
        "retrieval_audit_verified": False,
    }
    details: dict[str, Any] = {}
    event_id = ""

    try:
        reference = reference_gate(ROOT)
        checks["reference_runtime_gate_pass"] = reference.get("result") == "PASS"
        details["reference_gate"] = reference.get("result")

        privacy_ok, privacy_failures = _negative_privacy_tests(base)
        checks["privacy_negative_tests_passed"] = privacy_ok
        details["privacy_negative_failures"] = privacy_failures

        ingest = ingest_event(base, journal)
        event_id = str(ingest.get("event_id", ""))
        raw = read_journal_events(journal)
        checks["actual_journal_append_verified"] = bool(event_id and any(row.get("id") == event_id for row in raw))

        projection = build_derived_projection(journal)
        workstream_ok = any(row.get("id") == workstream_id and event_id in row.get("event_ids", []) for row in projection.get("workstreams", []))
        session_ok = any(row.get("session_id") == session_id and event_id in row.get("event_ids", []) for row in projection.get("sessions", []))
        checks["deterministic_projection_verified"] = workstream_ok and session_ok

        gateway_receipt, gateway_detail = _gateway_retrieval_e2e(
            project_id=TEST_PROJECT,
            workstream_id=workstream_id,
            session_id=session_id,
            run_id=run_id,
        )
        details["gateway_authorization"] = gateway_detail
        checks["gateway_authorization_verified"] = True
        retrieval = record_mcp_gateway_retrieval_audit(
            journal,
            gateway_receipt=gateway_receipt,
            purpose="FA3 OS current-host retrieval admission",
            project_id=TEST_PROJECT,
        )
        audit_id = str(retrieval.get("audit_event_id", ""))
        raw_after_retrieval = read_journal_events(journal)
        checks["retrieval_audit_verified"] = (
            event_id in retrieval.get("source_event_refs", [])
            and bool(audit_id)
            and any(row.get("id") == audit_id and row.get("event_type") == "AUDIT" for row in raw_after_retrieval)
        )

        gui_ok, gui_detail = _control_center_smoke(control_center_binary)
        checks["control_center_smoke_passed"] = gui_ok
        details["control_center_smoke"] = gui_detail

        erasure = selective_erase(
            journal,
            scope={"kind": "artifact", "value": artifact_id},
            actor="FA3 OS Current Host Admission",
            reason="Ephemeral admission probe retention cleanup",
            request_id=f"FA3-OS-ERASE-{run_id}",
        )
        raw_after = read_journal_events(journal)
        effective_after = effective_events(journal)
        original_preserved = any(row.get("id") == event_id for row in raw_after)
        tombstone_present = any(row.get("event_type") == "TOMBSTONE" and row.get("target_event_id") == event_id for row in raw_after)
        hidden_from_effective = not any(row.get("id") == event_id for row in effective_after)
        checks["selective_erasure_retention_verified"] = (
            erasure.get("matched_event_count") == 1
            and original_preserved
            and tombstone_present
            and hidden_from_effective
            and _journal_contract_retention_ok()
        )
        details["erasure_target_count"] = erasure.get("matched_event_count")
    except Exception as exc:
        details["collector_exception"] = f"{type(exc).__name__}: {exc}"
        if event_id:
            try:
                selective_erase(
                    journal,
                    scope={"kind": "event_id", "value": event_id},
                    actor="FA3 OS Current Host Admission",
                    reason="Admission probe emergency cleanup",
                )
            except Exception as cleanup_exc:
                details["cleanup_exception"] = f"{type(cleanup_exc).__name__}: {cleanup_exc}"

    passed = all(checks.values())
    receipt = {
        "schema": EVIDENCE_SCHEMA,
        "conformance_id": CONFORMANCE_ID,
        "result": "PASS" if passed else "FAIL",
        "captured_at": utc_now(),
        "repository_head": _git_head(ROOT),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "node": platform.node(),
            "uid": os.getuid() if hasattr(os, "getuid") else None,
        },
        "journal_path": str(journal),
        "journal_is_actual_default_path": journal == default_journal_path(),
        **checks,
        "details": details,
        "production_admitted": passed,
        "status": "CURRENT_HOST_PASS" if passed else "PENDING_CURRENT_HOST",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real FA3 OS current-host admission evidence")
    parser.add_argument("--output", default=str(ROOT / "evidence/receipts/fa3-os-runtime-current-host.json"))
    parser.add_argument("--control-center-binary")
    args = parser.parse_args()
    receipt = collect(
        output=Path(args.output),
        control_center_binary=Path(args.control_center_binary) if args.control_center_binary else None,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
