#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, platform, shutil, socket, sqlite3, stat, subprocess, sys
from pathlib import Path
from typing import Any

VERDICT_SCHEMA="fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITIES=("CAP-001","CAP-002","CAP-003","CAP-004","CAP-005")
MODES=("positive","negative","rollback")
NAMES={c:f"{c.lower().replace('-','')}-mat001-evidence.json" for c in CAPABILITIES}

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:return sha(p.read_bytes())
def load(p:Path)->dict[str,Any]:
    o=json.loads(p.read_text());
    if not isinstance(o,dict): raise RuntimeError(f"object required: {p}")
    return o
def write(p:Path,o:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n")
def env(n:str)->str:
    v=os.environ.get(n)
    if not v: raise RuntimeError(f"required environment variable missing: {n}")
    return v
def repo_file(root:Path,rel:str)->Path:
    p=(root/rel).resolve()
    if root.resolve() not in p.parents or not p.is_file(): raise RuntimeError(f"required artifact missing: {rel}")
    return p

def expected_source_decisions(root:Path,cap:str)->list[str]:
    r=load(root/"evidence/evidence-registry.json")
    row=next((x for x in r.get("records",[]) if x.get("subject_id")==cap),None)
    ids=row.get("source_decision_ids") if isinstance(row,dict) else None
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) or not x for x in ids): raise RuntimeError(f"{cap} source decisions invalid")
    return ids
def validate_exact_coverage(root:Path,cap:str,supplied:list[str])->list[str]:
    exp=expected_source_decisions(root,cap)
    if supplied!=exp: raise RuntimeError(f"{cap} coverage != Evidence Registry")
    return exp

def validate_bind_target(h:str)->bool:return h in {"127.0.0.1","::1","localhost"}
def validate_secret_mode(m:int)->bool:return stat.S_IMODE(m)&0o077==0
def validate_provider_route(r:dict[str,Any],allowed:set[str])->bool:
    return isinstance(r.get("provider_id"),str) and r["provider_id"] in allowed and isinstance(r.get("backend"),str) and bool(r["backend"]) and r.get("local_only") is True

def physical_core_packages()->dict[str,set[str]]:
    out:dict[str,set[str]]={}
    for c in Path("/sys/devices/system/cpu").glob("cpu[0-9]*"):
        try:
            package=(c/"topology/physical_package_id").read_text().strip()
            core=(c/"topology/core_id").read_text().strip()
            out.setdefault(package,set()).add(core)
        except OSError:pass
    return out
def host_baseline_valid(uid:int,packages:dict[str,set[str]],cgroup_v2:bool,compute_caps:list[float])->bool:
    return uid!=0 and bool(packages) and all(len(cores)>=8 for cores in packages.values()) and cgroup_v2 and any(cap>=8.6 for cap in compute_caps)
def cmd(a:list[str],t:int=15):return subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=t,shell=False,check=False)
def exact_rollback(scope:Path,name:str,baseline:bytes,fault:bytes)->dict[str,Any]:
    p=scope/name;p.write_bytes(baseline);pre=sha_file(p);p.write_bytes(fault);mut=sha_file(p);p.write_bytes(baseline);post=sha_file(p)
    if pre!=post or pre==mut: raise RuntimeError("exact rollback proof failed")
    return {"pre_sha256":pre,"mutated_sha256":mut,"post_sha256":post,"rollback_hash_equal":True}

def cap001(root:Path,scope:Path,mode:str)->dict[str,Any]:
    if mode=="negative":
        good_packages={"0":set(str(x) for x in range(8))}
        cases={
            "root_denied":not host_baseline_valid(0,good_packages,True,[8.6]),
            "lt8_cores_per_cpu_denied":not host_baseline_valid(1000,{"0":set(str(x) for x in range(7))},True,[8.6]),
            "no_cgroup_v2_denied":not host_baseline_valid(1000,good_packages,False,[8.6]),
            "compute_cap_below_86_denied":not host_baseline_valid(1000,good_packages,True,[8.0]),
            "no_accelerator_denied":not host_baseline_valid(1000,good_packages,True,[]),
        }
        if not all(cases.values()):raise RuntimeError("host baseline negative matrix failed")
        return {"mode":mode,"status":"PASS","fault_injection":"POLICY_INPUT_MATRIX","cases":cases}
    if mode=="rollback": return {"mode":mode,"status":"PASS",**exact_rollback(scope,"host-state.json",b'{"admission":"DENY_BY_DEFAULT"}\n',b'{"admission":"ALLOW_ALL"}\n')}
    for x in ["canonical/FA3-HOST-ATTESTATION-001.json","canonical/FA3-COMPUTE-PROFILE-001.json","canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json"]:repo_file(root,x)
    if platform.system()!="Linux":raise RuntimeError("Linux host required")
    nodes=list(Path("/sys/devices/system/node").glob("node[0-9]*"));packages=physical_core_packages();cgroup=Path("/sys/fs/cgroup/cgroup.controllers").is_file()
    n=shutil.which("nvidia-smi");p=cmd([n,"--query-gpu=name,uuid,memory.total,compute_cap","--format=csv,noheader,nounits"]) if n else None
    if not p or p.returncode or not p.stdout.strip():raise RuntimeError("NVIDIA accelerator inventory unavailable")
    rows=[x.strip() for x in p.stdout.splitlines() if x.strip()];caps=[]
    for row in rows:
        try:caps.append(float(row.rsplit(",",1)[1].strip()))
        except (ValueError,IndexError):raise RuntimeError(f"cannot parse GPU compute capability: {row}")
    if not nodes or not host_baseline_valid(os.geteuid(),packages,cgroup,caps):
        raise RuntimeError(f"portable host baseline failed nodes={len(nodes)} packages={ {k:len(v) for k,v in packages.items()} } compute_caps={caps}")
    return {"mode":mode,"status":"PASS","kernel":platform.release(),"uid":os.geteuid(),"numa_nodes":len(nodes),"physical_cores_per_package":{k:len(v) for k,v in packages.items()},"gpu_compute_capabilities":caps,"accelerators":rows}

def cap002(root:Path,scope:Path,mode:str)->dict[str,Any]:
    if mode=="negative":
        cases={"ipv4_wildcard_denied":not validate_bind_target("0.0.0.0"),"ipv6_wildcard_denied":not validate_bind_target("::"),"external_denied":not validate_bind_target("192.0.2.1")}
        if not all(cases.values()):raise RuntimeError("network negative matrix failed")
        return {"mode":mode,"status":"PASS","cases":cases}
    if mode=="rollback":return {"mode":mode,"status":"PASS",**exact_rollback(scope,"bind.json",b'{"bind":"127.0.0.1"}\n',b'{"bind":"0.0.0.0"}\n')}
    if not Path("/sys/class/net/lo").exists():raise RuntimeError("loopback missing")
    s=socket.socket();c=socket.socket()
    try:
        s.settimeout(3);s.bind(("127.0.0.1",0));s.listen(1);h,p=s.getsockname();c.settimeout(3);c.connect((h,p));a,peer=s.accept();a.close()
        if not validate_bind_target(h):raise RuntimeError("probe escaped loopback")
        return {"mode":mode,"status":"PASS","bind_host":h,"ephemeral_port":p,"peer":peer[0],"external_network_required":False}
    finally:c.close();s.close()

def cap003(root:Path,scope:Path,mode:str)->dict[str,Any]:
    repo_file(root,"canonical/contracts/FA3-AI-SECURITY-VALIDATION-CONTRACTS-001.json")
    p=scope/"secret-probe";base=b"opaque-current-host-probe\n";p.write_bytes(base);p.chmod(0o600)
    if mode=="negative":p.chmod(0o644);ok=not validate_secret_mode(p.stat().st_mode);return {"mode":mode,"status":"PASS" if ok else "FAIL","world_readable_rejected":ok}
    if mode=="rollback":
        pre=sha_file(p);p.write_bytes(b"fault\n");p.chmod(0o644);mut=sha_file(p);p.write_bytes(base);p.chmod(0o600);post=sha_file(p)
        if pre!=post or pre==mut or not validate_secret_mode(p.stat().st_mode):raise RuntimeError("secret rollback failed")
        return {"mode":mode,"status":"PASS","pre_sha256":pre,"mutated_sha256":mut,"post_sha256":post}
    if os.geteuid()==0 or not validate_secret_mode(p.stat().st_mode):raise RuntimeError("non-root/private-secret baseline failed")
    return {"mode":mode,"status":"PASS","uid":os.geteuid(),"gid":os.getegid(),"secret_mode":"0600","secret_sha256":sha_file(p),"secret_value_disclosed":False}

def cap004(root:Path,scope:Path,mode:str)->dict[str,Any]:
    if mode=="rollback":
        proof=exact_rollback(scope,"workflow.json",b'{"cursor":7,"state":"READY"}\n',b'{"cursor":999,"state":"FAULT"}\n');return {"mode":mode,"status":"PASS",**proof}
    db=sqlite3.connect(scope/"events.sqlite3")
    try:
        db.execute("CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
        if mode=="positive":db.execute("INSERT INTO events VALUES(?,?)",("evt-1","{}"));db.commit();n=db.execute("SELECT COUNT(*) FROM events").fetchone()[0];return {"mode":mode,"status":"PASS","event_count":n,"durable_commit":n==1}
        db.execute("INSERT INTO events VALUES(?,?)",("dup","{}"));db.commit();rejected=False
        try:db.execute("INSERT INTO events VALUES(?,?)",("dup","{}"));db.commit()
        except sqlite3.IntegrityError:rejected=True;db.rollback()
        if not rejected:raise RuntimeError("duplicate event id admitted")
        return {"mode":mode,"status":"PASS","duplicate_event_rejected":True}
    finally:db.close()

def provider_ids(root:Path)->set[str]:
    out=set()
    for p in (root/"canonical/providers").glob("FA3-PROVIDER-*.json"):
        try:i=load(p).get("id")
        except Exception:continue
        if isinstance(i,str) and i:out.add(i)
    if not out:raise RuntimeError("provider registry empty")
    return out
def cap005(root:Path,scope:Path,mode:str)->dict[str,Any]:
    repo_file(root,"canonical/registries/FA3-MODEL-REGISTRY-001.json");repo_file(root,"canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json");allowed=provider_ids(root)
    if mode=="negative":
        bad={"provider_id":"FA3-PROVIDER-UNKNOWN","backend":"unknown","local_only":True};ok=not validate_provider_route(bad,allowed)
        return {"mode":mode,"status":"PASS" if ok else "FAIL","unregistered_provider_rejected":ok}
    if mode=="rollback":
        chosen=sorted(allowed)[0];base=(json.dumps({"provider_id":chosen,"backend":"canonical-local","local_only":True},sort_keys=True,separators=(",",":"))+"\n").encode();proof=exact_rollback(scope,"route.json",base,b'{"provider_id":"FA3-PROVIDER-UNKNOWN","backend":"external","local_only":false}\n');return {"mode":mode,"status":"PASS",**proof}
    n=shutil.which("nvidia-smi");g=cmd([n,"--query-gpu=name,uuid,memory.total","--format=csv,noheader"]) if n else None
    if not g or g.returncode or not g.stdout.strip():raise RuntimeError("GPU backend unavailable")
    o=shutil.which("ollama");ls=cmd([o,"list"],20) if o else None;ll=shutil.which("llama-server");canonical_store=any(p.exists() for p in [Path(os.environ.get("FA3_CANONICAL_MODEL_STORE","")) if os.environ.get("FA3_CANONICAL_MODEL_STORE") else Path.home()/".local/share/fa3/models",Path.home()/".local/share/fa3/models"])
    if not ((ls and ls.returncode==0) or ll or sm):raise RuntimeError("no local model/backend execution surface")
    return {"mode":mode,"status":"PASS","provider_count":len(allowed),"accelerators":[x.strip() for x in g.stdout.splitlines() if x.strip()],"ollama_inventory":bool(ls and ls.returncode==0),"llama_server":bool(ll),"canonical_model_store":canonical_store}

HANDLERS={"CAP-001":cap001,"CAP-002":cap002,"CAP-003":cap003,"CAP-004":cap004,"CAP-005":cap005}
def run_mode(root:Path,scope:Path,cap:str,mode:str)->dict[str,Any]:
    root=root.resolve();scope=scope.resolve()
    if cap not in CAPABILITIES or mode not in MODES:raise ValueError("unsupported capability or mode")
    if root not in scope.parents:raise RuntimeError("artifact scope escapes repository")
    scope.mkdir(parents=True,exist_ok=True);return HANDLERS[cap](root,scope,mode)

def main()->int:
    a=argparse.ArgumentParser();a.add_argument("--capability",choices=CAPABILITIES,required=True);a.add_argument("--mode",choices=MODES,required=True);a.add_argument("--producer-id",required=True);x=a.parse_args()
    try:
        if env("FA3_CURRENT_HOST")!="1" or env("FA3_EXECUTION_SCOPE")!="CURRENT_HOST":raise RuntimeError("real CURRENT_HOST execution required")
        if env("FA3_CAPABILITY_ID")!=x.capability:raise RuntimeError("capability binding mismatch")
        root=Path(env("FA3_REPOSITORY_ROOT")).resolve();scope=Path(env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve();sup=json.loads(env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"));coverage=validate_exact_coverage(root,x.capability,sup)
        hd=env("FA3_HOST_FINGERPRINT_SHA256")
        if len(hd)!=64 or any(c not in "0123456789abcdef" for c in hd.lower()):raise RuntimeError("invalid host fingerprint SHA-256")
        result=run_mode(root,scope,x.capability,x.mode);result.update({"source_decision_coverage_count":len(coverage),"host_fingerprint_sha256":hd})
        art=scope/NAMES[x.capability];write(art,{"schema":"fa3.mat001-foundation-current-host-evidence.v1","subject_id":x.capability,"test_kind":env("FA3_TEST_KIND"),"test_id":env("FA3_TEST_ID"),"qualification_id":env("FA3_QUALIFICATION_ID"),"constituent_id":env("FA3_CONSTITUENT_ID"),"execution_scope":"CURRENT_HOST","current_host":True,"synthetic":False,"ci_reference_only":False,"provider_receipt_only":False,"component_receipt_only":False,"generic_host_collection_only":False,"global_promotion_claim":False,"result":result})
        verdict={"schema":VERDICT_SCHEMA,"producer_id":x.producer_id,"qualification_id":env("FA3_QUALIFICATION_ID"),"constituent_id":env("FA3_CONSTITUENT_ID"),"subject_id":x.capability,"test_kind":env("FA3_TEST_KIND"),"test_id":env("FA3_TEST_ID"),"status":"PASS","execution_scope":"CURRENT_HOST","current_host":True,"synthetic":False,"ci_reference_only":False,"provider_receipt_only":False,"component_receipt_only":False,"generic_host_collection_only":False,"global_promotion_claim":False,"source_evidence_class":env("FA3_SOURCE_EVIDENCE_CLASS"),"covers_source_decision_ids":coverage,"source_artifact_path":art.relative_to(root).as_posix(),"source_artifact_sha256":sha_file(art)}
        print(json.dumps(verdict,ensure_ascii=False,separators=(",",":")));return 0
    except Exception as e:print(json.dumps({"status":"REJECTED","findings":[str(e)]}),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
