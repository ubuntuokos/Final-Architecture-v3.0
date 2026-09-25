#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
from fa3_supply_chain_admission import evaluate_receipt
from fa3_provider_runtime import validate_runtime_environment
from fa3_upstream_patchset import evaluate_patchset
from fa3_hrb_composite_lease import evaluate_reservation_plan,derive_child_lease,cascade_revocation,CompositeLeaseError,RESOURCE_ORDER
from fa3_release_baseline import module_active_capability_count

GATESET_ID="FA3-SUPPLY-RUNTIME-HARDENING-GATESET-001"
CAPABILITY_COUNT=module_active_capability_count(__file__)

def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def finding(code,msg,**kw): return {"code":code,"severity":"P0","message":msg,**kw}

def regressions()->dict[str,Any]:
    H="a"*64; C="b"*40
    receipt={"schema":"fa3.software-supply-chain-receipt.v1","source":{"repository":"example/repo","commit":C},"artifact":{"sha256":H},
      "dependency_lock":{"required":True,"sha256":H},"sbom":{"format":"CYCLONEDX_JSON","sha256":H,"scanner":"syft","scanner_version":"1"},
      "license":{"scanner":"scancode","scanner_version":"1","declared_expression":"MIT","detected_expressions":["MIT"],"conflicts":[],"commercial_compatible":True,"redistribution_compatible":True},
      "vulnerabilities":{"scanner":"grype","scanner_version":"1","findings":[]},"provenance":{"builder":"fixture","build_recipe_sha256":H}}
    scs_ok=evaluate_receipt(receipt)["result"]=="PASS"
    bad=json.loads(json.dumps(receipt)); bad["license"]["conflicts"]=["MIT vs proprietary"]; scs_bad=evaluate_receipt(bad)["result"]=="FAIL"
    venv={"schema":"fa3.provider-runtime-environment.v1","provider_id":"P","execution_class":"VENV","hrb_admission_required":True,"secret_delivery":"NONE","host_global_reconfiguration":False,"upstream_uninstall_required":False,"supply_chain_receipt_status":"PASS","venv":{"manager":"uv","dependency_lock_sha256":H,"environment_identity_sha256":H,"system_site_packages":False}}
    rt_ok=validate_runtime_environment(venv)["result"]=="PASS"
    oci={"schema":"fa3.provider-runtime-environment.v1","provider_id":"P","execution_class":"OCI","hrb_admission_required":True,"secret_delivery":"SECRETREF","host_global_reconfiguration":False,"upstream_uninstall_required":False,"supply_chain_receipt_status":"PASS","oci":{"engine":"podman","rootless":True,"image_digest":"sha256:"+H,"build_recipe_sha256":H,"mutable_tag_only":False,"network_default":"DENY","explicit_mounts_only":True,"accelerator_device_projection_from_hrb":True}}
    oci_ok=validate_runtime_environment(oci)["result"]=="PASS"
    oci_bad=json.loads(json.dumps(oci)); oci_bad["oci"]["rootless"]=False; oci_refusal=validate_runtime_environment(oci_bad)["result"]=="FAIL"
    patch={"schema":"fa3.upstream-patch-set.v1","disposition":"PATCHED_VENDOR","upstream_repository":"x/y","upstream_commit":C,"patched_commit":"c"*40,"patch_series_sha256":H,"patched_tree_sha256":H,"dependency_lock_sha256":H,"reason":"security fix","upstream_issue_refs":["#1"],"security_disposition":"PASS","supply_chain_receipt_status":"PASS","review_by":"2099-01-01","license_disposition":{"commercial_compatible":True,"redistribution_compatible":True,"conflicts":[]}}
    patch_ok=evaluate_patchset(patch)["distribution_admitted"] is True
    lp=json.loads(json.dumps(patch)); lp["license_disposition"]["redistribution_compatible"]=False
    patch_license_refusal=evaluate_patchset(lp)["distribution_admitted"] is False
    plan={"schema":"fa3.resource-reservation-plan.v1","authority_id":"FA3-AUTH-HOST-RESOURCE-BROKER-001","atomic_admission":True,"hold_and_wait":False,"acquisition_order":list(RESOURCE_ORDER),"workloads":[{"id":"whisper","resources":{"cpu_threads":4,"ram_bytes":8,"vram_bytes":8}},{"id":"demucs","resources":{"cpu_threads":4,"ram_bytes":8,"vram_bytes":6}}],"overlap_groups":[["whisper","demucs"]],"accelerators":[{"stable_id":"GPU-test","runtime_ordinal_is_identity":False}]}
    hrb=evaluate_reservation_plan(plan,{"cpu_threads":16,"ram_bytes":32,"vram_bytes":24,"io_bytes_per_second":0,"network_bytes_per_second":0})
    hrb_ok=hrb["atomic_admitted"]
    too_small=evaluate_reservation_plan(plan,{"cpu_threads":16,"ram_bytes":32,"vram_bytes":10,"io_bytes_per_second":0,"network_bytes_per_second":0})["result"]=="FAIL"
    parent={"lease_id":"p","generation":1,"state":"ACTIVE","expires_at_utc":"2099-01-01T01:00:00Z","resources":{"cpu_threads":8,"ram_bytes":16,"vram_bytes":12},"child_allocated_resources":{},"accelerator_assignments":[{"stable_id":"GPU-test"}]}
    req={"lease_id":"c","issued_at_utc":"2099-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:30:00Z","resources":{"cpu_threads":4,"ram_bytes":8,"vram_bytes":6},"accelerator_assignments":[{"stable_id":"GPU-test"}],"scope":{"purpose":"demucs"}}
    child=derive_child_lease(parent,req,issuer="FA3-AUTH-HOST-RESOURCE-BROKER-001")
    derived_ok=child["parent_lease_id"]=="p" and child["may_mint_child_lease"] is False
    non_hrb=False
    try: derive_child_lease(parent,req,issuer="PROVIDER")
    except CompositeLeaseError: non_hrb=True
    parent["state"]="REVOKING"; casc=cascade_revocation(parent,[{**child,"state":"ACTIVE"}]); cascade_ok=casc[0]["state"]=="REVOKING"
    cases={"scs_positive":scs_ok,"scs_license_conflict_refused":scs_bad,"venv_positive":rt_ok,"oci_positive":oci_ok,"rootful_oci_refused":oci_refusal,"patch_positive":patch_ok,"patch_license_failure_not_overridden":patch_license_refusal,"hrb_atomic_positive":hrb_ok,"hrb_insufficient_capacity_refused":too_small,"derived_lease_positive":derived_ok,"non_hrb_issuer_refused":non_hrb,"parent_revocation_cascades":cascade_ok}
    return {"result":"PASS" if all(cases.values()) else "FAIL","cases":[{"case_id":k,"status":"PASS" if v else "FAIL"} for k,v in cases.items()]}

def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); findings=[]
    paths={
      "profile":"canonical/profiles/FA3-PROVIDER-RUNTIME-001.json",
      "contract":"canonical/contracts/FA3-PROVIDER-RUNTIME-CONTRACTS-001.json",
      "decision":"canonical/decisions/FA3-DEC-SUPPLY-RUNTIME-HRB-HARDENING-2026-09-25.json",
      "gate":"canonical/FA3-GATE-SUPPLY-RUNTIME-HARDENING-001.json",
      "enforcement":"canonical/supply-runtime-hardening-enforcement.json",
      "scs":"canonical/contracts/FA3-SCS-CONTRACTS-001.json",
      "hrb":"canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json",
      "runtime":"canonical/contracts/FA3-RUNTIME-HARDENING-CONTRACTS-001.json",
      "hu":"canonical/profiles/FA3-HU-AQC-001.json",
      "policy":"canonical/enforcement-policy.json",
      "scs_schema":"canonical/schemas/software-supply-chain-receipt.v1.json",
      "runtime_schema":"canonical/schemas/provider-runtime-environment.v1.json",
      "reservation_schema":"canonical/schemas/resource-reservation-plan.v1.json",
      "patch_schema":"canonical/schemas/upstream-patch-set.v1.json",
      "tencent_patch":"canonical/upstream-patches/FA3-UPSTREAM-PATCHSET-TENCENTDB-AGENT-MEMORY-001.json",
      "opencut_patch":"canonical/upstream-patches/FA3-UPSTREAM-PATCHSET-OPENCUT-001.json",
    }
    data={}
    for k,p in paths.items():
        try:data[k]=loadj(root/p)
        except Exception as e: findings.append(finding("SRH-000","required materialization unreadable",path=p,error=repr(e)))
    if not findings:
        p=data["profile"]; c=data["contract"]; d=data["decision"]; g=data["gate"]; e=data["enforcement"]
        if not(p.get("id")=="FA3-PROVIDER-RUNTIME-001" and p.get("capability_count")==CAPABILITY_COUNT and p.get("new_capability") is False and p.get("new_architectural_authority") is False): findings.append(finding("SRH-001","provider runtime profile invariant drift"))
        if c.get("id")!="FA3-PROVIDER-RUNTIME-CONTRACTS-001" or c.get("new_architectural_authority") is not False: findings.append(finding("SRH-002","provider runtime contract invariant drift"))
        if d.get("new_capabilities")!=0 or d.get("new_architectural_authorities")!=0 or d.get("capability_count_after")!=CAPABILITY_COUNT: findings.append(finding("SRH-003","decision changes capability/authority baseline"))
        if g.get("gateset_id")!=GATESET_ID or g.get("fail_closed") is not True: findings.append(finding("SRH-004","gate record drift"))
        if e.get("gateset_id")!=GATESET_ID or e.get("hrb",{}).get("hold_and_wait") is not False: findings.append(finding("SRH-005","enforcement drift"))
        scs=set(data["scs"].get("contracts",[]))
        for x in ("SBOMAttestation","VulnerabilityDispositionReceipt","SoftwareSupplyChainReceipt","UpstreamPatchSet"):
            if x not in scs: findings.append(finding("SRH-006","SCS contract extension missing",contract=x))
        hrb=set(data["hrb"].get("contracts",[]))
        for x in ("ResourceReservationPlan","LeaseGroup","DerivedExecutionLease","LeaseLineageReceipt"):
            if x not in hrb: findings.append(finding("SRH-007","HRB composite contract extension missing",contract=x))
        runtime=set(data["runtime"].get("contracts",[]))
        for x in ("ProviderRuntimeEnvironment","ProviderRuntimeReceipt"):
            if x not in runtime: findings.append(finding("SRH-008","runtime hardening provider environment contract missing",contract=x))
        if data["hu"].get("current_host_runtime_promotion_claimed") is not False: findings.append(finding("SRH-009","HU-AQC document-only promotion forbidden"))
        if GATESET_ID not in set(data["policy"].get("mandatory_reference_gates",[])): findings.append(finding("SRH-010","global enforcement binding missing"))
        if data["scs_schema"].get("$id")!="fa3.software-supply-chain-receipt.v1" or data["runtime_schema"].get("$id")!="fa3.provider-runtime-environment.v1" or data["reservation_schema"].get("$id")!="fa3.resource-reservation-plan.v1" or data["patch_schema"].get("$id")!="fa3.upstream-patch-set.v1": findings.append(finding("SRH-014","typed schema identity drift"))
        tp=evaluate_patchset(data["tencent_patch"])
        if tp["result"]!="PASS" or data["tencent_patch"].get("disposition")!="REFERENCE_ONLY" or data["tencent_patch"].get("runtime_admission") is not False or data["tencent_patch"].get("license_disposition",{}).get("conflicts")==[]: findings.append(finding("SRH-012","TencentDB security/license blockers must remain fail-closed reference-only"))
        op=evaluate_patchset(data["opencut_patch"])
        if op["result"]!="PASS" or data["opencut_patch"].get("disposition")!="REFERENCE_ONLY" or data["opencut_patch"].get("runtime_admission") is not False: findings.append(finding("SRH-013","OpenCut unstable interface disposition must remain reference-only"))
    reg=regressions()
    if reg["result"]!="PASS": findings.append(finding("SRH-011","fail-closed regression matrix failed"))
    report={"schema":"fa3.supply-runtime-hardening-gate-report.v1","gate_id":"FA3-GATE-SUPPLY-RUNTIME-HARDENING-001","gateset_id":GATESET_ID,"result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"regressions":reg,"capability_count":CAPABILITY_COUNT,"new_architectural_authorities":0,"current_host_hu_aqc_promotion_claim":False}
    out=root/"reports/supply-runtime-hardening-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args(); r=gate(Path(a.root)); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
