#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fa3_release_baseline import module_active_capability_count
from fa3_sysctl_governance import (
    SysctlGovernanceDenied,
    build_change_plan,
    classify_key,
    validate_persistence_path,
    validate_post_apply,
    validate_rollback,
    OBSERVE_ONLY,
    WORKLOAD_SENSITIVE,
    SAFETY_SECURITY_SENSITIVE,
    FORBIDDEN_AUTOMATIC_MUTATION,
)

PROFILE = "canonical/profiles/FA3-SYSCTL-HOST-TUNING-GOVERNANCE-001.json"
CONTRACT = "canonical/contracts/FA3-SYSCTL-HOST-TUNING-GOVERNANCE-CONTRACTS-001.json"
ENFORCEMENT = "canonical/sysctl-host-tuning-governance-enforcement.json"
GATE_ID = "FA3-GATE-SYSCTL-HOST-TUNING-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)


def loadj(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def check(name: str, value: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if value else "FAIL", "detail": detail}


def denied(call: Callable[[], object]) -> bool:
    try:
        call()
    except SysctlGovernanceDenied:
        return True
    return False


def evaluate(root: Path) -> dict[str, Any]:
    profile = loadj(root, PROFILE)
    contract = loadj(root, CONTRACT)
    enforcement = loadj(root, ENFORCEMENT)
    invariants = set(contract.get("invariants", []))
    enforced = set(enforcement.get("rules", []))

    current = {
        "vm.swappiness": "60",
        "vm.max_map_count": "65530",
        "kernel.kptr_restrict": "1",
        "kernel.core_pattern": "core",
    }

    admitted = build_change_plan(
        current,
        {"vm.swappiness": "40"},
        mode="EPHEMERAL_MUTATION",
        hrb_authorized=True,
        explicit_user_approval=True,
        benchmark_evidence=True,
        rollback_ready=True,
    )
    persistent = build_change_plan(
        current,
        {"vm.swappiness": "40"},
        mode="PERSISTENT_MUTATION",
        hrb_authorized=True,
        explicit_user_approval=True,
        benchmark_evidence=True,
        rollback_ready=True,
        persistence_path="/etc/sysctl.d/90-fa3-memory-pressure.conf",
    )

    checks = [
        check(
            "baseline-stable",
            profile.get("capability_count") == CAPABILITY_COUNT == contract.get("capability_count") == enforcement.get("capability_count"),
            "sysctl governance follows the active 175-capability baseline without adding a capability",
        ),
        check(
            "no-new-authority",
            profile.get("new_architectural_authority") is False
            and contract.get("new_architectural_authority") is False
            and profile.get("authority", {}).get("resource_admission") == "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "sysctl remains projection beneath HRB and security governance",
        ),
        check(
            "enforcement-complete",
            enforcement.get("fail_closed") is True
            and enforcement.get("mandatory_rule_count") == 24
            and len(invariants) == 24
            and invariants == enforced,
            "all sysctl invariants are represented by fail-closed enforcement",
        ),
        check(
            "observe-only-default",
            profile.get("default_mode") == "OBSERVE_ONLY"
            and profile.get("policy", {}).get("universal_optimization_profile") == "FORBIDDEN",
            "default behavior only observes; no universal optimization profile exists",
        ),
        check(
            "classification",
            classify_key("vm.swappiness") == WORKLOAD_SENSITIVE
            and classify_key("kernel.kptr_restrict") == SAFETY_SECURITY_SENSITIVE
            and classify_key("kernel.core_pattern") == FORBIDDEN_AUTOMATIC_MUTATION
            and classify_key("net.ipv4.tcp_syncookies") == OBSERVE_ONLY,
            "sysctl keys are classified before any mutation request",
        ),
        check(
            "observe-only-cannot-mutate",
            denied(lambda: build_change_plan(current, {"vm.swappiness": "40"})),
            "observe-only default rejects mutation",
        ),
        check(
            "unknown-key-mutation-denied",
            denied(lambda: build_change_plan(
                current,
                {"net.ipv4.tcp_syncookies": "1"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                benchmark_evidence=True,
                rollback_ready=True,
            )),
            "unknown/unclassified mutation is fail-closed",
        ),
        check(
            "forbidden-key-denied",
            denied(lambda: build_change_plan(
                current,
                {"kernel.core_pattern": "|/tmp/helper"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                security_authorized=True,
                explicit_user_approval=True,
                benchmark_evidence=True,
                rollback_ready=True,
            )),
            "forbidden automatic mutation cannot be approved",
        ),
        check(
            "hrb-authorization-required",
            denied(lambda: build_change_plan(
                current, {"vm.swappiness": "40"},
                mode="EPHEMERAL_MUTATION",
                explicit_user_approval=True,
                benchmark_evidence=True,
                rollback_ready=True,
            )),
            "host-global sysctl mutation requires HRB authorization",
        ),
        check(
            "explicit-approval-required",
            denied(lambda: build_change_plan(
                current, {"vm.swappiness": "40"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                benchmark_evidence=True,
                rollback_ready=True,
            )),
            "host-global sysctl mutation requires explicit approval",
        ),
        check(
            "benchmark-required",
            denied(lambda: build_change_plan(
                current, {"vm.swappiness": "40"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                rollback_ready=True,
            )),
            "workload-sensitive sysctl mutation requires benchmark evidence",
        ),
        check(
            "security-authorization-required",
            denied(lambda: build_change_plan(
                current, {"kernel.kptr_restrict": "2"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                rollback_ready=True,
            )),
            "security-sensitive sysctl mutation requires security authorization",
        ),
        check(
            "rollback-required",
            denied(lambda: build_change_plan(
                current, {"vm.swappiness": "40"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                benchmark_evidence=True,
            )),
            "sysctl mutation requires rollback readiness",
        ),
        check(
            "ephemeral-admission",
            admitted["status"] == "ADMITTED"
            and admitted["mode"] == "EPHEMERAL_MUTATION"
            and admitted["changes"][0]["rollback_value"] == "60",
            "admitted ephemeral plan binds pre-state and rollback value",
        ),
        check(
            "persistent-namespaced",
            persistent["status"] == "ADMITTED"
            and persistent["persistence_path"] == "/etc/sysctl.d/90-fa3-memory-pressure.conf"
            and validate_persistence_path(persistent["persistence_path"]),
            "persistent admission requires namespaced FA3 sysctl.d path",
        ),
        check(
            "unsafe-persistence-paths-denied",
            all(not validate_persistence_path(x) for x in [
                "/etc/sysctl.conf",
                "/etc/sysctl.d/99-sysctl.conf",
                "/etc/sysctl.d/90-fa3.conf",
                "/etc/sysctl.d/50-vendor.conf",
            ]),
            "FA3 does not overwrite global/distribution/user sysctl files",
        ),
        check(
            "post-apply-validation",
            validate_post_apply(admitted, {"vm.swappiness": "40"})["status"] == "PASS"
            and validate_post_apply(admitted, {"vm.swappiness": "60"})["status"] == "FAIL",
            "post-apply state must match admitted plan",
        ),
        check(
            "rollback-validation",
            validate_rollback(admitted, {"vm.swappiness": "60"})["status"] == "PASS"
            and validate_rollback(admitted, {"vm.swappiness": "40"})["status"] == "FAIL",
            "rollback must restore captured pre-state",
        ),
        check(
            "hardware-safety-bound",
            profile.get("hardware_safety_envelope", {}).get("decision_id") == "FA3-DEC-HARDWARE-SAFETY-2026-09-26"
            and profile.get("hardware_safety_envelope", {}).get("bypass") is False,
            "Hardware Safety Envelope remains non-bypassable",
        ),
        check(
            "coexistence",
            profile.get("coexistence", {}).get("host_non_interference_required") is True
            and profile.get("coexistence", {}).get("independent_tuning_tools_must_not_be_replaced") is True,
            "sysctl governance preserves host non-interference and independent tooling",
        ),
        check(
            "current-host-claim-honest",
            profile.get("current_host_runtime_promotion_claim") is False
            and enforcement.get("current_host_runtime_promotion_claim") is False
            and admitted.get("global_promotion_claim") is False,
            "static governance and change planning do not create current-host promotion",
        ),
        check(
            "capability-binding",
            set(profile.get("covered_capabilities", [])) == {"CAP-063", "CAP-065"},
            "sysctl governance strengthens existing tuning capabilities rather than creating a new one",
        ),
        check(
            "persistent-separate-admission",
            denied(lambda: build_change_plan(
                current, {"vm.swappiness": "40"},
                mode="PERSISTENT_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                benchmark_evidence=True,
                rollback_ready=True,
                persistence_path="/etc/sysctl.d/50-vendor.conf",
            )),
            "persistent host mutation cannot reuse an arbitrary config path",
        ),
        check(
            "no-change-is-safe",
            build_change_plan(current, {"vm.swappiness": "60"})["status"] == "NO_CHANGE",
            "requests that do not alter state require no mutation",
        ),
    ]

    passed = all(item["status"] == "PASS" for item in checks)
    return {
        "schema": "fa3.sysctl-host-tuning-governance-evidence.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if passed else "FAIL",
        "scope": "CANONICAL_POLICY_AND_CHANGE_PLANNING",
        "current_host_runtime_promotion_claim": False,
        "checks": checks,
        "summary": {
            "passed": sum(item["status"] == "PASS" for item in checks),
            "total": len(checks),
        },
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/sysctl-host-tuning-governance-gate-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = evaluate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
