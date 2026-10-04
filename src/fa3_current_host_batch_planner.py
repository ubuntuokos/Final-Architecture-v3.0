#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TEST_KINDS = ("positive", "negative", "rollback")
DEFAULT_BATCH_SIZE = 5


@dataclass(frozen=True)
class Coverage:
    capability_id: str
    test_kind: str
    executor: bool
    qualification: bool
    producer: bool

    @property
    def materialized(self) -> bool:
        return self.executor and self.qualification and self.producer


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def cap_sort_key(capability_id: str) -> tuple[int, str]:
    try:
        return (int(capability_id.split("-", 1)[1]), capability_id)
    except Exception:
        return (10**9, capability_id)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_index(data: dict[str, Any], *, label: str) -> dict[tuple[str, str], dict[str, Any]]:
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{label} entries must be a list")
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in entries:
        if not isinstance(row, dict):
            raise ValueError(f"{label} contains a non-object entry")
        subject = row.get("subject_id")
        test_kind = row.get("test_kind")
        if not isinstance(subject, str) or not isinstance(test_kind, str):
            raise ValueError(f"{label} entry missing subject_id/test_kind")
        key = (subject, test_kind)
        if key in index:
            raise ValueError(f"{label} contains duplicate obligation key: {subject}/{test_kind}")
        index[key] = row
    return index


def _selection_digest(
    capabilities: list[str],
    registry_sha256: dict[str, str],
) -> str:
    payload = json.dumps(
        {
            "capabilities": capabilities,
            "test_kinds": list(TEST_KINDS),
            "registry_sha256": registry_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_plan(root: Path, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")

    evidence = load_json(root / "evidence/evidence-registry.json")
    executors = load_json(root / "canonical/current-host-capability-test-executors.json")
    qualifications = load_json(root / "canonical/current-host-capability-test-qualifications.json")
    producers = load_json(root / "canonical/current-host-capability-qualification-constituent-producers.json")

    capability_ids = sorted(
        [
            row["subject_id"]
            for row in evidence.get("records", [])
            if isinstance(row.get("subject_id"), str) and row["subject_id"].startswith("CAP-")
        ],
        key=cap_sort_key,
    )
    expected_capability_count = evidence.get("canonical_capability_count")
    if len(capability_ids) != expected_capability_count:
        raise ValueError("evidence registry capability count mismatch")
    if len(set(capability_ids)) != len(capability_ids):
        raise ValueError("evidence registry contains duplicate capability subject_id values")

    obligation_count = len(capability_ids) * len(TEST_KINDS)
    expected_keys = {
        (capability_id, test_kind)
        for capability_id in capability_ids
        for test_kind in TEST_KINDS
    }
    registries = {
        "executors": executors,
        "qualifications": qualifications,
        "producers": producers,
    }
    indexes = {
        label: _entry_index(data, label=label)
        for label, data in registries.items()
    }
    for label, data in registries.items():
        if data.get("capability_count") != expected_capability_count:
            raise ValueError(f"{label} capability_count does not match active evidence registry")
        declared_obligations = data.get("required_test_obligation_count")
        if declared_obligations is not None and declared_obligations != obligation_count:
            raise ValueError(f"{label} required_test_obligation_count mismatch")
        if len(indexes[label]) != obligation_count:
            raise ValueError(f"{label} obligation cardinality mismatch")
        if set(indexes[label]) != expected_keys:
            missing = sorted(expected_keys - set(indexes[label]))
            extra = sorted(set(indexes[label]) - expected_keys)
            raise ValueError(f"{label} obligation key mismatch: missing={missing[:5]} extra={extra[:5]}")

    for key in sorted(expected_keys):
        executor = indexes["executors"][key]
        qualification = indexes["qualifications"][key]
        producer = indexes["producers"][key]
        qualification_id = qualification.get("qualification_id")
        test_id = qualification.get("test_id")
        if not isinstance(qualification_id, str) or not qualification_id:
            raise ValueError(f"qualification id missing for {key}")
        if executor.get("qualification_id") != qualification_id:
            raise ValueError(f"executor qualification binding mismatch for {key}")
        if producer.get("qualification_id") != qualification_id:
            raise ValueError(f"producer qualification binding mismatch for {key}")
        if executor.get("test_id") != test_id or producer.get("test_id") != test_id:
            raise ValueError(f"test id binding mismatch for {key}")

    registry_paths = {
        "executors": root / "canonical/current-host-capability-test-executors.json",
        "qualifications": root / "canonical/current-host-capability-test-qualifications.json",
        "producers": root / "canonical/current-host-capability-qualification-constituent-producers.json",
    }
    registry_sha256 = {label: _sha256_file(path) for label, path in registry_paths.items()}

    executor_keys = set(indexes["executors"])
    qualification_keys = set(indexes["qualifications"])
    producer_keys = set(indexes["producers"])

    coverage: list[Coverage] = []
    for capability_id in capability_ids:
        for test_kind in TEST_KINDS:
            key = (capability_id, test_kind)
            coverage.append(
                Coverage(
                    capability_id=capability_id,
                    test_kind=test_kind,
                    executor=key in executor_keys,
                    qualification=key in qualification_keys,
                    producer=key in producer_keys,
                )
            )

    obligations = len(coverage)
    if obligations != obligation_count:
        raise ValueError("derived current-host obligation count mismatch")
    materialized = [row for row in coverage if row.materialized]
    pending = [row for row in coverage if not row.materialized]

    per_capability: list[dict[str, Any]] = []
    fully_materialized_caps: list[str] = []
    pending_caps: list[str] = []
    for capability_id in capability_ids:
        rows = [row for row in coverage if row.capability_id == capability_id]
        complete = all(row.materialized for row in rows)
        if complete:
            fully_materialized_caps.append(capability_id)
        else:
            pending_caps.append(capability_id)
        per_capability.append(
            {
                "capability_id": capability_id,
                "materialization_status": "EXECUTION_READY" if complete else "PENDING_EXECUTOR_MATERIALIZATION",
                "obligations": [
                    {
                        "test_kind": row.test_kind,
                        "executor_registered": row.executor,
                        "qualification_registered": row.qualification,
                        "producer_registered": row.producer,
                        "materialized": row.materialized,
                    }
                    for row in rows
                ],
            }
        )

    execution_batches = []
    for index in range(0, len(fully_materialized_caps), batch_size):
        caps = fully_materialized_caps[index:index + batch_size]
        execution_batches.append(
            {
                "batch_id": f"EXEC-{index // batch_size + 1:03d}",
                "capabilities": caps,
                "obligation_count": len(caps) * len(TEST_KINDS),
                "status": "READY_FOR_REAL_CURRENT_HOST_EXECUTION",
                "selection_sha256": _selection_digest(caps, registry_sha256),
            }
        )

    materialization_batches = []
    for index in range(0, len(pending_caps), batch_size):
        caps = pending_caps[index:index + batch_size]
        materialization_batches.append(
            {
                "batch_id": f"MAT-{index // batch_size + 1:03d}",
                "capabilities": caps,
                "obligation_count": len(caps) * len(TEST_KINDS),
                "status": "REQUIRES_CAPABILITY_SPECIFIC_EXECUTOR_QUALIFICATION_AND_PRODUCER",
            }
        )

    return {
        "schema": "fa3.current-host-closure-batch-plan.v1",
        "status": "PASS",
        "planner_semantics": "MATERIALIZATION_AND_EXECUTION_ARE_SEPARATE_FAIL_CLOSED_STAGES",
        "capability_count": len(capability_ids),
        "required_test_kinds_per_capability": len(TEST_KINDS),
        "required_test_obligation_count": obligations,
        "materialized_obligation_count": len(materialized),
        "pending_obligation_count": len(pending),
        "fully_materialized_capability_count": len(fully_materialized_caps),
        "pending_materialization_capability_count": len(pending_caps),
        "execution_ready_capabilities": fully_materialized_caps,
        "execution_ready_selection_sha256": _selection_digest(fully_materialized_caps, registry_sha256),
        "registry_sha256": registry_sha256,
        "registry_integrity": "PASS",
        "next_materialization_batch": materialization_batches[0] if materialization_batches else None,
        "execution_batches": execution_batches,
        "materialization_batches": materialization_batches,
        "capabilities": per_capability,
        "invariants": {
            "provider_receipts_promoted": 0,
            "component_receipts_promoted": 0,
            "generic_host_evidence_promoted": 0,
            "synthetic_current_host_pass_allowed": False,
            "materialized_executor_implies_runtime_pass": False,
            "batch_completion_implies_global_promotion": False,
            "global_promotion_claim": False,
            "duplicate_obligation_keys_allowed": False,
            "cross_registry_qualification_binding_required": True,
            "batch_selection_digest_required": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan fail-closed FA3 current-host closure batches from the canonical evidence registry")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--output", default="reports/current-host-closure-batch-plan.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_plan(root, args.batch_size)
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
