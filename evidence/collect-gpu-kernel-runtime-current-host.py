#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, time
from pathlib import Path

FRAMEWORK_PROVIDER="FA3-PROVIDER-FRAMEWORK-NATIVE-CUDA-KERNEL-001"
AMPERE_PROVIDER="FA3-PROVIDER-AMPERE-KERNEL-RUNTIME-001"
DEEPGEMM_PROVIDER="FA3-PROVIDER-DEEPGEMM-001"

def run(args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT).strip()

def sha(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def lscpu_map():
    d=json.loads(run(["lscpu","-J"]))
    return {x["field"].rstrip(":"):x["data"] for x in d.get("lscpu",[])}

def gpu_rows():
    q="index,uuid,name,pci.bus_id,memory.total,compute_cap,driver_version"
    out=run(["nvidia-smi",f"--query-gpu={q}","--format=csv,noheader,nounits"])
    rows=[]
    for line in out.splitlines():
        p=[x.strip() for x in line.split(",")]
        if len(p)>=7:
            rows.append({"index":int(p[0]),"uuid":p[1],"name":p[2],"pci_bdf":p[3],"memory_mib":int(p[4]),"compute_cap":p[5],"driver":p[6]})
    return rows

def lease_uuid(d):
    for k in ("device_uuid","gpu_uuid","accelerator_uuid"):
        if d.get(k): return str(d[k])
    for parent in ("accelerator","assignment","device"):
        x=d.get(parent)
        if isinstance(x,dict):
            for k in ("device_uuid","gpu_uuid","uuid"):
                if x.get(k): return str(x[k])
    return None

def main():
    ap=argparse.ArgumentParser(description="Collect real FA3 portable GPU-kernel-runtime current-host evidence")
    ap.add_argument("--hrb-lease",required=True)
    ap.add_argument("--benchmark-evidence",required=True)
    ap.add_argument("--rollback-evidence",required=True)
    ap.add_argument("--output",default="evidence/receipts/gpu-kernel-runtime-current-host.json")
    ap.add_argument("--hrb-verify-bin",default="/usr/local/bin/fa3-host-resource-broker")
    a=ap.parse_args()
    lp,bp,rp=map(Path,(a.hrb_lease,a.benchmark_evidence,a.rollback_evidence))
    lease=json.loads(lp.read_text()); bench=json.loads(bp.read_text()); rb=json.loads(rp.read_text())

    required_lease_fields={"schema","lease_id","issuer","accelerator_uuid","memory_max_bytes","expires_epoch","issued_epoch","purpose","host","status","nonce","placement","enforcement","signature"}
    lease_doc_ok=(
        required_lease_fields.issubset(lease)
        and lease.get("schema")=="FA3-HOST-RESOURCE-BROKER-001/AcceleratorExecutionLease@1"
        and lease.get("issuer")=="FA3-HOST-RESOURCE-BROKER-001"
        and lease.get("status")=="ACTIVE"
        and int(lease.get("expires_epoch",0))>int(time.time())
        and str(lease.get("accelerator_uuid","")).startswith("GPU-")
        and int(lease.get("memory_max_bytes",0))>0
    )
    verifier_ok=False; verifier_result={}
    try:
        raw=run([a.hrb_verify_bin,"validate-lease",str(lp)])
        verifier_result=json.loads(raw)
        verifier_ok=(verifier_result.get("status")=="VALID" or verifier_result.get("result")=="VALID")
    except Exception as e:
        verifier_result={"error":type(e).__name__}

    cpu=lscpu_map(); gpus=gpu_rows(); uid=lease_uuid(lease); matches=[g for g in gpus if g["uuid"]==uid]
    gpu=matches[0] if len(matches)==1 else {}
    arch=f"sm{str(gpu.get('compute_cap','')).replace('.','')}" if gpu.get("compute_cap") else None

    lease_ok=bool(uid and gpu and lease_doc_ok and verifier_ok and uid==lease.get("accelerator_uuid"))
    selected=bench.get("selected_provider_ids",[])
    selected_ok=isinstance(selected,list) and bool(selected) and set(selected).issubset({FRAMEWORK_PROVIDER,AMPERE_PROVIDER,DEEPGEMM_PROVIDER})
    identity_ok=(
        bench.get("gpu_uuid")==uid
        and bench.get("gpu_pci_bdf")==gpu.get("pci_bdf")
        and bench.get("gpu_arch")==arch
    )
    provider_specific_ok=True
    if AMPERE_PROVIDER in selected and arch!="sm86":
        provider_specific_ok=False
    if DEEPGEMM_PROVIDER in selected and bench.get("deepgemm_runtime_admitted") is not True:
        provider_specific_ok=False
    if FRAMEWORK_PROVIDER in selected and bench.get("framework_native_compatibility_pass") is not True:
        provider_specific_ok=False

    bench_ok=(
        bench.get("status")=="PASS"
        and bench.get("synthetic") is False
        and identity_ok
        and bench.get("hardware_discovery_revalidated") is True
        and bench.get("provider_compatibility_pass") is True
        and selected_ok and provider_specific_ok
        and bench.get("correctness_pass") is True
        and bench.get("benchmark_pass") is True
        and bench.get("vram_workspace_preflight") is True
        and bench.get("no_silent_fallback") is True
    )
    rollback_ok=(
        rb.get("status")=="PASS"
        and rb.get("rollback_tested") is True
        and rb.get("baseline_backend_restored") is True
        and rb.get("failure_injection") is True
    )
    ok=lease_ok and bench_ok and rollback_ok

    sockets=int(cpu.get("Socket(s)","0") or 0)
    cores_per_socket=int(cpu.get("Core(s) per socket","0") or 0)
    logical=int(cpu.get("CPU(s)","0") or 0)
    numa=int(cpu.get("NUMA node(s)","0") or 0)
    out={
      "schema":"fa3.gpu-kernel-runtime-current-host-evidence.v2",
      "status":"CURRENT_HOST_PRODUCTION_E2E_PASS" if ok else "CURRENT_HOST_E2E_FAIL",
      "synthetic":False,
      "hardware_discovery_revalidated":bool(gpu and arch),
      "cpu_observation":{
        "model":cpu.get("Model name",""),
        "sockets":sockets,
        "cores_per_socket":cores_per_socket,
        "logical_cpus":logical,
        "numa_domains":numa,
        "semantics":"EVIDENCE_ONLY_NON_NORMATIVE"
      },
      "hrb_lease_valid":lease_ok,
      "hrb_lease_sha256":sha(lp),
      "hrb_verifier_result":verifier_result,
      "benchmark_evidence_sha256":sha(bp),
      "rollback_evidence_sha256":sha(rp),
      "compute_gpu_uuid":gpu.get("uuid"),
      "compute_gpu_name":gpu.get("name"),
      "compute_gpu_pci_bdf":gpu.get("pci_bdf"),
      "compute_gpu_arch":arch,
      "provider_compatibility_pass":bench_ok and provider_specific_ok,
      "selected_provider_ids":selected,
      "framework_native_compatibility_pass":bench.get("framework_native_compatibility_pass") is True,
      "deepgemm_runtime_admitted":bench.get("deepgemm_runtime_admitted") is True,
      "correctness_pass":bench_ok,
      "benchmark_pass":bench_ok,
      "rollback_pass":rollback_ok,
      "exact_host_tuple_required":False,
      "current_host_promotion_scope":"COMPONENT_ONLY_GLOBAL_143_CAPABILITY_PROMOTION_SEPARATE"
    }
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    raise SystemExit(0 if ok else 2)

if __name__=="__main__": main()
