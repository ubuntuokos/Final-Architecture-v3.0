#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

GATE_ID = "FA3-COMPUTER-INTERACTION-RUNTIME-GATESET-001"
PROFILE_ID = "FA3-COMPUTER-INTERACTION-RUNTIME-001"
CONTRACT_ID = "FA3-COMPUTER-INTERACTION-RUNTIME-CONTRACTS-001"
ACTION_ID = "computer.interaction.execute"
REQUIRED_CONTRACTS = {
    "ComputerInteractionObservation",
    "ComputerInteractionTarget",
    "ComputerInteractionCandidate",
    "ComputerInteractionActionSpace",
    "ComputerInteractionDecisionBinding",
    "ComputerInteractionExecutionGuard",
    "ComputerInteractionExecutionParameters",
    "ComputerInteractionEffectReceipt",
    "ComputerInteractionOutcomeVerification",
    "ComputerInteractionReobserveRequest",
    "ComputerInteractionAbstention",
    "ComputerInteractionTrajectoryEvent",
}
REQUIRED_INVARIANTS = {
    "COMPUTER_INTERACTION_RUNTIME_IS_EXECUTION_DOMAIN_NOT_AUTHORITY",
    "NATIVE_DESKTOP_ACTION_SPACE_BOUNDED",
    "MODEL_CANNOT_EXPAND_ACTION_SPACE",
    "OBSERVATION_AND_CAPTURE_BOUND_ACTION_REQUIRED",
    "STALE_OBSERVATION_OR_CAPTURE_EXECUTION_DENIED",
    "MUTATION_REQUIRES_AUTHORIZATION_REFERENCE",
    "BLIND_MUTATION_RETRY_DENIED",
    "MUTATION_REQUIRES_REOBSERVATION",
    "SUCCESS_REQUIRES_INDEPENDENT_VERIFICATION",
    "DIRECT_AGENT_DRIVER_OR_PROVIDER_BYPASS_FORBIDDEN",
    "NO_SILENT_LOCAL_REMOTE_OR_PROVIDER_FALLBACK",
    "TELEMETRY_DISABLED_BY_DEFAULT",
    "NO_UPSTREAM_CUA_RUNTIME_DEPENDENCY",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    required = [
        "canonical/profiles/FA3-COMPUTER-INTERACTION-RUNTIME-001.json",
        "canonical/contracts/FA3-COMPUTER-INTERACTION-RUNTIME-CONTRACTS-001.json",
        "canonical/actions/computer.interaction.execute.json",
        "canonical/FA3-GATE-COMPUTER-INTERACTION-RUNTIME-001.json",
        "canonical/computer-interaction-runtime-enforcement.json",
        "canonical/decisions/FA3-DEC-COMPUTER-INTERACTION-RUNTIME-2026-10-01.json",
        "canonical/intents/FA3-COMPUTER-INTERACTION-RUNTIME-APPLICATION-INTENT-001.json",
        "canonical/assessments/FA3-COMPUTER-INTERACTION-RUNTIME-REUSE-ASSESSMENT-001.json",
        "canonical/assessments/FA3-COMPUTER-INTERACTION-RUNTIME-DECISION-ASSESSMENT-2026-10-01.json",
        "canonical/FA3-COMPUTER-INTERACTION-CURRENT-HOST-IMPACT-001.json",
        "canonical/profiles/FA3-UNIFIED-ACTION-FABRIC-001.json",
        "canonical/profiles/FA3-SHARED-TOOL-ACTION-MEDIATION-001.json",
        "canonical/profiles/FA3-BROWSER-ACTION-RUNTIME-001.json",
        "src/fa3_computer_interaction_runtime.py",
        "tests/test_computer_interaction_runtime.py",
        "docs/FA3-COMPUTER-INTERACTION-RUNTIME-2026-10-01.md",
    ]
    for rel in required:
        if not (root / rel).is_file():
            findings.append({"code": "CIR-001", "message": "required file missing", "path": rel})
    if findings:
        return _report(findings)

    capability_count = module_active_capability_count(__file__)
    profile = load(root / required[0])
    contract = load(root / required[1])
    action = load(root / required[2])
    policy = load(root / "canonical/enforcement-policy.json")
    assessment = load(
        root / "canonical/assessments/FA3-COMPUTER-INTERACTION-RUNTIME-REUSE-ASSESSMENT-001.json"
    )
    decision_assessment = load(
        root / "canonical/assessments/FA3-COMPUTER-INTERACTION-RUNTIME-DECISION-ASSESSMENT-2026-10-01.json"
    )
    impact = load(root / "canonical/FA3-COMPUTER-INTERACTION-CURRENT-HOST-IMPACT-001.json")

    checks = [
        (
            profile.get("id") == PROFILE_ID
            and profile.get("capability_count") == capability_count
            and profile.get("new_capability") is False
            and profile.get("new_architectural_authority") is False,
            "CIR-002",
            "profile baseline or identity drift",
        ),
        (
            profile.get("parent_execution_fabric") == "FA3-UNIFIED-ACTION-FABRIC-001"
            and profile.get("shared_mediation_profile") == "FA3-SHARED-TOOL-ACTION-MEDIATION-001",
            "CIR-003",
            "UAF/shared mediation boundary missing",
        ),
        (
            profile.get("authorities", {}).get("model_routing") == "FA3-AUTH-MODEL-ROUTER-001"
            and profile.get("authorities", {}).get("tool_mediation") == "FA3-AUTH-MCP-GATEWAY-001"
            and profile.get("authorities", {}).get("host_resources") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
            and profile.get("authorities", {}).get("evidence") == "FA3-AUTH-OBS-EVIDENCE-001",
            "CIR-004",
            "existing authority boundary drift",
        ),
        (
            contract.get("id") == CONTRACT_ID
            and contract.get("profile") == PROFILE_ID
            and contract.get("capability_count") == capability_count
            and contract.get("upstream_runtime_dependency") is False,
            "CIR-005",
            "contract identity/baseline/runtime dependency drift",
        ),
        (
            set(contract.get("contracts", [])) >= REQUIRED_CONTRACTS,
            "CIR-006",
            "required contract family incomplete",
        ),
        (
            set(profile.get("invariants", [])) >= REQUIRED_INVARIANTS,
            "CIR-007",
            "required fail-closed invariants missing",
        ),
        (
            profile.get("runtime_materialization", {}).get("telemetry_default") == "DISABLED",
            "CIR-008",
            "telemetry is not disabled by default",
        ),
        (
            action.get("id") == ACTION_ID
            and action.get("security", {}).get("authentication") == "required"
            and action.get("security", {}).get("authorization") == "required"
            and action.get("evidence", {}).get("required") is True
            and action.get("semantics", {}).get("blind_retry") == "DENY"
            and action.get("semantics", {}).get("post_mutation_reobserve") == "REQUIRED",
            "CIR-009",
            "UAF action contract is not fail-closed",
        ),
        (
            assessment.get("status") == "REVIEWED_MATCH"
            and assessment.get("analysis_only_external_source", {}).get("repository")
            == "https://github.com/trycua/cua"
            and assessment.get("analysis_only_external_source", {}).get("registry_status")
            == "UNREGISTERED_UNMARKED_ANALYSIS_ONLY"
            and assessment.get("code_import_authorized") is False
            and assessment.get("runtime_admission_authorized") is False,
            "CIR-010",
            "research-only CUA boundary drift",
        ),
        (
            decision_assessment.get("schema") == "fa3.decision-fabric-assessment.v1"
            and "FA3-COMPUTER-INTERACTION-RUNTIME-001" in decision_assessment.get("covered_ids", [])
            and decision_assessment.get("assessment") == "REQUIRED"
            and decision_assessment.get("project_radar_checked") is True
            and decision_assessment.get("security_boundary", {}).get("may_expand_candidate_set") is False,
            "CIR-020",
            "Decision Fabric applicability assessment missing or unsafe",
        ),
        (
            impact.get("physical_current_host_pass_claimed") is False
            and impact.get("status") == "PENDING_PHYSICAL_REQUALIFICATION"
            and impact.get("capability_subject") == "CAP-013",
            "CIR-011",
            "Current Host impact is not honestly pending physical proof",
        ),
        (
            GATE_ID in policy.get("mandatory_reference_gates", [])
            and policy.get("computer_interaction_runtime_global_static_required") is True,
            "CIR-012",
            "global fail-closed enforcement binding missing",
        ),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append({"code": code, "message": message})

    runtime = (root / "src/fa3_computer_interaction_runtime.py").read_text(encoding="utf-8")
    for token, code in [
        ("UNTRUSTED_DESKTOP_CONTENT", "CIR-013"),
        ("STALE_OBSERVATION", "CIR-014"),
        ("AUTHORIZATION_REQUIRED", "CIR-015"),
        ("BLIND_MUTATION_RETRY_DENIED", "CIR-016"),
        ("REOBSERVE_REQUIRED", "CIR-017"),
        ("METADATA_MINIMAL", "CIR-018"),
    ]:
        if token not in runtime:
            findings.append({"code": code, "message": "runtime invariant token missing", "token": token})
    forbidden = ["trycua", "cua_driver", "cua-driver", "CUA_TELEMETRY_ENABLED"]
    leaked = [token for token in forbidden if token in runtime]
    if leaked:
        findings.append(
            {"code": "CIR-019", "message": "upstream CUA runtime dependency residue", "tokens": leaked}
        )
    return _report(findings)


def _report(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "fa3.computer-interaction-runtime-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "capability_count": module_active_capability_count(__file__),
        "capability_delta": 0,
        "authority_delta": 0,
        "global_promotion_claim": False,
        "current_host_runtime_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--report", default="reports/computer-interaction-runtime-gate-report.json"
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root)
    path = root / args.report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
