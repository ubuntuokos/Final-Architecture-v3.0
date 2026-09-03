#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

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
        if len(p)>=7: rows.append({"index":int(p[0]),"uuid":p[1],"name":p[2],"pci_bdf":p[3],"memory_mib":int(p[4]),"compute_cap":p[5],"driver":p[6]})
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
    ap=argparse.ArgumentParser(description="Collect real FA3 T7910 SM86 GPU-kernel-runtime evidence")
    ap.add_argument("--hrb-lease",required=True)
    ap.add_argument("--benchmark-evidence",required=True)
    ap.add_argument("--rollback-evidence",required=True)
    ap.add_argument("--output",default="evidence/receipts/gpu-kernel-runtime-current-host.json")
    a=ap.parse_args()
    lp,bp,rp=map(Path,(a.hrb_lease,a.benchmark_evidence,a.rollback_evidence))
    lease=json.loads(lp.read_text()); bench=json.loads(bp.read_text()); rb=json.loads(rp.read_text())
    cpu=lscpu_map(); gpus=gpu_rows(); uid=lease_uuid(lease); matches=[g for g in gpus if g["uuid"]==uid]
    gpu=matches[0] if len(matches)==1 else {}
    cpu_model=cpu.get("Model name","")
    cpu_ok=("E5-2696 v4" in cpu_model and int(cpu.get("Socket(s)","0"))==2 and int(cpu.get("Core(s) per socket","0"))==22 and int(cpu.get("CPU(s)","0"))==88 and int(cpu.get("NUMA node(s)","0"))==2)
    gpu_ok=("RTX 3080" in gpu.get("name","") and gpu.get("compute_cap")=="8.6")
    lease_ok=bool(uid and gpu and (lease.get("status") in ("VALID","PASS","ACTIVE",None)))
    bench_ok=(bench.get("status")=="PASS" and bench.get("synthetic") is False and bench.get("gpu_uuid")==uid and bench.get("gpu_arch")=="sm86" and bench.get("correctness_pass") is True and bench.get("benchmark_pass") is True and bench.get("vram_workspace_preflight") is True and bench.get("no_silent_fallback") is True)
    rollback_ok=(rb.get("status")=="PASS" and rb.get("rollback_tested") is True and rb.get("baseline_backend_restored") is True and rb.get("failure_injection") is True)
    ok=cpu_ok and gpu_ok and lease_ok and bench_ok and rollback_ok
    out={
      "schema":"fa3.gpu-kernel-runtime-current-host-evidence.v1",
      "status":"CURRENT_HOST_PRODUCTION_E2E_PASS" if ok else "CURRENT_HOST_E2E_FAIL",
      "synthetic":False,"cpu_model":cpu_model,"physical_cores":44 if cpu_ok else None,"logical_cpus":int(cpu.get("CPU(s)","0") or 0),
      "numa_domains":int(cpu.get("NUMA node(s)","0") or 0),"hrb_lease_valid":lease_ok,
      "hrb_lease_sha256":sha(lp),"benchmark_evidence_sha256":sha(bp),"rollback_evidence_sha256":sha(rp),
      "compute_gpu_uuid":gpu.get("uuid"),"compute_gpu_name":gpu.get("name"),"compute_gpu_pci_bdf":gpu.get("pci_bdf"),
      "compute_gpu_arch":"sm86" if gpu_ok else None,"correctness_pass":bench_ok,"benchmark_pass":bench_ok,"rollback_pass":rollback_ok,
      "deepgemm_current_host_eligible":False,
      "reference_host_assertions":{"cpu_ok":cpu_ok,"gpu_ok":gpu_ok},
      "current_host_promotion_scope":"COMPONENT_ONLY_GLOBAL_143_CAPABILITY_PROMOTION_SEPARATE"
    }
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))
    raise SystemExit(0 if ok else 2)
if __name__=="__main__": main()
