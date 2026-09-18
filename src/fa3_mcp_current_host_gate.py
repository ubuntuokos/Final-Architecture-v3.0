#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-MCP-CURRENT-HOST-001"
PROFILE_ID = "FA3-MCP-CURRENT-HOST-001"
AUTHORITY_ID = "FA3-AUTH-MCP-GATEWAY-001"
REGISTRY = Path("canonical/mcp-capability-registry.json")
RECEIPT = Path("evidence/receipts/mcp-current-host.json")
REQUIRED_DENIALS = {
    "UNKNOWN_IDENTITY",
    "UNKNOWN_CAPABILITY",
    "UNADMITTED_ADAPTER",
    "INVALID_SCHEMA",
    "MISSING_POLICY_DECISION",
    "MISSING_REQUIRED_APPROVAL",
    "MISSING_OR_INVALID_HRB_LEASE",
    "INLINE_SECRET_FORBIDDEN",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def validate_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if registry.get("schema") != "fa3.mcp.capability-registry.v1":
        findings.append(finding("MCP-STATIC-001", "Capability registry schema mismatch"))
    if registry.get("profile") != PROFILE_ID or registry.get("authority") != AUTHORITY_ID:
        findings.append(finding("MCP-STATIC-002", "Profile/authority binding mismatch"))
    if registry.get("fail_closed") is not True:
        findings.append(finding("MCP-STATIC-003", "Gateway registry is not fail-closed"))
    if registry.get("automatic_provider_activation") is not False:
        findings.append(finding("MCP-STATIC-004", "Automatic provider activation must be disabled"))
    if registry.get("direct_agent_provider_bypass") != "DENY":
        findings.append(finding("MCP-STATIC-005", "Direct agent-to-provider bypass must be DENY"))
    if registry.get("capability_delta") != 0 or registry.get("authority_delta") != 0:
        findings.append(finding("MCP-STATIC-006", "Current-host projection may not create capability/authority delta"))
    if not isinstance(registry.get("policy_authority"), str) or not registry.get("policy_authority", "").strip():
        findings.append(finding("MCP-STATIC-007", "External policy authority binding is missing"))
    if registry.get("canonical_gateway_profile") != "FA3-MCP-GATEWAY-001" or registry.get("canonical_protocol") != "2026-07-28":
        findings.append(finding("MCP-STATIC-016", "Final Central MCP Gateway modern protocol binding missing"))
    if registry.get("transport_session_state") is not False:
        findings.append(finding("MCP-STATIC-017", "Modern MCP transport session state must be disabled"))

    seen: set[str] = set()
    capabilities = registry.get("capabilities", [])
    if not isinstance(capabilities, list) or not capabilities:
        findings.append(finding("MCP-STATIC-008", "Capability registry is empty or malformed"))
        return findings
    for item in capabilities:
        if not isinstance(item, dict):
            findings.append(finding("MCP-STATIC-009", "Capability entry is not an object"))
            continue
        capability_id = item.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id.startswith("fa3.") or capability_id in seen:
            findings.append(finding("MCP-STATIC-010", "Capability id invalid or duplicated", capability_id=capability_id))
        else:
            seen.add(capability_id)
        if item.get("risk_class") not in {"R0", "R1", "R2", "R3", "R4"}:
            findings.append(finding("MCP-STATIC-011", "Capability risk class invalid", capability_id=capability_id))
        if item.get("approval") not in {"policy", "session", "explicit", "strong"}:
            findings.append(finding("MCP-STATIC-012", "Capability approval mode invalid", capability_id=capability_id))
        if not isinstance(item.get("providers"), list):
            findings.append(finding("MCP-STATIC-013", "Provider binding list malformed", capability_id=capability_id))
            continue
        for provider in item["providers"]:
            if not isinstance(provider, dict):
                findings.append(finding("MCP-STATIC-014", "Provider binding malformed", capability_id=capability_id))
                continue
            if provider.get("state") == "CONNECTED" and not provider.get("evidence_ref"):
                findings.append(finding(
                    "MCP-STATIC-015",
                    "CONNECTED provider lacks current-host E2E evidence reference",
                    capability_id=capability_id,
                    provider_id=provider.get("provider_id"),
                ))
    return findings


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if receipt.get("schema") != "fa3.mcp.current-host.evidence.v1":
        findings.append(finding("MCP-HOST-001", "Current-host evidence schema mismatch"))
    if receipt.get("profile_id") != PROFILE_ID or receipt.get("gate_id") != GATE_ID:
        findings.append(finding("MCP-HOST-002", "Current-host evidence binding mismatch"))
    if receipt.get("status") != "PASS":
        findings.append(finding("MCP-HOST-003", "Current-host MCP evidence does not claim PASS"))
    if receipt.get("global_promotion_claim") is not False:
        findings.append(finding("MCP-HOST-004", "Component evidence must not claim global FA3 promotion"))
    health = receipt.get("gateway_health", {})
    if not isinstance(health, dict) or health.get("status") != "ok" or health.get("authority") != AUTHORITY_ID:
        findings.append(finding("MCP-HOST-005", "Gateway health/authority evidence invalid"))
    readiness = receipt.get("gateway_readiness", {})
    if not isinstance(readiness, dict) or readiness.get("ready") is not True:
        findings.append(finding("MCP-HOST-006", "Gateway is not ready with an admitted CONNECTED adapter"))
    checks = receipt.get("checks", {})
    if not isinstance(checks, dict):
        checks = {}
    missing_denials = sorted(code for code in REQUIRED_DENIALS if checks.get(code) != "DENY")
    if missing_denials:
        findings.append(finding("MCP-HOST-007", "Required negative conformance denials missing", missing=missing_denials))
    for required in ("ADMITTED_PROVIDER_INVOCATION", "EVIDENCE_RECEIPT", "TIMEOUT_CANCELLATION", "AUTHORITY_NONREGRESSION", "MODERN_STATELESS_PROTOCOL", "HEADER_ROUTING"):
        if checks.get(required) != "PASS":
            findings.append(finding("MCP-HOST-008", "Required positive current-host check missing", check=required))
    return findings


def gate(root: Path, *, static_only: bool = False, receipt_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    try:
        registry = loadj(root / REGISTRY)
        findings.extend(validate_registry(registry))
    except Exception as exc:
        findings.append(finding("MCP-STATIC-000", "Capability registry missing or unreadable", error=repr(exc)))

    evidence_refs = [str(REGISTRY)]
    if not static_only and not findings:
        path = receipt_path or (root / RECEIPT)
        evidence_refs.append(str(path))
        try:
            findings.extend(validate_receipt(loadj(path)))
        except Exception as exc:
            findings.append(finding("MCP-HOST-000", "Current-host MCP evidence missing or unreadable", error=repr(exc)))

    result = "PASS" if not findings else "BLOCKED"
    report = {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": GATE_ID, "mode": "STATIC" if static_only else "CURRENT_HOST"},
        "result": result,
        "decision": {
            "reason_code": "MCP_STATIC_CONTRACT_PASS" if static_only and result == "PASS" else "MCP_CURRENT_HOST_PASS" if result == "PASS" else "MCP_CURRENT_HOST_BLOCKED",
            "promotion_effect": "COMPONENT_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
            "exit_code": 0 if result == "PASS" else 2,
        },
        "findings": findings,
        "evidence_refs": evidence_refs,
        "global_promotion_claim": False,
    }
    out = root / "reports/mcp-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FA3 Central MCP Gateway current-host closure")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--static", action="store_true")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    receipt = Path(args.receipt).resolve() if args.receipt else None
    report = gate(Path(args.root), static_only=args.static, receipt_path=receipt)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report["decision"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
