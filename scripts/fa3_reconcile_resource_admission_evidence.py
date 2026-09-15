#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ACCEPTANCE_SCHEMA = "fa3.resource-admission-current-host.production-evidence-acceptance.v1"
ACCEPTED_STATUS = "REAL_EXECUTION_PASS_CAPTURED_PER_WORKLOAD_READMISSION_REQUIRED"
ACCEPTED_EVIDENCE_PATH = Path("evidence/reference/resource-admission-current-host-pass.json")
GATE_PATH = Path("canonical/FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001.json")
DECISION_PATH = Path("canonical/decisions/FA3-DEC-RESOURCE-ADMISSION-CURRENT-HOST-2026-09-14.json")
MANIFEST_PATH = Path("fa3-current-host/manifest.json")
REGISTRY_PATH = Path("evidence/evidence-registry.json")
DECISION_ID = "FA3-DEC-RESOURCE-ADMISSION-CURRENT-HOST-2026-09-14"
GATE_ID = "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001"
CONTRACT_ID = "FA3-RESOURCE-ADMISSION-CONTRACTS-001"
CAPABILITY_ID = "CAP-006"
CAPABILITY_NAME = "Resource Fabric"
EVIDENCE_LEVEL = "CURRENT_HOST_RESOURCE_ADMISSION_PASS"


class ReconcileError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ReconcileError(f"JSON root must be object: {path}")
    return data


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _validate_acceptance(record: dict[str, Any]) -> None:
    if record.get("schema") != ACCEPTANCE_SCHEMA:
        raise ReconcileError("acceptance schema mismatch")
    if record.get("status") != ACCEPTED_STATUS:
        raise ReconcileError("acceptance status mismatch")
    subject = record.get("subject")
    if not isinstance(subject, dict):
        raise ReconcileError("acceptance subject missing")
    if subject.get("capability_id") != CAPABILITY_ID or subject.get("gate_id") != GATE_ID:
        raise ReconcileError("acceptance subject mismatch")
    if record.get("claims") != [EVIDENCE_LEVEL]:
        raise ReconcileError("acceptance claim mismatch")
    non_claims = record.get("non_claims")
    if not isinstance(non_claims, list) or "GLOBAL_FA3_PROMOTION" not in non_claims or "PROVIDER_RUNTIME_E2E" not in non_claims:
        raise ReconcileError("acceptance non-claims incomplete")
    projection = record.get("projection_semantics")
    if not isinstance(projection, dict):
        raise ReconcileError("projection semantics missing")
    if projection.get("global_promotion_claim") is not False:
        raise ReconcileError("acceptance cannot claim global promotion")
    if projection.get("provider_runtime_e2e_claim") is not False:
        raise ReconcileError("acceptance cannot claim provider runtime E2E")
    if projection.get("capability_delta") != 0 or projection.get("authority_delta") != 0:
        raise ReconcileError("acceptance capability/authority delta must be zero")
    archival = record.get("archival_semantics")
    if not isinstance(archival, dict):
        raise ReconcileError("archival semantics missing")
    if archival.get("historical_execution_pass") is not True:
        raise ReconcileError("historical execution pass not proven")
    if archival.get("current_or_future_workload_authorization") is not False:
        raise ReconcileError("archival evidence cannot authorize future workloads")
    if archival.get("future_workloads_require_fresh_hrb_lease") is not True:
        raise ReconcileError("fresh HRB lease requirement missing")
    source = record.get("source_evidence")
    if not isinstance(source, dict) or len(str(source.get("receipt_sha256", ""))) != 64:
        raise ReconcileError("receipt digest missing")


def _reconcile_gate(gate: dict[str, Any], acceptance: dict[str, Any]) -> None:
    gate["status"] = ACCEPTED_STATUS
    gate["accepted_production_evidence"] = str(ACCEPTED_EVIDENCE_PATH)
    gate["latest_production_receipt_sha256"] = acceptance["source_evidence"]["receipt_sha256"]
    gate["per_workload_readmission_required"] = True
    gate["global_promotion_claim"] = False
    gate["provider_runtime_e2e_claim"] = False


def _reconcile_decision(decision: dict[str, Any], acceptance: dict[str, Any]) -> None:
    decision["production_evidence_status"] = ACCEPTED_STATUS
    decision["accepted_production_evidence"] = str(ACCEPTED_EVIDENCE_PATH)
    decision["latest_production_receipt_sha256"] = acceptance["source_evidence"]["receipt_sha256"]
    decision["future_workloads_require_fresh_hrb_lease"] = True
    decision["future_workloads_require_fresh_resource_admission"] = True
    decision["global_promotion_claim"] = False


def _reconcile_manifest(manifest: dict[str, Any]) -> None:
    required = manifest.get("required_repository_paths")
    if not isinstance(required, list):
        raise ReconcileError("current-host manifest required_repository_paths missing")
    for path in (
        str(ACCEPTED_EVIDENCE_PATH),
        "canonical/FA3-RESOURCE-ADMISSION-EVIDENCE-ACCEPTANCE-001.json",
        "src/fa3_resource_admission_evidence_acceptance.py",
        "scripts/fa3_reconcile_resource_admission_evidence.py",
        "tests/test_resource_admission_evidence_acceptance.py",
        "tests/test_resource_admission_evidence_reconciliation.py",
    ):
        if path not in required:
            required.append(path)

    surfaces = manifest.get("registered_current_host_surfaces")
    if not isinstance(surfaces, list):
        raise ReconcileError("current-host manifest surfaces missing")
    matches = [item for item in surfaces if isinstance(item, dict) and item.get("name") == "resource-admission"]
    if len(matches) != 1:
        raise ReconcileError("resource-admission surface missing or duplicated")
    surface = matches[0]
    surface["collection_status"] = ACCEPTED_STATUS
    surface["accepted_evidence"] = str(ACCEPTED_EVIDENCE_PATH)
    surface["future_workloads_require_fresh_hrb_lease"] = True
    surface["future_workloads_require_fresh_resource_admission"] = True
    surface["global_promotion_claim"] = False


def _reconcile_registry(registry: dict[str, Any]) -> None:
    if registry.get("canonical_capability_count") != 143 or registry.get("record_count") != 143:
        raise ReconcileError("canonical capability/evidence record count must remain 143")
    records = registry.get("records")
    if not isinstance(records, list) or len(records) != 143:
        raise ReconcileError("evidence registry must contain exactly 143 records")
    matches = [item for item in records if isinstance(item, dict) and item.get("subject_id") == CAPABILITY_ID]
    if len(matches) != 1:
        raise ReconcileError("CAP-006 evidence record missing or duplicated")
    cap = matches[0]
    if cap.get("subject") != CAPABILITY_NAME:
        raise ReconcileError("CAP-006 subject mismatch")

    preserved = {
        "runtime_conformance": cap.get("runtime_conformance"),
        "status": cap.get("status"),
        "blocking": cap.get("blocking"),
        "promotion_state": cap.get("promotion_state"),
    }

    artifacts = cap.get("evidence_artifacts")
    if not isinstance(artifacts, list):
        raise ReconcileError("CAP-006 evidence_artifacts missing")
    if str(ACCEPTED_EVIDENCE_PATH) not in artifacts:
        artifacts.append(str(ACCEPTED_EVIDENCE_PATH))

    decisions = cap.get("source_decision_ids")
    if not isinstance(decisions, list):
        raise ReconcileError("CAP-006 source_decision_ids missing")
    if DECISION_ID not in decisions:
        decisions.append(DECISION_ID)

    cap["resource_admission_current_host_projection_status"] = {
        "contract_id": CONTRACT_ID,
        "gate_id": GATE_ID,
        "accepted_evidence": str(ACCEPTED_EVIDENCE_PATH),
        "state": ACCEPTED_STATUS,
        "evidence_level": EVIDENCE_LEVEL,
        "component_pass_claim": True,
        "historical_execution_pass": True,
        "current_or_future_workload_authorization": False,
        "future_workloads_require_fresh_hrb_lease": True,
        "future_workloads_require_fresh_resource_admission": True,
        "capability_top_level_status_changed": False,
        "global_promotion_claim": False,
        "provider_runtime_e2e_claim": False,
    }

    for key, value in preserved.items():
        if cap.get(key) != value:
            raise ReconcileError(f"CAP-006 top-level field changed unexpectedly: {key}")
    if registry.get("canonical_capability_count") != 143 or registry.get("record_count") != 143 or len(records) != 143:
        raise ReconcileError("reconciliation changed canonical capability count")


def reconcile(root: Path, acceptance_path: Path) -> list[Path]:
    root = root.resolve()
    acceptance = _load(acceptance_path.resolve())
    _validate_acceptance(acceptance)

    gate_path = root / GATE_PATH
    decision_path = root / DECISION_PATH
    manifest_path = root / MANIFEST_PATH
    registry_path = root / REGISTRY_PATH

    gate = _load(gate_path)
    decision = _load(decision_path)
    manifest = _load(manifest_path)
    registry = _load(registry_path)

    _reconcile_gate(gate, acceptance)
    _reconcile_decision(decision, acceptance)
    _reconcile_manifest(manifest)
    _reconcile_registry(registry)

    accepted_path = root / ACCEPTED_EVIDENCE_PATH
    _write(accepted_path, acceptance)
    _write(gate_path, gate)
    _write(decision_path, decision)
    _write(manifest_path, manifest)
    _write(registry_path, registry)
    return [accepted_path, gate_path, decision_path, manifest_path, registry_path]


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile accepted FA3 resource-admission current-host evidence into tracked projections.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--acceptance", required=True)
    args = parser.parse_args()
    try:
        changed = reconcile(Path(args.root), Path(args.acceptance))
    except (OSError, json.JSONDecodeError, ReconcileError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"status": "PASS", "changed": [str(path) for path in changed], "global_promotion_claim": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
