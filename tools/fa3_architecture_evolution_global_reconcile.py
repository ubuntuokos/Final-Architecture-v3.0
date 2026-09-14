#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from fa3_release_baseline import load_active_release_baseline  # noqa: E402
import fa3_buzz_global_reconcile as common  # noqa: E402

GATE_ID = "FA3-ARCHITECTURE-EVOLUTION-GATESET-001"
GATE_RECORD_ID = "FA3-GATE-ARCHITECTURE-EVOLUTION-001"
DECISION_ID = "FA3-DEC-ARCHITECTURE-EVOLUTION-2026-09-14"
RELEASE = common.RELEASE
POLICY = "canonical/enforcement-policy.json"
ENFORCER = "src/fa3_enforce.py"


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write(rel: str, obj: dict[str, Any]) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def active_capability_count() -> int:
    return load_active_release_baseline(ROOT).capability_count


def patch_policy() -> None:
    policy = load(POLICY)
    gates = policy.setdefault("mandatory_reference_gates", [])
    if GATE_ID not in gates:
        gates.append(GATE_ID)
    policy["architecture_evolution_gate_id"] = GATE_ID
    policy["architecture_evolution_gate_record_id"] = GATE_RECORD_ID
    policy["architecture_evolution_decision_id"] = DECISION_ID
    policy["architecture_evolution_current_host_promotion_claim"] = False
    write(POLICY, policy)


def patch_global_enforcer() -> None:
    path = ROOT / ENFORCER
    text = path.read_text(encoding="utf-8")
    import_line = "from fa3_architecture_evolution_gate import gate as architecture_evolution_gate\n"
    if import_line not in text:
        anchor = "from fa3_pytorch3d_gate import gate as pytorch3d_gate\n"
        if anchor not in text:
            raise RuntimeError("fa3_enforce.py import anchor missing")
        text = text.replace(anchor, anchor + import_line, 1)

    policy_check = (
        "    if \"FA3-ARCHITECTURE-EVOLUTION-GATESET-001\" not in pol.get(\"mandatory_reference_gates\",[]):\n"
        "        fs.append(finding(\"FA3-STATIC-101\",\"Architecture evolution trust-root/compute/promotion/OCI gate is not bound into global enforcement policy\"))\n"
    )
    if policy_check not in text:
        anchor = (
            "    if \"FA3-OPENFX-INTEROPERABILITY-GATESET-001\" not in pol.get(\"mandatory_reference_gates\",[]):\n"
            "        fs.append(finding(\"FA3-STATIC-099\",\"OpenFX VFX plug-in interoperability gate is not bound into global enforcement policy\"))\n"
        )
        if anchor not in text:
            raise RuntimeError("fa3_enforce.py mandatory gate anchor missing")
        text = text.replace(anchor, anchor + policy_check, 1)

    execution_check = (
        "    architecture_evolution_ref=architecture_evolution_gate(root)\n"
        "    if architecture_evolution_ref[\"result\"]!=\"PASS\":\n"
        "        fs.append(finding(\"FA3-STATIC-102\",\"Architecture evolution canonical/executable gate failed\",architecture_evolution_gate=architecture_evolution_ref))\n"
    )
    if execution_check not in text:
        anchor = (
            "    openfx_ref=openfx_interop_gate(root)\n"
            "    if openfx_ref[\"result\"]!=\"PASS\":\n"
            "        fs.append(finding(\"FA3-STATIC-100\",\"OpenFX VFX plug-in interoperability gate failed\",openfx_interoperability_gate=openfx_ref))\n"
        )
        if anchor not in text:
            raise RuntimeError("fa3_enforce.py execution anchor missing")
        text = text.replace(anchor, anchor + execution_check, 1)

    path.write_text(text, encoding="utf-8")


def patch_release_semantics(snapshot_head: str) -> None:
    release = load(RELEASE)
    policy = load(POLICY)
    release["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    release["architecture_evolution_reconciliation"] = {
        "gate_id": GATE_ID,
        "gate_record_id": GATE_RECORD_ID,
        "decision_id": DECISION_ID,
        "reconciliation_status": "GLOBAL_PROJECTION_RECONCILED_REFERENCE_GATE_PASS_CURRENT_HOST_UNCHANGED",
        "federated_lifecycle": "CENTRALIZED_TRUST_ROOT",
        "capability_count_semantics": "RELEASE_SCOPED",
        "compute_admission": "MULTIDIMENSIONAL_WORKLOAD_ENVELOPE",
        "dependency_promotion": "POLICY_CONTROLLED_CURRENT_HOST_AND_ACCEPTANCE_REQUIRED",
        "oci_execution": "ROOTLESS_DIGEST_PINNED_FAIL_CLOSED",
        "ffmpeg_zero_copy": "UPSTREAM_CANDIDATE_NO_PERMANENT_FORK",
        "reference_gate_required": True,
        "current_host_runtime_evidence": "UNCHANGED_NOT_CLAIMED",
        "production_promotion_claimed": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": active_capability_count(),
        "snapshot_head": snapshot_head,
    }
    note = (
        "FA3 architecture evolution is globally reconciled as a zero-capability, zero-authority "
        "policy projection: federated domain lifecycle retains the central trust root; hardware "
        "admission is multidimensional; staging has no current-host/production authority; OCI is "
        "digest-pinned and fail-closed; current-host evidence and production promotion remain unchanged."
    )
    notes = release.setdefault("review_notes", [])
    if note not in notes:
        notes.append(note)
    write(RELEASE, release)


def prepare_only() -> None:
    patch_policy()
    patch_global_enforcer()


def projection_only(snapshot_head: str) -> None:
    current = common.git("rev-parse", "HEAD")
    if current != common.git("rev-parse", snapshot_head):
        raise RuntimeError("projection snapshot must equal current committed HEAD")
    dirty = common.dirty_release_surface_paths()
    if dirty:
        raise RuntimeError(f"projection-only requires clean committed release surface: {dirty}")
    patch_release_semantics(snapshot_head)
    common.regenerate_release(snapshot_head)
    release = load(RELEASE)
    verification = release.setdefault("manifest_verification", {})
    verification["architecture_evolution_reconciliation_generator"] = "tools/fa3_architecture_evolution_global_reconcile.py"
    verification["architecture_evolution_deterministic_regeneration_pass"] = True
    verification["architecture_evolution_snapshot_head"] = snapshot_head
    write(RELEASE, release)
    dirty_after = common.dirty_release_surface_paths()
    if dirty_after != [RELEASE]:
        raise RuntimeError(f"projection-only may modify exactly {RELEASE}; observed: {dirty_after}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FA3 architecture evolution global reconciliation")
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
        print(json.dumps({"result":"PASS","mode":"PREPARE_ONLY","gate_id":GATE_ID}, indent=2))
        return 0
    snapshot = args.snapshot_head or common.git("rev-parse", "HEAD")
    projection_only(snapshot)
    print(json.dumps({"result":"PASS","mode":"PROJECTION_ONLY","gate_id":GATE_ID,"snapshot_head":snapshot}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
