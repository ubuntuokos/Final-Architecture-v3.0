#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,stat,subprocess
from pathlib import Path
from typing import Any
from fa3_provider_runtime import validate_runtime_environment
from fa3_supply_chain_admission import canonical_json_sha256,sha256_file
from fa3_release_baseline import module_active_capability_count

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def writej(p:Path,o:dict[str,Any])->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def run(cmd:list[str],timeout:int=60)->subprocess.CompletedProcess[str]:return subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,check=False)

def _venv(plan:dict[str,Any])->dict[str,Any]:
    v=plan["venv"];root=Path(str(v.get("path",""))).resolve();cfg=root/"pyvenv.cfg";py=root/"bin/python"
    if not cfg.is_file() or not py.is_file():raise RuntimeError("declared venv path is not a materialized Python venv")
    cfg_text=cfg.read_text(encoding="utf-8",errors="replace")
    if "include-system-site-packages = false" not in cfg_text.lower():raise RuntimeError("venv exposes system site packages")
    lock=Path(str(v.get("dependency_lock_path",""))).resolve()
    if not lock.is_file() or sha256_file(lock)!=v.get("dependency_lock_sha256"):raise RuntimeError("venv dependency lock path/hash mismatch")
    probe=run([str(py),"-I","-c","import json,sys;print(json.dumps({'prefix':sys.prefix,'base_prefix':sys.base_prefix,'executable':sys.executable}))"])
    if probe.returncode!=0:raise RuntimeError("venv isolated Python probe failed")
    p=json.loads(probe.stdout.strip())
    if p.get("prefix")==p.get("base_prefix"):raise RuntimeError("declared Python is not executing inside a venv")
    identity=canonical_json_sha256({"pyvenv_cfg_sha256":hashlib.sha256(cfg.read_bytes()).hexdigest(),"python_sha256":sha256_file(py),"dependency_lock_sha256":v.get("dependency_lock_sha256")})
    if identity!=v.get("environment_identity_sha256"):raise RuntimeError("venv environment identity mismatch")
    return {"execution_class":"VENV","venv_path":str(root),"python_executable_sha256":sha256_file(py),"environment_identity_sha256":identity,"isolated_python_probe":True}

def _oci(plan:dict[str,Any])->dict[str,Any]:
    if os.geteuid()==0:raise RuntimeError("OCI current-host proof must run unprivileged/rootless")
    o=plan["oci"];podman=run(["podman","info","--format","json"])
    if podman.returncode!=0:raise RuntimeError("rootless Podman info failed")
    info=json.loads(podman.stdout)
    rootless=bool(info.get("host",{}).get("security",{}).get("rootless",False))
    if not rootless:raise RuntimeError("Podman is not rootless")
    ref=str(o.get("image_ref",""))
    if not ref:raise RuntimeError("OCI image_ref missing")
    inspect=run(["podman","image","inspect",ref,"--format","json"])
    if inspect.returncode!=0:raise RuntimeError("preloaded OCI image inspect failed; network pull is forbidden")
    rows=json.loads(inspect.stdout);row=rows[0] if isinstance(rows,list) and rows else {}
    expected=str(o.get("image_digest",""))
    digests=[str(x) for x in row.get("RepoDigests",[])]+[str(row.get("Digest",""))]
    if not any(expected in x for x in digests):raise RuntimeError("preloaded OCI image digest mismatch")
    smoke=run(["podman","run","--rm","--pull=never","--network","none","--read-only",ref,"/bin/true"],120)
    if smoke.returncode!=0:raise RuntimeError("rootless OCI immutable smoke execution failed")
    return {"execution_class":"OCI","rootless":True,"image_ref":ref,"image_digest":expected,"network":"none","read_only":True,"pull":"never","smoke_execution":True}

def _host_native(plan:dict[str,Any])->dict[str,Any]:
    h=plan["host_native"];exe=Path(str(h.get("executable_path","")))
    if not exe.is_absolute():raise RuntimeError("host-native executable path must be absolute")
    st=exe.lstat()
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):raise RuntimeError("host-native executable must be regular non-symlink")
    digest=sha256_file(exe)
    if digest!=h.get("executable_sha256"):raise RuntimeError("host-native executable identity mismatch")
    return {"execution_class":"HOST_NATIVE","executable_path":str(exe),"executable_sha256":digest,"identity_only":True,"arbitrary_execution_performed":False}

def collect(root:Path,plan_path:Path,output:Path)->dict[str,Any]:
    receipt={"schema":"fa3.provider-runtime-current-host-receipt.v1","surface":"PROVIDER_RUNTIME_ENVIRONMENT","synthetic":False,"global_promotion_claim":False,"capability_count":module_active_capability_count(__file__)}
    try:
        plan=loadj(plan_path);validation=validate_runtime_environment(plan)
        if validation["result"]!="PASS":raise RuntimeError("provider runtime plan invalid: "+",".join(validation["findings"]))
        cls=plan["execution_class"]
        proof=_venv(plan) if cls=="VENV" else _oci(plan) if cls=="OCI" else _host_native(plan)
        receipt.update({"result":"PASS","status":"CURRENT_HOST_PASS","provider_id":plan["provider_id"],"execution_class":cls,"plan_path":str(plan_path),"plan_sha256":sha256_file(plan_path),"proof":proof})
    except Exception as exc:
        receipt.update({"result":"PENDING","status":"PENDING_CURRENT_HOST","error_type":type(exc).__name__,"error":str(exc)})
    writej(output,receipt);return receipt

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--plan",required=True);p.add_argument("--output",default="evidence/receipts/provider-runtime-current-host.json");a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.output);out=out if out.is_absolute() else root/out
    r=collect(root,Path(a.plan).resolve(),out);print(json.dumps(r,indent=2,ensure_ascii=False));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
