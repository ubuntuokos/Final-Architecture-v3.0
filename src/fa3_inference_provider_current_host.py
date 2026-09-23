#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROVIDERS = (
    "FA3-PROVIDER-OPENVINO-001",
    "FA3-PROVIDER-ONNXRUNTIME-001",
    "FA3-PROVIDER-TENSORRT-001",
    "FA3-PROVIDER-TENSORRT-RTX-001",
)
CONFORMANCE_ID = "FA3-INFERENCE-PROVIDER-CURRENT-HOST-CONFORMANCE-001"
GATE_ID = "FA3-GATE-INFERENCE-PROVIDER-CURRENT-HOST-001"
AGGREGATE_RECEIPT = "evidence/receipts/inference-provider-current-host.json"
DIRECT_PROBE_SCOPE = "ADMISSION_HARNESS_ONLY_NOT_APPLICATION_PATH"
EVIDENCE_LEVEL = "CURRENT_HOST_PROVIDER_SCOPE_PRODUCTION_E2E_PASS"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sha(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def _resolved_executable_identity(value: str | None, label: str) -> dict[str,Any]:
    if not value:
        return {"path":None,"sha256":None}
    p=Path(value).expanduser().resolve()
    if not p.is_file() or not os.access(p,os.X_OK):
        raise RuntimeError(f"{label} executable invalid: {p}")
    return {"path":str(p),"sha256":sha256_file(p)}


def run(argv: list[str], timeout: int = 120, env: dict[str,str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False,env=env)


def git_head(root: Path) -> str:
    p=run(["git","-C",str(root),"rev-parse","HEAD"],30)
    if p.returncode:
        raise RuntimeError("unable to resolve repository HEAD")
    return p.stdout.strip()


def host_fingerprint() -> dict[str,Any]:
    u=platform.uname()
    return {
        "hostname_sha256":hashlib.sha256(socket.gethostname().encode()).hexdigest(),
        "system":u.system,"release":u.release,"machine":u.machine,
        "python":platform.python_version(),"cpu_count":os.cpu_count(),
    }


def _vint(n: int) -> bytes:
    out=bytearray()
    while True:
        b=n & 0x7f
        n >>= 7
        if n:
            out.append(b|0x80)
        else:
            out.append(b)
            return bytes(out)


def _fld_var(field: int, value: int) -> bytes:
    return _vint((field<<3)|0)+_vint(value)


def _fld_bytes(field: int, value: bytes) -> bytes:
    return _vint((field<<3)|2)+_vint(len(value))+value


def _fld_str(field: int, value: str) -> bytes:
    return _fld_bytes(field,value.encode("utf-8"))


def embedded_onnx_identity() -> bytes:
    # Minimal ONNX ModelProto: float[1] x -> Identity -> float[1] y, opset 13.
    dim=_fld_var(1,1)
    shape=_fld_bytes(1,dim)
    tensor_type=_fld_var(1,1)+_fld_bytes(2,shape)  # FLOAT
    typ=_fld_bytes(1,tensor_type)
    def vi(name: str) -> bytes:
        return _fld_str(1,name)+_fld_bytes(2,typ)
    node=_fld_str(1,"x")+_fld_str(2,"y")+_fld_str(4,"Identity")
    graph=_fld_bytes(1,node)+_fld_str(2,"fa3_identity")+_fld_bytes(11,vi("x"))+_fld_bytes(12,vi("y"))
    opset=_fld_var(2,13)
    return _fld_var(1,8)+_fld_str(2,"FA3")+_fld_bytes(7,graph)+_fld_bytes(8,opset)


def _default_probe_environment(cli_name: str | None) -> dict[str,Any]:
    py=_resolved_executable_identity(sys.executable,"python")
    cli=_resolved_executable_identity(shutil.which(cli_name) if cli_name else None,"provider CLI")
    return {
      "environment_id":"CURRENT_RUNNER_ENVIRONMENT",
      "discovery_scope":"DEFAULT_RUNNER_ENVIRONMENT_ONLY",
      "python_executable":py["path"],
      "python_executable_sha256":py["sha256"],
      "cli_path":cli["path"],
      "cli_sha256":cli["sha256"],
      "source_refs":["SELF_HOSTED_RUNNER_CHECKOUT_ENVIRONMENT"],
      "descriptor_receipt_id":None,
      "host_wide_absence_claim":False,
    }


def _runtime_probe_descriptors(path: Path | None, specs: dict[str,tuple[str,str|None]]) -> dict[str,dict[str,Any]]:
    result={pid:_default_probe_environment(cli_name) for pid,(_,cli_name) in specs.items()}
    if path is None:
        return result
    d=json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema")!="fa3.inference-provider-runtime-descriptor-receipt.v1" or not str(d.get("receipt_id","")).strip():
        raise RuntimeError("runtime descriptor receipt identity invalid")
    entries=d.get("providers")
    if not isinstance(entries,dict) or any(pid not in specs for pid in entries):
        raise RuntimeError("runtime descriptor provider inventory invalid")
    for pid,entry in entries.items():
        if not isinstance(entry,dict) or entry.get("result")!="PASS":
            raise RuntimeError(f"runtime descriptor invalid for {pid}")
        env_id=str(entry.get("environment_id","")).strip()
        if not env_id or entry.get("discovery_scope")!="EXPLICIT_RUNTIME_ENVIRONMENT":
            raise RuntimeError(f"runtime descriptor environment invalid for {pid}")
        if entry.get("host_wide_absence_claim") not in (None,False):
            raise RuntimeError(f"runtime descriptor cannot claim host-wide absence for {pid}")
        refs=entry.get("source_refs")
        if not isinstance(refs,list) or not refs or any(not str(x).strip() for x in refs):
            raise RuntimeError(f"runtime descriptor source refs missing for {pid}")
        py=entry.get("python_executable")
        cli=entry.get("cli_path")
        if py is None and cli is None:
            raise RuntimeError(f"runtime descriptor has no executable probe target for {pid}")
        py_ident=_resolved_executable_identity(str(py) if py is not None else None,"python")
        cli_ident=_resolved_executable_identity(str(cli) if cli is not None else None,"provider CLI")
        expected_py_sha=str(entry.get("python_executable_sha256","")).lower() if py is not None else ""
        expected_cli_sha=str(entry.get("cli_sha256","")).lower() if cli is not None else ""
        if py is not None and expected_py_sha!=py_ident["sha256"]:
            raise RuntimeError(f"runtime descriptor python executable identity mismatch for {pid}")
        if cli is not None and expected_cli_sha!=cli_ident["sha256"]:
            raise RuntimeError(f"runtime descriptor CLI identity mismatch for {pid}")
        if py is None and entry.get("python_executable_sha256") not in (None,""):
            raise RuntimeError(f"runtime descriptor python digest has no executable for {pid}")
        if cli is None and entry.get("cli_sha256") not in (None,""):
            raise RuntimeError(f"runtime descriptor CLI digest has no executable for {pid}")
        result[pid]={
          "environment_id":env_id,
          "discovery_scope":"EXPLICIT_RUNTIME_ENVIRONMENT",
          "python_executable":py_ident["path"],
          "python_executable_sha256":py_ident["sha256"],
          "cli_path":cli_ident["path"],
          "cli_sha256":cli_ident["sha256"],
          "source_refs":[str(x) for x in refs],
          "descriptor_receipt_id":str(d.get("receipt_id")),
          "host_wide_absence_claim":False,
        }
    return result


def _module_info(module: str, python_executable: str | None) -> dict[str,Any]:
    code=(
      "import importlib,json,hashlib,pathlib;"
      f"m=importlib.import_module({module!r});"
      "p=getattr(m,'__file__','') or '';"
      "d='';"
      "\nif p and pathlib.Path(p).is_file():\n d=hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()\n"
      "print(json.dumps({'version':str(getattr(m,'__version__','UNKNOWN')),'module_file':p,'module_file_sha256':d}))"
    )
    if not python_executable:
        return {"present":False,"error_class":"PYTHON_NOT_CONFIGURED","python_executable":None}
    p=run([python_executable,"-c",code],60)
    if p.returncode:
        return {"present":False,"error_class":"IMPORT_FAILED","python_executable":python_executable}
    try:
        data=json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"present":False,"error_class":"IMPORT_OUTPUT_INVALID"}
    return {"present":True,"python_executable":python_executable,**data}


def _reference_version(root: Path, provider_id: str) -> str:
    p=root/"canonical/providers"/f"{provider_id}.json"
    d=json.loads(p.read_text(encoding="utf-8"))
    if provider_id=="FA3-PROVIDER-TENSORRT-001":
        return str(d.get("documented_runtime_release",""))
    return str(d.get("observed_release",""))


def _cpu_openvino_e2e(python_executable: str) -> dict[str,Any]:
    code=r'''
import hashlib,json
import numpy as np
import openvino as ov
from openvino import opset13
core=ov.Core()
devices=list(core.available_devices)
if "CPU" not in devices:
    raise SystemExit("CPU plugin unavailable")
x=opset13.parameter([1],ov.Type.f32,name="x")
y=opset13.relu(x)
model=ov.Model([y],[x],"fa3_current_host_probe")
compiled=core.compile_model(model,"CPU")
req=compiled.create_infer_request()
out=req.infer({"x":np.asarray([-2.0],dtype=np.float32)})
arr=np.asarray(next(iter(out.values())))
if arr.shape!=(1,) or float(arr[0])!=0.0:
    raise SystemExit("unexpected inference output")
print(json.dumps({"result":"PASS","devices":devices,"output_sha256":hashlib.sha256(arr.tobytes()).hexdigest()}))
'''
    p=run([python_executable,"-c",code],120)
    if p.returncode:
        return {"result":"FAIL","reason_code":"OPENVINO_CPU_E2E_FAILED","stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest()}
    return json.loads(p.stdout.strip().splitlines()[-1])


def _ort_child(provider: str, python_executable: str, cuda_uuid: str | None = None) -> dict[str,Any]:
    model_b64=base64.b64encode(embedded_onnx_identity()).decode()
    code=r'''
import base64,hashlib,json,os
import numpy as np
import onnxruntime as ort
model=base64.b64decode(os.environ["FA3_ONNX_B64"])
provider=os.environ["FA3_ORT_PROVIDER"]
opts={}
if provider=="CUDAExecutionProvider":
    opts={"device_id":0}
available=ort.get_available_providers()
if provider not in available:
    raise SystemExit("requested EP unavailable")
sess=ort.InferenceSession(model,providers=[(provider,opts)] if opts else [provider])
arr=np.asarray([7.0],dtype=np.float32)
out=np.asarray(sess.run(None,{"x":arr})[0])
if out.shape!=(1,) or float(out[0])!=7.0:
    raise SystemExit("unexpected inference output")
print(json.dumps({"result":"PASS","available_providers":available,"session_providers":sess.get_providers(),"output_sha256":hashlib.sha256(out.tobytes()).hexdigest()}))
'''
    env=os.environ.copy()
    env["FA3_ONNX_B64"]=model_b64
    env["FA3_ORT_PROVIDER"]=provider
    if cuda_uuid:
        env["CUDA_VISIBLE_DEVICES"]=cuda_uuid
    p=run([python_executable,"-c",code],180,env)
    if p.returncode:
        return {"result":"FAIL","reason_code":"ORT_E2E_FAILED","stderr_sha256":hashlib.sha256(p.stderr.encode()).hexdigest()}
    return json.loads(p.stdout.strip().splitlines()[-1])


def _norm_bdf(v: Any) -> str:
    s=str(v or "").strip().lower()
    m=re.fullmatch(r"([0-9a-f]{4,8}):([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])",s)
    return f"{m.group(1)[-4:]}:{m.group(2)}:{m.group(3)}.{m.group(4)}" if m else s


def _nvidia_inventory() -> list[dict[str,str]]:
    if not shutil.which("nvidia-smi"):
        return []
    p=run(["nvidia-smi","--query-gpu=uuid,pci.bus_id,name,driver_version","--format=csv,noheader"],30)
    if p.returncode:
        return []
    rows=[]
    for line in p.stdout.splitlines():
        parts=[x.strip() for x in line.split(",",3)]
        if len(parts)==4:
            rows.append({"uuid":parts[0],"pci_bdf":_norm_bdf(parts[1]),"name":parts[2],"driver_version":parts[3]})
    return rows


def _validate_hrb_lease(path: Path | None, hrb_bin: str) -> dict[str,Any]:
    if path is None:
        return {"result":"MISSING"}
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        if d.get("schema")!="FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1":
            raise ValueError("schema")
        if d.get("issuer")!="FA3-HOST-RESOURCE-BROKER-001" or d.get("status")!="ACTIVE" or d.get("broker_validation") is not True:
            raise ValueError("authority")
        if int(d.get("expires_epoch",0))<=int(time.time()):
            raise ValueError("expired")
        uuid=str(d.get("accelerator_uuid","")).strip()
        bdf=_norm_bdf(d.get("pci_bus_id"))
        if not uuid or not bdf:
            raise ValueError("identity")
        if shutil.which(hrb_bin) or Path(hrb_bin).is_file():
            p=run([hrb_bin,"validate-lease",str(path)],30)
            if p.returncode or "VALID" not in p.stdout:
                raise ValueError("broker validation")
        matches=[x for x in _nvidia_inventory() if x["uuid"]==uuid and x["pci_bdf"]==bdf]
        if len(matches)!=1:
            raise ValueError("live device binding")
        return {"result":"PASS","lease_id":d.get("lease_id"),"accelerator_uuid":uuid,"pci_bdf":bdf,"purpose":d.get("purpose"),"live_device":matches[0]}
    except Exception as exc:
        return {"result":"FAIL","reason_code":"HRB_LEASE_INVALID","error_class":type(exc).__name__}


def _runtime_pin(path: Path | None, provider_id: str, installed_version: str, runtime_identity: dict[str,Any]) -> dict[str,Any]:
    if path is None:
        return {"result":"MISSING","provider_version":None,"identity_match":False}
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        if d.get("schema")!="fa3.inference-provider-runtime-pin-receipt.v1":
            raise ValueError("schema")
        entry=(d.get("providers") or {}).get(provider_id)
        if not isinstance(entry,dict) or entry.get("result")!="PASS" or entry.get("immutable") is not True:
            raise ValueError("provider")
        if str(entry.get("provider_version",""))!=installed_version:
            raise ValueError("version")
        if not isinstance(entry.get("source_refs"),list) or not entry.get("source_refs"):
            raise ValueError("source refs")
        identity=entry.get("runtime_identity")
        if not isinstance(identity,dict) or identity!=runtime_identity:
            raise ValueError("runtime identity")
        for key in ("python_executable_sha256","module_file_sha256"):
            if not re.fullmatch(r"[0-9a-f]{64}",str(identity.get(key) or "")):
                raise ValueError(key)
        if provider_id in {"FA3-PROVIDER-TENSORRT-001","FA3-PROVIDER-TENSORRT-RTX-001"}:
            if not identity.get("cli_path") or not re.fullmatch(r"[0-9a-f]{64}",str(identity.get("cli_sha256") or "")):
                raise ValueError("cli identity")
        return {
          "result":"PASS","receipt_id":str(d.get("receipt_id","")),
          "provider_version":installed_version,"entry_sha256":canonical_sha(entry),
          "immutable":True,"identity_match":True,"entry":entry,
        }
    except Exception as exc:
        return {"result":"FAIL","reason_code":"RUNTIME_PIN_RECEIPT_INVALID","error_class":type(exc).__name__,"identity_match":False}


def _support_matrix(path: Path | None, provider_id: str, version: str, lease: dict[str,Any]) -> dict[str,Any]:
    if path is None:
        return {"result":"MISSING"}
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        if d.get("schema")!="fa3.inference-provider-support-matrix-receipt.v1":
            raise ValueError("schema")
        entry=(d.get("providers") or {}).get(provider_id)
        if not isinstance(entry,dict) or entry.get("result")!="PASS":
            raise ValueError("provider")
        if str(entry.get("provider_version",""))!=version:
            raise ValueError("version")
        if not isinstance(entry.get("source_refs"),list) or not entry.get("source_refs"):
            raise ValueError("source refs")
        live=lease.get("live_device") or {}
        if entry.get("accelerator_uuid") not in (None,"",live.get("uuid")):
            raise ValueError("accelerator uuid")
        if entry.get("driver_version") not in (None,"",live.get("driver_version")):
            raise ValueError("driver")
        return {"result":"PASS","receipt_id":str(d.get("receipt_id","")),"entry_sha256":canonical_sha(entry),"entry":entry}
    except Exception as exc:
        return {"result":"FAIL","reason_code":"SUPPORT_MATRIX_RECEIPT_INVALID","error_class":type(exc).__name__}


def _write_probe_model(runtime_dir: Path) -> tuple[Path,str]:
    p=runtime_dir/"fa3-identity.onnx"
    data=embedded_onnx_identity()
    p.write_bytes(data)
    return p,hashlib.sha256(data).hexdigest()


def _trtexec_e2e(runtime_dir: Path, uuid: str, cli: str | None) -> dict[str,Any]:
    if not cli:
        return {"result":"FAIL","reason_code":"TRTEXEC_NOT_AVAILABLE"}
    model,model_sha=_write_probe_model(runtime_dir)
    engine=runtime_dir/"fa3-tensorrt.engine"
    log=runtime_dir/"tensorrt.log"
    env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]=uuid
    p=run([cli,f"--onnx={model}",f"--saveEngine={engine}","--iterations=3"],600,env)
    log.write_text(p.stdout+"\n"+p.stderr,encoding="utf-8")
    if p.returncode or not engine.is_file():
        return {"result":"FAIL","reason_code":"TENSORRT_E2E_FAILED","model_probe_sha256":model_sha,"log_sha256":sha256_file(log)}
    return {"result":"PASS","model_probe_sha256":model_sha,"engine_sha256":sha256_file(engine),"log_sha256":sha256_file(log),"probe_method":"TRTEXEC_BUILD_AND_INFER"}


def _trt_rtx_e2e(runtime_dir: Path, uuid: str, cli: str | None) -> dict[str,Any]:
    if not cli:
        return {"result":"FAIL","reason_code":"TENSORRT_RTX_CLI_NOT_AVAILABLE"}
    model,model_sha=_write_probe_model(runtime_dir)
    engine=runtime_dir/"fa3-tensorrt-rtx.engine"
    cache=runtime_dir/"fa3-tensorrt-rtx.cache"
    log1=runtime_dir/"tensorrt-rtx-build.log"
    log2=runtime_dir/"tensorrt-rtx-run.log"
    env=os.environ.copy(); env["CUDA_VISIBLE_DEVICES"]=uuid
    b=run([cli,f"--onnx={model}",f"--saveEngine={engine}"],600,env)
    log1.write_text(b.stdout+"\n"+b.stderr,encoding="utf-8")
    if b.returncode or not engine.is_file():
        return {"result":"FAIL","reason_code":"TENSORRT_RTX_AOT_FAILED","model_probe_sha256":model_sha,"build_log_sha256":sha256_file(log1)}
    r=run([cli,f"--loadEngine={engine}",f"--runtimeCacheFile={cache}"],600,env)
    log2.write_text(r.stdout+"\n"+r.stderr,encoding="utf-8")
    if r.returncode or not cache.is_file():
        return {"result":"FAIL","reason_code":"TENSORRT_RTX_JIT_FAILED","model_probe_sha256":model_sha,"engine_sha256":sha256_file(engine),"run_log_sha256":sha256_file(log2)}
    return {
      "result":"PASS_DIAGNOSTIC_ONLY_CACHE_OBSERVABILITY_REQUIRED",
      "model_probe_sha256":model_sha,"engine_sha256":sha256_file(engine),
      "runtime_cache_sha256":sha256_file(cache),"build_log_sha256":sha256_file(log1),
      "run_log_sha256":sha256_file(log2),"probe_method":"TENSORRT_RTX_CLI_AOT_PLUS_JIT",
    }


def _decision_advisory(root: Path, present: list[str]) -> dict[str,Any]:
    if not present:
        return {"status":"NO_DECISION","provider":"FA3-PROVIDER-DECISION-RULES-001","authority":False,"candidate_set_expanded":False,"candidate_ids":[]}
    sys.path.insert(0,str(root/"src"))
    from fa3_decision_fabric import DecisionFabric, RuleDecisionProvider
    fabric=DecisionFabric([RuleDecisionProvider()])
    trace=fabric.decide({
      "contract":"RANK","purpose":"order present inference providers for current-host admission probes",
      "candidates":[{"id":pid,"metadata":{"priority":len(PROVIDERS)-PROVIDERS.index(pid)}} for pid in present],
      "constraints":{},"policy_context":{"authority":"NONE_ADVISORY_ONLY"},
      "evidence_refs":[],"failure_policy":"NO_DECISION","rollout":"ADVISORY",
      "final_policy_owner":"FA3-INFERENCE-PORTABILITY-001",
    })
    return trace


def collect(root: Path, required: set[str], hrb_lease_path: Path | None, support_matrix_path: Path | None, runtime_pin_path: Path | None, runtime_descriptor_path: Path | None, hrb_bin: str) -> dict[str,Any]:
    root=root.resolve()
    runtime_dir=root/"evidence/runtime/inference-provider-current-host"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir.mkdir(parents=True,exist_ok=True)
    specs={
      "FA3-PROVIDER-OPENVINO-001":("openvino",None),
      "FA3-PROVIDER-ONNXRUNTIME-001":("onnxruntime",None),
      "FA3-PROVIDER-TENSORRT-001":("tensorrt","trtexec"),
      "FA3-PROVIDER-TENSORRT-RTX-001":("tensorrt_rtx","tensorrt_rtx"),
    }
    out={}
    probe_envs=_runtime_probe_descriptors(runtime_descriptor_path,specs)
    lease=_validate_hrb_lease(hrb_lease_path,hrb_bin)
    for pid,(module,cli_name) in specs.items():
        probe=probe_envs[pid]
        python_executable=probe.get("python_executable")
        cli_path=probe.get("cli_path")
        mi=_module_info(module,python_executable)
        runtime_identity={
          "environment_id":probe.get("environment_id"),
          "python_executable":python_executable,
          "python_executable_sha256":probe.get("python_executable_sha256"),
          "module_file":mi.get("module_file") if mi.get("present") else None,
          "module_file_sha256":mi.get("module_file_sha256") if mi.get("present") else None,
          "cli_path":cli_path,
          "cli_sha256":probe.get("cli_sha256"),
        }
        reference=_reference_version(root,pid)
        version=str(mi.get("version","")) if mi.get("present") else ""
        reference_version_match=bool(version and version==reference)
        pin=_runtime_pin(runtime_pin_path,pid,version,runtime_identity) if version else {"result":"MISSING","provider_version":None,"identity_match":False}
        admission_identity_match=bool(pin.get("result")=="PASS" and pin.get("identity_match") is True)
        admission_pin_match=bool(version and admission_identity_match and pin.get("provider_version")==version)
        if pid in {"FA3-PROVIDER-TENSORRT-001","FA3-PROVIDER-TENSORRT-RTX-001"}:
            present=bool(mi.get("present") or cli_path)
        else:
            present=bool(mi.get("present"))
        scopes={}
        admitted=[]
        base={
          "schema":"fa3.inference-provider-current-host-provider-receipt.v1",
          "provider_id":pid,"present":present,"provider_version":version or None,
          "reference_version":reference,"reference_version_match":reference_version_match,
          "admission_pin":pin,"admission_pin_match":admission_pin_match,
          "admission_identity_match":admission_identity_match,"runtime_identity":runtime_identity,
          "probe_environment":probe,"host_wide_absence_claim":False,
          "module":mi,"cli":{"name":cli_name,"path":cli_path,"sha256":probe.get("cli_sha256")},
          "direct_probe_scope":DIRECT_PROBE_SCOPE,"auto_install_performed":False,
          "network_model_fetch_performed":False,"global_promotion_claim":False,
        }
        if not present:
            base.update({"status":"NOT_PRESENT_IN_PROBE_ENVIRONMENT","admitted_scopes":[],"scopes":{}})
            out[pid]=base; continue

        if pid=="FA3-PROVIDER-OPENVINO-001":
            e2e=_cpu_openvino_e2e(str(python_executable))
            ok=admission_pin_match and e2e.get("result")=="PASS"
            scopes["CPU"]={
              "scope_id":"CPU","execution_kind":"CPU","status":"ADMITTED" if ok else "PRESENT_NOT_ADMITTED",
              "evidence_level":EVIDENCE_LEVEL if ok else None,"e2e":e2e,
              "runtime_pin":pin,"model_probe_sha256":"PROGRAMMATIC_OPENVINO_IDENTITY_GRAPH",
              "hardware_binding":{"accelerator":False,"hrb_lease":None},"support_matrix":{"result":"NOT_REQUIRED_CPU_SCOPE"}
            }
            if ok: admitted.append("CPU")

        elif pid=="FA3-PROVIDER-ONNXRUNTIME-001":
            e2e=_ort_child("CPUExecutionProvider",str(python_executable))
            ok=admission_pin_match and e2e.get("result")=="PASS"
            scopes["CPU_EP"]={
              "scope_id":"CPU_EP","execution_kind":"CPU","status":"ADMITTED" if ok else "PRESENT_NOT_ADMITTED",
              "evidence_level":EVIDENCE_LEVEL if ok else None,"e2e":e2e,
              "runtime_pin":pin,"model_probe_sha256":hashlib.sha256(embedded_onnx_identity()).hexdigest(),
              "hardware_binding":{"accelerator":False,"hrb_lease":None},"support_matrix":{"result":"NOT_REQUIRED_CPU_SCOPE"}
            }
            if ok: admitted.append("CPU_EP")
            cuda_possible="CUDAExecutionProvider" in (e2e.get("available_providers") or [])
            if cuda_possible:
                sm=_support_matrix(support_matrix_path,pid,version,lease)
                ge2e=_ort_child("CUDAExecutionProvider",str(python_executable),lease.get("accelerator_uuid")) if lease.get("result")=="PASS" and sm.get("result")=="PASS" else {"result":"NOT_RUN"}
                gok=admission_pin_match and lease.get("result")=="PASS" and sm.get("result")=="PASS" and ge2e.get("result")=="PASS"
                scopes["CUDA_EP"]={
                  "scope_id":"CUDA_EP","execution_kind":"ACCELERATOR","status":"ADMITTED" if gok else "PRESENT_NOT_ADMITTED",
                  "evidence_level":EVIDENCE_LEVEL if gok else None,"e2e":ge2e,"runtime_pin":pin,
                  "model_probe_sha256":hashlib.sha256(embedded_onnx_identity()).hexdigest(),
                  "hardware_binding":{"accelerator":True,"hrb_lease":lease},"support_matrix":sm
                }
                if gok: admitted.append("CUDA_EP")

        elif pid=="FA3-PROVIDER-TENSORRT-001":
            sm=_support_matrix(support_matrix_path,pid,version,lease)
            e2e=_trtexec_e2e(runtime_dir,lease.get("accelerator_uuid"),cli_path) if lease.get("result")=="PASS" and sm.get("result")=="PASS" else {"result":"NOT_RUN"}
            ok=admission_pin_match and lease.get("result")=="PASS" and sm.get("result")=="PASS" and e2e.get("result")=="PASS"
            scopes["NVIDIA_GPU_NATIVE"]={
              "scope_id":"NVIDIA_GPU_NATIVE","execution_kind":"ACCELERATOR","status":"ADMITTED" if ok else "PRESENT_NOT_ADMITTED",
              "evidence_level":EVIDENCE_LEVEL if ok else None,"e2e":e2e,"runtime_pin":pin,
              "model_probe_sha256":e2e.get("model_probe_sha256"),"hardware_binding":{"accelerator":True,"hrb_lease":lease},"support_matrix":sm
            }
            if ok: admitted.append("NVIDIA_GPU_NATIVE")

        elif pid=="FA3-PROVIDER-TENSORRT-RTX-001":
            sm=_support_matrix(support_matrix_path,pid,version,lease)
            e2e=_trt_rtx_e2e(runtime_dir,lease.get("accelerator_uuid"),cli_path) if lease.get("result")=="PASS" and sm.get("result")=="PASS" else {"result":"NOT_RUN"}
            # Diagnostic execution alone cannot satisfy production cache-observability requirements.
            scopes["NVIDIA_RTX_NATIVE"]={
              "scope_id":"NVIDIA_RTX_NATIVE","execution_kind":"ACCELERATOR","status":"PRESENT_NOT_ADMITTED",
              "evidence_level":None,"e2e":e2e,"runtime_pin":pin,
              "model_probe_sha256":e2e.get("model_probe_sha256"),"hardware_binding":{"accelerator":True,"hrb_lease":lease},
              "support_matrix":sm,"runtime_cache_observability":{"result":"REQUIRED_SEPARATE_CACHE_USE_RECEIPT"}
            }

        base["scopes"]=scopes
        base["admitted_scopes"]=admitted
        base["status"]="ADMITTED" if admitted else ("PRESENT_UNPINNED" if not admission_pin_match else "PRESENT_NOT_ADMITTED")
        out[pid]=base

    provider_dir=root/"evidence/receipts/inference-provider-current-host"
    provider_dir.mkdir(parents=True,exist_ok=True)
    receipt_hashes={}
    for pid,value in out.items():
        p=provider_dir/(pid+".json")
        p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        receipt_hashes[pid]=sha256_file(p)

    present=[pid for pid,v in out.items() if v.get("present")]
    advisory=_decision_advisory(root,present)
    missing_required=sorted(pid for pid in required if not out.get(pid,{}).get("admitted_scopes"))
    result="PASS" if not missing_required else "BLOCKED"
    aggregate={
      "schema":"fa3.inference-provider-current-host-receipt.v1",
      "conformance_id":CONFORMANCE_ID,"gate_id":GATE_ID,"result":result,
      "captured_at":now(),"repository_head":git_head(root),"host":host_fingerprint(),
      "physical_current_host":True,"provider_neutral":True,
      "inventory_scope":"PROBE_ENVIRONMENT_SCOPED_NOT_HOST_WIDE",
      "host_wide_absence_claim":False,
      "runtime_descriptor_receipt":{
        "provided":runtime_descriptor_path is not None,
        "sha256":sha256_file(runtime_descriptor_path) if runtime_descriptor_path is not None else None,
      },
      "mode":"REQUIRED_ADMISSION" if required else "PROBE_ENVIRONMENT_INVENTORY_AND_SAFE_CPU_PROBES",
      "required_provider_ids":sorted(required),"missing_required_provider_ids":missing_required,
      "providers":out,"provider_receipt_sha256":receipt_hashes,
      "decision_fabric_advisory":advisory,
      "direct_provider_probe_scope":DIRECT_PROBE_SCOPE,
      "auto_install_performed":False,"network_model_fetch_performed":False,
      "existing_429_closure_reopened":False,"current_host_obligation_delta":0,
      "global_promotion_claim":False,
    }
    path=root/AGGREGATE_RECEIPT
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(aggregate,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return aggregate


def main() -> int:
    ap=argparse.ArgumentParser(description="Collect FA3 inference-provider current-host admission evidence without installing providers")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--require-provider",action="append",default=[])
    ap.add_argument("--hrb-lease")
    ap.add_argument("--support-matrix-receipt")
    ap.add_argument("--runtime-pin-receipt")
    ap.add_argument("--runtime-descriptor-receipt")
    ap.add_argument("--hrb-bin",default="/usr/local/bin/fa3-host-resource-broker")
    args=ap.parse_args()
    required=set(args.require_provider)
    unknown=required-set(PROVIDERS)
    if unknown:
        raise SystemExit("unknown required provider(s): "+",".join(sorted(unknown)))
    rec=collect(
      Path(args.root),
      required,
      Path(args.hrb_lease).resolve() if args.hrb_lease else None,
      Path(args.support_matrix_receipt).resolve() if args.support_matrix_receipt else None,
      Path(args.runtime_pin_receipt).resolve() if args.runtime_pin_receipt else None,
      Path(args.runtime_descriptor_receipt).resolve() if args.runtime_descriptor_receipt else None,
      args.hrb_bin,
    )
    print(json.dumps(rec,indent=2,ensure_ascii=False))
    return 0 if rec["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
