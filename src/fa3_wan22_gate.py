#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PIN="1ea34ff48f87168174e12956e200b1d908b1c5ff"
PROVIDER="FA3-PROVIDER-WAN22-001"
REQUIRED=[
 "canonical/providers/FA3-PROVIDER-WAN22-001.json",
 "canonical/references/FA3-WAN22-UPSTREAM-REFERENCE-2026-09-26.json",
 "bin/fa3-wan22-provider-exec.py",
 "bin/fa3-wan22-current-host-admit.py",
 "bin/fa3-wan22-build-motion-video-manifest.py",
 "src/fa3_video_model_router.py",
 "canonical/contracts/FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001.json"
]
def load(rel):return json.loads((ROOT/rel).read_text())
def gate():
 errors=[]
 for rel in REQUIRED:
  if not (ROOT/rel).is_file():errors.append(f"missing:{rel}")
 if errors:return {"result":"FAIL","errors":errors}
 p=load(REQUIRED[0]);r=load(REQUIRED[1]);profile=load("canonical/profiles/FA3-VIDEO-001.json");video=load("canonical/video-enforcement.json");reuse=load("canonical/assessments/FA3-H3-REPLACEMENT-REUSE-ASSESSMENT-001.json")
 checks=[
  (p.get("architectural_authority") is False,"provider authority"),
  (p.get("upstream",{}).get("commit")==PIN,"provider pin"),
  (p.get("upstream",{}).get("code_license")=="Apache-2.0","code license"),
  (p.get("upstream",{}).get("model_license")=="Apache-2.0","model license"),
  (p.get("execution",{}).get("cost_class")=="FREE_LOCAL","cost class"),
  (p.get("execution",{}).get("direct_application_execution_forbidden") is True,"direct application execution"),
  (p.get("execution",{}).get("model_router_selection_required") is True,"router selection"),
  (p.get("execution",{}).get("local_accelerator_requires_hrb") is True,"HRB"),
  (p.get("model_policy",{}).get("admitted_model_artifact_required") is True,"model admission"),
  (p.get("current_host_production_evidence")=="PENDING","current host pending"),
  (r.get("observed_commit")==PIN,"reference pin"),
  (r.get("rules",{}).get("network_download_during_fa3_admission") is False,"no admission download"),
  (PROVIDER in profile.get("providers",[]),"profile provider registration"),
  (PROVIDER in video.get("provider_ids",[]),"video enforcement registration"),
  (PROVIDER in reuse.get("covered_ids",[]),"reuse assessment coverage"),
  ("FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001" in profile.get("contracts",[]),"router contract"),
 ]
 errors += [name for ok,name in checks if not ok]
 return {"schema":"fa3.wan22-gate-report.v1","gate_id":"FA3-WAN22-GATESET-001","result":"PASS" if not errors else "FAIL","errors":errors,"capability_count":143,"new_capabilities":0,"new_architectural_authorities":0,"current_host_runtime_promotion_claim":False}
def main():
 report=gate();out=ROOT/"reports/wan22-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2));return 0 if report["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
