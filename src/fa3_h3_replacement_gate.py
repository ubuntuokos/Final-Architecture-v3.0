#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count

REPORT=Path("reports/h3-replacement-gate-report.json")
def loadj(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def gate(root:Path)->dict:
    errors=[]
    def chk(cond,msg):
        if not cond: errors.append(msg)
    required=[
      "canonical/FA3-GATE-H3-REPLACEMENT-001.json","canonical/h3-replacement-enforcement.json",
      "canonical/contracts/FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001.json","canonical/contracts/FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001.json",
      "canonical/assessments/FA3-H3-REPLACEMENT-REUSE-ASSESSMENT-001.json","src/fa3_motion_video_provider_adapter.py","src/fa3_video_model_router.py"
    ]
    for rel in required: chk((root/rel).is_file(),f"missing {rel}")
    if not errors:
        h3=loadj(root/"canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        profile=loadj(root/"canonical/profiles/FA3-VIDEO-001.json")
        policy=loadj(root/"canonical/h3-replacement-enforcement.json")
        contract=loadj(root/"canonical/contracts/FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001.json")
        assessment=loadj(root/"canonical/assessments/FA3-H3-REPLACEMENT-REUSE-ASSESSMENT-001.json")
        chk(module_active_capability_count(__file__)==175,"active capability baseline is not 175")
        chk(h3.get("status")=="RETIRED_REFERENCE_ONLY" and h3.get("runtime_execution_forbidden") is True,"H3 not retired")
        chk("FA3-PROVIDER-MINIMAX-H3-001" not in profile.get("providers",[]),"H3 remains active in video profile")
        chain=policy.get("replacement",{}).get("mandatory_execution_chain",[])
        for item in ("FA3-AUTH-MODEL-ROUTER-001","FA3-WORKLOAD-MODE-CONTRACTS-001","FA3-AUTH-HOST-RESOURCE-BROKER-001","HrbResourceLeaseSetProjection","FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001"):
            chk(item in chain,f"v2 execution chain missing {item}")
        chk(contract.get("hrb_resource_projection",{}).get("resource_cardinality")=="0..N","0..N resource projection missing")
        chk(contract.get("rules",{}).get("synchronized_av_output_must_not_claim_voice_authority") is True,"AV authority boundary missing")
        snap=assessment.get("donor_planning_snapshot",{})
        chk(snap.get("donor_registry_entry_count")==1349 and snap.get("donor_registry_blob_sha")=="22f262dcc88e4429bf5f5b7a4175efad72f63945","stale donor planning snapshot")
        chk(len(assessment.get("adopted_pattern_donors",[]))==4,"pattern donor usage set incomplete")
    report={"schema":"fa3.h3-replacement-gate-report.v2","gate_id":"FA3-H3-REPLACEMENT-GATESET-001","result":"PASS" if not errors else "FAIL","errors":errors,"capability_count":175,"capability_delta":0,"authority_delta":0,"current_host_runtime_claim":False,"provider_runtime_promotion_claim":False}
    out=root/REPORT; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); return report
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); a=ap.parse_args(); r=gate(Path(a.root).resolve()); print(json.dumps(r,indent=2)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
