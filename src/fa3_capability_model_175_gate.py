#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

from fa3_release_baseline import load_active_release_baseline

GATESET_ID = "FA3-CAPABILITY-MODEL-175-GATESET-001"
DECISION_ID = "FA3-DEC-CAPABILITY-MODEL-175-2026-09-26"
MODEL_ID = "FA3-CAPABILITY-MODEL-175-001"
EXPECTED_COUNT = 175
PREVIOUS_COUNT = 143
EXPECTED_NEW = 32
EXPECTED_OBLIGATIONS = 525

def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def evaluate(root: Path):
    root = Path(root).resolve()
    baseline = load_active_release_baseline(root)
    model = loadj(root / "canonical/FA3-CAPABILITY-MODEL-175-001.json")
    decision = loadj(root / "canonical/decisions/FA3-DEC-CAPABILITY-MODEL-175-2026-09-26.json")
    policy = loadj(root / "canonical/enforcement-policy.json")
    governance = loadj(root / "canonical/FA3-GOVERNANCE-TIERING-001.json")
    projection = loadj(root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")
    registry = loadj(root / "evidence/evidence-registry.json")
    with (root / "canonical/conformance-matrix.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ids = [r["capability_id"] for r in rows]
    expected_ids = [f"CAP-{i:03d}" for i in range(1, EXPECTED_COUNT + 1)]
    new_records = registry["records"][PREVIOUS_COUNT:]
    checks = {
        "active-count-175": baseline.capability_count == EXPECTED_COUNT,
        "model-id-count": model.get("id") == MODEL_ID and model.get("canonical_capability_count") == EXPECTED_COUNT,
        "stable-id-range": ids == expected_ids,
        "matrix-cardinality": len(rows) == EXPECTED_COUNT,
        "registry-cardinality": registry.get("canonical_capability_count") == EXPECTED_COUNT and registry.get("record_count") == EXPECTED_COUNT and len(registry.get("records", [])) == EXPECTED_COUNT,
        "policy-mirror": policy.get("canonical_capability_count") == EXPECTED_COUNT,
        "governance-delta": governance.get("canonical_capability_count_before") == PREVIOUS_COUNT and governance.get("canonical_capability_count_after") == EXPECTED_COUNT and governance.get("capability_delta") == EXPECTED_NEW,
        "projection-delta": projection.get("invariants", {}).get("canonical_capability_count") == EXPECTED_COUNT and projection.get("invariants", {}).get("new_capabilities") == EXPECTED_NEW,
        "decision-delta": decision.get("capability_count_before") == PREVIOUS_COUNT and decision.get("capability_count_after") == EXPECTED_COUNT and decision.get("capability_delta") == EXPECTED_NEW and decision.get("authority_delta") == 0,
        "new-records-pending-current-host": len(new_records) == EXPECTED_NEW and all(r.get("status") == "PENDING_CURRENT_HOST" and r.get("runtime_conformance") == "EVIDENCE-PENDING" and r.get("blocking") is True for r in new_records),
        "no-document-runtime-promotion": all(r.get("promotion_state") == "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE" for r in new_records),
        "obligation-count": model.get("runtime_truth", {}).get("required_total_obligations") == EXPECTED_OBLIGATIONS,
        "mandatory-gate": GATESET_ID in policy.get("mandatory_reference_gates", []),
    }
    failed = [name for name, ok in checks.items() if not ok]
    return {
        "schema": "fa3.capability-model-175-gate-report.v1",
        "gate_set_id": GATESET_ID,
        "result": "PASS" if not failed else "FAIL",
        "checks": checks,
        "blocking_findings": failed,
        "capability_count": baseline.capability_count,
        "new_capabilities": EXPECTED_NEW,
        "required_current_host_obligations": EXPECTED_OBLIGATIONS,
        "current_host_closure_claim": False,
    }

def main():
    root = Path(__file__).resolve().parents[1]
    result = evaluate(root)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
