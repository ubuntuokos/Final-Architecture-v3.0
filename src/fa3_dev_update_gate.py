#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
from fa3_uaf import ActionRegistry
ROOT=Path(__file__).resolve().parents[1]
FILES={"dev":ROOT/"canonical/FA3-DEV-MODE-001.json","update":ROOT/"canonical/FA3-UPDATE-FABRIC-001.json","security":ROOT/"canonical/FA3-SECURITY-UPDATE-001.json","restart":ROOT/"canonical/FA3-UPDATE-RESTART-001.json","runtime":ROOT/"canonical/FA3-DEV-UPDATE-RUNTIME-CONFORMANCE-001.json","dev_policy":ROOT/"config/fa3-dev-policy.json","update_policy":ROOT/"config/fa3-update-policy.json"}
ACTIONS={"development.enter","development.snapshot","development.freeze","update.check","update.apply-selected","update.security","update.restart-choice","update.rollback"}
VENDOR_TOKENS=("NVIDIA_driver","CUDA","ROCm","cuda:auto-fallback")
def load(path:Path)->dict[str,Any]:
    try:data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:raise AssertionError(f"{path.relative_to(ROOT)} unavailable/invalid: {exc}")
    if not isinstance(data,dict):raise AssertionError(f"{path.relative_to(ROOT)} must be JSON object")
    return data
def check(root:Path=ROOT)->dict[str,Any]:
    del root;docs={n:load(p) for n,p in FILES.items()};findings=[]
    for n in ("dev","update","security","restart"):
      d=docs[n]
      if d.get("status")!="CANONICAL" or d.get("priority")!="P0":findings.append(f"{n}: canonical P0 required")
      if d.get("new_capabilities")!=0 or d.get("new_architectural_authorities")!=0 or d.get("capability_count")!=143:findings.append(f"{n}: capability/authority invariant")
    dev=docs["dev"];update=docs["update"];security=docs["security"];restart=docs["restart"];runtime=docs["runtime"];dp=docs["dev_policy"];up=docs["update_policy"]
    if dev.get("production_invariant")!="FAIL_CLOSED_UNCHANGED" or dev.get("trust_domains",{}).get("development",{}).get("canonical_write")!="DENY":findings.append("dev: production/canonical boundary")
    if dev.get("operations",{}).get("freeze",{}).get("canonical_write") is not False or dev.get("operations",{}).get("promote",{}).get("requires")!=["STATIC_PASS","HOST_PASS","PROMOTION_READY"]:findings.append("dev: freeze/promotion boundary")
    rb=dev.get("resource_policy",{})
    if rb.get("accelerator_cardinality")!="0..N" or rb.get("cpu_only_valid") is not True or rb.get("global_vendor_pin") is not None:findings.append("dev: vendor-neutral hardware boundary")
    if dp.get("host_resource_broker",{}).get("fallback_backend")!="AUTO_COMPATIBLE_DISCOVERED_BACKEND" or dp.get("host_resource_broker",{}).get("global_vendor_pin") is not None:findings.append("dev policy: provider-neutral fallback")
    if update.get("operations",{}).get("blind_update_all") is not False or update.get("operations",{}).get("check_all") is not True:findings.append("update: blind/check-all invariant")
    if update.get("models",{}).get("separate_queue") is not True or update.get("host_critical",{}).get("automatic_blind_activation") is not False:findings.append("update: model/host critical invariant")
    hb=update.get("hardware_boundary",{})
    if hb.get("accelerator_cardinality")!="0..N" or hb.get("cpu_only_valid") is not True or hb.get("global_vendor_pin") is not None:findings.append("update: hardware boundary")
    if security.get("silent_forced_reboot")!="DENY" or security.get("protected_workload_interruption")!="DENY":findings.append("security: reboot/workload boundary")
    if restart.get("recommended_default")!="WHEN_IDLE_SAFE" or restart.get("scheduling",{}).get("scheduled_time_overrides_protected_workload") is not False:findings.append("restart: user/workload boundary")
    if set(restart.get("choices",[]))!={"RESTART_NOW","WHEN_IDLE_SAFE","SCHEDULE","LATER"}:findings.append("restart: choice set")
    if restart.get("execution_boundary",{}).get("decision_fabric_authority") is not False or restart.get("execution_boundary",{}).get("user_choice_authoritative") is not True:findings.append("restart: Decision Fabric/user authority")
    if up.get("allow_blind_update_all") is not False or up.get("automatic_security_updates") is not True or up.get("restart",{}).get("allow_silent_forced_reboot") is not False:findings.append("update policy invariant")
    if runtime.get("status")!="EXECUTABLE_REFERENCE_MATERIALIZED_CURRENT_HOST_E2E_PENDING" or runtime.get("claims")!=[] or "CURRENT_HOST_E2E_PASS" not in runtime.get("non_claims",[]):findings.append("runtime: false promotion claim")
    serialized="\n".join(json.dumps(d,sort_keys=True) for d in docs.values())
    for token in VENDOR_TOKENS:
      if token in serialized:findings.append(f"vendor-pin:{token}")
    amap={a.action_id:a for a in ActionRegistry.from_directory(ROOT/"canonical/actions").list()}
    missing=sorted(ACTIONS-set(amap))
    if missing:findings.append("uaf-actions-missing:"+",".join(missing))
    for aid in sorted(ACTIONS&set(amap)):
      a=amap[aid]
      if a.security.get("authentication")!="required" or a.security.get("authorization")!="required" or a.evidence.get("required") is not True:findings.append(f"uaf-action-security:{aid}")
      if a.resources.get("accelerator",{}).get("cardinality")!="0..N":findings.append(f"uaf-action-hardware:{aid}")
    return {"schema":"fa3.dev-update-gate-report.v2","gate":"FA3-DEV-MODE-001+FA3-UPDATE-FABRIC-001","status":"PASS" if not findings else "FAIL","blocking_findings":findings,"capability_delta":0,"authority_delta":0,"capability_count":143,"runtime_promotion_claimed":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--report",default="reports/fa3-dev-update-gate-report.json");a=p.parse_args();r=check();out=ROOT/a.report;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8");print(json.dumps(r,indent=2));return 0 if r["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
