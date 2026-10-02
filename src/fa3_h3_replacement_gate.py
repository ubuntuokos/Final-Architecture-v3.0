#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

GATE_ID="FA3-H3-REPLACEMENT-GATESET-001"
H3_ID="FA3-PROVIDER-MINIMAX-H3-001"
REQUIRED_CAPS={"CAP-159","CAP-160"}
ROOT=Path(__file__).resolve().parents[1]

def load(root:Path, rel:str)->dict[str,Any]:
    return json.loads((root/rel).read_text(encoding="utf-8"))

def gate(root:Path)->dict[str,Any]:
    errors=[]
    cap_count=module_active_capability_count(__file__)
    policy=load(root,"canonical/h3-replacement-enforcement.json")
    profile=load(root,"canonical/profiles/FA3-VIDEO-001.json")
    provider=load(root,"canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
    video=load(root,"canonical/video-enforcement.json")
    execution=load(root,"canonical/contracts/FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001.json")
    router=load(root,"canonical/contracts/FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001.json")
    kling=load(root,"canonical/providers/FA3-PROVIDER-KLING-001.json")

    def require(cond:bool,msg:str)->None:
        if not cond: errors.append(msg)

    require(cap_count==175,"active capability baseline must be 175")
    require(policy.get("capability_count")==cap_count,"replacement policy baseline drift")
    require(policy.get("capability_delta")==0 and policy.get("authority_delta")==0,"replacement must not add capability or authority")
    require(policy.get("mandatory") is True and policy.get("fail_closed") is True,"replacement policy must be mandatory/fail-closed")
    require(H3_ID not in profile.get("providers",[]),"H3 remains active in video profile")
    require(H3_ID not in video.get("provider_ids",[]),"H3 remains active in video enforcement provider set")
    require(provider.get("status")=="RETIRED_REFERENCE_ONLY","H3 provider must be retired reference only")
    require(provider.get("activation_mode")=="DISABLED_FORBIDDEN","H3 activation must be forbidden")
    require(provider.get("runtime_execution_forbidden") is True,"H3 runtime execution must be forbidden")
    require(provider.get("provider_selection_forbidden") is True,"H3 provider selection must be forbidden")
    require(REQUIRED_CAPS.issubset(set(profile.get("capabilities",[]))),"CAP-159/CAP-160 missing from video profile")
    for contract in ("FA3-MOTION-VIDEO-EXECUTION-CONTRACTS-001","FA3-VIDEO-MODEL-ROUTER-PROJECTION-CONTRACTS-001"):
        require(contract in profile.get("contracts",[]),f"video profile missing {contract}")
    require(execution.get("provider_neutral") is True,"motion/video execution contract must be provider neutral")
    require(execution.get("capability_count")==cap_count,"motion/video execution contract baseline drift")
    require(set(execution.get("capability_bindings",[]))==REQUIRED_CAPS,"motion/video capability binding drift")
    require(router.get("authority")=="FA3-AUTH-MODEL-ROUTER-001","video router authority drift")
    require(router.get("capability_count")==cap_count,"video router contract baseline drift")
    rules=execution.get("rules",{})
    require(rules.get("hard_projection_loss_fails_closed") is True,"hard projection loss must fail closed")
    require(rules.get("provider_numeric_limits_are_runtime_metadata") is True,"provider limits must remain runtime metadata")
    require(rules.get("silent_provider_fallback_forbidden") is True,"silent provider fallback must be forbidden")
    chain=policy.get("replacement",{}).get("mandatory_execution_chain",[])
    for item in ("FA3-AUTH-MODEL-ROUTER-001","provider_admission","FA3-AUTH-HOST-RESOURCE-BROKER-001","ProviderProjectionLossReport"):
        require(item in chain,f"replacement chain missing {item}")
    discovery=kling.get("capability_discovery",{})
    require(discovery.get("mode")=="DYNAMIC_AT_ADMISSION_AND_EXECUTION","Kling capability discovery must be dynamic")
    require(discovery.get("canonical_numeric_limits_forbidden") is True,"Kling numeric limits must not be canonical")
    identity=kling.get("provider_identity_policy",{})
    require(identity.get("proxy_or_aggregator_must_not_impersonate_native_kling") is True,"proxy/native Kling identity separation missing")
    require(video.get("h3_policy_mode")=="HISTORICAL_REFERENCE_ONLY_NO_EXECUTION","video H3 policy must be historical-only")
    mv=video.get("motion_video_execution",{})
    require(mv.get("provider_selection_authority")=="FA3-AUTH-MODEL-ROUTER-001","Motion/Video must use Model Router")
    require(mv.get("resource_authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","Motion/Video must use HRB")
    require(mv.get("current_host_provider_runtime_promotion_requires_real_e2e") is True,"provider current-host promotion must require real E2E")

    result={
      "schema":"fa3.h3-replacement-gate-report.v2",
      "gate_id":GATE_ID,
      "result":"PASS" if not errors else "FAIL",
      "errors":errors,
      "capability_count":cap_count,
      "capability_delta":0,
      "authority_delta":0,
      "current_host_runtime_claim":False,
      "provider_runtime_promotion_claim":False
    }
    out=root/"reports/h3-replacement-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(ROOT))
    args=ap.parse_args()
    result=gate(Path(args.root).resolve())
    print(json.dumps(result,indent=2))
    return 0 if result["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
