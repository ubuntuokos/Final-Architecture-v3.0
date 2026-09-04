#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-XYOPS-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-XYOPS-001"
PROFILE_ID = "FA3-OPS-AUTO-001"
CONTRACT_ID = "FA3-OPS-AUTO-CONTRACTS-001"
XYOPS_PROVIDER_ID = "FA3-PROVIDER-XYOPS-001"
XYSAT_PROVIDER_ID = "FA3-PROVIDER-XYSAT-001"
DECISION_ID = "FA3-DEC-XYOPS-2026-09-04"
REFERENCE_ID = "FA3-XYOPS-UPSTREAM-REFERENCE-2026-09-04"
CAPABILITY_COUNT = 143
RUNTIME_STATUS = "NOT_PROMOTED_REFERENCE_ONLY"
XYOPS_COMMIT = "6c42aaf022f8f59458915af95fb9ca21dd8f96f5"
XYOPS_VERSION = "1.0.95"
XYSAT_COMMIT = "c4d29cd16e880da648010c06ae021479a2c0aebd"
XYSAT_VERSION = "1.0.44"
CAPABILITY_PROJECTION = ["CAP-004", "CAP-006", "CAP-011", "CAP-038", "CAP-049", "CAP-101", "CAP-104", "CAP-130", "CAP-132"]
P0_RULES = ["XYOPS_PROVIDER_NOT_AUTHORITY", "XYSAT_PROVIDER_NOT_AUTHORITY", "TEMPORAL_REMAINS_DURABLE_ORCHESTRATION_AUTHORITY", "TYPED_OPERATIONAL_EXECUTION_REQUEST_REQUIRED", "PRODUCTION_POLICY_ADMISSION_REQUIRED", "HRB_ADMISSION_REQUIRED", "XYOPS_RESOURCE_LIMITS_CANONICALIZED", "XYSAT_HRB_BYPASS_FORBIDDEN", "HARDWARE_DISCOVERY_REQUIRED", "GPU_ORDINAL_OR_SKU_HARDCODING_FORBIDDEN_AS_CANONICAL_PLACEMENT", "SYSTEMD_CGROUP_ENFORCEMENT_REQUIRED_FOR_LOCAL_HOST", "CANONICAL_SECRET_REFERENCE_REQUIRED", "RAW_SECRET_PROVIDER_PERSISTENCE_FORBIDDEN", "QUERY_STRING_CREDENTIALS_FORBIDDEN_IN_PRODUCTION", "SHORT_LIVED_ROTATABLE_IDENTITY_BOUND_CREDENTIALS_REQUIRED", "LEAST_PRIVILEGE_PROVIDER_SCOPE_REQUIRED", "ARBITRARY_SHELL_REQUIRES_EXPLICIT_POLICY", "ARBITRARY_HTTP_REQUIRES_EGRESS_POLICY", "EXECUTION_RECEIPT_REQUIRED", "TELEMETRY_EXPORT_TO_CANONICAL_OBSERVABILITY_REQUIRED", "EVIDENCE_REGISTRY_WRITE_REQUIRED", "RETRY_IDEMPOTENCY_REQUIRED", "RESUME_SEMANTICS_REQUIRED", "CANCEL_TIMEOUT_ABORT_EVIDENCE_REQUIRED", "IMMUTABLE_PROVIDER_PIN_REQUIRED", "SBOM_PROVENANCE_LICENSE_GATE_REQUIRED", "ROLLBACK_PATH_REQUIRED", "SHARED_CAPACITY_POOL_IS_POLICY_NOT_RESOURCE_AUTHORITY", "SOURCE_GRAPH_LINK_REQUIRED", "CONFORMANCE_MATRIX_LINK_REQUIRED"]
PATHS = {"profile": "canonical/profiles/FA3-OPS-AUTO-001.json", "contract": "canonical/contracts/FA3-OPS-AUTO-CONTRACTS-001.json", "xyops": "canonical/providers/FA3-PROVIDER-XYOPS-001.json", "xysat": "canonical/providers/FA3-PROVIDER-XYSAT-001.json", "decision": "canonical/decisions/FA3-DEC-XYOPS-2026-09-04.json", "reference": "canonical/references/FA3-XYOPS-UPSTREAM-REFERENCE-2026-09-04.json", "gate_record": "canonical/FA3-GATE-XYOPS-001.json", "enforcement": "canonical/xyops-enforcement.json", "admission": "canonical/xyops-runtime-admission.json", "matrix": "canonical/conformance-matrix.csv"}

def _load(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]: return {"code": code, "severity": "P0", "message": message, **extra}
def provider_not_authority(*, canonical_root: bool, architectural_authority: bool, authority_owner: str | None) -> bool: return not canonical_root and not architectural_authority and authority_owner not in {XYOPS_PROVIDER_ID, XYSAT_PROVIDER_ID}
def typed_execution_request_valid(*, typed: bool, versioned: bool, request_id: str | None) -> bool: return typed and versioned and bool(request_id)
def production_policy_admission_valid(*, production: bool, policy_decision: str | None) -> bool: return (not production) or policy_decision in {"ALLOW", "ALLOW_WITH_CONSTRAINTS"}
def hrb_admission_valid(*, host_workload: bool, admitted: bool, placement_owner: str) -> bool: return (not host_workload) or (admitted and placement_owner == "FA3-AUTH-HOST-RESOURCE-BROKER-001")
def resource_projection_valid(*, provider_native_limit: bool, canonicalized: bool, provider_is_authority: bool) -> bool: return (not provider_native_limit) or (canonicalized and not provider_is_authority)
def hardware_discovery_valid(*, host_workload: bool, live_discovery: bool, static_accelerator_placement: bool) -> bool: return (not host_workload) or (live_discovery and not static_accelerator_placement)
def local_enforcement_valid(*, local_host: bool, systemd_cgroup_v2: bool) -> bool: return (not local_host) or systemd_cgroup_v2
def secret_projection_valid(*, secret_refs: list[str], raw_secret_values: list[str], provider_persisted_raw: bool) -> bool: return not raw_secret_values and not provider_persisted_raw and all(isinstance(x, str) and x.startswith("secret-ref:") for x in secret_refs)
def credential_transport_valid(*, production: bool, location: str, short_lived: bool, rotatable: bool, identity_bound: bool) -> bool: return True if not production else location not in {"QUERY", "URL"} and short_lived and rotatable and identity_bound
def least_privilege_valid(*, granted: set[str], required: set[str]) -> bool: return required <= granted and granted <= required
def shell_execution_valid(*, arbitrary_shell: bool, explicit_policy: bool, bounded_executor: bool) -> bool: return (not arbitrary_shell) or (explicit_policy and bounded_executor)
def http_execution_valid(*, arbitrary_http: bool, egress_policy: bool, destination_admitted: bool) -> bool: return (not arbitrary_http) or (egress_policy and destination_admitted)
def execution_receipt_valid(receipt: dict[str, Any]) -> bool:
    required = {"request_id", "workflow_id", "job_id", "provider", "provider_version", "executor", "target", "started_at", "finished_at", "exit_status", "resource_admission", "policy_decision", "artifacts", "logs", "metrics", "alerts", "snapshots", "incident_ids", "provenance", "evidence_hash"}; return required <= set(receipt)
def retry_valid(*, retry: bool, idempotency_classified: bool, idempotency_key: str | None) -> bool: return (not retry) or (idempotency_classified and bool(idempotency_key))
def resume_valid(*, resume: bool, committed_checkpoint: bool, provider_resume_receipt: bool) -> bool: return (not resume) or committed_checkpoint or provider_resume_receipt
def terminal_control_evidence_valid(*, cancelled: bool, timed_out: bool, aborted: bool, evidence_written: bool) -> bool: return not (cancelled or timed_out or aborted) or evidence_written
def immutable_pin_valid(component: dict[str, Any], *, commit: str, version: str) -> bool: return component.get("commit") == commit and component.get("version") == version and component.get("license") == "BSD-3-Clause" and all(component.get(k) not in {"latest", "main", "*", "floating", ""} for k in ("commit", "version"))
def supply_chain_valid(*, runtime_promotion: bool, sbom: bool, provenance: bool, license_gate: bool) -> bool: return (not runtime_promotion) or (sbom and provenance and license_gate)
def rollback_valid(*, mutating_production: bool, rollback_path: bool) -> bool: return (not mutating_production) or rollback_path
def capacity_pool_valid(*, declarative_policy: bool, provider_is_resource_authority: bool) -> bool: return declarative_policy and not provider_is_resource_authority

def provider_shape_valid(provider: dict[str, Any], *, provider_id: str, commit: str, version: str) -> bool:
    return provider.get("id") == provider_id and provider.get("canonical_root") is False and provider.get("architectural_authority") is False and provider.get("new_capability") is False and provider.get("new_architectural_authority") is False and provider.get("capability_count") == CAPABILITY_COUNT and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT" and provider.get("runtime_activation_status") == RUNTIME_STATUS and provider.get("current_host_runtime_evidence") is False and provider.get("parent_profile") == PROFILE_ID and provider.get("contract") == CONTRACT_ID and immutable_pin_valid(provider.get("immutable_component_tuple", {}), commit=commit, version=version)

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings=[]; canonical=root/"canonical"; scanned=0
    if not canonical.exists(): return {"result":"FAIL","scanned_json_files":0,"findings":[_finding("XYOPS-AUTH-000","canonical directory missing")]}
    providers={XYOPS_PROVIDER_ID,XYSAT_PROVIDER_ID}
    def walk(value: Any, *, path: str, file_path: str) -> None:
        if isinstance(value,dict):
            for key,item in value.items():
                kp=f"{path}.{key}"; normalized=key.lower().replace("-","_")
                if "authority" in normalized and isinstance(item,str) and item in providers: findings.append(_finding("XYOPS-AUTH-001","xyOps/xySat assigned to authority-bearing field",file=file_path,path=kp))
                if key=="authority_boundaries" and isinstance(item,dict):
                    for domain,owner in item.items():
                        if owner in providers: findings.append(_finding("XYOPS-AUTH-002","xyOps/xySat owns an FA3 authority boundary",file=file_path,path=f"{kp}.{domain}"))
                walk(item,path=kp,file_path=file_path)
        elif isinstance(value,list):
            for i,item in enumerate(value): walk(item,path=f"{path}[{i}]",file_path=file_path)
    for path in sorted(canonical.rglob("*.json")):
        scanned+=1
        try: walk(_load(path),path="$",file_path=str(path.relative_to(root)))
        except Exception as exc: findings.append(_finding("XYOPS-AUTH-003","canonical JSON parse failure during xyOps authority scan",file=str(path.relative_to(root)),error=str(exc)))
    return {"result":"PASS" if not findings else "FAIL","scanned_json_files":scanned,"findings":findings}

def matrix_link_valid(root: Path) -> tuple[bool,list[str]]:
    path=root/PATHS["matrix"]
    if not path.is_file(): return False,CAPABILITY_PROJECTION
    with path.open(encoding="utf-8-sig",newline="") as fh: ids={row.get("capability_id") for row in csv.DictReader(fh)}
    missing=[x for x in CAPABILITY_PROJECTION if x not in ids]; return not missing,missing

def reference_check(root: Path) -> dict[str, Any]:
    findings=[]; loaded={}
    for name,rel in PATHS.items():
        if name=="matrix": continue
        path=root/rel
        if not path.is_file(): findings.append(_finding("XYOPS-REF-001","required xyOps canonical file missing",path=rel)); continue
        try: loaded[name]=_load(path)
        except Exception as exc: findings.append(_finding("XYOPS-REF-002","required xyOps JSON invalid",path=rel,error=str(exc)))
    if findings: return {"result":"FAIL","findings":findings}
    profile,contract,xyops,xysat,decision,reference,gate_record,enforcement,admission=(loaded[k] for k in ("profile","contract","xyops","xysat","decision","reference","gate_record","enforcement","admission"))
    if not (profile.get("id")==PROFILE_ID and profile.get("status")=="CANONICAL" and profile.get("priority")=="P0" and profile.get("requirement")=="MUST" and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count")==CAPABILITY_COUNT and profile.get("capability_projection")==CAPABILITY_PROJECTION and profile.get("invariants")==P0_RULES and profile.get("authority_boundaries",{}).get("durable_orchestration")=="TEMPORAL_EXISTING_GLOBAL_DURABLE_ORCHESTRATION_AUTHORITY" and profile.get("authority_boundaries",{}).get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001"): findings.append(_finding("XYOPS-REF-003","operational automation profile drift"))
    sec=contract.get("security_semantics",{}); exe=contract.get("execution_semantics",{}); res=contract.get("resource_semantics",{}); ev=contract.get("observability_evidence_semantics",{}); link=contract.get("canonical_linkage",{})
    if not (contract.get("id")==CONTRACT_ID and contract.get("status")=="CANONICAL" and contract.get("provider_neutral") is True and contract.get("new_capability") is False and contract.get("new_architectural_authority") is False and contract.get("capability_count")==CAPABILITY_COUNT and exe.get("typed_request_required") is True and exe.get("policy_preflight_required") is True and exe.get("host_resource_broker_admission_required") is True and res.get("provider_limits_are_policy_projection_only") is True and res.get("shared_capacity_pool_is_declarative_policy_not_resource_authority") is True and res.get("hardware_discovery_before_admission") is True and res.get("static_gpu_ordinal_or_sku_placement") is False and sec.get("canonical_secret_ref_required") is True and sec.get("raw_secret_provider_persistence") is False and sec.get("query_string_credentials_in_production") is False and sec.get("credentials_short_lived_rotatable_identity_bound") is True and sec.get("least_privilege_scope_required") is True and sec.get("arbitrary_shell_requires_explicit_policy") is True and sec.get("arbitrary_http_requires_egress_policy") is True and ev.get("telemetry_export_to_canonical_observability_required") is True and ev.get("evidence_registry_write_required") is True and link.get("source_graph_link_required") is True and link.get("conformance_matrix_capability_projection")==CAPABILITY_PROJECTION): findings.append(_finding("XYOPS-REF-004","operational automation contract drift"))
    if not provider_shape_valid(xyops,provider_id=XYOPS_PROVIDER_ID,commit=XYOPS_COMMIT,version=XYOPS_VERSION): findings.append(_finding("XYOPS-REF-005","xyOps provider shape or immutable pin drift"))
    if not provider_shape_valid(xysat,provider_id=XYSAT_PROVIDER_ID,commit=XYSAT_COMMIT,version=XYSAT_VERSION): findings.append(_finding("XYOPS-REF-006","xySat provider shape or immutable pin drift"))
    if xysat.get("canonical_projection",{}).get("hrb_bypass_allowed") is not False: findings.append(_finding("XYOPS-REF-007","xySat HRB bypass became allowed"))
    if not (decision.get("id")==DECISION_ID and decision.get("status")=="CANONICAL_CLOSED" and decision.get("profile_id")==PROFILE_ID and decision.get("provider_ids")==[XYOPS_PROVIDER_ID,XYSAT_PROVIDER_ID] and decision.get("contract_id")==CONTRACT_ID and decision.get("mandatory_p0_rules")==P0_RULES and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and decision.get("capability_count_after")==CAPABILITY_COUNT): findings.append(_finding("XYOPS-REF-008","xyOps decision semantics drift"))
    components=reference.get("components",{})
    if not (reference.get("id")==REFERENCE_ID and reference.get("promotion_evidence") is False and reference.get("floating_main_allowed_as_promotion_evidence") is False and components.get("xyops",{}).get("immutable_observed_commit")==XYOPS_COMMIT and components.get("xyops",{}).get("version")==XYOPS_VERSION and components.get("xysat",{}).get("immutable_observed_commit")==XYSAT_COMMIT and components.get("xysat",{}).get("version")==XYSAT_VERSION): findings.append(_finding("XYOPS-REF-009","upstream reference identity/version drift"))
    if not (enforcement.get("gate_id")==GATE_ID and enforcement.get("executable_gate_id")==EXECUTABLE_GATE_ID and enforcement.get("p0_invariants")==P0_RULES and enforcement.get("mandatory_rule_count")==30 and enforcement.get("fail_closed") is True): findings.append(_finding("XYOPS-REF-010","xyOps enforcement rule set drift"))
    if not (gate_record.get("id")==EXECUTABLE_GATE_ID and gate_record.get("gate_set_id")==GATE_ID and gate_record.get("rule_count")==30 and gate_record.get("fail_closed") is True and gate_record.get("capability_count")==CAPABILITY_COUNT): findings.append(_finding("XYOPS-REF-011","xyOps gate record drift"))
    providers=admission.get("providers",{})
    if not (admission.get("document_only_promotion_forbidden") is True and providers.get(XYOPS_PROVIDER_ID,{}).get("status")==RUNTIME_STATUS and providers.get(XYSAT_PROVIDER_ID,{}).get("status")==RUNTIME_STATUS and providers.get(XYOPS_PROVIDER_ID,{}).get("current_host_runtime_evidence")=="NOT_CLAIMED" and providers.get(XYSAT_PROVIDER_ID,{}).get("current_host_runtime_evidence")=="NOT_CLAIMED"): findings.append(_finding("XYOPS-REF-012","runtime admission status drift"))
    matrix_ok,missing=matrix_link_valid(root)
    if not matrix_ok: findings.append(_finding("XYOPS-REF-013","conformance matrix capability linkage incomplete",missing=missing))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    ref=reference_check(root); authority=scan_canonical_authority_assignments(root); findings=[*ref.get("findings",[]),*authority.get("findings",[])]; result="PASS" if not findings else "FAIL"
    report={"schema":"fa3.xyops-gate-report.v1","gate_id":GATE_ID,"executable_gate_id":EXECUTABLE_GATE_ID,"result":result,"blocking_findings":len(findings),"rule_count":len(P0_RULES),"capability_count":CAPABILITY_COUNT,"reference_check":ref.get("result"),"authority_scan":authority.get("result"),"current_host_runtime_promotion_claimed":False,"findings":findings}
    _write(root/"reports/xyops-gate-report.json",report); return report
