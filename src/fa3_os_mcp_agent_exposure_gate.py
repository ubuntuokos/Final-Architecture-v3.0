#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-OS-MCP-AGENT-EXPOSURE-GATESET-001"
CONFORMANCE_ID = "FA3-OS-MCP-AGENT-EXPOSURE-CONFORMANCE-001"
CAPABILITY_ID = "fa3.memory.retrieve"
PROVIDER_ID = "FA3-OS-REFERENCE-RUNTIME-001"
ADAPTER_ID = "fa3.adapter.fa3-os.memory.retrieve"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def validate_current_host_evidence(receipt: dict[str, Any], *, root: Path, conformance_status: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if receipt.get("schema") != "fa3.os-mcp-agent-exposure-current-host-evidence.v1":
        findings.append(finding("FA3-OS-MCP-HOST-001", "Current-host evidence schema mismatch"))
    if receipt.get("conformance_id") != CONFORMANCE_ID or receipt.get("gate_id") != GATE_ID:
        findings.append(finding("FA3-OS-MCP-HOST-002", "Current-host evidence binding mismatch"))
    if receipt.get("result") != "PASS":
        findings.append(finding("FA3-OS-MCP-HOST-003", "Current-host evidence is not PASS"))
    try:
        captured = dt.datetime.fromisoformat(str(receipt.get("captured_at", "")).replace("Z", "+00:00"))
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=dt.timezone.utc)
        age = dt.datetime.now(dt.timezone.utc) - captured.astimezone(dt.timezone.utc)
        if age < dt.timedelta(0) or age > dt.timedelta(hours=24):
            raise ValueError("stale")
    except Exception:
        findings.append(finding("FA3-OS-MCP-HOST-004", "Current-host evidence timestamp is stale or invalid"))
    try:
        head = __import__("subprocess").check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        head = "UNKNOWN"
    if receipt.get("repository_head") != head:
        findings.append(finding("FA3-OS-MCP-HOST-005", "Current-host evidence is not bound to repository HEAD"))
    checks = receipt.get("checks", {})
    required = (
        "persistent_service_active",
        "persistent_service_enabled",
        "service_restart_verified",
        "unix_socket_0600_verified",
        "gateway_authority_verified",
        "gateway_readiness_verified",
        "non_agent_cgroup_denied",
        "wrong_actor_denied",
        "unscoped_retrieval_denied",
        "scoped_agent_retrieval_passed",
        "provider_binding_verified",
        "source_event_retrieved",
        "journal_audit_verified",
        "minimized_projection_verified",
        "global_promotion_not_claimed",
        "canonical_registry_unchanged",
        "installer_coexistence_controls_verified",
        "legacy_unit_adoption_safe",
    )
    for key in required:
        if not isinstance(checks, dict) or checks.get(key) is not True:
            findings.append(finding("FA3-OS-MCP-HOST-006", "Required current-host evidence flag missing", flag=key))
    if conformance_status == "CURRENT_HOST_ADMITTED":
        if receipt.get("status") != "CURRENT_HOST_PASS" or receipt.get("canonical_binding_state") != "CONNECTED" or receipt.get("service_left_enabled") is not True:
            findings.append(finding("FA3-OS-MCP-HOST-007", "Admitted exposure requires live CONNECTED persistent service evidence"))
    elif receipt.get("status") != "CANDIDATE_PASS":
        findings.append(finding("FA3-OS-MCP-HOST-008", "Pending exposure requires candidate current-host PASS"))
    if receipt.get("global_promotion_claim") is not False:
        findings.append(finding("FA3-OS-MCP-HOST-009", "Component evidence improperly claims global promotion"))
    return findings


def gate(root: Path, *, receipt_path: Path | None = None, require_evidence: bool = False) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    conformance = loadj(root / "canonical/FA3-OS-MCP-AGENT-EXPOSURE-CONFORMANCE-001.json")
    runtime = loadj(root / "canonical/FA3-OS-RUNTIME-CONFORMANCE-001.json")
    registry = loadj(root / "canonical/mcp-capability-registry.json")

    if runtime.get("status") != "CURRENT_HOST_ADMITTED" or runtime.get("production_admitted") is not True:
        findings.append(finding("FA3-OS-MCP-001", "FA3 OS runtime is not current-host admitted"))
    if conformance.get("id") != CONFORMANCE_ID or conformance.get("gate_id") != GATE_ID:
        findings.append(finding("FA3-OS-MCP-002", "Agent-exposure conformance identity drift"))
    if conformance.get("promotion_claimed") is not False:
        findings.append(finding("FA3-OS-MCP-003", "Agent exposure may not claim global promotion"))

    capability = next((x for x in registry.get("capabilities", []) if x.get("capability_id") == CAPABILITY_ID), None)
    if not isinstance(capability, dict):
        findings.append(finding("FA3-OS-MCP-004", "fa3.memory.retrieve capability missing"))
        binding = None
    else:
        binding = next((x for x in capability.get("providers", []) if x.get("provider_id") == PROVIDER_ID), None)
    if not isinstance(binding, dict):
        findings.append(finding("FA3-OS-MCP-005", "FA3 OS memory provider binding missing"))
    else:
        expected = {
            "adapter_id": ADAPTER_ID,
            "policy_mode": "external_resolver",
            "require_scoped_arguments": True,
            "require_policy_purpose": True,
            "receipt_audit_required": True,
        }
        for key, value in expected.items():
            if binding.get(key) != value:
                findings.append(finding("FA3-OS-MCP-006", "Provider binding contract drift", field=key))
        scope = binding.get("identity_scope", {})
        if scope.get("actor_prefixes") != ["FA3-AGENT-"] or scope.get("client_ids") != ["fa3-agent-runtime"]:
            findings.append(finding("FA3-OS-MCP-007", "Agent identity scope drift"))

        status = conformance.get("status")
        if status == "PENDING_CURRENT_HOST":
            if binding.get("state") != "PENDING_CURRENT_HOST":
                findings.append(finding("FA3-OS-MCP-008", "Pending conformance must keep provider binding non-CONNECTED"))
            if conformance.get("agent_exposure_admitted") is not False or conformance.get("evidence_present") is not False:
                findings.append(finding("FA3-OS-MCP-009", "Pending conformance must remain fail-closed"))
        elif status == "CURRENT_HOST_ADMITTED":
            evidence_ref = str(conformance.get("evidence_ref", ""))
            if binding.get("state") != "CONNECTED":
                findings.append(finding("FA3-OS-MCP-010", "Admitted conformance requires CONNECTED binding"))
            if not evidence_ref or not (root / evidence_ref).is_file():
                findings.append(finding("FA3-OS-MCP-011", "Durable agent-exposure evidence reference missing"))
            if binding.get("evidence_ref") != evidence_ref:
                findings.append(finding("FA3-OS-MCP-012", "Registry/evidence reference mismatch"))
            if conformance.get("agent_exposure_admitted") is not True or conformance.get("production_binding_connected") is not True:
                findings.append(finding("FA3-OS-MCP-013", "Admitted conformance missing exposure/binding flags"))
        else:
            findings.append(finding("FA3-OS-MCP-014", "Unknown agent-exposure conformance status", status=status))

    required_files = [
        "src/fa3_security_policy_plane.py",
        "src/fa3_os_mcp_adapter.py",
        "deployment/mcp-gateway/fa3-mcp-gateway-user.service.in",
        "bin/fa3-os-mcp-agent-exposure-install",
    ]
    for rel in required_files:
        if not (root / rel).is_file():
            findings.append(finding("FA3-OS-MCP-015", "Required persistent exposure artifact missing", path=rel))

    if require_evidence:
        path = receipt_path or (root / "evidence/receipts/fa3-os-mcp-agent-exposure-current-host.json")
        if not path.is_absolute():
            path = root / path
        try:
            receipt = loadj(path)
            findings.extend(validate_current_host_evidence(receipt, root=root, conformance_status=str(conformance.get("status"))))
        except Exception as exc:
            findings.append(finding("FA3-OS-MCP-HOST-000", "Current-host evidence missing or unreadable", error=repr(exc)))

    return {
        "schema":"fa3.os-mcp-agent-exposure-gate-report.v1",
        "gate_id":GATE_ID,
        "conformance_id":CONFORMANCE_ID,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "agent_exposure_status":conformance.get("status"),
        "global_promotion_claim":False,
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--require-evidence", action="store_true")
    parser.add_argument("--receipt")
    args=parser.parse_args()
    report=gate(Path(args.repo_root), receipt_path=Path(args.receipt) if args.receipt else None, require_evidence=args.require_evidence)
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report["result"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
