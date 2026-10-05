#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, subprocess
from pathlib import Path
from typing import Any
from fa3_resource_admission_current_host_gate import validate_receipt as validate_resource_admission_receipt

ROOT=Path(__file__).resolve().parents[1]
ROUTER_AUTHORITY="FA3-AUTH-MODEL-ROUTER-001"
HRB_AUTHORITY="FA3-AUTH-HOST-RESOURCE-BROKER-001"
WORKLOAD_CONTRACT="FA3-WORKLOAD-MODE-CONTRACTS-001"
LIFECYCLE_CONTRACT="FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001"
BILLABLE_ACK="I_ACKNOWLEDGE_BILLABLE_FA3_VIDEO_E2E"
ALLOWED_COSTS={"FREE_LOCAL","FREE_REMOTE","BILLABLE_REMOTE"}
ALLOWED_TRANSPORTS={"FA3_EXECUTOR_COMMAND"}

class MotionVideoDenied(RuntimeError): pass

def loadj(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def nonempty(v:Any)->bool: return isinstance(v,str) and bool(v.strip())
def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def validate_provider_state(provider_id:str)->dict[str,Any]:
    p=ROOT/"canonical/providers"/f"{provider_id}.json"
    if not p.is_file(): raise MotionVideoDenied("canonical provider record missing")
    r=loadj(p)
    if r.get("architectural_authority") is not False: raise MotionVideoDenied("provider cannot be architectural authority")
    if r.get("status") in {"RETIRED_REFERENCE_ONLY","REJECTED","SUPERSEDED"}: raise MotionVideoDenied("retired/rejected provider cannot execute")
    if r.get("activation_mode") in {"DISABLED_FORBIDDEN","FORBIDDEN"}: raise MotionVideoDenied("disabled provider cannot execute")
    return r

def validate_selection(selection:dict[str,Any],manifest:dict[str,Any])->str:
    if selection.get("schema")!="fa3.motion-video-route-selection-receipt.v2": raise MotionVideoDenied("selection receipt schema mismatch")
    if selection.get("authority")!=ROUTER_AUTHORITY or selection.get("status")!="ROUTED": raise MotionVideoDenied("selection receipt is not Model Router authoritative")
    pid=str(selection.get("provider_id","")).strip()
    if manifest.get("schema")!="fa3.motion-video-execution-manifest.v2" or manifest.get("status")!="ADMITTED": raise MotionVideoDenied("execution manifest invalid")
    if not pid or manifest.get("provider_id")!=pid: raise MotionVideoDenied("selection/manifest provider mismatch")
    if manifest.get("provider_selection_authority")!=ROUTER_AUTHORITY or manifest.get("resource_authority")!=HRB_AUTHORITY: raise MotionVideoDenied("authority boundary mismatch")
    if manifest.get("transport") not in ALLOWED_TRANSPORTS or manifest.get("cost_class") not in ALLOWED_COSTS: raise MotionVideoDenied("unsupported transport or cost class")
    if manifest.get("silent_fallback_allowed") is not False: raise MotionVideoDenied("silent fallback forbidden")
    for key in ("service_provider","model_family"):
        if not nonempty(manifest.get(key)) or selection.get(key)!=manifest.get(key): raise MotionVideoDenied(f"{key} identity mismatch")
    snap=manifest.get("capability_snapshot")
    if not isinstance(snap,dict) or snap.get("schema")!="fa3.video-capability-snapshot.v2": raise MotionVideoDenied("capability snapshot v2 required")
    return pid

def validate_admission(manifest:dict[str,Any],provider_id:str)->None:
    ref=str(manifest.get("admission_receipt","")).strip(); expected=str(manifest.get("admission_receipt_sha256","")).lower()
    p=Path(ref).expanduser()
    if not p.is_absolute(): p=(ROOT/p).resolve()
    if not p.is_file() or len(expected)!=64 or sha256_file(p)!=expected: raise MotionVideoDenied("provider admission receipt binding invalid")
    r=loadj(p)
    if r.get("provider_id")!=provider_id or (r.get("status") not in {"PASS","ADMITTED"} and r.get("result") not in {"PASS","ADMITTED"}): raise MotionVideoDenied("provider admission denied")
    if r.get("synthetic_or_mock_provider") is True: raise MotionVideoDenied("synthetic provider admission forbidden")

def validate_lifecycle(manifest:dict[str,Any])->dict[str,Any]:
    lc=manifest.get("lifecycle_compatibility")
    if not isinstance(lc,dict): raise MotionVideoDenied("video lifecycle compatibility receipt required")
    if lc.get("contract_id")!=LIFECYCLE_CONTRACT: raise MotionVideoDenied("wrong lifecycle contract")
    required=("requested_backend","observed_backend","runtime_version_tuple","model_identity","model_component_tuple","compatibility_evidence")
    if any(not lc.get(k) for k in required): raise MotionVideoDenied("incomplete lifecycle compatibility")
    if lc["requested_backend"]!=lc["observed_backend"]: raise MotionVideoDenied("backend mismatch")
    if lc.get("fallback_policy")!="DENY": raise MotionVideoDenied("backend fallback must be DENY")
    return lc

def validate_workload_binding(manifest:dict[str,Any],binding:dict[str,Any]|None)->dict[str,Any]|None:
    if manifest.get("execution_topology")!="LOCAL": return None
    if not isinstance(binding,dict): raise MotionVideoDenied("local execution requires Workload Mode binding")
    if binding.get("schema")!="fa3.motion-video-workload-binding.v1" or binding.get("contract_id")!=WORKLOAD_CONTRACT: raise MotionVideoDenied("Workload Mode binding invalid")
    if binding.get("status")!="ACTIVE" or binding.get("domain")!="VIDEO_GENERATION": raise MotionVideoDenied("VIDEO_GENERATION workload session required")
    if not nonempty(binding.get("workload_session_id")) or binding.get("physical_resource_authority")!=HRB_AUTHORITY: raise MotionVideoDenied("workload session/HRB authority missing")
    if binding.get("provider_selection_authority")!=ROUTER_AUTHORITY: raise MotionVideoDenied("Workload Mode cannot own provider selection")
    if binding.get("workload_mode_mints_hrb_lease") is not False: raise MotionVideoDenied("Workload Mode must not mint HRB lease")
    mlp=binding.get("mode_lease_projection")
    if not isinstance(mlp,dict) or mlp.get("status")!="VALID": raise MotionVideoDenied("valid ModeLeaseProjection required")
    return binding

def validate_resource_projection(manifest:dict[str,Any],projection:dict[str,Any]|None)->list[dict[str,Any]]:
    local=manifest.get("execution_topology")=="LOCAL"
    accel=bool(manifest.get("requires_accelerator"))
    if not local: return []
    if not isinstance(projection,dict): raise MotionVideoDenied("local execution requires HRB resource projection")
    if projection.get("schema")!="fa3.motion-video-hrb-resource-projection.v1" or projection.get("authority")!=HRB_AUTHORITY: raise MotionVideoDenied("HRB resource projection invalid")
    resources=projection.get("resources")
    if not isinstance(resources,list): raise MotionVideoDenied("resource set missing")
    if projection.get("cardinality")!=len(resources): raise MotionVideoDenied("resource projection cardinality mismatch")
    if accel and not resources: raise MotionVideoDenied("accelerator execution requires non-empty HRB resource set")
    if not accel and resources: raise MotionVideoDenied("CPU-only execution cannot carry accelerator resources")
    seen=set(); out=[]
    for item in resources:
        if not isinstance(item,dict): raise MotionVideoDenied("invalid resource member")
        ref=Path(str(item.get("receipt_path",""))).expanduser()
        if not ref.is_absolute(): ref=(ROOT/ref).resolve()
        expected=str(item.get("receipt_sha256","")).lower()
        if not ref.is_file() or len(expected)!=64 or sha256_file(ref)!=expected: raise MotionVideoDenied("HRB member receipt binding invalid")
        receipt=loadj(ref); findings=validate_resource_admission_receipt(receipt)
        if findings: raise MotionVideoDenied("HRB member receipt rejected")
        lease=receipt.get("payload",{}).get("hrb_lease_identity",{})
        ident=(lease.get("lease_id"),lease.get("accelerator_uuid"),lease.get("pci_bus_id"))
        if not all(nonempty(x) for x in ident) or ident in seen: raise MotionVideoDenied("HRB resource identity missing or duplicated")
        seen.add(ident)
        out.append({"lease_id":ident[0],"accelerator_uuid":ident[1],"pci_bus_id":ident[2],"evidence_id":receipt.get("evidence_id")})
    return out

def validate_billing(manifest:dict[str,Any])->None:
    if manifest.get("cost_class")=="BILLABLE_REMOTE" and os.environ.get("FA3_VIDEO_BILLABLE_E2E_ACK")!=BILLABLE_ACK:
        raise MotionVideoDenied("explicit billable video acknowledgement required")

def execute_command(manifest:dict[str,Any],ir_path:Path,output_path:Path,timeout:float,resources:list[dict[str,Any]],binding:dict[str,Any]|None)->dict[str,Any]:
    exe=Path(str(manifest.get("executable",""))).expanduser()
    if not exe.is_absolute() or not exe.is_file(): raise MotionVideoDenied("executor command must be existing absolute file")
    if sha256_file(exe)!=str(manifest.get("executable_sha256","")).lower(): raise MotionVideoDenied("executor SHA256 mismatch")
    argv=manifest.get("argv")
    if not isinstance(argv,list) or any(not isinstance(x,str) for x in argv): raise MotionVideoDenied("executor argv invalid")
    rendered=[x.replace("{ir}",str(ir_path)).replace("{output}",str(output_path)) for x in argv]
    env={k:v for k,v in os.environ.items() if not any(t in k.upper() for t in ("API_KEY","TOKEN","SECRET","PASSWORD"))}
    env["FA3_HRB_RESOURCE_PROJECTION_JSON"]=json.dumps(resources,sort_keys=True,separators=(",",":"))
    if binding: env["FA3_WORKLOAD_SESSION_ID"]=str(binding["workload_session_id"])
    if len(resources)==1:
        env["FA3_HRB_LEASE_ID"]=resources[0]["lease_id"]; env["FA3_ACCELERATOR_UUID"]=resources[0]["accelerator_uuid"]; env["FA3_ACCELERATOR_PCI_BDF"]=resources[0]["pci_bus_id"]
    p=subprocess.run([str(exe),*rendered],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,env=env)
    if p.returncode!=0: raise MotionVideoDenied(f"executor command failed rc={p.returncode}")
    if output_path.is_file(): return {"status":"SUCCEEDED","artifact_path":str(output_path),"artifact_sha256":sha256_file(output_path)}
    try: result=json.loads(p.stdout)
    except Exception as exc: raise MotionVideoDenied("executor produced no artifact or JSON") from exc
    if not isinstance(result,dict): raise MotionVideoDenied("executor result invalid")
    return result

def execute(selection_path:Path,manifest_path:Path,ir_path:Path,*,workload_path:Path|None,resource_projection_path:Path|None,output_path:Path,timeout:float)->dict[str,Any]:
    selection=loadj(selection_path); manifest=loadj(manifest_path); ir=loadj(ir_path)
    pid=validate_selection(selection,manifest); validate_provider_state(pid)
    if str(selection.get("provider_manifest_sha256","")).lower()!=sha256_file(manifest_path): raise MotionVideoDenied("selection not bound to exact manifest")
    validate_admission(manifest,pid); lifecycle=validate_lifecycle(manifest)
    binding=validate_workload_binding(manifest,loadj(workload_path) if workload_path else None)
    resources=validate_resource_projection(manifest,loadj(resource_projection_path) if resource_projection_path else None)
    validate_billing(manifest)
    if ir.get("schema") not in {"fa3.video-generation-ir.v1","fa3.video-generation-ir.v2"}: raise MotionVideoDenied("VideoGenerationIR schema mismatch")
    result=execute_command(manifest,ir_path,output_path,timeout,resources,binding)
    if str(result.get("status","")).upper() not in {"COMPLETE","SUCCEEDED","PASS"}: raise MotionVideoDenied("execution result not successful")
    artifact=result.get("artifact_path") or result.get("artifact_url")
    if not nonempty(artifact): raise MotionVideoDenied("artifact reference missing")
    snap=manifest["capability_snapshot"]; av="SYNCHRONIZED_AV" in set(snap.get("output_modes",[]))
    if av and manifest.get("audio_authority_claim") is not False: raise MotionVideoDenied("synchronized AV provider cannot claim voice authority")
    return {
      "schema":"fa3.motion-video-execution-receipt.v2","status":"PASS","provider_id":pid,
      "service_provider":manifest.get("service_provider"),"model_family":manifest.get("model_family"),
      "model_id":manifest.get("model_id"),"model_version":manifest.get("model_version"),
      "provider_capability_snapshot":snap,"selection_receipt_sha256":sha256_file(selection_path),
      "provider_manifest_sha256":sha256_file(manifest_path),"video_generation_ir_sha256":sha256_file(ir_path),
      "workload_binding_sha256":sha256_file(workload_path) if workload_path else None,
      "resource_projection_sha256":sha256_file(resource_projection_path) if resource_projection_path else None,
      "resource_count":len(resources),"lifecycle_compatibility":lifecycle,
      "synchronized_av":av,"audio_authority_claim":False,"voice_identity_authority":"SEPARATE_FA3_VOICE_LAYER",
      "artifact_reference":artifact,"artifact_sha256":result.get("artifact_sha256"),
      "silent_fallback_used":False,"current_host_runtime_claim":False,"provider_runtime_promotion_claim":False
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--selection",required=True); ap.add_argument("--manifest",required=True); ap.add_argument("--ir",required=True)
    ap.add_argument("--workload"); ap.add_argument("--resource-projection"); ap.add_argument("--output",default="evidence/receipts/motion-video-current-host.json")
    ap.add_argument("--artifact-output",default="evidence/runtime/motion-video-current-host/output.bin"); ap.add_argument("--timeout",type=float,default=1800.0)
    a=ap.parse_args()
    try:
        r=execute(Path(a.selection),Path(a.manifest),Path(a.ir),workload_path=Path(a.workload) if a.workload else None,resource_projection_path=Path(a.resource_projection) if a.resource_projection else None,output_path=Path(a.artifact_output),timeout=a.timeout)
    except Exception as exc:
        print(json.dumps({"status":"BLOCKED","error":str(exc)},indent=2)); return 2
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8"); print(json.dumps(r,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
