#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-KANEO-001"
GATE_ID = "FA3-KANEO-GATESET-001"
REFERENCE_ID = "FA3-KANEO-UPSTREAM-REFERENCE-2026-09-12"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v2.24.0"
REFERENCE_COMMIT = "863b979e2af6d9b4d75064edc43a2c118d9af7ce"
AGENTS_BLOB = "a0ccf325b7da268e0da6ebd463e1c707e65701d7"
PACKAGE_BLOB = "8c656597786d54fa371a90f184e1a8988456f3b7"
AUTH_BOUNDARY_TEST_BLOB = "1cc7da5b3c676a354c0587510842ddbe1cecef1a"
REFERENCE_EVIDENCE = "evidence/reference/kaneo-v2.24.0.json"

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
    reference_path = root / "canonical/references/FA3-KANEO-UPSTREAM-REFERENCE-2026-09-12.json"
    evidence_path = root / REFERENCE_EVIDENCE
    required = (
        (policy_path, "KANEO-REF-001"),
        (provider_path, "KANEO-REF-002"),
        (reference_path, "KANEO-REF-003"),
        (evidence_path, "KANEO-REF-004"),
    )
    for path, code in required:
        if not path.exists():
            findings.append(_finding(code, f"Missing required Kaneo canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    policy = _load(policy_path)
    provider = _load(provider_path)
    reference = _load(reference_path)
    evidence = _load(evidence_path)

    if policy.get("gate_id") != GATE_ID or policy.get("provider_id") != PROVIDER_ID:
        findings.append(_finding("KANEO-REF-005", "Kaneo gate/provider identity mismatch"))
    if policy.get("mandatory_rule_count") != 4 or policy.get("p0_invariants") != P0_INVARIANTS:
        findings.append(_finding("KANEO-REF-006", "Kaneo mandatory P0 invariant set drift"))
    if policy.get("fail_closed") is not True:
        findings.append(_finding("KANEO-REF-007", "Kaneo canonical invariant gate is not fail-closed"))
    if policy.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("KANEO-REF-008", "Floating Kaneo main was enabled as promotion evidence"))
    if policy.get("runtime_provider_required_for_global_promotion") is not False:
        findings.append(_finding("KANEO-REF-009", "Optional Kaneo provider was made a global runtime promotion dependency"))
    if policy.get("upstream_reference_id") != REFERENCE_ID or policy.get("reference_evidence") != REFERENCE_EVIDENCE:
        findings.append(_finding("KANEO-REF-010", "Kaneo enforcement upstream-reference binding drift"))
    if policy.get("stable_reference") != {"release": REFERENCE_RELEASE, "commit_sha": REFERENCE_COMMIT}:
        findings.append(_finding("KANEO-REF-011", "Kaneo enforcement stable reference drift"))

    if provider.get("id") != PROVIDER_ID or provider.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("KANEO-REF-012", "Kaneo provider identity/capability-count invariant mismatch"))
    if any(provider.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability")):
        findings.append(_finding("KANEO-REF-013", "Kaneo was promoted to forbidden authority/root/new capability"))
    classes = set(provider.get("classification", []))
    if not {"OPTIONAL_PROVIDER", "ARCHITECTURAL_PATTERN_SOURCE"}.issubset(classes):
        findings.append(_finding("KANEO-REF-014", "Kaneo optional-provider/pattern-source classification drift"))
    if provider.get("global_runtime_promotion_required_when_disabled") is not False:
        findings.append(_finding("KANEO-REF-015", "Disabled optional Kaneo provider became mandatory for global promotion"))
    admission = provider.get("runtime_admission", {})
    if admission.get("upstream_reference_id") != REFERENCE_ID:
        findings.append(_finding("KANEO-REF-016", "Kaneo provider admission reference drift"))
    if admission.get("release") != REFERENCE_RELEASE or admission.get("commit_sha") != REFERENCE_COMMIT:
        findings.append(_finding("KANEO-REF-017", "Kaneo provider admission release/commit drift"))
    if admission.get("evidence") != REFERENCE_EVIDENCE or admission.get("floating_main_forbidden") is not True:
        findings.append(_finding("KANEO-REF-018", "Kaneo provider admission evidence/floating-ref policy drift"))

    if reference.get("id") != REFERENCE_ID or reference.get("provider_id") != PROVIDER_ID:
        findings.append(_finding("KANEO-REF-019", "Kaneo canonical upstream-reference identity drift"))
    ref_stable = reference.get("stable_reference", {})
    if ref_stable.get("release") != REFERENCE_RELEASE or ref_stable.get("commit_sha") != REFERENCE_COMMIT:
        findings.append(_finding("KANEO-REF-020", "Kaneo canonical upstream stable reference drift"))
    ref_blobs = ref_stable.get("source_blobs", {})
    expected_blobs = {
        "AGENTS.md": AGENTS_BLOB,
        "package.json": PACKAGE_BLOB,
        "tests/api-integration/authorization-boundaries.test.ts": AUTH_BOUNDARY_TEST_BLOB,
    }
    if ref_blobs != expected_blobs:
        findings.append(_finding("KANEO-REF-021", "Kaneo canonical upstream source-blob reference drift"))
    disposition = reference.get("fa3_disposition", {})
    if disposition.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("KANEO-REF-022", "Kaneo canonical upstream reference permits floating main"))
    if disposition.get("provider_runtime_required_for_global_promotion") is not False:
        findings.append(_finding("KANEO-REF-023", "Kaneo canonical upstream reference made runtime globally mandatory"))
    if disposition.get("capability_count") != CAPABILITY_COUNT or disposition.get("mandatory_p0_rule_count") != 4:
        findings.append(_finding("KANEO-REF-024", "Kaneo canonical upstream disposition changed capability/P0 counts"))

    stable = evidence.get("stable_reference", {})
    if stable.get("release") != REFERENCE_RELEASE or stable.get("commit_sha") != REFERENCE_COMMIT:
        findings.append(_finding("KANEO-REF-025", "Stable Kaneo immutable evidence reference drift"))
    blobs = stable.get("source_blobs", {})
    if blobs != expected_blobs:
        findings.append(_finding("KANEO-REF-026", "Kaneo evidence source-blob reference drift"))
    if evidence.get("floating_main_allowed") is not False:
        findings.append(_finding("KANEO-REF-027", "Kaneo evidence permits floating main"))
    compatibility = evidence.get("compatibility_evidence", {})
    if any(compatibility.get(name) != "PASS" for name in (
        "human_agent_common_authorization_boundary",
        "capability_surface_drift_fail_closed",
        "change_surface_closure_required",
        "distributed_security_state_shared",
    )):
        findings.append(_finding("KANEO-REF-028", "Kaneo v2.24.0 compatibility evidence does not PASS all four P0 invariants"))
    if compatibility.get("new_capabilities") != 0 or compatibility.get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(_finding("KANEO-REF-029", "Kaneo compatibility evidence changed FA3 capability count"))

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
        "upstream_reference_id": REFERENCE_ID,
        "reference_release": REFERENCE_RELEASE,
        "reference_commit": REFERENCE_COMMIT,
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
