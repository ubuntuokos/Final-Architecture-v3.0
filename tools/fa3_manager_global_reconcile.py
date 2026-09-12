#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import fa3_buzz_global_reconcile as common  # noqa: E402

PROFILE_ID = "FA3-MANAGER-001"
CONTRACT_ID = "FA3-MANAGER-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-MANAGER-LOCAL-001"
DECISION_ID = "FA3-DEC-MANAGER-2026-09-12"
GATE_ID = "FA3-GATE-MANAGER-001"
GATESET_ID = "FA3-MANAGER-GATESET-001"
CONFORMANCE_ID = "FA3-MANAGER-CONFORMANCE-MATRIX-001"
RUNTIME_ID = "FA3-MANAGER-RUNTIME-CONFORMANCE-001"
CAPABILITY_COUNT = 143
POLICY = "canonical/enforcement-policy.json"
RELEASE = common.RELEASE
REFERENCE_EVIDENCE = "evidence/reference/fa3-manager-reference-pending.json"
RECONCILIATION_STATUS = "GLOBAL_RELEASE_INVENTORY_RECONCILED_REFERENCE_GATE_ENFORCED_CURRENT_HOST_PENDING"


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write(rel: str, obj: dict[str, Any]) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_policy() -> None:
    policy = load(POLICY)
    if policy.get("canonical_capability_count") != CAPABILITY_COUNT:
        raise RuntimeError("FA3 capability count must remain exactly 143")
    gates = policy.setdefault("mandatory_reference_gates", [])
    if GATESET_ID not in gates:
        try:
            coach_index = gates.index("FA3-COACH-GATESET-001")
        except ValueError:
            gates.append(GATESET_ID)
        else:
            gates.insert(coach_index + 1, GATESET_ID)
    if len(gates) != len(set(gates)):
        raise RuntimeError("mandatory_reference_gates must remain unique")
    write(POLICY, policy)


def patch_release_semantics() -> None:
    release = load(RELEASE)
    policy = load(POLICY)
    if policy.get("canonical_capability_count") != CAPABILITY_COUNT:
        raise RuntimeError("policy capability count drift")
    release["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    release["manager_reconciliation"] = {
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "provider_id": PROVIDER_ID,
        "decision_id": DECISION_ID,
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "conformance_matrix_id": CONFORMANCE_ID,
        "runtime_conformance_id": RUNTIME_ID,
        "classification": "P0_MUST_PROVIDER_NEUTRAL_OPERATIONAL_WORK_MANAGEMENT_DELEGATION_EVIDENCE_CLOSURE_OVERLAY",
        "reconciliation_status": RECONCILIATION_STATUS,
        "direct_execution": "FORBIDDEN",
        "typed_action_delegation": "REQUIRED",
        "dependency_graph": "ACYCLIC_REQUIRED",
        "implicit_done": "FORBIDDEN",
        "verified_closure": "ACCEPTANCE_PLUS_EVIDENCE_REQUIRED",
        "knowledge_gap_delegation": "FA3-MENTOR-001",
        "coaching_delegation": "FA3-COACH-001",
        "capability_provider_resolution": "PROPOSAL_ONLY",
        "reference_evidence": REFERENCE_EVIDENCE,
        "reference_gate_status": "CI_ENFORCED",
        "runtime_status": "PENDING_CURRENT_HOST",
        "production_admitted": False,
        "current_host_runtime_promotion_claimed": False,
        "provider_is_architectural_authority": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
    }
    note = (
        "FA3-MANAGER-001 is globally reconciled as a P0/MUST provider-neutral operational management overlay. "
        "It owns no execution or architectural authority; typed delegation, acyclic dependencies, explicit work "
        "states and evidence-backed VERIFIED closure are mandatory. FA3-MENTOR-001 and FA3-COACH-001 retain their "
        "respective boundaries; capability count stays 143 and current-host promotion remains evidence-gated."
    )
    notes = release.setdefault("review_notes", [])
    if note not in notes:
        notes.append(note)
    write(RELEASE, release)


def prepare_only() -> None:
    patch_policy()


def projection_only(snapshot_head: str) -> None:
    snapshot = common.git("rev-parse", "--verify", f"{snapshot_head}^{{commit}}")
    current = common.git("rev-parse", "HEAD")
    if snapshot != current:
        raise RuntimeError("projection snapshot must equal the clean checked-out HEAD before projection regeneration")
    dirty = common.dirty_release_surface_paths()
    if dirty:
        raise RuntimeError(f"projection-only requires clean committed release surface: {dirty}")

    patch_release_semantics()
    common.regenerate_release(snapshot)

    release = load(RELEASE)
    verification = release.setdefault("manifest_verification", {})
    verification["manager_reconciliation_generator"] = "tools/fa3_manager_global_reconcile.py"
    verification["manager_deterministic_regeneration_pass"] = True
    verification["manager_snapshot_head"] = snapshot
    write(RELEASE, release)

    dirty_after = common.dirty_release_surface_paths()
    if dirty_after != [RELEASE]:
        raise RuntimeError(
            "Manager projection-only mode may modify exactly the unified release projection; observed: "
            + ", ".join(dirty_after)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FA3 Manager deterministic global reconciliation")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--projection-only", action="store_true")
    parser.add_argument("--snapshot-head")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prepare_only:
        if args.snapshot_head:
            raise RuntimeError("--snapshot-head is projection-only")
        prepare_only()
        print(json.dumps({"result": "PASS", "mode": "PREPARE_ONLY", "profile_id": PROFILE_ID, "gateset_id": GATESET_ID}, indent=2))
        return 0

    snapshot_head = args.snapshot_head or common.git("rev-parse", "HEAD")
    projection_only(snapshot_head)
    print(json.dumps({"result": "PASS", "mode": "PROJECTION_ONLY", "profile_id": PROFILE_ID, "snapshot_head": snapshot_head, "reconciliation_status": RECONCILIATION_STATUS}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
