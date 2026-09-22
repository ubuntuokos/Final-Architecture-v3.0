#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-PAGEINDEX-LOCAL-001"
GATE_ID = "FA3-KNOWLEDGE-HYBRID-RETRIEVAL-GATESET-001"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    try:
        knowledge = loadj(root / "canonical/profiles/FA3-KNOWLEDGE-001.json")
        sub = loadj(root / "canonical/profiles/FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001.json")
        contracts = loadj(root / "canonical/contracts/FA3-HIERARCHICAL-HYBRID-RETRIEVAL-CONTRACTS-001.json")
        runbook_contract = loadj(root / "canonical/contracts/FA3-KNOWLEDGE-RUNBOOK-INTERFACE-001.json")
        provider = loadj(root / "canonical/providers/FA3-PROVIDER-PAGEINDEX-LOCAL-001.json")
        decision = loadj(root / "canonical/decisions/FA3-DEC-KNOWLEDGE-HYBRID-RETRIEVAL-2026-09-18.json")
        runbook_decision = loadj(root / "canonical/decisions/FA3-DEC-KNOWLEDGE-RUNBOOK-BOUNDARY-2026-09-20.json")
        page_ref = loadj(root / "canonical/references/FA3-PAGEINDEX-LOCAL-UPSTREAM-REFERENCE-2026-09-18.json")
        openkb = loadj(root / "canonical/references/FA3-OPENKB-UPSTREAM-REFERENCE-2026-09-18.json")
        condb = loadj(root / "canonical/references/FA3-CONDB-UPSTREAM-REFERENCE-2026-09-18.json")
        enforcement = loadj(root / "canonical/knowledge-hybrid-retrieval-enforcement.json")
        registry = loadj(root / "canonical/mcp-capability-registry.json")
    except Exception as exc:
        return {"schema":"fa3.knowledge-hybrid-retrieval-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":[finding("KNOWLEDGE-000","Materialization unreadable",error=repr(exc))],"global_promotion_claim":False}

    if knowledge.get("id") != "FA3-KNOWLEDGE-001" or knowledge.get("canonical_root") is not True:
        findings.append(finding("KNOWLEDGE-001","Existing FA3-KNOWLEDGE-001 must remain canonical root"))
    if knowledge.get("capability_count") != 143 or knowledge.get("new_architectural_authority") is not False:
        findings.append(finding("KNOWLEDGE-002","Knowledge root capability/authority invariant drift"))
    if sub.get("parent_profile") != "FA3-KNOWLEDGE-001" or sub.get("canonical_root") is not False:
        findings.append(finding("KNOWLEDGE-003","Hybrid retrieval must be a subprofile, not a new root"))
    required_contracts={"RetrievalPlan","RetrievalTrace","ContextPassport","StructuralIndex","HierarchicalNode","EvidenceLink","SourceRegion","MediaSegment","TemporalSpan","CrossModalRelation"}
    actual=set(contracts.get("contracts",{}))
    if not required_contracts.issubset(actual):
        findings.append(finding("KNOWLEDGE-004","Hybrid retrieval contract family incomplete",missing=sorted(required_contracts-actual)))
    if provider.get("id") != PROVIDER_ID or provider.get("architectural_authority") is not False:
        findings.append(finding("KNOWLEDGE-005","PageIndex Local provider identity/authority drift"))
    local=provider.get("local_runtime",{})
    if local.get("model_access") != "FA3_CENTRAL_MODEL_ROUTER_ONLY" or local.get("model_router_authority") != "FA3-AUTH-MODEL-ROUTER-001" or local.get("physical_backend_binding") != "ROUTER_RUNTIME_DECISION_ONLY" or local.get("physical_model_binding") != "ROUTER_RUNTIME_DECISION_ONLY" or local.get("direct_external_model_provider") != "DENY" or local.get("pageindex_api_key") != "DENY":
        findings.append(finding("KNOWLEDGE-006","PageIndex Local direct egress/credential boundary drift"))
    if page_ref.get("commit") != "9a8dd6658278fec90347e8ac3388a205305667a3":
        findings.append(finding("KNOWLEDGE-007","PageIndex Local upstream pin drift"))
    if openkb.get("materialized_provider") is not False or "source authority" not in [x.lower() for x in openkb.get("prohibited_roles",[])]:
        findings.append(finding("KNOWLEDGE-008","OpenKB must remain non-authoritative reference/optional compiler"))
    if condb.get("materialized_provider") is not False or "durable knowledge authority" not in [x.lower() for x in condb.get("prohibited_roles",[])]:
        findings.append(finding("KNOWLEDGE-009","ConDB must remain rebuildable acceleration reference"))
    if decision.get("capability_count_after") != 143 or decision.get("new_architectural_authorities") != 0:
        findings.append(finding("KNOWLEDGE-010","Decision changes capability/authority baseline"))
    if enforcement.get("rules",{}).get("media_binary_in_knowledge_store") != "DENY":
        findings.append(finding("KNOWLEDGE-011","Binary media must remain outside knowledge index"))

    runbook_contracts = runbook_contract.get("contracts", {})
    if not {"ExternalKnowledgeSourceRecord", "VerifiedKnowledgeItem", "RunbookObject"}.issubset(set(runbook_contracts)):
        findings.append(finding("KNOWLEDGE-018","Knowledge-to-Runbook interface contract family incomplete"))
    execution_boundary = runbook_contract.get("execution_boundary", {})
    if execution_boundary.get("retrieved_text_to_executor") != "FORBIDDEN" or execution_boundary.get("runbook_object_to_typed_capability") != "REQUIRED":
        findings.append(finding("KNOWLEDGE-019","Retrieved text or RunbookObject execution boundary drift"))
    if execution_boundary.get("capability_tool_boundary") != "FA3-AUTH-MCP-GATEWAY-001":
        findings.append(finding("KNOWLEDGE-020","Runbook execution must cross the canonical MCP/capability tool boundary"))
    if execution_boundary.get("governed_compute_resource_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append(finding("KNOWLEDGE-027","Governed Runbook compute must retain HRB resource authority"))
    source = runbook_contract.get("source_dispositions", {}).get("trimstray/the-book-of-secret-knowledge", {})
    if source.get("role") != "REFERENCE_SOURCE_ONLY" or source.get("provider") is not False or source.get("execution_authority") is not False:
        findings.append(finding("KNOWLEDGE-021","Trimstray source disposition drifted toward provider/execution authority"))
    rules = enforcement.get("rules", {})
    required_boundary_rules = {
        "external_reference_source_execution_authority": "DENY",
        "retrieved_text_direct_execution": "DENY",
        "runbook_object_required_for_knowledge_derived_action": "REQUIRED",
        "runbook_object_direct_execution": "DENY",
        "runbook_execution_boundary": "FA3-AUTH-MCP-GATEWAY-001",
        "community_source_provenance": "REQUIRED",
        "community_source_revision_or_digest_binding": "REQUIRED",
        "community_source_freshness_assessment": "REQUIRED_BEFORE_VERIFIED",
        "community_source_target_compatibility_assessment": "REQUIRED_BEFORE_VERIFIED",
        "inline_secret_material_in_knowledge_or_runbook": "DENY",
    }
    drift = {key: {"expected": value, "actual": rules.get(key)} for key, value in required_boundary_rules.items() if rules.get(key) != value}
    if drift:
        findings.append(finding("KNOWLEDGE-022","Knowledge-to-Runbook fail-closed enforcement drift",drift=drift))
    if runbook_decision.get("capability_count_after") != 143 or runbook_decision.get("new_architectural_authorities") != 0:
        findings.append(finding("KNOWLEDGE-023","Runbook boundary decision changes capability/authority baseline"))
    if runbook_decision.get("dispositions", {}).get("trimstray/the-book-of-secret-knowledge") != "COMMUNITY_CURATED_REFERENCE_SOURCE_ONLY":
        findings.append(finding("KNOWLEDGE-024","Community source classification drift"))
    if runbook_decision.get("hardware_audit_compliance", {}).get("status") != "PASS" or runbook_decision.get("hardware_audit_compliance", {}).get("vendor_neutral") is not True:
        findings.append(finding("KNOWLEDGE-025","Runbook boundary hardware-audit compliance missing or non-neutral"))
    if runbook_decision.get("current_host_impact", {}).get("runtime_delta") != "NONE":
        findings.append(finding("KNOWLEDGE-026","Decision unexpectedly introduces current-host runtime delta"))

    for cap_id, adapter_id in (
        ("fa3.document.index","fa3.adapter.pageindex.local.index"),
        ("fa3.document.retrieve","fa3.adapter.pageindex.local.retrieve"),
    ):
        cap=next((x for x in registry.get("capabilities",[]) if x.get("capability_id")==cap_id),None)
        rows=[x for x in (cap or {}).get("providers",[]) if x.get("provider_id")==PROVIDER_ID]
        if len(rows)!=1 or rows[0].get("adapter_id")!=adapter_id:
            findings.append(finding("KNOWLEDGE-012","Local PageIndex binding missing/duplicated",capability_id=cap_id))
            continue
        row=rows[0]
        if row.get("state")=="CONNECTED" and not row.get("evidence_ref"):
            findings.append(finding("KNOWLEDGE-013","CONNECTED local provider requires current-host evidence",capability_id=cap_id))
        elif row.get("state") not in {"PENDING_CURRENT_HOST","CONNECTED"}:
            findings.append(finding("KNOWLEDGE-014","Invalid local provider lifecycle state",capability_id=cap_id))
        cloud=[x for x in (cap or {}).get("providers",[]) if x.get("provider_id")=="FA3-PROVIDER-PAGEINDEX-MCP-001"]
        if not cloud:
            findings.append(finding("KNOWLEDGE-015","Existing PageIndex MCP cloud provider binding must be preserved",capability_id=cap_id))
        elif int(row.get("priority",999)) >= int(cloud[0].get("priority",999)):
            findings.append(finding("KNOWLEDGE-016","Admitted local provider must route before optional cloud provider",capability_id=cap_id))

    for rel in [
        "src/fa3_hybrid_retrieval.py",
        "src/fa3_pageindex_local_provider.py",
        "apps/fa3-control-center/qml/KnowledgePage.qml",
    ]:
        if not (root/rel).is_file():
            findings.append(finding("KNOWLEDGE-017","Required runtime/GUI artifact missing",path=rel))

    return {
        "schema":"fa3.knowledge-hybrid-retrieval-gate-report.v1",
        "gate_id":GATE_ID,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "capability_count":143,
        "authority_delta":0,
        "global_promotion_claim":False,
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=".")
    parser.add_argument("--report",default="reports/knowledge-hybrid-retrieval-gate-report.json")
    args=parser.parse_args()
    report=gate(Path(args.root))
    path=Path(args.root)/args.report
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report["result"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
