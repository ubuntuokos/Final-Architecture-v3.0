#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-BUZZ-001"
DECISION_ID = "FA3-DEC-BUZZ-2026-08-30"
GATE_ID = "FA3-BUZZ-GATESET-001"
CAPABILITY_COUNT = 143
P0_INVARIANT = "BUZZ_AUTHORITY_SEPARATION_FAIL_CLOSED"
MANDATORY_CONSTRAINT = (
    "Buzz SHALL NOT become an FA3 identity, authorization, MCP, workflow, evidence, "
    "secrets, host-resource or developer-execution authority."
)

PROHIBITED_DOMAINS = (
    "identity",
    "authorization",
    "mcp",
    "workflow",
    "evidence",
    "secrets",
    "host_resource",
    "developer_execution",
)

DOMAIN_ROLE_MARKERS = {
    "identity": ("IDENTITY_AUTHORITY",),
    "authorization": ("AUTHORIZATION_AUTHORITY", "AUTHZ_AUTHORITY"),
    "mcp": ("MCP_AUTHORITY", "MCP_GATEWAY_AUTHORITY"),
    "workflow": ("WORKFLOW_AUTHORITY", "ORCHESTRATION_AUTHORITY"),
    "evidence": ("EVIDENCE_AUTHORITY", "OBSERVABILITY_EVIDENCE_AUTHORITY"),
    "secrets": ("SECRETS_AUTHORITY", "SECRET_AUTHORITY", "CREDENTIAL_AUTHORITY"),
    "host_resource": ("HOST_RESOURCE_AUTHORITY", "RESOURCE_AUTHORITY", "PLACEMENT_AUTHORITY"),
    "developer_execution": ("DEVELOPER_EXECUTION_AUTHORITY", "ADE_AUTHORITY"),
}

DOMAIN_KEY_MARKERS = {
    "identity": ("identity",),
    "authorization": ("authorization", "authz", "policy"),
    "mcp": ("mcp", "tool_mediation"),
    "workflow": ("workflow", "orchestration"),
    "evidence": ("evidence", "observability"),
    "secrets": ("secret", "secrets", "credential"),
    "host_resource": ("host_resource", "resource", "placement"),
    "developer_execution": ("developer_execution", "ade"),
}

IDENTITY_KEYS = {
    "id",
    "provider_id",
    "subject",
    "name",
    "source",
    "repository",
    "provider",
    "implementation",
}

ROLE_KEYS = {
    "role",
    "roles",
    "provider_role",
    "authority_role",
    "authority_roles",
    "classification",
}

GENERIC_AUTHORITY_KEYS = {
    "authority",
    "authority_id",
    "authority_owner",
    "authority_provider",
    "architectural_authority",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)


def _is_buzz_value(value: Any) -> bool:
    for raw in _iter_strings(value):
        text = raw.upper()
        if PROVIDER_ID in raw or "BLOCK/BUZZ" in text or text == "BUZZ" or text.startswith("FA3-AUTH-BUZZ"):
            return True
    return False


def _object_is_buzz_scoped(obj: dict[str, Any]) -> bool:
    for key in IDENTITY_KEYS:
        if key in obj and _is_buzz_value(obj[key]):
            return True
    return False


def _role_domain(value: Any) -> str | None:
    for raw in _iter_strings(value):
        text = raw.upper().replace("-", "_")
        for domain, markers in DOMAIN_ROLE_MARKERS.items():
            if any(marker in text for marker in markers):
                return domain
    return None


def _semantic_authority_domain(key: str) -> str | None:
    normalized = key.lower().replace("-", "_")
    if normalized in GENERIC_AUTHORITY_KEYS:
        return "generic"
    if "authority" not in normalized:
        return None
    for domain, markers in DOMAIN_KEY_MARKERS.items():
        if any(marker in normalized for marker in markers):
            return domain
    return None


def authority_assignment_allowed(domain: str, authority_value: Any) -> bool:
    if domain not in PROHIBITED_DOMAINS:
        return False
    return not _is_buzz_value(authority_value)


def provider_shape_valid(provider: dict[str, Any]) -> bool:
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("global_runtime_promotion_required_when_disabled") is False
    )


def decision_shape_valid(decision: dict[str, Any]) -> bool:
    return bool(
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("gate_id") == GATE_ID
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
        and decision.get("mandatory_constraint") == MANDATORY_CONSTRAINT
    )


def enforcement_shape_valid(enforcement: dict[str, Any]) -> bool:
    return bool(
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("runtime_provider_required_for_global_promotion") is False
        and enforcement.get("mandatory_rule_count") == 1
        and enforcement.get("p0_invariants") == [P0_INVARIANT]
        and enforcement.get("rules")
        and enforcement["rules"][0].get("id") == "FA3-BUZZ-P0-001"
        and enforcement["rules"][0].get("requirement") == MANDATORY_CONSTRAINT
    )


def capability_invariant_valid(*, capability_count: int, new_capability: bool, new_authorities: int) -> bool:
    return capability_count == CAPABILITY_COUNT and new_capability is False and new_authorities == 0


def _scan_value(
    value: Any,
    *,
    path: str,
    file_path: str,
    inherited_buzz_scope: bool = False,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if isinstance(value, dict):
        local_buzz_scope = inherited_buzz_scope or _object_is_buzz_scoped(value)

        record_id = value.get("id")
        if local_buzz_scope and isinstance(record_id, str) and record_id.upper().startswith("FA3-AUTH-BUZZ"):
            findings.append(
                _finding(
                    "BUZZ-AUTH-001",
                    "Buzz was introduced as an FA3 authority record",
                    file=file_path,
                    path=f"{path}.id",
                    value=record_id,
                )
            )

        for key, item in value.items():
            key_path = f"{path}.{key}"
            semantic_domain = _semantic_authority_domain(key)

            if key == "authority_boundaries" and isinstance(item, dict):
                for boundary_domain, boundary_authority in item.items():
                    if _is_buzz_value(boundary_authority):
                        findings.append(
                            _finding(
                                "BUZZ-AUTH-006",
                                "Buzz was assigned as an authority boundary owner",
                                file=file_path,
                                path=f"{key_path}.{boundary_domain}",
                                domain=boundary_domain,
                                value=boundary_authority,
                            )
                        )

            if semantic_domain and _is_buzz_value(item):
                findings.append(
                    _finding(
                        "BUZZ-AUTH-002",
                        "Buzz was assigned to an authority-bearing field",
                        file=file_path,
                        path=key_path,
                        domain=semantic_domain,
                        value=item,
                    )
                )

            if key == "architectural_authority" and item is True and local_buzz_scope:
                findings.append(
                    _finding(
                        "BUZZ-AUTH-003",
                        "Buzz architectural_authority was enabled",
                        file=file_path,
                        path=key_path,
                    )
                )

            if key in ROLE_KEYS and local_buzz_scope:
                domain = _role_domain(item)
                if domain:
                    findings.append(
                        _finding(
                            "BUZZ-AUTH-004",
                            "Buzz received a prohibited authority role",
                            file=file_path,
                            path=key_path,
                            domain=domain,
                            value=item,
                        )
                    )

            findings.extend(
                _scan_value(
                    item,
                    path=key_path,
                    file_path=file_path,
                    inherited_buzz_scope=local_buzz_scope,
                )
            )

    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                _scan_value(
                    item,
                    path=f"{path}[{index}]",
                    file_path=file_path,
                    inherited_buzz_scope=inherited_buzz_scope,
                )
            )

    return findings


def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    canonical = root / "canonical"
    if not canonical.exists():
        return {
            "result": "FAIL",
            "scanned_json_files": 0,
            "findings": [_finding("BUZZ-AUTH-000", "canonical directory is missing")],
        }

    for path in sorted(canonical.rglob("*.json")):
        scanned += 1
        try:
            data = _load(path)
        except Exception as exc:
            findings.append(
                _finding(
                    "BUZZ-AUTH-005",
                    "Canonical JSON could not be parsed during Buzz authority scan",
                    file=str(path.relative_to(root)),
                    error=str(exc),
                )
            )
            continue
        findings.extend(
            _scan_value(
                data,
                path="$",
                file_path=str(path.relative_to(root)),
                inherited_buzz_scope=False,
            )
        )

    return {
        "result": "PASS" if not findings else "FAIL",
        "scanned_json_files": scanned,
        "findings": findings,
    }


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    provider_path = root / "canonical/providers/FA3-PROVIDER-BUZZ-001.json"
    decision_path = root / "canonical/decisions/FA3-DEC-BUZZ-2026-08-30.json"
    enforcement_path = root / "canonical/buzz-enforcement.json"
    policy_path = root / "canonical/enforcement-policy.json"

    required = (
        (provider_path, "BUZZ-REF-001"),
        (decision_path, "BUZZ-REF-002"),
        (enforcement_path, "BUZZ-REF-003"),
        (policy_path, "BUZZ-REF-004"),
    )
    for path, code in required:
        if not path.exists():
            findings.append(_finding(code, f"Missing required Buzz canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = _load(provider_path)
    decision = _load(decision_path)
    enforcement = _load(enforcement_path)
    policy = _load(policy_path)

    if not provider_shape_valid(provider):
        findings.append(_finding("BUZZ-REF-005", "Buzz provider root/authority/capability invariant drift"))
    classes = set(provider.get("classification", []))
    required_classes = {
        "OPTIONAL_PROVIDER",
        "HUMAN_AGENT_COLLABORATIVE_WORKSPACE",
        "EVENTED_DEVELOPMENT_FORGE_REFERENCE_PROVIDER",
        "STRONG_ARCHITECTURAL_PATTERN_SOURCE",
    }
    if not required_classes.issubset(classes):
        findings.append(_finding("BUZZ-REF-006", "Buzz canonical classification drift"))

    if not decision_shape_valid(decision):
        findings.append(_finding("BUZZ-REF-007", "Buzz canonical decision invariant drift"))
    prohibited = set(decision.get("prohibited_promotions", []))
    expected_prohibited = {
        "BUZZ_AS_CANONICAL_ROOT",
        "BUZZ_AS_FA3_IDENTITY_AUTHORITY",
        "BUZZ_AS_FA3_AUTHORIZATION_AUTHORITY",
        "BUZZ_AS_FA3_MCP_AUTHORITY",
        "BUZZ_AS_FA3_WORKFLOW_AUTHORITY",
        "BUZZ_AS_FA3_EVIDENCE_AUTHORITY",
        "BUZZ_AS_FA3_SECRETS_AUTHORITY",
        "BUZZ_AS_FA3_HOST_RESOURCE_AUTHORITY",
        "BUZZ_AS_FA3_DEVELOPER_EXECUTION_AUTHORITY",
    }
    if not expected_prohibited.issubset(prohibited):
        findings.append(_finding("BUZZ-REF-008", "Buzz prohibited-promotion set drift"))

    if not enforcement_shape_valid(enforcement):
        findings.append(_finding("BUZZ-REF-009", "Buzz fail-closed enforcement record drift"))

    if GATE_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("BUZZ-REF-010", "Buzz gate is not bound into mandatory_reference_gates"))
    if policy.get("buzz_provider_id") != PROVIDER_ID:
        findings.append(_finding("BUZZ-REF-011", "Global enforcement policy Buzz provider identity drift"))
    if policy.get("buzz_mandatory_p0_rules") != [P0_INVARIANT]:
        findings.append(_finding("BUZZ-REF-012", "Global enforcement policy Buzz P0 invariant drift"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    good_authorities = {
        "identity": "FA3-AUTH-IDENTITY-001",
        "authorization": "FA3-AUTH-SECURITY-GOV-001",
        "mcp": "FA3-AUTH-MCP-GATEWAY-001",
        "workflow": "FA3-AUTH-WORKFLOW-001",
        "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
        "secrets": "FA3-AUTH-SECRETS-001",
        "host_resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "developer_execution": "FA3-AUTH-DEVELOPER-EXECUTION-001",
    }

    for domain in PROHIBITED_DOMAINS:
        positive = authority_assignment_allowed(domain, good_authorities[domain])
        negative = not authority_assignment_allowed(domain, PROVIDER_ID)
        cases.append(
            {
                "rule_id": "FA3-BUZZ-P0-001",
                "name": f"{domain} authority escalation denial",
                "status": "PASS" if positive and negative else "FAIL",
                "positive_case": positive,
                "negative_case": negative,
            }
        )

    root_positive = provider_shape_valid(
        {
            "id": PROVIDER_ID,
            "capability_count": CAPABILITY_COUNT,
            "canonical_root": False,
            "architectural_authority": False,
            "new_capability": False,
            "global_runtime_promotion_required_when_disabled": False,
        }
    )
    root_negative = not provider_shape_valid(
        {
            "id": PROVIDER_ID,
            "capability_count": CAPABILITY_COUNT,
            "canonical_root": True,
            "architectural_authority": False,
            "new_capability": False,
            "global_runtime_promotion_required_when_disabled": False,
        }
    )
    cases.append(
        {
            "rule_id": "FA3-BUZZ-P0-001",
            "name": "canonical-root promotion denial",
            "status": "PASS" if root_positive and root_negative else "FAIL",
            "positive_case": root_positive,
            "negative_case": root_negative,
        }
    )

    cap_positive = capability_invariant_valid(
        capability_count=CAPABILITY_COUNT,
        new_capability=False,
        new_authorities=0,
    )
    cap_negative = not capability_invariant_valid(
        capability_count=CAPABILITY_COUNT + 1,
        new_capability=True,
        new_authorities=1,
    )
    cases.append(
        {
            "rule_id": "FA3-BUZZ-P0-001",
            "name": "capability/authority count drift denial",
            "status": "PASS" if cap_positive and cap_negative else "FAIL",
            "positive_case": cap_positive,
            "negative_case": cap_negative,
        }
    )

    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema": "fa3.buzz-regression-report.v1",
        "result": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "cases": cases,
    }


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    authority_scan = scan_canonical_authority_assignments(root)
    regressions = run_regressions()
    ok = (
        reference["result"] == "PASS"
        and authority_scan["result"] == "PASS"
        and regressions["result"] == "PASS"
    )
    report = {
        "schema": "fa3.buzz-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "mode": "CANONICAL_AUTHORITY_SEPARATION_AND_EXECUTABLE_REGRESSIONS",
        "reference": reference,
        "authority_scan": authority_scan,
        "regressions": regressions,
        "runtime_provider_required": False,
        "promotion_effect": "MANDATORY_CANONICAL_AUTHORITY_SEPARATION_PROVIDER_RUNTIME_OPTIONAL",
    }
    _write(root / "reports/buzz-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Buzz fail-closed authority-separation regression gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
