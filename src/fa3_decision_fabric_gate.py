#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-DECISION-FABRIC-001"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path}")
    return data


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    required = [
        "canonical/profiles/FA3-DECISION-FABRIC-001.json",
        "canonical/profiles/FA3-CONTEXT-SELECTION-001.json",
        "canonical/profiles/FA3-EXTERNAL-PROJECT-RADAR-001.json",
        "canonical/contracts/FA3-DECISION-FABRIC-CONTRACTS-001.json",
        "canonical/providers/FA3-PROVIDER-DECISION-RULES-001.json",
        "canonical/providers/FA3-PROVIDER-DECISION-LOCAL-001.json",
        "canonical/providers/FA3-PROVIDER-JEV-DECISION-001.json",
        "canonical/decisions/FA3-DEC-JEV-CONSOLIDATION-2026-09-23.json",
        "canonical/decisions/FA3-DEC-JEV-ADOPTION-RULE-2026-09-23.json",
        "canonical/decision-fabric-enforcement.json",
        "src/fa3_decision_fabric.py",
        "src/fa3_context_selection.py",
        "src/fa3_external_project_radar.py",
        "src/fa3_jev_decision_provider.py",
        "src/fa3_decision_adapters.py",
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append(finding("DECISION-000", "required materialization missing", path=rel))

    if findings:
        return {
            "schema": "fa3.decision-fabric-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": findings,
            "global_promotion_claim": False,
        }

    profile = load(root / "canonical/profiles/FA3-DECISION-FABRIC-001.json")
    contracts = load(root / "canonical/contracts/FA3-DECISION-FABRIC-CONTRACTS-001.json")
    enforcement = load(root / "canonical/decision-fabric-enforcement.json")
    jev = load(root / "canonical/providers/FA3-PROVIDER-JEV-DECISION-001.json")
    decision = load(root / "canonical/decisions/FA3-DEC-JEV-CONSOLIDATION-2026-09-23.json")

    if profile.get("architectural_authority") is not False or profile.get("authority_delta") != 0:
        findings.append(finding("DECISION-001", "Decision Fabric must not become an architectural authority"))
    if profile.get("capability_count") != 143 or profile.get("capability_delta") != 0:
        findings.append(finding("DECISION-002", "capability baseline drift"))
    if profile.get("mandatory_jev_dependency") is not False or profile.get("mandatory_cloud_dependency") is not False:
        findings.append(finding("DECISION-003", "Jev/cloud must remain optional"))
    result_contract = contracts.get("result", {})
    if result_contract.get("authority_must_be_false") is not True or result_contract.get("candidate_set_expanded_must_be_false") is not True:
        findings.append(finding("DECISION-004", "result contract authority/candidate boundary drift"))
    security = contracts.get("security", {})
    for key in (
        "may_grant_permission", "may_expand_scope", "may_create_agent",
        "may_admit_model", "may_admit_provider", "may_obtain_secret",
        "may_obtain_hrb_lease",
    ):
        if security.get(key) is not False:
            findings.append(finding("DECISION-005", "security boundary drift", field=key))
    rules = enforcement.get("rules", {})
    required_rules = {
        "direct_application_jev_call": "DENY",
        "candidate_set_expansion": "DENY",
        "direct_secret_access": "DENY",
        "direct_hrb_lease": "DENY",
        "direct_tool_execution": "DENY",
        "model_router_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "mcp_authority": "FA3-AUTH-MCP-GATEWAY-001",
        "resource_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "silent_local_to_cloud_fallback": "DENY",
    }
    for key, expected in required_rules.items():
        if rules.get(key) != expected:
            findings.append(finding("DECISION-006", "enforcement drift", field=key, expected=expected, actual=rules.get(key)))
    if jev.get("mandatory") is not False or jev.get("direct_application_calls") != "DENY":
        findings.append(finding("DECISION-007", "Jev provider boundary drift"))
    if jev.get("physical_model_pin") is not False or jev.get("silent_local_to_cloud_fallback") != "DENY":
        findings.append(finding("DECISION-008", "Jev pin/fallback drift"))
    if decision.get("new_architectural_authorities") != 0 or decision.get("capability_count_after") != 143:
        findings.append(finding("DECISION-009", "canonical decision baseline drift"))

    # Direct TypeSafe network calls are allowed only inside the optional provider adapter
    # and immutable research snapshots. Applications must cross the Decision Fabric.
    for base in ("src", "apps", "bin"):
        for path in (root / base).rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".cpp", ".h", ".qml", ".sh"} and path.parent.name != "bin":
                continue
            rel = path.relative_to(root).as_posix()
            if rel == "src/fa3_jev_decision_provider.py":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "api.typesafe.ai" in text or "TYPESAFE_API_KEY" in text:
                findings.append(finding("DECISION-010", "direct application/provider Jev path detected", path=rel))

    return {
        "schema": "fa3.decision-fabric-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": 143,
        "authority_delta": 0,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="reports/decision-fabric-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root)
    report = gate(root)
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
