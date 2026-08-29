#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-KANEO-001"
GATE_ID = "FA3-KANEO-GATESET-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v2.22.0"
REFERENCE_COMMIT = "4faa14858913801cfc62991cb326f35fe5fcae00"
AGENTS_BLOB = "98455101df0f398b200904e3f0ab3de537ca3122"
PACKAGE_BLOB = "9b612efc615b690b320eb260d49492c0148345bc"

P0_INVARIANTS = [
    "HUMAN_AGENT_COMMON_AUTHORIZATION_BOUNDARY",
    "CAPABILITY_SURFACE_DRIFT_FAIL_CLOSED",
    "CHANGE_SURFACE_CLOSURE_REQUIRED",
    "DISTRIBUTED_SECURITY_STATE_SHARED",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def common_authorization_boundary_valid(
    *,
    human_policy_ref: str,
    agent_policy_ref: str,
    authoritative_policy_ref: str,
    agent_bypass: bool,
) -> bool:
    return bool(
        authoritative_policy_ref
        and human_policy_ref == authoritative_policy_ref
        and agent_policy_ref == authoritative_policy_ref
        and not agent_bypass
    )


def capability_surface_parity_valid(
    canonical_capabilities: set[str],
    projected_surfaces: dict[str, set[str]],
    required_surfaces: set[str],
) -> bool:
    if not canonical_capabilities or not required_surfaces:
        return False
    if not required_surfaces.issubset(projected_surfaces):
        return False
    return all(projected_surfaces[name] == canonical_capabilities for name in required_surfaces)


def change_surface_closed(
    applicable_surfaces: set[str],
    evidence_status: dict[str, str],
) -> bool:
    if not applicable_surfaces:
        return False
    if not applicable_surfaces.issubset(evidence_status):
        return False
    return all(str(evidence_status[name]).upper() == "PASS" for name in applicable_surfaces)


def distributed_security_state_valid(
    *,
    crosses_replicas: bool,
    shared_state: bool,
    expiry: bool,
    atomic_consume: bool,
    replay_protection: bool,
) -> bool:
    if not crosses_replicas:
        return True
    return bool(shared_state and expiry and atomic_consume and replay_protection)


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    policy_path = root / "canonical/kaneo-enforcement.json"
    provider_path = root / "canonical/providers/FA3-PROVIDER-KANEO-001.json"
    evidence_path = root / "evidence/reference/kaneo-v2.22.0.json"
    required = (
        (policy_path, "KANEO-REF-001"),
        (provider_path, "KANEO-REF-002"),
        (evidence_path, "KANEO-REF-003"),
    )
    for path, code in required:
        if not path.exists():
            findings.append(_finding(code, f"Missing required Kaneo canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    policy = _load(policy_path)
    provider = _load(provider_path)
    evidence = _load(evidence_path)

    if policy.get("gate_id") != GATE_ID or policy.get("provider_id") != PROVIDER_ID:
        findings.append(_finding("KANEO-REF-004", "Kaneo gate/provider identity mismatch"))
    if policy.get("mandatory_rule_count") != 4 or policy.get("p0_invariants") != P0_INVARIANTS:
        findings.append(_finding("KANEO-REF-005", "Kaneo mandatory P0 invariant set drift"))
    if policy.get("fail_closed") is not True:
        findings.append(_finding("KANEO-REF-006", "Kaneo canonical invariant gate is not fail-closed"))
    if policy.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("KANEO-REF-007", "Floating Kaneo main was enabled as promotion evidence"))
    if policy.get("runtime_provider_required_for_global_promotion") is not False:
        findings.append(_finding("KANEO-REF-008", "Optional Kaneo provider was made a global runtime promotion dependency"))

    if provider.get("id") != PROVIDER_ID or provider.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("KANEO-REF-009", "Kaneo provider identity/capability-count invariant mismatch"))
    if any(provider.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability")):
        findings.append(_finding("KANEO-REF-010", "Kaneo was promoted to forbidden authority/root/new capability"))
    classes = set(provider.get("classification", []))
    if not {"OPTIONAL_PROVIDER", "ARCHITECTURAL_PATTERN_SOURCE"}.issubset(classes):
        findings.append(_finding("KANEO-REF-011", "Kaneo optional-provider/pattern-source classification drift"))
    if provider.get("global_runtime_promotion_required_when_disabled") is not False:
        findings.append(_finding("KANEO-REF-012", "Disabled optional Kaneo provider became mandatory for global promotion"))

    stable = evidence.get("stable_reference", {})
    if stable.get("release") != REFERENCE_RELEASE or stable.get("commit_sha") != REFERENCE_COMMIT:
        findings.append(_finding("KANEO-REF-013", "Stable Kaneo immutable reference drift"))
    blobs = stable.get("source_blobs", {})
    if blobs.get("AGENTS.md") != AGENTS_BLOB or blobs.get("package.json") != PACKAGE_BLOB:
        findings.append(_finding("KANEO-REF-014", "Kaneo source-blob reference drift"))
    if evidence.get("floating_main_allowed") is not False:
        findings.append(_finding("KANEO-REF-015", "Kaneo evidence permits floating main"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(rule_id: str, name: str, positive: bool, negative: bool, detail: str) -> None:
        cases.append(
            {
                "rule_id": rule_id,
                "name": name,
                "status": "PASS" if positive and negative else "FAIL",
                "positive_case": positive,
                "negative_case": negative,
                "detail": detail,
            }
        )

    auth = "FA3-AUTH-SECURITY-GOV-001"
    add(
        "FA3-KANEO-P0-001",
        "human/agent common authorization boundary",
        common_authorization_boundary_valid(
            human_policy_ref=auth,
            agent_policy_ref=auth,
            authoritative_policy_ref=auth,
            agent_bypass=False,
        ),
        not common_authorization_boundary_valid(
            human_policy_ref=auth,
            agent_policy_ref="KANEO_AGENT_BYPASS",
            authoritative_policy_ref=auth,
            agent_bypass=True,
        ),
        "agent-originated operations cannot bypass the same authoritative policy boundary used by humans",
    )

    canonical = {"task.read", "task.update", "project.read"}
    good = {name: set(canonical) for name in ("api", "mcp", "sdk")}
    drift = {**good, "mcp": {"task.read", "task.update", "project.read", "admin.write"}}
    add(
        "FA3-KANEO-P0-002",
        "capability-surface drift gate",
        capability_surface_parity_valid(canonical, good, {"api", "mcp", "sdk"}),
        not capability_surface_parity_valid(canonical, drift, {"api", "mcp", "sdk"}),
        "missing, extra or widened equivalent projections fail closed",
    )

    applicable = {"authorization", "api", "mcp", "event", "persistence"}
    good_evidence = {name: "PASS" for name in applicable}
    incomplete = {name: "PASS" for name in applicable if name != "mcp"}
    add(
        "FA3-KANEO-P0-003",
        "change-surface closure",
        change_surface_closed(applicable, good_evidence),
        not change_surface_closed(applicable, incomplete),
        "a change cannot close while an applicable surface lacks PASS evidence",
    )

    add(
        "FA3-KANEO-P0-004",
        "distributed security-state",
        distributed_security_state_valid(
            crosses_replicas=True,
            shared_state=True,
            expiry=True,
            atomic_consume=True,
            replay_protection=True,
        ),
        not distributed_security_state_valid(
            crosses_replicas=True,
            shared_state=False,
            expiry=True,
            atomic_consume=False,
            replay_protection=False,
        ),
        "cross-replica security state requires shared expiry, atomic consume and replay protection",
    )

    passed = sum(case["status"] == "PASS" for case in cases)
    return {
        "schema": "fa3.kaneo-regression-report.v1",
        "result": "PASS" if passed == 4 else "FAIL",
        "passed": passed,
        "total": 4,
        "cases": cases,
    }


def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    ok = reference["result"] == "PASS" and regressions["result"] == "PASS"
    report = {
        "schema": "fa3.kaneo-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "mode": "CANONICAL_REFERENCE_AND_EXECUTABLE_INVARIANTS",
        "reference": reference,
        "regressions": regressions,
        "runtime_provider_required": False,
        "promotion_effect": "MANDATORY_CANONICAL_RULE_PASS_PROVIDER_RUNTIME_OPTIONAL",
    }
    _write(root / "reports/kaneo-gate-report.json", report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Kaneo mandatory canonical invariant gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
