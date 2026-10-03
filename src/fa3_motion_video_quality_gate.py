#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count
C=["FA3-MOTION-PLAN-CONTRACTS-001","FA3-MOTION-RENDER-CONTRACTS-001","FA3-MEDIA-QUALITY-REVIEW-CONTRACTS-001","FA3-MOTION-COMPONENT-LAB-CONTRACTS-001"];R=[f"MVQ-{i:03d}" for i in range(1,25)]
def L(p):return json.loads(p.read_text(encoding="utf-8"))
def gate(root:Path)->dict:
 f=[];p=L(root/"canonical/profiles/FA3-SHARED-MOTION-VIDEO-QUALITY-001.json");e=L(root/"canonical/motion-video-quality-enforcement.json");d=L(root/"canonical/decisions/FA3-DEC-SHARED-MOTION-VIDEO-QUALITY-2026-10-03.json");c=[L(root/f"canonical/contracts/{x}.json") for x in C];n=module_active_capability_count(__file__)
 def q(ok,code,msg):
  if not ok:f.append({"code":code,"severity":"P0","message":msg})
 checks=[p.get("capability_count")==175 and n==175,p.get("new_architectural_authority") is False and p.get("architectural_authority") is False,p.get("canonical_root") is False,p.get("provider_neutral") is True,p["editorial_boundary"].get("native_project_authoritative") is True,p["editorial_boundary"].get("direct_native_project_mutation_forbidden") is True,p["editorial_boundary"].get("mutation_surface")=="FA3_VIDEO_EDITOR_COMMAND_BUS",any(x.get("name")=="Revision Binding" for x in c[0]["contracts"]),any(x.get("name")=="Revision Binding" for x in c[0]["contracts"]),p["editorial_boundary"].get("stale_revision_fail_closed") is True,any(x.get("name")=="Truthful Determinism" for x in c[1]["contracts"]),any("nondeterministic" in x.get("rule","").lower() for x in c[1]["contracts"]),p["hardware_audit"].get("cpu_only_viable") is True,p["hardware_audit"].get("accelerator_cardinality")=="0..N",p["authorities"].get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001",p["authorities"].get("model_routing")=="FA3-AUTH-MODEL-ROUTER-001",p["authorities"].get("action_execution")=="FA3-UNIFIED-ACTION-FABRIC-001",any(x.get("name")=="Independent Review" for x in c[2]["contracts"]),any(x.get("name")=="Verification State" for x in c[2]["contracts"]),any("producer task MUST NOT" in x.get("rule","") for x in c[2]["contracts"]),any(x.get("name")=="Evidence Chain" for x in c[2]["contracts"]),L(root/"canonical/actions/motion.apply.json").get("rollback_reference_required") is True,p["engine_policy"].get("direct_engine_execution") is False,p["current_host"].get("physical_current_host_pass_claimed") is False and d["current_host"].get("physical_current_host_pass_claimed") is False]
 for i,ok in enumerate(checks,1):q(ok,f"MVQ-{i:03d}",f"motion video quality invariant {i} failed")
 q(e.get("rules")==R and e.get("rule_count")==24 and e.get("fail_closed") is True,"MVQ-ENF","enforcement drift")
 q(d.get("capability_count_after")==175 and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0,"MVQ-DEC","decision baseline drift")
 return {"schema":"fa3.motion-video-quality-gate-report.v1","gate_id":"FA3-MOTION-VIDEO-QUALITY-GATESET-001","result":"PASS" if not f else "FAIL","capability_count":n,"rules_checked":24,"findings":f,"physical_current_host_pass_claimed":False}
if __name__=="__main__":
 import argparse
 a=argparse.ArgumentParser();a.add_argument("--root",default=".");x=a.parse_args();print(json.dumps(gate(Path(x.root).resolve()),indent=2))
