#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-MCP-GATEWAY-001"
AUTHORITY_ID = "FA3-AUTH-MCP-GATEWAY-001"
GATE_ID = "FA3-GATE-MCP-GATEWAY-001"
MODERN_VERSION = "2026-07-28"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def validate(root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    required = {
        "profile": root / "canonical/profiles/FA3-MCP-GATEWAY-001.json",
        "contracts": root / "canonical/contracts/FA3-MCP-GATEWAY-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-CENTRAL-MCP-GATEWAY-2026-09-18.json",
        "reference": root / "canonical/references/FA3-MCP-GATEWAY-MICROSOFT-REFERENCE-2026-09-18.json",
        "gate": root / "canonical/FA3-GATE-MCP-GATEWAY-001.json",
        "enforcement": root / "canonical/mcp-gateway-enforcement.json",
        "gui": root / "canonical/FA3-MCP-GATEWAY-GUI-001.json",
        "current_host": root / "canonical/FA3-MCP-CURRENT-HOST-001.json",
        "registry": root / "canonical/mcp-capability-registry.json",
        "server": root / "src/fa3_mcp_gateway_server.py",
        "core": root / "src/fa3_mcp_gateway.py",
        "qml": root / "apps/fa3-control-center/qml/McpGatewayPage.qml",
        "service": root / "apps/fa3-control-center/src/McpGatewayService.cpp",
    }
    for name, path in required.items():
        if not path.exists():
            findings.append(finding("MCP-FINAL-000", "Required Central MCP Gateway artifact missing", artifact=name))
    if findings:
        return findings

    profile = loadj(required["profile"])
    contracts = loadj(required["contracts"])
    decision = loadj(required["decision"])
    reference = loadj(required["reference"])
    gate = loadj(required["gate"])
    enforcement = loadj(required["enforcement"])
    gui = loadj(required["gui"])
    current = loadj(required["current_host"])
    registry = loadj(required["registry"])

    checks = [
        (profile.get("id") == PROFILE_ID, "MCP-FINAL-001", "Canonical profile id mismatch"),
        (profile.get("authority") == AUTHORITY_ID, "MCP-FINAL-002", "Canonical authority mismatch"),
        (profile.get("status") == "CANONICAL", "MCP-FINAL-003", "Profile is not canonical"),
        (profile.get("capability_count") == 143 and profile.get("capability_delta") == 0, "MCP-FINAL-004", "Capability baseline changed"),
        (profile.get("authority_delta") == 0 and profile.get("new_architectural_authority") is False, "MCP-FINAL-005", "Authority delta is not zero"),
        (profile.get("canonical_transport", {}).get("revision") == MODERN_VERSION, "MCP-FINAL-006", "Modern protocol revision mismatch"),
        (profile.get("canonical_transport", {}).get("mode") == "STATELESS", "MCP-FINAL-007", "Canonical transport must be stateless"),
        (contracts.get("transport", {}).get("mcp_session_id") == "REJECT", "MCP-FINAL-008", "Modern MCP session id must be rejected"),
        (contracts.get("transport", {}).get("server_discover") is True, "MCP-FINAL-009", "server/discover must be supported"),
        (decision.get("status") == "FINAL", "MCP-FINAL-010", "Central MCP decision is not FINAL"),
        (decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0, "MCP-FINAL-011", "Decision changes baseline"),
        (reference.get("runtime_dependency") is False and reference.get("authority") is False, "MCP-FINAL-012", "Microsoft reference became a runtime authority"),
        (gate.get("fail_closed") is True, "MCP-FINAL-013", "Canonical gate is not fail-closed"),
        (enforcement.get("canonical_protocol") == MODERN_VERSION, "MCP-FINAL-014", "Enforcement protocol mismatch"),
        (current.get("parent_authority") == AUTHORITY_ID, "MCP-FINAL-015", "Current-host authority binding changed"),
        (registry.get("authority") == AUTHORITY_ID and registry.get("direct_agent_provider_bypass") == "DENY", "MCP-FINAL-016", "Registry authority/bypass invariant broken"),
        (gui.get("direct_qml_tool_invocation") is False and gui.get("gui_self_approval") is False, "MCP-FINAL-017", "GUI authority boundary broken"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(finding(code, message))

    server = required["server"].read_text(encoding="utf-8")
    for token in [
        'MODERN_PROTOCOL_VERSION = "2026-07-28"',
        '"/mcp"',
        '"server/discover"',
        '"tools/list"',
        '"tools/call"',
        '"MCP-Protocol-Version"',
        '"Mcp-Method"',
        '"Mcp-Name"',
        '"Mcp-Session-Id"',
        '"MCP_SESSION_ID_FORBIDDEN"',
    ]:
        if token not in server:
            findings.append(finding("MCP-FINAL-018", "Modern server contract token missing", token=token))

    qml = required["qml"].read_text(encoding="utf-8")
    for section in gui.get("sections", []):
        if section not in qml:
            findings.append(finding("MCP-FINAL-019", "GUI section missing", section=section))
    for forbidden in ["executeTool(", "directToolCall(", "selfApprove("]:
        if forbidden in qml:
            findings.append(finding("MCP-FINAL-020", "Direct GUI execution primitive found", token=forbidden))

    service = required["service"].read_text(encoding="utf-8")
    if "QNetworkAccessManager" not in service or "/healthz" not in service or "/capabilities" not in service:
        findings.append(finding("MCP-FINAL-021", "GUI service lacks read-only live gateway projection"))
    if "POST" in service or "sendCustomRequest" in service or "post(" in service:
        findings.append(finding("MCP-FINAL-022", "GUI gateway service must remain read-only"))

    return findings


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings = validate(root)
    report = {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": GATE_ID, "mode": "STATIC_CANONICAL"},
        "result": "PASS" if not findings else "BLOCKED",
        "decision": {
            "reason_code": "MCP_GATEWAY_CANONICAL_PASS" if not findings else "MCP_GATEWAY_CANONICAL_BLOCKED",
            "promotion_effect": "STATIC_CANONICAL_ONLY_CURRENT_HOST_PROMOTION_UNCHANGED",
            "exit_code": 0 if not findings else 2,
        },
        "findings": findings,
        "evidence_refs": [
            "canonical/profiles/FA3-MCP-GATEWAY-001.json",
            "canonical/contracts/FA3-MCP-GATEWAY-CONTRACTS-001.json",
            "canonical/decisions/FA3-DEC-CENTRAL-MCP-GATEWAY-2026-09-18.json",
            "canonical/FA3-MCP-GATEWAY-GUI-001.json",
        ],
        "capability_delta": 0,
        "authority_delta": 0,
        "global_promotion_claim": False,
    }
    out = root / "reports/mcp-gateway-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report["decision"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
