#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise AssertionError(f"JSON object required: {path}")
    return value


def assert_current_host_closure(root: Path, selected_obligation_count: int) -> dict[str, Any]:
    root=Path(root).resolve()
    producer_audit=_load(root/"reports/current-host-capability-qualification-constituent-producer-audit.json")
    producer_orchestrator=_load(root/"reports/current-host-capability-qualification-constituent-orchestrator.json")
    executor=_load(root/"reports/current-host-capability-test-executor-audit.json")
    orchestrator=_load(root/"reports/current-host-capability-test-orchestrator.json")
    assembler=_load(root/"reports/current-host-capability-test-bundle-assembler.json")
    producer=_load(root/"reports/current-host-capability-attestation-producer.json")
    handoff=_load(root/"reports/current-host-capability-handoff.json")
    audit=_load(root/"reports/current-host-evidence-audit.json")
    acceptance=_load(root/"acceptance/acceptance-report.json")
    promotion=_load(root/"promotion/runtime-status.json")

    assert selected_obligation_count > 0

    assert producer_audit["audit_integrity"]=="PASS", producer_audit
    assert producer_audit["registered_producer_count"]+producer_audit["pending_producer_count"]==producer_audit["required_constituent_count"], producer_audit
    assert producer_audit["global_promotion_claim"] is False, producer_audit

    assert producer_orchestrator["orchestrator_integrity"]=="PASS", producer_orchestrator
    assert producer_orchestrator["execution_requested"] is True, producer_orchestrator
    assert producer_orchestrator["constituents_materialized"]==producer_orchestrator["selected_producer_count"], producer_orchestrator
    assert producer_orchestrator["constituents_materialized"]==selected_obligation_count, producer_orchestrator
    assert producer_orchestrator["provider_receipts_promoted"]==0, producer_orchestrator
    assert producer_orchestrator["component_receipts_promoted"]==0, producer_orchestrator
    assert producer_orchestrator["global_promotion_claim"] is False, producer_orchestrator

    assert executor["audit_integrity"]=="PASS", executor
    assert executor["required_test_obligation_count"]==429, executor
    assert executor["registered_executor_count"]+executor["pending_executor_count"]==429, executor
    assert executor["provider_receipts_promoted"]==0, executor
    assert executor["generic_host_evidence_promoted"]==0, executor
    assert executor["global_promotion_claim"] is False, executor

    assert orchestrator["orchestrator_integrity"]=="PASS", orchestrator
    assert orchestrator["execution_requested"] is True, orchestrator
    assert orchestrator["results_materialized"]==orchestrator["selected_executor_count"], orchestrator
    assert orchestrator["results_materialized"]==selected_obligation_count, orchestrator
    assert orchestrator["provider_receipts_promoted"]==0, orchestrator
    assert orchestrator["generic_host_evidence_promoted"]==0, orchestrator
    assert orchestrator["global_promotion_claim"] is False, orchestrator

    assert assembler["assembler_integrity"]=="PASS", assembler
    assert assembler["provider_receipts_promoted"]==0, assembler
    assert assembler["generic_host_evidence_promoted"]==0, assembler
    assert assembler["global_promotion_claim"] is False, assembler

    assert producer["producer_integrity"]=="PASS", producer
    assert producer["provider_receipts_promoted"]==0, producer
    assert producer["generic_host_evidence_promoted"]==0, producer
    assert producer["global_promotion_claim"] is False, producer

    assert handoff["handoff_integrity"]=="PASS", handoff
    assert handoff["provider_receipts_promoted"]==0, handoff
    assert handoff["generic_host_evidence_promoted"]==0, handoff
    assert handoff["global_promotion_claim"] is False, handoff

    assert audit["audit_integrity"]=="PASS", audit
    assert audit["registry_pass_count"]+audit["registry_pending_count"]==143, audit
    assert acceptance["criteria_total"]==19, acceptance

    runtime_closure=audit["runtime_closure"]
    if runtime_closure=="PASS":
        assert executor["coverage_status"]=="COMPLETE_429_OF_429", executor
        assert executor["registered_executor_count"]==429, executor
        assert orchestrator["results_materialized"]==429, orchestrator
        assert assembler["bundles_materialized"]==143, assembler
        assert producer["attestations_materialized"]==143, producer
        assert handoff["receipts_materialized"]==143, handoff
        assert audit["registry_pass_count"]==143 and audit["registry_pending_count"]==0, audit
        assert audit["qualified_current_host_receipt_count"]==143, audit
        assert acceptance["runtime_gate"]=="PASS", acceptance

    # Runtime closure and global release promotion are deliberately separate.
    # A FULL-429 runtime PASS MUST NOT fabricate the independent 19-point
    # static/release acceptance artifacts.
    if acceptance["status"]=="PASS":
        assert runtime_closure=="PASS", audit
        assert acceptance["static_gate"]=="PASS", acceptance
        assert acceptance["criteria_passed"]==19, acceptance
        assert promotion["actual_state"]=="PROMOTED", promotion
        assert promotion["promotion_allowed"] is True, promotion
    else:
        assert acceptance["status"]=="DENIED", acceptance
        assert promotion["actual_state"]=="PROMOTION_BLOCKED", promotion
        assert promotion["promotion_allowed"] is False, promotion

    return {
        "executor_coverage": executor["coverage_status"],
        "registered_executors": executor["registered_executor_count"],
        "pending_executors": executor["pending_executor_count"],
        "orchestrator": orchestrator["status"],
        "test_results_materialized": orchestrator["results_materialized"],
        "bundle_assembler": assembler["materialization_status"],
        "bundles_materialized": assembler["bundles_materialized"],
        "pending_capability_tests": assembler["pending_capability_count"],
        "producer": producer["materialization_status"],
        "attestations_materialized": producer["attestations_materialized"],
        "handoff": handoff["materialization_status"],
        "receipts_materialized": handoff["receipts_materialized"],
        "runtime_closure": runtime_closure,
        "registry_pass_count": audit["registry_pass_count"],
        "registry_pending_count": audit["registry_pending_count"],
        "qualified_current_host_receipt_count": audit["qualified_current_host_receipt_count"],
        "static_gate": acceptance["static_gate"],
        "acceptance": acceptance["status"],
        "criteria_passed": acceptance["criteria_passed"],
        "criteria_total": acceptance["criteria_total"],
        "promotion": promotion["actual_state"],
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--selected-obligation-count", type=int, default=None)
    args=ap.parse_args()
    count=args.selected_obligation_count
    if count is None:
        raw=os.environ.get("FA3_CURRENT_HOST_SELECTED_OBLIGATION_COUNT","")
        if not raw.isdigit():
            raise SystemExit("FA3_CURRENT_HOST_SELECTED_OBLIGATION_COUNT missing or invalid")
        count=int(raw)
    summary=assert_current_host_closure(Path(args.root),count)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
