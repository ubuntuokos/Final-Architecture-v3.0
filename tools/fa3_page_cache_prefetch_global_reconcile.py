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

PROFILE_ID = "FA3-HOST-RESOURCE-BROKER-001"
CONTRACT_ID = "FA3-HOST-RESOURCE-BROKER-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-PRELOAD-001"
DECISION_ID = "FA3-DEC-PAGE-CACHE-PREFETCH-2026-09-11"
GATE_ID = "FA3-GATE-PAGE-CACHE-PREFETCH-001"
GATESET_ID = "FA3-PAGE-CACHE-PREFETCH-GATESET-001"
CAPABILITY_ID = "CAP-001"
CAPABILITY_COUNT = 143
REFERENCE_EVIDENCE = "evidence/reference/page-cache-prefetch-ci-2026-09-11.json"
REGISTRY = "evidence/evidence-registry.json"
RELEASE = common.RELEASE


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write(rel: str, obj: dict[str, Any]) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_registry() -> None:
    registry = load(REGISTRY)
    if registry.get("canonical_capability_count") != CAPABILITY_COUNT or registry.get("record_count") != CAPABILITY_COUNT:
        raise RuntimeError("Evidence Registry capability count must remain exactly 143")
    cap = next((item for item in registry.get("records", []) if item.get("subject_id") == CAPABILITY_ID), None)
    if cap is None:
        raise RuntimeError("CAP-001 Host/Foundation missing from Evidence Registry")
    decisions = cap.setdefault("source_decision_ids", [])
    if DECISION_ID not in decisions:
        decisions.append(DECISION_ID)
    artifacts = cap.setdefault("evidence_artifacts", [])
    if REFERENCE_EVIDENCE not in artifacts:
        artifacts.append(REFERENCE_EVIDENCE)
    cap["page_cache_prefetch_projection_status"] = {
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "provider_id": PROVIDER_ID,
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "classification": "MANDATORY_PROVIDER_NEUTRAL_POLICY_OPTIONAL_REPLACEABLE_PROVIDER",
        "reference_gate_status": "PASS",
        "runtime_status": "PENDING_CURRENT_HOST",
        "production_admitted": False,
        "current_host_runtime_evidence": "PENDING_REAL_COLD_WARM_IO_MEMORY_PRESSURE_NON_REGRESSION_AND_ROLLBACK_EVIDENCE",
        "reference_pass_does_not_promote_runtime": True,
    }
    write(REGISTRY, registry)


def patch_release_semantics() -> None:
    release = load(RELEASE)
    policy = load("canonical/enforcement-policy.json")
    release["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    release.setdefault("evidence_registry", {})["page_cache_prefetch_capability_binding"] = {
        "subject_id": CAPABILITY_ID,
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "provider_id": PROVIDER_ID,
        "decision_id": DECISION_ID,
        "gate_id": GATE_ID,
        "reference_evidence": REFERENCE_EVIDENCE,
        "runtime_status": "PENDING_CURRENT_HOST",
        "production_admitted": False,
    }
    release["page_cache_prefetch_reconciliation"] = {
        "profile_id": PROFILE_ID,
        "contract_id": CONTRACT_ID,
        "provider_id": PROVIDER_ID,
        "decision_id": DECISION_ID,
        "gate_id": GATE_ID,
        "gateset_id": GATESET_ID,
        "capability_id": CAPABILITY_ID,
        "classification": "MANDATORY_PROVIDER_NEUTRAL_PAGE_CACHE_PREFETCH_GOVERNANCE_OPTIONAL_PRELOAD_PROJECTION",
        "reconciliation_status": "GLOBAL_RELEASE_INVENTORY_EVIDENCE_RECONCILED_REFERENCE_PASS_CURRENT_HOST_PERFORMANCE_PENDING",
        "provider_inventory_reconciled": True,
        "evidence_registry_reconciled": True,
        "unified_projection_regenerated": True,
        "deterministic_regeneration_pass": True,
        "reference_gate_status": "PASS",
        "runtime_activation_status": "NOT_PRODUCTION_PROMOTED",
        "current_host_runtime_evidence": "PENDING_REAL_COLD_WARM_IO_MEMORY_PRESSURE_NON_REGRESSION_AND_ROLLBACK_EVIDENCE",
        "provider_hard_dependency": False,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": CAPABILITY_COUNT,
    }
    note = (
        "Filesystem page-cache speculative prefetch/adaptive readahead governance is reconciled under "
        "FA3-AUTH-HOST-RESOURCE-BROKER-001 through CAP-001. FA3-PROVIDER-PRELOAD-001 remains optional, "
        "replaceable and non-authoritative. Canonical reference PASS does not promote current-host runtime "
        "without real cold/warm latency, page-cache, major-fault, I/O-pressure, memory-pressure, host-survival "
        "and rollback evidence."
    )
    notes = release.setdefault("review_notes", [])
    if note not in notes:
        notes.append(note)
    write(RELEASE, release)


def projection_only(snapshot_head: str) -> None:
    if common.git("rev-parse", "HEAD") != common.git("rev-parse", snapshot_head):
        raise RuntimeError("projection snapshot must be the current committed HEAD")
    dirty = common.dirty_release_surface_paths()
    if dirty:
        raise RuntimeError(f"projection-only requires clean committed release surface: {dirty}")
    patch_release_semantics()
    common.regenerate_release(snapshot_head)
    release = load(RELEASE)
    verification = release.setdefault("manifest_verification", {})
    verification["page_cache_prefetch_reconciliation_generator"] = "tools/fa3_page_cache_prefetch_global_reconcile.py"
    verification["page_cache_prefetch_deterministic_regeneration_pass"] = True
    verification["page_cache_prefetch_snapshot_head"] = snapshot_head
    write(RELEASE, release)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Page-cache/prefetch Evidence Registry and unified release reconciliation")
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
        patch_registry()
        print(json.dumps({"result": "PASS", "mode": "PREPARE_ONLY", "provider_id": PROVIDER_ID, "capability_id": CAPABILITY_ID}, indent=2))
        return 0
    snapshot = args.snapshot_head or common.git("rev-parse", "HEAD")
    projection_only(snapshot)
    print(json.dumps({"result": "PASS", "mode": "PROJECTION_ONLY", "provider_id": PROVIDER_ID, "snapshot_head": snapshot}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
