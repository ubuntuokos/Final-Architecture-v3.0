#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

PROVIDER="FA3-PROVIDER-OPEN-SCIENCE-DESKTOP-001"
CONTRACT="FA3-SCIENTIFIC-RESEARCH-WORKBENCH-CONTRACTS-001"
DECISION="FA3-DEC-OPEN-SCIENCE-DESKTOP-2026-09-12"
GATE="FA3-GATE-OPEN-SCIENCE-DESKTOP-001"
CONFORMANCE="FA3-OPEN-SCIENCE-DESKTOP-CURRENT-HOST-CONFORMANCE-001"
UPSTREAM="2f3d7e6ff75851e5f53ba0fb21adb3a1a1ad1375"
COUNT=143
CHAIN=["HRB_UI_DISPLAY_ROLE_BINDING","HRB_COMPUTE_ROLE_ADMISSION","UI_AND_COMPUTE_ACCELERATORS_DISTINCT","COMPUTE_ACCELERATOR_NON_DISPLAY","LIVE_UUID_PCI_BDF_IDENTITY","NUMA_LOCALITY_EVIDENCE","CUDA_EXECUTION","NO_CPU_OR_CROSS_ACCELERATOR_FALLBACK"]
RULES=["immutable_upstream_pin","optional_non_authoritative_provider","capability_and_authority_invariants","existing_authorities_only","production_full_approval_forbidden","destructive_install_network_operations_require_approval","third_party_skill_admission_required","third_party_skill_license_admission_required","provider_provenance_non_authoritative_projection","hrb_placement_authority_only","ui_display_role_binding","compute_non_display_role_admission","ui_compute_role_separation","live_identity_numa_cuda_evidence_required","no_cpu_or_cross_accelerator_fallback"]
PATHS={
"p":"canonical/providers/FA3-PROVIDER-OPEN-SCIENCE-DESKTOP-001.json",
"c":"canonical/contracts/FA3-SCIENTIFIC-RESEARCH-WORKBENCH-CONTRACTS-001.json",
"d":"canonical/decisions/FA3-DEC-OPEN-SCIENCE-DESKTOP-2026-09-12.json",
"h":"canonical/FA3-OPEN-SCIENCE-DESKTOP-CURRENT-HOST-CONFORMANCE-001.json",
"g":"canonical/FA3-GATE-OPEN-SCIENCE-DESKTOP-001.json",
"e":"canonical/open-science-desktop-enforcement.json",
"b":"fa3-current-host/open-science-desktop-hardware-binding.json",
"v":"canonical/evidence/FA3-EVIDENCE-OPEN-SCIENCE-DESKTOP-STATIC-2026-09-12.json"}

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def fail(code,msg): return {"code":code,"severity":"P0","message":msg}
def bdf(x):
    s=str(x or "").strip().lower()
    m=re.fullmatch(r"(?:[0-9a-f]{4,8}:)?([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])",s)
    return f"0000:{m.group(1)}:{m.group(2)}.{m.group(3)}" if m else s

def static_findings(root:Path):
    try: x={k:load(root/v) for k,v in PATHS.items()}
    except Exception as exc: return [fail("OSD-000",f"required artifact missing/unreadable: {exc!r}")]
    p,c,d,h,g,e,b,v=(x[k] for k in "pcdhgebv")
    out=[]
    checks=[
      ("OSD-001",p.get("id")==PROVIDER and p.get("status")=="ACCEPTED_REFERENCE" and p.get("canonical_root") is False and p.get("architectural_authority") is False and p.get("new_capability") is False and p.get("capability_count")==COUNT and p.get("activation_mode")=="OPTIONAL_DISABLED_BY_DEFAULT" and p.get("runtime_activation_status")=="NOT_ADMITTED_PENDING_CURRENT_HOST","provider optional/non-authoritative invariant drift"),
      ("OSD-002",p.get("upstream",{}).get("commit")==UPSTREAM and p.get("upstream",{}).get("license")=="MIT" and bool(re.fullmatch(r"[0-9a-f]{40}",UPSTREAM)),"immutable upstream pin/license drift"),
      ("OSD-003",c.get("id")==CONTRACT and c.get("provider_neutral") is True and c.get("authority",{}).get("independent_root_authority") is False and c.get("baseline_effect")=={"capability_count_after":143,"new_capabilities":0,"new_architectural_authorities":0},"provider-neutral contract drift"),
      ("OSD-004",d.get("id")==DECISION and d.get("status")=="CANONICAL_CLOSED" and d.get("production_constraints",{}).get("full_approval_mode_forbidden") is True and d.get("production_constraints",{}).get("document_only_promotion_forbidden") is True,"decision safety drift"),
      ("OSD-005",p.get("approval_policy",{}).get("production_full_approval_mode")=="FORBIDDEN" and c.get("runtime_safety",{}).get("production_full_approval_mode_allowed") is False and c.get("runtime_safety",{}).get("unmediated_shell_execution_allowed") is False,"approval mediation drift"),
      ("OSD-006",p.get("skill_policy",{}).get("third_party_skill_activation_requires_fa3_admission") is True and p.get("skill_policy",{}).get("third_party_skill_license_must_be_independently_admitted") is True and c.get("skills",{}).get("third_party_skill_inert_until_admitted") is True,"skill admission/license drift"),
      ("OSD-007",p.get("provenance_policy",{}).get("upstream_local_run_log_role")=="NON_AUTHORITATIVE_PROJECTION_ONLY" and c.get("research_artifacts",{}).get("provider_run_history")=="NON_AUTHORITATIVE_LOCAL_PROJECTION","provenance authority escape"),
      ("OSD-008",p.get("authority_boundaries",{}).get("mcp_tool_mediation")=="FA3-AUTH-MCP-GATEWAY-001" and p.get("authority_boundaries",{}).get("host_resource")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","authority delegation drift"),
      ("OSD-009",c.get("hardware",{}).get("placement_authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and c.get("hardware",{}).get("exact_gpu_sku_pin_forbidden") is True and c.get("hardware",{}).get("runtime_gpu_ordinal_as_identity_forbidden") is True,"portable HRB policy drift"),
      ("OSD-010",all(c.get("hardware",{}).get(k) is True for k in ["ui_display_role_required","compute_non_display_role_required_for_accelerated_research","ui_and_compute_accelerator_roles_must_be_distinct","ui_process_compute_gpu_default_claim_forbidden","compute_on_display_role_gpu_forbidden"]),"UI/compute role separation drift"),
      ("OSD-011",c.get("hardware",{}).get("no_cpu_or_cross_accelerator_fallback") is True and c.get("runtime_safety",{}).get("cross_accelerator_fallback_allowed") is False and c.get("runtime_safety",{}).get("cpu_fallback_for_gpu_required_work_allowed") is False,"fallback policy drift"),
      ("OSD-012",h.get("status")=="PENDING_REAL_CURRENT_HOST_EXECUTION" and h.get("production_admitted") is False and h.get("mandatory_hardware_conformance_chain")==CHAIN and h.get("portable_hardware_policy",{}).get("current_host_hardware_tuple")=="EVIDENCE_ONLY","current-host conformance drift"),
      ("OSD-013",g.get("id")==GATE and g.get("fail_closed") is True and g.get("hosted_ci_may_promote_runtime") is False and g.get("rule_count")==len(RULES) and g.get("mandatory_hardware_conformance_chain")==CHAIN,"gate descriptor drift"),
      ("OSD-014",e.get("rules")==RULES and e.get("mandatory_rule_count")==len(RULES) and e.get("mandatory_hardware_conformance_chain")==CHAIN,"enforcement drift"),
      ("OSD-015",v.get("status")=="PASS" and v.get("runtime_evidence")=="NOT_CLAIMED" and v.get("current_host_production_claim") is False and v.get("execution",{}).get("regression_cases",{}).get("passed")==7,"static evidence drift"),
      ("OSD-016",b.get("hardware_authority_id")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and b.get("roles",{}).get("display_ui",{}).get("model")=="NVIDIA RTX A1000" and b.get("roles",{}).get("compute_ai",{}).get("model")=="NVIDIA GeForce RTX 3090" and b.get("role_swap_allowed") is False and b.get("automatic_fallback_allowed") is False,"current-host 3090 compute/A1000 UI binding drift")]
    for code,ok,msg in checks:
        if not ok: out.append(fail(code,msg))
    return out

def host_findings(root:Path,receipt:Path):
    try: r,b=load(receipt),load(root/PATHS["b"])
    except Exception as exc: return [fail("OSD-HOST-000",f"receipt/binding missing: {exc!r}")]
    out=[]; pol=r.get("policy",{}); hrb=r.get("hrb",{}); ui=hrb.get("display_binding",{}); ai=hrb.get("compute_lease",{}); hw=r.get("hardware_conformance",{}); ex=r.get("execution",{})
    checks=[
      ("OSD-HOST-001",r.get("schema")=="fa3.open-science-desktop-current-host-receipt.v1" and r.get("conformance_id")==CONFORMANCE and r.get("status")=="PASS" and r.get("real_current_host_execution") is True and r.get("capability_count_after")==COUNT and r.get("new_architectural_authorities")==0 and r.get("global_promotion_claim") is False,"real current-host PASS missing"),
      ("OSD-HOST-002",pol.get("full_approval_mode") is False and pol.get("unadmitted_skills_active") is False and pol.get("provenance_projection_only") is True,"runtime policy proof failed"),
      ("OSD-HOST-003",hrb.get("authority_id")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and ui.get("role")=="DISPLAY" and ui.get("model")==b["roles"]["display_ui"]["model"] and ui.get("display_active") is True and ai.get("role")=="COMPUTE" and ai.get("model")==b["roles"]["compute_ai"]["model"] and ai.get("compute_eligible") is True and ai.get("display_active") is False and ai.get("lease_valid") is True,"HRB GPU-role binding mismatch"),
      ("OSD-HOST-004",bool(ui.get("device_uuid")) and bool(ai.get("device_uuid")) and ui.get("device_uuid")!=ai.get("device_uuid") and bdf(ui.get("pci_bdf"))!=bdf(ai.get("pci_bdf")),"accelerator identities not distinct"),
      ("OSD-HOST-005",all(hw.get(k) is True for k in ["uuid_bdf_live_identity","topology_revalidated_at_admission","numa_locality_evidence","cuda_execution","no_fallback"]),"UUID/BDF/NUMA/CUDA/no-fallback proof failed"),
      ("OSD-HOST-006",ex.get("ui_gpu_uuid")==ui.get("device_uuid") and ex.get("compute_gpu_uuid")==ai.get("device_uuid") and ex.get("ui_claimed_compute_gpu") is False and ex.get("compute_used_display_gpu") is False and ex.get("observed_cuda") is True and ex.get("silent_cpu_fallback_observed") is False and ex.get("cross_accelerator_fallback_observed") is False,"execution role separation/fallback violation")]
    for code,ok,msg in checks:
        if not ok: out.append(fail(code,msg))
    return out

def run(root:Path,receipt:Path|None=None):
    findings=static_findings(root); scope="STATIC_MATERIALIZATION"
    if receipt is not None:
        scope="CURRENT_HOST_RUNTIME"
        if not findings: findings.extend(host_findings(root,receipt))
    report={"schema":"fa3.open-science-desktop-gate-report.v1","gate_id":GATE,"scope":scope,"result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"capability_count":COUNT,"current_host_production_claim":scope=="CURRENT_HOST_RUNTIME" and not findings,"mandatory_hardware_conformance_chain":CHAIN}
    out=root/"reports/open-science-desktop-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--current-host-receipt"); a=ap.parse_args()
    report=run(Path(a.root).resolve(),Path(a.current_host_receipt).resolve() if a.current_host_receipt else None); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
