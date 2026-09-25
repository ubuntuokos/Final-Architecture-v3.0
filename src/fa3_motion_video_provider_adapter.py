#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
BILLABLE_ACK = "I_ACKNOWLEDGE_BILLABLE_FA3_VIDEO_E2E"
ALLOWED_COSTS = {"FREE_LOCAL", "FREE_REMOTE", "BILLABLE_REMOTE"}
ALLOWED_TRANSPORTS = {"FA3_HTTP_BRIDGE", "FA3_EXECUTOR_COMMAND"}
ROOT = Path(__file__).resolve().parents[1]

class MotionVideoDenied(RuntimeError):
    pass

def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def nonempty(v: Any) -> bool:
    return isinstance(v,str) and bool(v.strip())

def assert_no_secret_values(obj: Any, where: str) -> None:
    if isinstance(obj, dict):
        for k,v in obj.items():
            lk=str(k).lower()
            if lk in {"api_key","token","secret","password","authorization","bearer"} and nonempty(v):
                raise MotionVideoDenied(f"{where} embeds secret-like value: {k}")
            assert_no_secret_values(v, where)
    elif isinstance(obj, list):
        for v in obj:
            assert_no_secret_values(v, where)

def validate_selection(selection: dict[str,Any], manifest: dict[str,Any]) -> str:
    if selection.get("schema") != "fa3.motion-video-route-selection-receipt.v1":
        raise MotionVideoDenied("selection receipt schema mismatch")
    if selection.get("authority") != ROUTER_AUTHORITY:
        raise MotionVideoDenied("selection receipt is not Model Router authoritative")
    if selection.get("status") != "ROUTED":
        raise MotionVideoDenied("selection receipt is not ROUTED")
    provider_id=str(selection.get("provider_id","")).strip()
    if not provider_id:
        raise MotionVideoDenied("selection receipt provider_id missing")
    if manifest.get("schema") != "fa3.motion-video-execution-manifest.v1":
        raise MotionVideoDenied("execution manifest schema mismatch")
    if manifest.get("status") != "ADMITTED":
        raise MotionVideoDenied("provider execution manifest is not ADMITTED")
    if manifest.get("provider_id") != provider_id:
        raise MotionVideoDenied("selection/manifest provider mismatch")
    if manifest.get("provider_selection_authority") != ROUTER_AUTHORITY:
        raise MotionVideoDenied("manifest routing authority mismatch")
    if manifest.get("resource_authority") != HRB_AUTHORITY:
        raise MotionVideoDenied("manifest resource authority mismatch")
    if manifest.get("transport") not in ALLOWED_TRANSPORTS:
        raise MotionVideoDenied("unsupported transport")
    if manifest.get("cost_class") not in ALLOWED_COSTS:
        raise MotionVideoDenied("unsupported cost class")
    if manifest.get("silent_fallback_allowed") is not False:
        raise MotionVideoDenied("silent fallback must be disabled")
    assert_no_secret_values(manifest, "manifest")
    return provider_id

def validate_admission(manifest: dict[str,Any], provider_id: str) -> None:
    ref=str(manifest.get("admission_receipt","")).strip()
    expected=str(manifest.get("admission_receipt_sha256","")).strip().lower()
    if not ref or len(expected)!=64:
        raise MotionVideoDenied("provider admission receipt binding missing")
    path=Path(ref).expanduser()
    if not path.is_absolute():
        path=(ROOT/path).resolve()
    if not path.is_file() or sha256_file(path)!=expected:
        raise MotionVideoDenied("provider admission receipt missing or SHA256 mismatch")
    receipt=loadj(path)
    if receipt.get("provider_id") != provider_id:
        raise MotionVideoDenied("provider admission receipt provider mismatch")
    if receipt.get("status") not in {"PASS","ADMITTED"} and receipt.get("result") not in {"PASS","ADMITTED"}:
        raise MotionVideoDenied("provider admission receipt is not admitted")
    if receipt.get("synthetic_or_mock_provider") is True:
        raise MotionVideoDenied("synthetic/mock provider admission forbidden")

def validate_hrb(manifest: dict[str,Any], hrb: dict[str,Any] | None) -> None:
    local=manifest.get("execution_topology") == "LOCAL"
    accel=bool(manifest.get("requires_accelerator"))
    if local and accel:
        if not isinstance(hrb,dict):
            raise MotionVideoDenied("local accelerator execution requires HRB receipt")
        if hrb.get("authority") != HRB_AUTHORITY or hrb.get("status") not in {"ADMITTED","PASS"}:
            raise MotionVideoDenied("HRB receipt is not admitted")
        if not nonempty(hrb.get("lease_id")):
            raise MotionVideoDenied("HRB lease_id missing")
    if local and not accel and isinstance(hrb,dict) and hrb.get("accelerator_lease") is True:
        raise MotionVideoDenied("CPU-only execution must not carry accelerator lease")

def validate_billing(manifest: dict[str,Any]) -> None:
    if manifest.get("cost_class") == "BILLABLE_REMOTE":
        if os.environ.get("FA3_VIDEO_BILLABLE_E2E_ACK","") != BILLABLE_ACK:
            raise MotionVideoDenied("explicit billable video E2E acknowledgement required")

def request_json(url: str, method: str, payload: dict[str,Any] | None, timeout: float) -> dict[str,Any]:
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    headers={"Accept":"application/json","Content-Type":"application/json"}
    req=urllib.request.Request(url,method=method,data=data,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            raw=response.read(64*1024*1024)
    except (urllib.error.HTTPError,urllib.error.URLError) as exc:
        raise MotionVideoDenied(f"provider bridge request failed: {exc}") from exc
    try:
        obj=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise MotionVideoDenied("provider bridge returned invalid JSON") from exc
    if not isinstance(obj,dict):
        raise MotionVideoDenied("provider bridge returned non-object JSON")
    return obj

def execute_http(manifest: dict[str,Any], ir: dict[str,Any], timeout: float) -> dict[str,Any]:
    base=str(manifest.get("api_base","")).rstrip("/")
    if not base.startswith(("http://127.0.0.1:","http://localhost:","http://[::1]:","https://127.0.0.1:","https://localhost:")) and manifest.get("execution_topology") == "LOCAL":
        raise MotionVideoDenied("local bridge endpoint must be loopback")
    create_path=str(manifest.get("create_path","/v1/video/generate"))
    response=request_json(base+create_path,"POST",{"video_generation_ir":ir},timeout)
    if response.get("status") in {"COMPLETE","SUCCEEDED"}:
        return response
    task_id=str(response.get("task_id","")).strip()
    if not task_id:
        raise MotionVideoDenied("provider bridge returned neither completed result nor task_id")
    poll_template=str(manifest.get("poll_path_template","/v1/video/tasks/{task_id}"))
    deadline=time.time()+float(manifest.get("max_wait_seconds",timeout))
    interval=max(0.2,float(manifest.get("poll_interval_seconds",1.0)))
    while time.time()<deadline:
        item=request_json(base+poll_template.replace("{task_id}",task_id),"GET",None,timeout)
        status=str(item.get("status","")).upper()
        if status in {"COMPLETE","SUCCEEDED"}:
            return item
        if status in {"FAILED","ERROR","CANCELLED"}:
            raise MotionVideoDenied(f"provider task terminal failure: {status}")
        time.sleep(interval)
    raise MotionVideoDenied("provider task timed out")

def execute_command(manifest: dict[str,Any], ir_path: Path, output_path: Path, timeout: float) -> dict[str,Any]:
    executable=Path(str(manifest.get("executable",""))).expanduser()
    if not executable.is_absolute() or not executable.is_file():
        raise MotionVideoDenied("executor command must be an existing absolute file")
    expected=str(manifest.get("executable_sha256","")).lower()
    if len(expected)!=64 or sha256_file(executable)!=expected:
        raise MotionVideoDenied("executor command SHA256 mismatch")
    argv=manifest.get("argv")
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) for x in argv):
        raise MotionVideoDenied("executor argv missing")
    rendered=[x.replace("{ir}",str(ir_path)).replace("{output}",str(output_path)) for x in argv]
    env=os.environ.copy()
    for key in list(env):
        if any(t in key.upper() for t in ("API_KEY","TOKEN","SECRET","PASSWORD")):
            env.pop(key,None)
    p=subprocess.run([str(executable),*rendered],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,env=env)
    if p.returncode!=0:
        raise MotionVideoDenied(f"executor command failed rc={p.returncode}")
    if output_path.is_file():
        return {"status":"SUCCEEDED","artifact_path":str(output_path),"artifact_sha256":sha256_file(output_path)}
    try:
        obj=json.loads(p.stdout)
    except Exception as exc:
        raise MotionVideoDenied("executor produced neither output artifact nor JSON result") from exc
    if not isinstance(obj,dict):
        raise MotionVideoDenied("executor JSON result must be object")
    return obj

def execute(selection_path: Path, manifest_path: Path, ir_path: Path, *, hrb_path: Path | None, output_path: Path, timeout: float) -> dict[str,Any]:
    selection=loadj(selection_path); manifest=loadj(manifest_path); ir=loadj(ir_path)
    provider_id=validate_selection(selection,manifest)
    if ir.get("schema") not in {"fa3.video-generation-ir.v1","fa3.video-generation-ir.v2"}:
        raise MotionVideoDenied("VideoGenerationIR schema mismatch")
    assert_no_secret_values(ir,"video generation IR")
    validate_admission(manifest,provider_id)
    validate_hrb(manifest,loadj(hrb_path) if hrb_path else None)
    validate_billing(manifest)
    if manifest["transport"]=="FA3_HTTP_BRIDGE":
        result=execute_http(manifest,ir,timeout)
    else:
        result=execute_command(manifest,ir_path,output_path,timeout)
    assert_no_secret_values(result,"provider result")
    if str(result.get("status","")).upper() not in {"COMPLETE","SUCCEEDED","PASS"}:
        raise MotionVideoDenied("execution result is not successful")
    artifact=result.get("artifact_path") or result.get("artifact_url")
    if not nonempty(artifact):
        raise MotionVideoDenied("successful execution result lacks artifact reference")
    receipt={
      "schema":"fa3.motion-video-execution-receipt.v1",
      "status":"PASS",
      "provider_id":provider_id,
      "selection_receipt_sha256":sha256_file(selection_path),
      "provider_manifest_sha256":sha256_file(manifest_path),
      "video_generation_ir_sha256":sha256_file(ir_path),
      "hrb_receipt_sha256":sha256_file(hrb_path) if hrb_path else None,
      "transport":manifest["transport"],
      "cost_class":manifest["cost_class"],
      "execution_topology":manifest.get("execution_topology"),
      "requires_accelerator":bool(manifest.get("requires_accelerator")),
      "artifact_reference":artifact,
      "artifact_sha256":result.get("artifact_sha256"),
      "provider_native_result":{k:v for k,v in result.items() if k not in {"raw_secret","api_key","token","authorization"}},
      "silent_fallback_used":False,
      "raw_secret_present":False,
      "current_host_runtime_claim":False,
      "provider_runtime_promotion_claim":False
    }
    return receipt

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--selection",required=True)
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--ir",required=True)
    ap.add_argument("--hrb")
    ap.add_argument("--output",default="evidence/receipts/motion-video-current-host.json")
    ap.add_argument("--artifact-output",default="evidence/runtime/motion-video-current-host/output.bin")
    ap.add_argument("--timeout",type=float,default=1800.0)
    args=ap.parse_args()
    receipt=execute(Path(args.selection),Path(args.manifest),Path(args.ir),hrb_path=Path(args.hrb) if args.hrb else None,output_path=Path(args.artifact_output),timeout=args.timeout)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
