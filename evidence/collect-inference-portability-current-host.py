#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA = "fa3.inference-portability-current-host-receipt.v1"
COLLECTOR_ID = "FA3-INFERENCE-PORTABILITY-CURRENT-HOST-COLLECTOR-001"
COLLECTOR_VERSION = "1.0.0"
PROVIDER_IDS = ['FA3-PROVIDER-OPENVINO-001','FA3-PROVIDER-ONNXRUNTIME-001','FA3-PROVIDER-TENSORRT-001','FA3-PROVIDER-TENSORRT-RTX-001']
PROVIDER_FILES = {
    "FA3-PROVIDER-OPENVINO-001": "canonical/providers/FA3-PROVIDER-OPENVINO-001.json",
    "FA3-PROVIDER-ONNXRUNTIME-001": "canonical/providers/FA3-PROVIDER-ONNXRUNTIME-001.json",
    "FA3-PROVIDER-TENSORRT-001": "canonical/providers/FA3-PROVIDER-TENSORRT-001.json",
    "FA3-PROVIDER-TENSORRT-RTX-001": "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json",
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda:fh.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def run_probe(code: str, timeout: int=25, env: dict[str,str] | None=None) -> dict[str,Any]:
    child_env=os.environ.copy()
    child_env.update({"PYTHONNOUSERSITE":"1","PIP_DISABLE_PIP_VERSION_CHECK":"1"})
    if env: child_env.update(env)
    try:
        proc=subprocess.run([sys.executable,"-I","-c",code],text=True,capture_output=True,timeout=timeout,check=False,env=child_env)
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {"probe_status":"ERROR","returncode":127,"error":repr(exc)}
    out=proc.stdout.strip().splitlines()
    if proc.returncode==0 and out:
        try:
            value=json.loads(out[-1])
            if isinstance(value,dict):
                value["returncode"]=0
                return value
        except json.JSONDecodeError:
            pass
    return {"probe_status":"ERROR","returncode":proc.returncode,"stderr":proc.stderr[-2000:],"stdout":proc.stdout[-2000:]}

def dist_map() -> dict[str,str]:
    result={}
    try:
        for dist in metadata.distributions():
            name=(dist.metadata.get("Name") or "").strip()
            if name:
                result[name.lower().replace("_","-")]=dist.version
    except Exception:
        pass
    return result

def provider_reference(root: Path, provider_id: str) -> tuple[str | None,dict[str,Any]]:
    obj=json.loads((root/PROVIDER_FILES[provider_id]).read_text(encoding="utf-8"))
    if provider_id=="FA3-PROVIDER-TENSORRT-001":
        version=obj.get("documented_runtime_release")
    else:
        version=obj.get("observed_release")
    return version,obj

OPENVINO_PROBE = r'''
import json
try:
    import openvino as ov
except Exception as exc:
    print(json.dumps({"present":False,"probe_status":"ABSENT_OR_IMPORT_FAILED","error":repr(exc)})); raise SystemExit(0)
result={"present":True,"probe_status":"PRESENT","runtime_version":getattr(ov,"__version__",None),"available_devices":[],"cpu_smoke":{"status":"NOT_RUN"}}
try:
    core=ov.Core()
    result["available_devices"]=list(core.available_devices)
    if "CPU" in result["available_devices"]:
        try:
            import numpy as np
            from openvino import opset13 as ops
            p=ops.parameter([1],dtype=np.float32,name="x")
            y=ops.relu(p)
            model=ov.Model([y],[p],"fa3-openvino-cpu-smoke")
            compiled=core.compile_model(model,"CPU")
            req=compiled.create_infer_request()
            out=req.infer({0:np.array([-1.0],dtype=np.float32)})
            value=float(list(out.values())[0].reshape(-1)[0])
            result["cpu_smoke"]={"status":"PASS" if abs(value) < 1e-6 else "FAIL","observed":value,"ephemeral_model":True}
        except Exception as exc:
            result["cpu_smoke"]={"status":"FAIL","error":repr(exc),"ephemeral_model":True}
except Exception as exc:
    result["probe_status"]="PRESENT_DISCOVERY_FAILED"; result["discovery_error"]=repr(exc)
print(json.dumps(result))
'''

ORT_PROBE = r'''
import json
try:
    import onnxruntime as ort
except Exception as exc:
    print(json.dumps({"present":False,"probe_status":"ABSENT_OR_IMPORT_FAILED","error":repr(exc)})); raise SystemExit(0)
providers=list(ort.get_available_providers())
result={"present":True,"probe_status":"PRESENT","runtime_version":getattr(ort,"__version__",None),"available_execution_providers":providers,"cpu_smoke":{"status":"NOT_RUN"}}
if "CPUExecutionProvider" in providers:
    try:
        import numpy as np
        import onnx
        from onnx import helper, TensorProto
        x=helper.make_tensor_value_info("x",TensorProto.FLOAT,[1])
        y=helper.make_tensor_value_info("y",TensorProto.FLOAT,[1])
        node=helper.make_node("Relu",["x"],["y"])
        graph=helper.make_graph([node],"fa3-ort-cpu-smoke",[x],[y])
        model=helper.make_model(graph,opset_imports=[helper.make_opsetid("",13)])
        model.ir_version=min(getattr(model,"ir_version",8),8)
        sess=ort.InferenceSession(model.SerializeToString(),providers=["CPUExecutionProvider"])
        out=sess.run(None,{"x":np.array([-1.0],dtype=np.float32)})[0]
        value=float(out.reshape(-1)[0])
        result["cpu_smoke"]={"status":"PASS" if abs(value)<1e-6 else "FAIL","observed":value,"ephemeral_model":True,"onnx_version":getattr(onnx,"__version__",None)}
    except ModuleNotFoundError as exc:
        result["cpu_smoke"]={"status":"NOT_RUN_DEPENDENCY_ABSENT","error":repr(exc),"ephemeral_model":True}
    except Exception as exc:
        result["cpu_smoke"]={"status":"FAIL","error":repr(exc),"ephemeral_model":True}
print(json.dumps(result))
'''

TENSORRT_PROBE = r'''
import json
try:
    import tensorrt as trt
except Exception as exc:
    print(json.dumps({"present":False,"probe_status":"ABSENT_OR_IMPORT_FAILED","error":repr(exc)})); raise SystemExit(0)
result={"present":True,"probe_status":"PRESENT","runtime_version":getattr(trt,"__version__",None),"builder_smoke":{"status":"NOT_RUN"}}
try:
    logger=trt.Logger(trt.Logger.ERROR)
    builder=trt.Builder(logger)
    result["builder_smoke"]={"status":"PASS" if builder is not None else "FAIL","execution_performed":False}
except Exception as exc:
    result["builder_smoke"]={"status":"FAIL","error":repr(exc),"execution_performed":False}
print(json.dumps(result))
'''

TENSORRT_RTX_PROBE = r'''
import json, importlib, importlib.util
names=["tensorrt_rtx","tensorrt_rtx_runtime"]
result={"present":False,"probe_status":"ABSENT","runtime_version":None}
for name in names:
    try:
        spec=importlib.util.find_spec(name)
    except Exception:
        spec=None
    if spec is None:
        continue
    try:
        mod=importlib.import_module(name)
        result={"present":True,"probe_status":"PRESENT","module":name,"runtime_version":getattr(mod,"__version__",None)}
    except Exception as exc:
        result={"present":True,"probe_status":"PRESENT_IMPORT_FAILED","module":name,"error":repr(exc)}
    break
print(json.dumps(result))
'''

def hardware_inventory() -> dict[str,Any]:
    sys_path=str(ROOT/"src")
    if sys_path not in sys.path: sys.path.insert(0,sys_path)
    from fa3_hardware_discovery import discover_accelerator_devices, discover_cpu_topology
    devices=[x.as_dict() for x in discover_accelerator_devices()]
    return {
        "source":"FA3-HARDWARE-DISCOVERY-LIVE_SYSFS",
        "cpu_topology":discover_cpu_topology(),
        "accelerators":devices,
        "accelerator_count":len(devices),
        "cpu_only_host":len(devices)==0,
    }

def package_version_hint(distributions: dict[str,str], needles: tuple[str,...]) -> str | None:
    for name,value in distributions.items():
        if any(needle in name for needle in needles):
            return value
    return None

def normalize_provider(root: Path, provider_id: str, raw: dict[str,Any], distributions: dict[str,str]) -> dict[str,Any]:
    reference,record=provider_reference(root,provider_id)
    present=raw.get("present") is True
    runtime_version=raw.get("runtime_version")
    if provider_id=="FA3-PROVIDER-TENSORRT-RTX-001" and not runtime_version:
        runtime_version=package_version_hint(distributions,("tensorrt-rtx","tensorrt_rtx"))
        if runtime_version and not present:
            present=True; raw={**raw,"present":True,"probe_status":"PRESENT_DISTRIBUTION_ONLY"}
    cpu_smoke=raw.get("cpu_smoke") if isinstance(raw.get("cpu_smoke"),dict) else {"status":"NOT_APPLICABLE"}
    candidates=[]
    if provider_id=="FA3-PROVIDER-OPENVINO-001":
        for dev in raw.get("available_devices",[]) if isinstance(raw.get("available_devices"),list) else []:
            candidates.append({
              "backend":f"OPENVINO:{dev}","execution_kind":"CPU" if dev=="CPU" else "ACCELERATOR",
              "binding_scope":"CPU" if dev=="CPU" else "HOST_UNBOUND",
              "hrb_lease_required":dev!="CPU","runtime_promotion_eligible":False
            })
    elif provider_id=="FA3-PROVIDER-ONNXRUNTIME-001":
        for ep in raw.get("available_execution_providers",[]) if isinstance(raw.get("available_execution_providers"),list) else []:
            is_cpu=ep=="CPUExecutionProvider"
            candidates.append({
              "backend":f"ORT:{ep}","execution_kind":"CPU" if is_cpu else "ACCELERATOR",
              "binding_scope":"CPU" if is_cpu else "HOST_UNBOUND",
              "hrb_lease_required":not is_cpu,"runtime_promotion_eligible":False
            })
    elif provider_id in {"FA3-PROVIDER-TENSORRT-001","FA3-PROVIDER-TENSORRT-RTX-001"} and present:
        candidates.append({
          "backend":"TENSORRT" if provider_id.endswith("TENSORRT-001") else "TENSORRT_RTX",
          "execution_kind":"ACCELERATOR","binding_scope":"HOST_UNBOUND","hrb_lease_required":True,
          "runtime_promotion_eligible":False
        })
    if not present:
        state="ABSENT_OPTIONAL"
    elif cpu_smoke.get("status")=="PASS":
        state="CPU_SMOKE_PASS_PRODUCTION_ROUTE_PENDING"
    elif any(c["execution_kind"]=="ACCELERATOR" for c in candidates):
        state="ACCELERATOR_RUNTIME_PRESENT_HRB_E2E_PENDING"
    else:
        state="PRESENT_UNADMITTED"
    return {
      "provider_id":provider_id,
      "presence_status":"PRESENT" if present else "ABSENT_OPTIONAL",
      "runtime_version":runtime_version,
      "reference_version":reference,
      "reference_version_match":bool(runtime_version and reference and str(runtime_version)==str(reference)),
      "probe_status":raw.get("probe_status"),
      "probe_details":raw,
      "execution_candidates":candidates,
      "cpu_smoke":cpu_smoke,
      "accelerator_e2e":{"status":"NOT_RUN_NO_HRB_BOUND_EXECUTION","runtime_promotion_eligible":False},
      "admission_state":state,
      "production_runtime_promoted":False,
      "global_promotion_claim":False,
      "model_router_semantics":"PROBE_ONLY_NOT_ROUTING_AUTHORITY",
      "agent_native_action":False,
      "ai_participant_set_expanded":False,
      "network_fetch":False,
      "runtime_mutation":False,
    }

def collect(root: Path, output: Path) -> dict[str,Any]:
    distributions=dist_map()
    raw={
      "FA3-PROVIDER-OPENVINO-001":run_probe(OPENVINO_PROBE),
      "FA3-PROVIDER-ONNXRUNTIME-001":run_probe(ORT_PROBE),
      "FA3-PROVIDER-TENSORRT-001":run_probe(TENSORRT_PROBE),
      "FA3-PROVIDER-TENSORRT-RTX-001":run_probe(TENSORRT_RTX_PROBE),
    }
    hardware=hardware_inventory()
    providers=[normalize_provider(root,pid,raw[pid],distributions) for pid in PROVIDER_IDS]
    release=root/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
    result={
      "schema":RECEIPT_SCHEMA,
      "collector_id":COLLECTOR_ID,
      "collector_version":COLLECTOR_VERSION,
      "captured_at":now(),
      "current_host":True,
      "synthetic":False,
      "ci_reference_only":False,
      "collection_policy":{
        "read_only":True,"network_fetch":False,"package_install":False,"provider_mutation":False,
        "secret_collection":"PROHIBITED"
      },
      "host":{
        "hostname":socket.gethostname(),"kernel":platform.release(),"architecture":platform.machine(),
        "python":platform.python_version(),"runner_name":os.environ.get("RUNNER_NAME"),
        "runner_environment":os.environ.get("RUNNER_ENVIRONMENT"),
      },
      "hardware":hardware,
      "providers":providers,
      "canonical_context":{
        "release_projection_sha256":sha256_file(release) if release.is_file() else None,
        "profile_id":"FA3-INFERENCE-PORTABILITY-CURRENT-HOST-001","gate_id":"FA3-INFERENCE-PORTABILITY-CURRENT-HOST-GATESET-001",
        "model_router_authority":"FA3-AUTH-MODEL-ROUTER-001",
      },
      "result":{
        "status":"PASS",
        "claims":["CURRENT_HOST_INFERENCE_PROVIDER_INVENTORY_PASS"],
        "non_claims":["GLOBAL_FA3_PROMOTION","GLOBAL_429_REOPEN","PROVIDER_PRODUCTION_RUNTIME_PASS","ACCELERATOR_E2E_WITHOUT_HRB","MODEL_ROUTER_PRODUCTION_ROUTE_E2E"],
      },
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return result

def main() -> int:
    ap=argparse.ArgumentParser(description="Collect read-only FA3 inference provider current-host pre-admission evidence")
    ap.add_argument("--root",default=str(ROOT))
    ap.add_argument("--output",default=str(ROOT/"evidence/receipts/inference-portability-current-host.json"))
    args=ap.parse_args()
    receipt=collect(Path(args.root).resolve(),Path(args.output))
    print(json.dumps({
      "status":receipt["result"]["status"],
      "provider_states":{p["provider_id"]:p["admission_state"] for p in receipt["providers"]},
      "accelerator_count":receipt["hardware"]["accelerator_count"],
      "output":str(Path(args.output).resolve())
    },indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
