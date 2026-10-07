"""Design/executable gate for FA3-ACCEL-GUARD-001."""
from __future__ import annotations

import json
from pathlib import Path

from fa3_accelerator_guard import (
    AcceleratorSnapshot,
    ClientUsage,
    DecisionAction,
    GuardMode,
    Origin,
    SavedPolicy,
    WorkloadRequest,
    action_plan,
    evaluate_request,
    resolve_actor,
    submit_decision,
)


REQUIRED_PROFILE_INVARIANTS = {
    "startup_scan": True,
    "runtime_scan": True,
    "gpu_and_npu": True,
    "user_importance_must_not_be_inferred": True,
    "automatic_arbitration_requires_explicit_saved_policy": True,
    "forced_external_termination_without_user_or_policy": "FORBIDDEN",
    "silent_fa3_workload_sacrifice": "FORBIDDEN",
    "alternative_must_match_execution_path": True,
    "physical_device_presence_not_sufficient_for_execution": True,
    "translation_backend_never_implicit": True,
}


def run_gate(repo_root: Path) -> list[str]:
    failures: list[str] = []
    profile = json.loads((repo_root / "canonical/profiles/FA3-ACCEL-GUARD-001.json").read_text())
    contracts = json.loads((repo_root / "canonical/contracts/FA3-ACCEL-GUARD-CONTRACTS-001.json").read_text())

    if profile.get("parent_profile_id") != "FA3-HOST-RESOURCE-BROKER-001":
        failures.append("guard must remain an HRB subprofile")
    if profile.get("new_capability") is not False:
        failures.append("guard must project into existing CAP-006 for this release")
    if profile.get("new_architectural_authority") is not False:
        failures.append("guard must not create a parallel resource authority")
    if profile.get("default_mode") != "RECOMMEND":
        failures.append("default mode must be RECOMMEND")

    mandatory = profile.get("mandatory_semantics", {})
    for key, expected in REQUIRED_PROFILE_INVARIANTS.items():
        if mandatory.get(key) != expected:
            failures.append(f"mandatory_semantics.{key} must equal {expected!r}")

    decision_contract = contracts.get("decision_contract", {})
    if decision_contract.get("default_actor") != "USER":
        failures.append("decision default actor must be USER")
    if decision_contract.get("policy_actor_allowed_only_if_explicit_saved_policy") is not True:
        failures.append("policy automation must require explicit saved policy")
    if decision_contract.get("force_termination_requires_separate_explicit_authorization") is not True:
        failures.append("force termination must require separate authorization")

    gib = 1024 ** 3
    busy = AcceleratorSnapshot(
        "gpu-1", "GPU", 24 * gib,
        clients=(ClientUsage(18421, "blender", Origin.EXTERNAL_KNOWN, 17 * gib, 0.85),),
        safety_headroom_bytes=1 * gib,
    )
    free = AcceleratorSnapshot("gpu-2", "GPU", 24 * gib, safety_headroom_bytes=1 * gib)
    request = WorkloadRequest("fa3-comfy-427", 12 * gib, "GPU")
    conflict = evaluate_request(busy, request, candidates=(busy, free), conflict_id="gate-conflict")
    if conflict is None:
        failures.append("busy accelerator did not produce conflict")
    else:
        if conflict.recommendation.action is not DecisionAction.MOVE_FA3:
            failures.append("alternative accelerator was not recommended")
        actor, policy = resolve_actor(conflict, GuardMode.RECOMMEND, ())
        if actor != "USER" or policy is not None:
            failures.append("RECOMMEND mode must keep decision with USER")
        submit_decision(conflict, DecisionAction.MOVE_FA3)
        plan = action_plan(conflict)
        if plan["force_terminate_external"] is not False:
            failures.append("executor plan must never imply force termination by default")

    if conflict is not None:
        bad_policy = SavedPolicy(
            "bad", "blender", "fa3-comfy", DecisionAction.PREFER_FA3,
            explicit_user_created=False,
        )
        actor, _ = resolve_actor(conflict, GuardMode.POLICY, (bad_policy,))
        if actor != "USER":
            failures.append("non-explicit policy incorrectly acquired decision authority")

    return failures


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[1]
    failures = run_gate(root)
    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        raise SystemExit(1)
    print("PASS: FA3-ACCEL-GUARD-001 design/executable gate")
