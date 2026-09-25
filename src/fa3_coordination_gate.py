#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_objective_coordination import CoordinationContractError, compile_snapshot, deduplicate_events
from fa3_release_baseline import module_active_capability_count

PROFILE_ID = "FA3-COORDINATION-LAYER-001"
CONTRACT_ID = "FA3-OBJECTIVE-COORDINATION-CONTRACTS-001"
GATE_ID = "FA3-COORDINATION-GATESET-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)

P0_INVARIANTS = [
    "COORDINATION_LAYER_CREATES_NO_ARCHITECTURAL_AUTHORITY",
    "OBJECTIVE_IDENTITY_IS_PROVIDER_NEUTRAL",
    "COORDINATION_EVENTS_DO_NOT_AUTHORIZE_ACTIONS",
    "EXECUTION_REMAINS_EXISTING_UAF_WORKFLOW_ORCHESTRATION_AUTHORITY",
    "RESOURCE_ADMISSION_REMAINS_HRB",
    "DECISION_FABRIC_REMAINS_BOUNDED_ADVISORY",
    "ARTIFACT_TRANSFER_REMAINS_EXISTING_ARTIFACT_LOGISTICS_AUTHORITY",
    "REQUIRED_DEPENDENCY_CYCLES_FAIL_CLOSED",
    "HANDOFF_ARTIFACT_AND_PROVENANCE_REFS_ARE_REQUIRED",
    "CORRELATION_AND_CAUSATION_CONTEXT_IS_PRESERVED",
    "EVENT_REPLAY_IS_IDEMPOTENT_AND_PAYLOAD_MISMATCH_FAILS_CLOSED",
    "TASK_MANAGER_AND_LOGISTICS_FUTURE_BINDINGS_ARE_OPTIONAL_NOT_HARD_DEPENDENCIES",
    "WORK_MANAGEMENT_COORDINATION_VIEW_IS_READ_ONLY_PROJECTION",
    "CAPABILITY_AND_AUTHORITY_COUNT_REMAIN_UNCHANGED",
]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def _sample() -> dict[str, Any]:
    return {
        "schema": "fa3.objective-coordination.v1",
        "objective_id": "OBJ-DEMO",
        "title": "Demo objective",
        "authority": False,
        "trace_context": {"correlation_id": "corr-demo", "causation_id": None},
        "nodes": [
            {"node_id": "story", "kind": "WORK_ITEM", "state": "COMPLETED"},
            {"node_id": "voice", "kind": "WORKFLOW", "state": "PENDING"},
            {"node_id": "edit", "kind": "WORKFLOW", "state": "PENDING"},
        ],
        "dependencies": [
            {"upstream": "story", "downstream": "voice", "relation": "REQUIRES"},
            {"upstream": "voice", "downstream": "edit", "relation": "HANDOFF_AFTER"},
        ],
        "handoffs": [{
            "handoff_id": "voice-to-edit",
            "source_node": "voice",
            "target_node": "edit",
            "state": "PLANNED",
            "artifact_refs": ["artifact://voice/master"],
            "provenance_refs": ["journal://evt/voice"],
        }],
        "blockers": [],
    }


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(name: str, passed: bool) -> None:
        cases.append({"name": name, "status": "PASS" if passed else "FAIL"})

    sample = _sample()
    snap = compile_snapshot(sample)
    add("ready set derives from completed prerequisites", snap["ready_node_ids"] == ["voice"])
    add("handoff blocks downstream until received", "edit" in snap["blocked_node_ids"])
    add("snapshot is explicitly non-authoritative", snap["authority"] is False)

    cyclic = json.loads(json.dumps(sample))
    cyclic["dependencies"].append({"upstream": "edit", "downstream": "story", "relation": "REQUIRES"})
    try:
        compile_snapshot(cyclic)
        cycle_denied = False
    except CoordinationContractError:
        cycle_denied = True
    add("required dependency cycle fails closed", cycle_denied)

    bad_handoff = json.loads(json.dumps(sample))
    bad_handoff["handoffs"][0]["provenance_refs"] = []
    try:
        compile_snapshot(bad_handoff)
        provenance_denied = False
    except CoordinationContractError:
        provenance_denied = True
    add("handoff without provenance fails closed", provenance_denied)

    bad_authority = json.loads(json.dumps(sample))
    bad_authority["execute"] = True
    try:
        compile_snapshot(bad_authority)
        authority_denied = False
    except CoordinationContractError:
        authority_denied = True
    add("execution authority claim fails closed", authority_denied)

    event = {
        "event_id": "evt-1", "event_type": "NODE_OBSERVED", "correlation_id": "corr-demo",
        "causation_id": None, "source_ref": "work-item://1", "payload": {"state": "COMPLETED"},
    }
    replay = deduplicate_events([event, dict(event)])
    add("identical event replay becomes no-op", len(replay.accepted) == 1 and replay.replayed_event_ids == ("evt-1",))

    mismatch = dict(event)
    mismatch["payload"] = {"state": "FAILED"}
    try:
        deduplicate_events([event, mismatch])
        mismatch_denied = False
    except CoordinationContractError:
        mismatch_denied = True
    add("same event id with different payload fails closed", mismatch_denied)

    passed = sum(case["status"] == "PASS" for case in cases)
    return {"result": "PASS" if passed == len(cases) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    paths = {
        "profile": root / "canonical/profiles/FA3-COORDINATION-LAYER-001.json",
        "contracts": root / "canonical/contracts/FA3-OBJECTIVE-COORDINATION-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-COORDINATION-LAYER-2026-09-25.json",
        "intent": root / "canonical/intents/FA3-COORDINATION-LAYER-APPLICATION-INTENT-001.json",
        "assessment": root / "canonical/assessments/FA3-COORDINATION-LAYER-REUSE-ASSESSMENT-001.json",
        "enforcement": root / "canonical/coordination-enforcement.json",
        "work_management": root / "canonical/FA3-WORK-MANAGEMENT-PROJECTION-001.json",
        "work_qml": root / "apps/fa3-control-center/qml/WorkManagementPage.qml",
    }
    fs: list[dict[str, Any]] = []
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        return {"schema": "fa3.coordination-gate-report.v1", "gate_id": GATE_ID, "result": "FAIL",
                "findings": [finding("COORD-001", "Required coordination materialization file missing", missing=missing)]}

    profile = loadj(paths["profile"])
    contracts = loadj(paths["contracts"])
    decision = loadj(paths["decision"])
    intent = loadj(paths["intent"])
    assessment = loadj(paths["assessment"])
    enforcement = loadj(paths["enforcement"])
    work = loadj(paths["work_management"])
    qml = paths["work_qml"].read_text(encoding="utf-8")

    if profile.get("id") != PROFILE_ID or profile.get("new_capability") is not False or profile.get("new_architectural_authority") is not False or profile.get("capability_count") != CAPABILITY_COUNT:
        fs.append(finding("COORD-002", "Profile capability/authority invariant drift"))

    boundaries = profile.get("authority_boundaries", {})
    expected = {
        "authorization": "FA3-AUTH-SECURITY-GOV-001",
        "resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "decision_support": "FA3-DECISION-FABRIC-001",
        "execution": "EXISTING_FA3_WORKFLOW_AUTHORITY_ONLY",
        "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    }
    if any(boundaries.get(k) != v for k, v in expected.items()):
        fs.append(finding("COORD-003", "Existing authority binding drift", expected=expected, actual=boundaries))

    if contracts.get("id") != CONTRACT_ID or contracts.get("authority_delta") != 0 or contracts.get("capability_delta") != 0:
        fs.append(finding("COORD-004", "Coordination contract identity/delta drift"))
    if contracts.get("event_contract", {}).get("event_occurrence_implies_action_authorization") is not False:
        fs.append(finding("COORD-005", "Coordination event may authorize action"))
    if contracts.get("objective_contract", {}).get("provider_may_own_objective_identity") is not False:
        fs.append(finding("COORD-006", "Provider may own canonical objective identity"))
    if contracts.get("dependency_contract", {}).get("required_cycles") != "DENY_FAIL_CLOSED":
        fs.append(finding("COORD-007", "Required dependency cycles are not fail-closed"))

    if decision.get("status") != "CANONICAL_CLOSED" or decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0:
        fs.append(finding("COORD-008", "Decision record is not a zero-delta canonical closure"))

    if intent.get("project_id") != PROFILE_ID or intent.get("proposed_authority_roles") != [] or intent.get("hardware_audit", {}).get("cpu_only_viable") is not True or intent.get("hardware_audit", {}).get("vendor_neutral") is not True:
        fs.append(finding("COORD-009", "Application intent violates hardware/authority baseline"))

    if assessment.get("result") != "PASS" or assessment.get("implementation_readiness") != "READY_FOR_NORMAL_ADMISSION" or assessment.get("coexistence", {}).get("result") != "PASS":
        fs.append(finding("COORD-010", "Reuse Discovery assessment is not PASS/ready/coexistent"))

    sources = profile.get("external_pattern_sources", [])
    required_sources = {"Temporal", "Dagster", "Prefect", "Kestra", "Backstage", "OpenTelemetry"}
    present = {entry.get("name") for entry in sources if isinstance(entry, dict)}
    unsafe = [entry.get("name") for entry in sources if isinstance(entry, dict) and (entry.get("reuse_mode") != "PATTERN_ONLY" or entry.get("code_copied") is not False)]
    if not required_sources.issubset(present) or unsafe:
        fs.append(finding("COORD-011", "External pattern-source boundary drift", missing=sorted(required_sources-present), unsafe=unsafe))

    future = profile.get("future_optional_bindings", {})
    if future.get("task_manager") != "PENDING_CANONICAL_MATERIALIZATION" or future.get("logistics") != "PENDING_CANONICAL_MATERIALIZATION" or future.get("hard_dependency") is not False:
        fs.append(finding("COORD-012", "Future Task Manager/Logistics binding became a hard dependency"))

    sections = work.get("gui_surface", {}).get("sections", [])
    projection = work.get("coordination_projection", {})
    if "COORDINATION" not in sections or projection.get("profile_id") != PROFILE_ID or projection.get("view_kind") != "READ_ONLY_COORDINATION_STATE_PROJECTION":
        fs.append(finding("COORD-013", "Work Management coordination projection missing or invalid"))

    qml_required = [
        'TabButton { text: "Coordination" }',
        "property var objectives: []",
        "property var coordinationBlockers: []",
        "property var coordinationHandoffs: []",
        "Read-only Objective / Dependency / Handoff / Blocker projection",
    ]
    absent = [token for token in qml_required if token not in qml]
    if absent:
        fs.append(finding("COORD-014", "Coordination GUI projection is incomplete", absent=absent))

    if enforcement.get("gate_id") != GATE_ID or enforcement.get("p0_invariants") != P0_INVARIANTS:
        fs.append(finding("COORD-015", "Coordination enforcement invariant set drift"))

    regressions = run_regressions()
    if regressions["result"] != "PASS":
        fs.append(finding("COORD-016", "Objective coordination executable regressions failed", regressions=regressions))

    return {
        "schema": "fa3.coordination-gate-report.v1", "gate_id": GATE_ID, "profile_id": PROFILE_ID,
        "result": "PASS" if not fs else "FAIL", "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0, "new_architectural_authorities": 0, "regressions": regressions, "findings": fs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
