#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

GATE_ID = "FA3-KNOWLEDGE-SHARED-ENHANCEMENT-GATESET-001"
PLANNING_MAIN = "6bcb6b7d4d5ece9e98a0eb091382c41c790f2256"
DONOR_BLOB = "55111e30b4508efb4e8825c40c0f9c6152ca5b35"
DONOR_SHA256 = "56ca1a4846d8d866b1b4317bca2f9240f85e6f5031752a31cd21c2051839916c"
DONOR_COUNT = 1307

PATHS = {
    "knowledge": "canonical/profiles/FA3-KNOWLEDGE-001.json",
    "shared": "canonical/profiles/FA3-SHARED-KNOWLEDGE-RETRIEVAL-001.json",
    "shared_contracts": "canonical/contracts/FA3-SHARED-KNOWLEDGE-RETRIEVAL-CONTRACTS-001.json",
    "hybrid": "canonical/profiles/FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001.json",
    "hybrid_contracts": "canonical/contracts/FA3-HIERARCHICAL-HYBRID-RETRIEVAL-CONTRACTS-001.json",
    "runbook": "canonical/contracts/FA3-KNOWLEDGE-RUNBOOK-INTERFACE-001.json",
    "ragflow": "canonical/providers/FA3-PROVIDER-RAGFLOW-001.json",
    "haystack": "canonical/providers/FA3-PROVIDER-HAYSTACK-001.json",
    "pageindex": "canonical/providers/FA3-PROVIDER-PAGEINDEX-LOCAL-001.json",
    "decision": "canonical/decisions/FA3-DEC-KNOWLEDGE-SHARED-MULTISOURCE-2026-10-01.json",
    "assessment": "canonical/assessments/FA3-KNOWLEDGE-SHARED-MULTISOURCE-REUSE-ASSESSMENT-001.json",
    "reference": "canonical/references/FA3-KNOWLEDGE-MULTISOURCE-PATTERN-REFERENCE-2026-10-01.json",
    "ragflow_ref": "canonical/references/FA3-RAGFLOW-UPSTREAM-REFERENCE-2026-10-01.json",
    "impact": "canonical/reconciliations/FA3-KNOWLEDGE-SHARED-CONSUMER-IMPACT-2026-10-01.json",
    "enforcement": "canonical/knowledge-shared-enhancement-enforcement.json",
    "historic_ragflow": "canonical/decisions/FA3-DEC-RAGFLOW-2026-08-30.json",
    "historic_hybrid": "canonical/decisions/FA3-DEC-KNOWLEDGE-HYBRID-RETRIEVAL-2026-09-18.json",
    "historic_runbook": "canonical/decisions/FA3-DEC-KNOWLEDGE-RUNBOOK-BOUNDARY-2026-09-20.json",
}


def loadj(root: Path, key: str) -> dict[str, Any]:
    value = json.loads((root / PATHS[key]).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {PATHS[key]}")
    return value


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    try:
        baseline = load_active_release_baseline(root)
        docs = {key: loadj(root, key) for key in PATHS}
    except Exception as exc:
        return {
            "schema": "fa3.knowledge-shared-enhancement-gate-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": [finding("KSE-000", "materialization unreadable", error=repr(exc))],
            "current_host_runtime_promotion_claim": False,
        }

    expected = baseline.capability_count
    active_counts = {
        key: docs[key].get("capability_count")
        for key in ("knowledge", "shared", "shared_contracts", "hybrid", "hybrid_contracts", "runbook", "ragflow", "haystack", "pageindex")
    }
    if any(value != expected for value in active_counts.values()):
        findings.append(finding("KSE-001", "active Knowledge surfaces do not match release baseline", expected=expected, actual=active_counts))

    if docs["knowledge"].get("canonical_root") is not True or docs["shared"].get("canonical_root") is not False:
        findings.append(finding("KSE-002", "Knowledge root/shared placement drift"))
    if "FA3-SHARED-KNOWLEDGE-RETRIEVAL-001" not in docs["knowledge"].get("shared_components", []):
        findings.append(finding("KSE-003", "Knowledge root does not bind the shared Knowledge component"))

    shared_names = set(docs["shared_contracts"].get("contracts", []))
    required_shared = {"SourceSyncState", "IngestionReconciliationReceipt", "KnowledgeMaterializationState", "KnowledgeCompilationPlan"}
    if not required_shared.issubset(shared_names):
        findings.append(finding("KSE-004", "shared gap-only contracts incomplete", missing=sorted(required_shared - shared_names)))
    shapes = docs["shared_contracts"].get("contract_shapes", {})
    if shapes.get("KnowledgeCompilationPlan", {}).get("skill_projection_disposition") != "CANDIDATE_REQUIRES_SEPARATE_SKILL_ADMISSION":
        findings.append(finding("KSE-005", "compiled Skill projection can bypass Skill Fabric admission"))
    if shapes.get("KnowledgeMaterializationState", {}).get("authoritative") is not False or shapes.get("KnowledgeMaterializationState", {}).get("rebuildable") is not True:
        findings.append(finding("KSE-006", "derived materialization state authority/rebuildability drift"))
    if shapes.get("IngestionReconciliationReceipt", {}).get("authorization_expansion_allowed") is not False:
        findings.append(finding("KSE-007", "ingestion checkpoint/reconciliation may expand authorization"))

    hcontracts = docs["hybrid_contracts"].get("contracts", {})
    budget = hcontracts.get("RetrievalEffortBudget", {})
    if budget.get("unbounded_execution_allowed") is not False or budget.get("provider_expansion_allowed") is not False:
        findings.append(finding("KSE-008", "retrieval budget may be unbounded or provider-expanded"))
    if "effort_budget" not in hcontracts.get("RetrievalPlan", {}).get("required", []):
        findings.append(finding("KSE-009", "RetrievalPlan does not require an effort budget"))
    if docs["hybrid"].get("retrieval_effort_budget", {}).get("resolved_before_provider_dispatch") is not True:
        findings.append(finding("KSE-010", "retrieval effort budget is not resolved before provider dispatch"))

    rag = docs["ragflow"]
    if not (
        rag.get("status") == "ACCEPTED_REFERENCE"
        and rag.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and rag.get("runtime_activation_status") == "NOT_PROMOTED_REFERENCE_ONLY"
        and rag.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and rag.get("canonical_root") is False
        and rag.get("architectural_authority") is False
        and rag.get("new_capability") is False
        and rag.get("new_architectural_authority") is False
    ):
        findings.append(finding("KSE-011", "RAGFlow optional reference/provider boundary drift"))
    required_denials = {
        "NO_KNOWLEDGE_AUTHORITY", "NO_MODEL_ROUTING_AUTHORITY", "NO_SECURITY_AUTHORITY",
        "NO_MCP_OR_TOOL_AUTHORITY", "NO_SECRET_AUTHORITY", "NO_HOST_RESOURCE_AUTHORITY",
        "NO_EVIDENCE_AUTHORITY", "NO_ORCHESTRATION_AUTHORITY", "NO_MEMORY_AUTHORITY",
    }
    if not required_denials.issubset(set(rag.get("authority_boundaries", []))):
        findings.append(finding("KSE-012", "RAGFlow authority denial set incomplete"))
    snap = rag.get("upstream_snapshot", {})
    if snap.get("release") != "v1.0.0-rc1" or snap.get("release_commit") != "14bb02ee4584c1ab18f0c722c48beecd6bbf9860":
        findings.append(finding("KSE-013", "RAGFlow immutable release reference drift"))
    if rag.get("runtime_constraints", {}).get("migration") != "SNAPSHOT_EXPORT_RESTORE_VALIDATION_AND_EXPLICIT_CUTOVER_REQUIRED":
        findings.append(finding("KSE-014", "RAGFlow irreversible migration boundary is not fail-closed"))

    hay = docs["haystack"]
    if hay.get("architectural_authority") is not False or hay.get("new_architectural_authority") is not False:
        findings.append(finding("KSE-015", "Haystack gained architectural authority"))

    refdoc = docs["reference"]
    if not (
        refdoc.get("status") == "ANALYSIS_ONLY_PATTERN_STUDY"
        and refdoc.get("formal_donor_registry_mutation") is False
        and refdoc.get("donor_usage_edge_created") is False
        and refdoc.get("code_copied") is False
        and refdoc.get("runtime_dependency_created") is False
    ):
        findings.append(finding("KSE-016", "analysis-only pattern source boundary drift"))

    assessment = docs["assessment"]
    snapshot = assessment.get("donor_planning_snapshot", {})
    expected_snapshot = {
        "published_main_commit": PLANNING_MAIN,
        "donor_registry_id": "FA3-DONOR-REFERENCE-REGISTRY-001",
        "donor_registry_blob_sha": DONOR_BLOB,
        "donor_registry_sha256": DONOR_SHA256,
        "donor_registry_entry_count": DONOR_COUNT,
    }
    if any(snapshot.get(k) != v for k, v in expected_snapshot.items()):
        findings.append(finding("KSE-017", "materialization planning snapshot provenance drift"))
    placement = assessment.get("shared_capability_placement", {})
    if not (
        assessment.get("result") == "PASS"
        and assessment.get("adoption_authorized") is False
        and assessment.get("donor_adoption_authorized") is False
        and not assessment.get("selected_existing_donor_ids")
        and placement.get("reviewed") is True
        and placement.get("multi_application_reuse_detected") is True
        and placement.get("disposition") == "SHARED"
        and placement.get("retrospective_consumer_impact_reviewed") is True
    ):
        findings.append(finding("KSE-018", "Reuse Assessment donor/shared placement boundary drift"))

    impact = docs["impact"]
    if impact.get("status") != "STATIC_IMPACT_REVIEW_PASS" or impact.get("compatibility", {}).get("capability_loss") is not False:
        findings.append(finding("KSE-019", "retroactive shared consumer impact review incomplete"))

    dec = docs["decision"]
    if not (
        dec.get("status") == "CANONICAL_CLOSED"
        and dec.get("capability_count_before") == expected
        and dec.get("capability_count_after") == expected
        and dec.get("new_capabilities") == 0
        and dec.get("new_architectural_authorities") == 0
        and dec.get("new_canonical_roots") == 0
        and dec.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("KSE-020", "reconciliation decision changes capability/authority/promotion boundary"))

    historic = {
        "ragflow": docs["historic_ragflow"].get("capability_count_after"),
        "hybrid": docs["historic_hybrid"].get("capability_count_after"),
        "runbook": docs["historic_runbook"].get("capability_count_after"),
    }
    if any(value != 143 for value in historic.values()):
        findings.append(finding("KSE-021", "historical 143-era decisions were rewritten instead of preserved", actual=historic))

    enforcement = docs["enforcement"]
    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("capability_count") == expected
        and enforcement.get("authority_delta") == 0
        and enforcement.get("current_host_runtime_promotion_claim") is False
    ):
        findings.append(finding("KSE-022", "shared Knowledge enforcement record drift"))

    return {
        "schema": "fa3.knowledge-shared-enhancement-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "active_release": baseline.release,
        "capability_count": expected,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "formal_donor_adoption": False,
        "current_host_runtime_promotion_claim": False,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default="reports/knowledge-shared-enhancement-gate-report.json")
    args = parser.parse_args()
    report = gate(Path(args.root))
    path = Path(args.root) / args.report
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
