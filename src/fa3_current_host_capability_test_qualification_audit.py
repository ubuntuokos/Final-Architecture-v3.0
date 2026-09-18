#!/usr/bin/env python3
from __future__ import annotations

from fa3_release_baseline import module_active_capability_count

import argparse
import json
import re
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = module_active_capability_count(__file__)
OBLIGATION_COUNT = CAPABILITY_COUNT * 3
REGISTRY_SCHEMA = "fa3.current-host-capability-test-qualification-registry.v1"
REPORT_SCHEMA = "fa3.current-host-capability-test-qualification-audit.v1"
AUDITOR_ID = "FA3-CURRENT-HOST-CAPABILITY-TEST-QUALIFICATION-AUDIT-001"
QUALIFICATION_REGISTRY = "canonical/current-host-capability-test-qualifications.json"
EVIDENCE_REGISTRY = "evidence/evidence-registry.json"
CONSTITUENT_SCHEMA = "fa3.capability-current-host-qualification-constituent.v1"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
KINDS = ("positive", "negative", "rollback")
QUAL_KIND_TOKEN = {"positive": "POS", "negative": "NEG", "rollback": "ROLLBACK"}
CAP_ID = re.compile(r"^CAP-\d{3}$")
QUAL_ID = re.compile(r"^FA3-QUAL-CAP-\d{3}-(?:POS|NEG|ROLLBACK)-\d{3}$")
CONSTITUENT_ID = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _expected_test_id(record: dict[str, Any], kind: str) -> Any:
    return {
        "positive": record.get("required_positive_test"),
        "negative": record.get("required_negative_test"),
        "rollback": record.get("rollback_requirement"),
    }[kind]


def audit(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    evidence = _load(root / EVIDENCE_REGISTRY)
    registry = _load(root / QUALIFICATION_REGISTRY)
    findings: list[dict[str, Any]] = []

    records = evidence.get("records", [])
    expected_ids = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    actual_ids = [row.get("subject_id") for row in records]
    if (
        evidence.get("record_count") != CAPABILITY_COUNT
        or len(records) != CAPABILITY_COUNT
        or actual_ids != expected_ids
    ):
        findings.append({"code": "CHQA-001", "message": "Evidence Registry is not the exact active capability set"})
    record_map = {row.get("subject_id"): row for row in records if isinstance(row, dict)}

    if registry.get("schema") != REGISTRY_SCHEMA:
        findings.append({"code": "CHQA-002", "message": "Qualification registry schema mismatch"})
    if registry.get("capability_count") != CAPABILITY_COUNT:
        findings.append({"code": "CHQA-003", "message": "Qualification registry capability_count mismatch"})
    if registry.get("required_test_obligation_count") != OBLIGATION_COUNT:
        findings.append({"code": "CHQA-004", "message": "Qualification registry obligation count mismatch"})
    if registry.get("execution_scope") != "CURRENT_HOST":
        findings.append({"code": "CHQA-005", "message": "Qualification execution_scope must be CURRENT_HOST"})
    if registry.get("registration_semantics") != "EXPLICIT_ONLY_NO_INFERENCE":
        findings.append({"code": "CHQA-006", "message": "Qualification registration must be explicit-only"})
    if registry.get("evidence_authority_id") != EVIDENCE_AUTHORITY:
        findings.append({"code": "CHQA-007", "message": "Qualification registry must use the existing evidence authority"})

    invariants = registry.get("invariants")
    required_false = (
        "provider_receipt_substitution_allowed",
        "component_receipt_substitution_allowed",
        "generic_host_evidence_substitution_allowed",
        "hosted_ci_substitution_allowed",
        "static_reference_substitution_allowed",
        "synthetic_constituent_allowed",
        "implicit_constituent_inference_allowed",
        "evidence_registry_artifact_inference_allowed",
        "automatic_capability_promotion",
        "automatic_global_promotion",
    )
    required_true = (
        "exact_registry_test_identity_required",
        "exact_source_decision_coverage_required",
        "explicit_constituent_set_required",
        "current_host_binding_required",
        "freshness_required",
        "source_artifact_hash_binding_required",
    )
    if not isinstance(invariants, dict):
        findings.append({"code": "CHQA-008", "message": "Qualification invariants missing"})
    else:
        for key in required_false:
            if invariants.get(key) is not False:
                findings.append({"code": "CHQA-009", "message": f"Invariant must remain false: {key}"})
        for key in required_true:
            if invariants.get(key) is not True:
                findings.append({"code": "CHQA-010", "message": f"Invariant must remain true: {key}"})
        if invariants.get("new_capabilities") != 0 or invariants.get("new_architectural_authorities") != 0:
            findings.append({"code": "CHQA-011", "message": "Qualification layer may not create capabilities or authorities"})

    entries = registry.get("entries")
    if not isinstance(entries, list):
        findings.append({"code": "CHQA-012", "message": "Qualification entries must be a list"})
        entries = []

    accepted: dict[tuple[str, str], dict[str, Any]] = {}
    seen_keys: set[tuple[Any, Any]] = set()
    qualification_ids: set[str] = set()
    entry_audit: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        item_findings: list[str] = []
        if not isinstance(entry, dict):
            findings.append({"code": "CHQA-013", "message": "Qualification entry is not an object", "index": index})
            continue

        qualification_id = entry.get("qualification_id")
        cap = entry.get("subject_id")
        kind = entry.get("test_kind")
        record = record_map.get(cap)
        valid_qualification_id = isinstance(qualification_id, str) and QUAL_ID.fullmatch(qualification_id)
        if not valid_qualification_id:
            item_findings.append("qualification_id invalid")
        elif qualification_id in qualification_ids:
            item_findings.append("duplicate qualification_id")
        else:
            qualification_ids.add(qualification_id)
        if not isinstance(cap, str) or not CAP_ID.fullmatch(cap) or record is None:
            item_findings.append("subject_id is not an active capability")
        if kind not in KINDS:
            item_findings.append("test_kind invalid")
        if valid_qualification_id and isinstance(cap, str) and kind in QUAL_KIND_TOKEN:
            expected_prefix = f"FA3-QUAL-{cap}-{QUAL_KIND_TOKEN[kind]}-"
            if not qualification_id.startswith(expected_prefix):
                item_findings.append("qualification_id does not encode exact subject_id/test_kind")

        expected_test_id = _expected_test_id(record, kind) if record is not None and kind in KINDS else None
        if entry.get("test_id") != expected_test_id:
            item_findings.append(f"test_id mismatch: expected {expected_test_id}")
        key = (cap, kind)
        if key in seen_keys:
            item_findings.append("duplicate capability/test-kind qualification")
        else:
            seen_keys.add(key)

        if entry.get("coverage_semantics") != "COMPLETE_CAPABILITY_OBLIGATION":
            item_findings.append("coverage_semantics must be COMPLETE_CAPABILITY_OBLIGATION")
        if entry.get("evidence_authority_id") != EVIDENCE_AUTHORITY:
            item_findings.append("evidence_authority_id mismatch")
        if entry.get("runtime_constituent_schema") != CONSTITUENT_SCHEMA:
            item_findings.append("runtime_constituent_schema mismatch")
        if entry.get("provider_receipt_only") is not False:
            item_findings.append("provider_receipt_only must be false")
        if entry.get("component_receipt_only") is not False:
            item_findings.append("component_receipt_only must be false")
        if entry.get("generic_host_collection_only") is not False:
            item_findings.append("generic_host_collection_only must be false")
        if entry.get("global_promotion_claim") is not False:
            item_findings.append("global_promotion_claim must be false")

        ttl = entry.get("max_constituent_ttl_seconds")
        if not isinstance(ttl, int) or ttl < 60 or ttl > 604800:
            item_findings.append("max_constituent_ttl_seconds outside 60..604800")

        expected_decisions = list(record.get("source_decision_ids", [])) if record is not None else []
        basis = entry.get("completeness_basis")
        if not isinstance(basis, dict):
            item_findings.append("completeness_basis missing")
            basis_decisions: list[Any] = []
        else:
            if basis.get("type") != "EXACT_EVIDENCE_REGISTRY_SOURCE_DECISION_COVERAGE":
                item_findings.append("completeness_basis type mismatch")
            basis_decisions = basis.get("source_decision_ids", [])
            if not isinstance(basis_decisions, list) or any(not isinstance(x, str) or not x for x in basis_decisions):
                item_findings.append("completeness_basis source_decision_ids invalid")
                basis_decisions = []
            elif basis_decisions != expected_decisions:
                item_findings.append("completeness_basis does not exactly match Evidence Registry source_decision_ids")

        constituents = entry.get("required_constituents")
        if not isinstance(constituents, list) or not constituents:
            item_findings.append("required_constituents must be a non-empty explicit list")
            constituents = []
        seen_constituents: set[str] = set()
        covered: list[str] = []
        allowed_sources = {"COMPONENT_CURRENT_HOST_EXECUTION", "CROSS_CUTTING_CURRENT_HOST_EXECUTION"}
        for constituent in constituents:
            if not isinstance(constituent, dict):
                item_findings.append("constituent is not an object")
                continue
            cid = constituent.get("constituent_id")
            if not isinstance(cid, str) or not CONSTITUENT_ID.fullmatch(cid):
                item_findings.append("constituent_id invalid")
            elif cid in seen_constituents:
                item_findings.append(f"duplicate constituent_id: {cid}")
            else:
                seen_constituents.add(cid)
            if constituent.get("source_evidence_class") not in allowed_sources:
                item_findings.append(f"constituent source_evidence_class invalid: {cid}")
            decisions = constituent.get("covers_source_decision_ids")
            if not isinstance(decisions, list) or not decisions or any(not isinstance(x, str) or not x for x in decisions):
                item_findings.append(f"constituent decision coverage invalid: {cid}")
                continue
            if any(decision not in expected_decisions for decision in decisions):
                item_findings.append(f"constituent covers unknown decision id: {cid}")
            covered.extend(decisions)
        if expected_decisions and (set(covered) != set(expected_decisions) or len(set(covered)) != len(expected_decisions)):
            item_findings.append("constituent union does not exactly cover capability source_decision_ids")
        if len(covered) != len(set(covered)):
            item_findings.append("source decision coverage overlaps between constituents")

        status = "QUALIFIED_DEFINITION" if not item_findings else "REJECTED"
        entry_audit.append({
            "index": index,
            "qualification_id": qualification_id,
            "subject_id": cap,
            "test_kind": kind,
            "test_id": entry.get("test_id"),
            "status": status,
            "findings": item_findings,
        })
        if item_findings:
            findings.append({
                "code": "CHQA-014",
                "message": "Capability qualification definition rejected",
                "index": index,
                "qualification_id": qualification_id,
                "subject_id": cap,
                "test_kind": kind,
                "findings": item_findings,
            })
        else:
            accepted[key] = entry

    if findings:
        integrity = "FAIL"
        status = "BLOCKED_INVALID_CAPABILITY_QUALIFICATION_REGISTRY"
    elif accepted:
        integrity = "PASS"
        status = "PARTIAL_EXPLICIT_CAPABILITY_QUALIFICATION_COVERAGE"
    else:
        integrity = "PASS"
        status = "PENDING_CAPABILITY_QUALIFICATION_DEFINITIONS"

    accepted_rows = [{
        "qualification_id": entry["qualification_id"],
        "subject_id": cap,
        "test_kind": kind,
        "test_id": entry["test_id"],
    } for (cap, kind), entry in sorted(accepted.items())]

    report = {
        "schema": REPORT_SCHEMA,
        "id": AUDITOR_ID,
        "qualification_registry": QUALIFICATION_REGISTRY,
        "capability_count": CAPABILITY_COUNT,
        "required_test_obligation_count": OBLIGATION_COUNT,
        "audit_integrity": integrity,
        "status": status,
        "qualified_definition_count": len(accepted),
        "pending_definition_count": OBLIGATION_COUNT - len(accepted),
        "accepted_qualifications": accepted_rows,
        "entry_audit": entry_audit,
        "blocking_findings": findings,
        "provider_receipts_promoted": 0,
        "component_receipts_promoted": 0,
        "generic_host_evidence_promoted": 0,
        "global_promotion_claim": False,
        "truth_constraints": {
            "qualification_may_be_inferred_from_provider": False,
            "qualification_may_be_inferred_from_component_receipt": False,
            "qualification_may_be_inferred_from_evidence_artifacts": False,
            "partial_source_decision_coverage_is_complete": False,
            "qualification_registry_is_promotion_authority": False,
        },
    }
    _write(root / "reports/current-host-capability-test-qualification-audit.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit FA3 capability-level current-host test qualification definitions")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = audit(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["audit_integrity"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
