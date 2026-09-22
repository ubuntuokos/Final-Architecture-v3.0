#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_uaf import ActionRegistry, UafError
from fa3_release_baseline import load_active_release_baseline

GATE_ID = "FA3-UNIFIED-ACTION-FABRIC-GATESET-001"
PROFILE_ID = "FA3-UNIFIED-ACTION-FABRIC-001"
CONTRACT_ID = "FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001"
DECISION_ID = "FA3-DEC-UNIFIED-ACTION-FABRIC-2026-09-21"
FORBIDDEN_GLOBAL_HARDWARE_TOKENS = (
    "nvidia", "cuda", "rocm", "level zero", "oneapi",
    "zluda", "pci_bdf", "gpu sku",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, **details}


def validate(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    capability_count = load_active_release_baseline(root).capability_count
    required = {
        "profile": root / "canonical/profiles/FA3-UNIFIED-ACTION-FABRIC-001.json",
        "contract": root / "canonical/contracts/FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-UNIFIED-ACTION-FABRIC-2026-09-21.json",
        "gate": root / "canonical/FA3-GATE-UNIFIED-ACTION-FABRIC-001.json",
        "actions": root / "canonical/actions",
        "hardware_contract": root / "canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json",
        "resource_contract": root / "canonical/FA3-RESOURCE-ADMISSION-CONTRACTS-001.json",
        "secret_contract": root / "canonical/contracts/FA3-SECRET-BROKER-CONTRACTS-001.json",
        "mcp_contract": root / "canonical/contracts/FA3-MCP-GATEWAY-CONTRACTS-001.json",
        "evidence_contract": root / "canonical/FA3-EVIDENCE-ENVELOPE-001.json",
    }
    for name, path in required.items():
        if name == "actions":
            if not path.is_dir():
                findings.append(_finding(
                    "UAF-GATE-001", "action registry directory missing",
                    path=path.as_posix(),
                ))
        elif not path.is_file():
            findings.append(_finding(
                "UAF-GATE-001", "required canonical dependency missing",
                name=name, path=path.as_posix(),
            ))
    if findings:
        return findings

    profile = _load(required["profile"])
    contract = _load(required["contract"])
    decision = _load(required["decision"])
    gate_record = _load(required["gate"])

    checks = [
        (profile.get("id") == PROFILE_ID, "UAF-GATE-002", "profile id mismatch"),
        (profile.get("priority") == "P0" and profile.get("requirement") == "MUST", "UAF-GATE-003", "profile is not P0/MUST"),
        (profile.get("new_capability") is False and profile.get("new_architectural_authority") is False, "UAF-GATE-004", "profile changes capability or authority baseline"),
        (profile.get("capability_count") == capability_count, "UAF-GATE-005", "capability count drift"),
        (profile.get("provider_neutral") is True and profile.get("fail_closed") is True, "UAF-GATE-006", "provider-neutral/fail-closed invariant disabled"),
        (profile.get("hrb_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "UAF-GATE-007", "HRB authority not preserved"),
        (profile.get("mcp_boundary") == "FA3-MCP-GATEWAY-001", "UAF-GATE-008", "Central MCP Gateway boundary not preserved"),
        (contract.get("id") == CONTRACT_ID and contract.get("profile") == PROFILE_ID, "UAF-GATE-009", "contract/profile binding mismatch"),
        (contract.get("new_capability") is False and contract.get("new_architectural_authority") is False, "UAF-GATE-010", "contract changes capability or authority baseline"),
        (decision.get("id") == DECISION_ID and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0, "UAF-GATE-011", "decision changes baseline"),
        (gate_record.get("profile") == PROFILE_ID and gate_record.get("fail_closed") is True, "UAF-GATE-012", "gate record invalid"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    declared_schemas = contract.get("contract_schemas", [])
    if not isinstance(declared_schemas, list) or not declared_schemas:
        findings.append(_finding(
            "UAF-GATE-022", "contract schema inventory missing"
        ))
    else:
        schema_root = root / "canonical/contracts"
        for name in declared_schemas:
            if not isinstance(name, str) or not name.strip():
                findings.append(_finding(
                    "UAF-GATE-022", "invalid contract schema inventory entry"
                ))
                continue
            path = schema_root / name
            if not path.is_file():
                findings.append(_finding(
                    "UAF-GATE-022", "declared contract schema missing",
                    schema=name,
                ))
                continue
            try:
                schema_doc = _load(path)
            except (ValueError, json.JSONDecodeError) as exc:
                findings.append(_finding(
                    "UAF-GATE-023", "declared contract schema unreadable",
                    schema=name, error=str(exc),
                ))
                continue
            if (
                schema_doc.get("$schema")
                != "https://json-schema.org/draft/2020-12/schema"
                or not str(schema_doc.get("$id", "")).strip()
                or not str(schema_doc.get("x-fa3-contract-id", "")).strip()
            ):
                findings.append(_finding(
                    "UAF-GATE-023",
                    "declared contract schema identity is incomplete",
                    schema=name,
                ))

    try:
        registry = ActionRegistry.from_directory(required["actions"])
    except (UafError, ValueError, json.JSONDecodeError) as exc:
        findings.append(_finding(
            "UAF-GATE-013", "action registry invalid", error=str(exc)
        ))
        return findings

    ids = {item.action_id for item in registry.list()}
    missing = sorted({
        "system.capabilities.list",
        "system.providers.list",
        "hardware.describe",
    } - ids)
    if missing:
        findings.append(_finding(
            "UAF-GATE-014", "bootstrap action missing", missing=missing
        ))

    for action in registry.list():
        if (
            action.security.get("authentication") != "required"
            or action.security.get("authorization") != "required"
        ):
            findings.append(_finding(
                "UAF-GATE-015",
                "action does not require authentication and authorization",
                action=action.action_id,
            ))
        if action.evidence.get("required") is not True:
            findings.append(_finding(
                "UAF-GATE-016",
                "action does not require evidence",
                action=action.action_id,
            ))
        serialized = json.dumps(
            {"resources": action.resources},
            sort_keys=True,
        ).lower()
        for token in FORBIDDEN_GLOBAL_HARDWARE_TOKENS:
            if token in serialized:
                findings.append(_finding(
                    "UAF-GATE-017",
                    "vendor/runtime-specific global hardware coupling in action",
                    action=action.action_id,
                    token=token,
                ))
        accelerator = action.resources.get("accelerator")
        if (
            isinstance(accelerator, dict)
            and accelerator.get("cardinality") not in (None, "0..N")
        ):
            findings.append(_finding(
                "UAF-GATE-018",
                "accelerator cardinality must remain dynamic 0..N",
                action=action.action_id,
            ))
        cpu = action.resources.get("cpu")
        if (
            isinstance(cpu, dict)
            and "logical_processors" in cpu
            and "physical_cores" not in cpu
        ):
            findings.append(_finding(
                "UAF-GATE-019",
                "logical CPU requirement cannot stand in for physical-core accounting",
                action=action.action_id,
            ))

    required_invariants = {
        "one_action_contract_per_execution_semantics",
        "gui_agent_cli_mcp_a2a_automation_are_adapters_not_business_logic_authorities",
        "direct_agent_provider_bypass_forbidden",
        "hrb_remains_exclusive_resource_admission_placement_reservation_lease_authority",
        "secret_material_is_opaque_reference_only",
        "current_host_evidence_not_implied_by_static_pass",
    }
    invariants = {str(value).lower() for value in contract.get("invariants", [])}
    for invariant in sorted(required_invariants - invariants):
        findings.append(_finding(
            "UAF-GATE-020",
            "required invariant missing",
            invariant=invariant,
        ))
    if (
        "agent-native" in json.dumps(contract, sort_keys=True).lower()
        and contract.get("upstream_runtime_dependency") is not False
    ):
        findings.append(_finding(
            "UAF-GATE-021", "upstream reference became runtime dependency"
        ))
    return findings


def gate(root: Path) -> dict[str, Any]:
    findings = validate(root)
    report = {
        "schema_id": "FA3-ENFORCEMENT-RESULT-001",
        "schema_version": "1.0.0",
        "gate": {"id": GATE_ID, "mode": "STATIC_CANONICAL"},
        "result": "PASS" if not findings else "BLOCKED",
        "decision": {
            "reason_code": "UAF_CANONICAL_PASS" if not findings else "UAF_CANONICAL_BLOCKED",
            "promotion_effect": "STATIC_CANONICAL_ONLY_CURRENT_HOST_PROMOTION_UNCHANGED",
            "exit_code": 0 if not findings else 2,
        },
        "findings": findings,
        "capability_delta": 0,
        "authority_delta": 0,
        "global_promotion_claim": False,
    }
    out = root.resolve() / "reports/uaf-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", default=str(Path(__file__).resolve().parents[1])
    )
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report["decision"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
