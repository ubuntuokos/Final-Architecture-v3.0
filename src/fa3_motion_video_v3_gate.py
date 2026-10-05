#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REQ=[
 "canonical/profiles/FA3-VIDEO-001.json",
 "canonical/contracts/FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001.json",
 "canonical/contracts/FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001.json",
 "canonical/contracts/FA3-VIDEO-REFINEMENT-CONTRACTS-001.json",
 "canonical/intents/FA3-MOTION-VIDEO-V3-APPLICATION-INTENT-2026-10-02.json",
 "canonical/assessments/FA3-MOTION-VIDEO-V3-REUSE-ASSESSMENT-2026-10-02.json",
 "canonical/decisions/FA3-DEC-MOTION-VIDEO-V3-SOL-REFINEMENT-2026-10-02.json",
 "src/fa3_motion_video_provider_adapter.py","src/fa3_video_model_router.py","src/fa3_video_refinement.py"
]
DONORS={"FA3-DONOR-HUGGINGFACE-DIFFUSERS-001","FA3-DONOR-XDIT-001","FA3-DONOR-SKYREELS-V3-001","FA3-DONOR-VIDEOSYS-001","FA3-DONOR-NVLABS-SANA-001"}
def load(rel): return json.loads((ROOT/rel).read_text())
def gate():
 f=[]
 for rel in REQ:
  if not (ROOT/rel).is_file(): f.append({"code":"MV3-001","path":rel})
 if f:return {"schema":"fa3.motion-video-v3-gate-report.v1","result":"FAIL","findings":f}
 p=load(REQ[0]); h=load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json"); a=load(REQ[5]); c=load(REQ[3]); links=load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
 for cap in ("CAP-159","CAP-160"):
  if cap not in p.get("capabilities",[]):f.append({"code":"MV3-010","missing":cap})
 for cid in ("FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001","FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001","FA3-VIDEO-REFINEMENT-CONTRACTS-001"):
  if cid not in p.get("contracts",[]):f.append({"code":"MV3-011","missing":cid})
 if h.get("status")!="ACCEPTED_CONDITIONAL_REFERENCE" or h.get("activation_mode")!="OPTIONAL_DISABLED_BY_DEFAULT":f.append({"code":"MV3-020"})
 if a.get("result")!="PASS" or a.get("capability_count_after")!=175 or a.get("new_capabilities")!=0 or a.get("new_architectural_authorities")!=0:f.append({"code":"MV3-030"})
 used={x.get("donor_id") for x in links.get("donor_usage_records",[]) if x.get("status")!="REMOVED"}
 if not DONORS.issubset(used):f.append({"code":"MV3-031","missing":sorted(DONORS-used)})
 rules=c.get("rules",{})
 for k in ("generator_and_refiner_lifecycle_separated","cpu_reference_path_mandatory_at_fabric_level","silent_device_backend_provider_or_model_fallback_forbidden"):
  if rules.get(k) is not True:f.append({"code":"MV3-040","rule":k})
 if c.get("donor_pattern_provenance",{}).get("runtime_dependency") is not False:f.append({"code":"MV3-041"})
 return {"schema":"fa3.motion-video-v3-gate-report.v1","gate_id":"FA3-MOTION-VIDEO-V3-GATESET-001","result":"PASS" if not f else "FAIL","findings":f,"capability_count":175,"current_host_runtime_promotion_claim":False}
if __name__=="__main__":
 r=gate();print(json.dumps(r,indent=2));raise SystemExit(0 if r["result"]=="PASS" else 2)
