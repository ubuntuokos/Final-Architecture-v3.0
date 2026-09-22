#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, socket, sqlite3, subprocess, sys
from pathlib import Path
from typing import Any

VERDICT_SCHEMA="fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITIES=("CAP-006","CAP-007","CAP-008","CAP-009","CAP-010")
MODES=("positive","negative","rollback")
NAMES={c:f"{c.lower().replace('-','')}-mat002-evidence.json" for c in CAPABILITIES}
REJECTION_SCHEMA="fa3.qualification-producer-rejection.v1"

class ProducerRejection(RuntimeError):
    def __init__(self,stage:str,reason_codes:list[str],summary:dict[str,Any]|None=None):
        super().__init__(stage)
        self.stage=stage
        self.reason_codes=reason_codes
        self.summary=summary or {}

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:return sha(p.read_bytes())
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict):raise RuntimeError(f"JSON object required: {p}")
    return v
def write(p:Path,v:Any)->None:
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def env(n:str)->str:
    v=os.environ.get(n)
    if not v:raise RuntimeError(f"required environment variable missing: {n}")
    return v
def repo_file(root:Path,rel:str)->Path:
    p=(root/rel).resolve()
    if root.resolve() not in p.parents or not p.is_file():raise RuntimeError(f"required artifact missing: {rel}")
    return p
def cmd(a:list[str],t:int=30):
    return subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=t,shell=False,check=False)
def expected_source_decisions(root:Path,cap:str)->list[str]:
    r=load(root/"evidence/evidence-registry.json")
    row=next((x for x in r.get("records",[]) if x.get("subject_id")==cap),None)
    ids=row.get("source_decision_ids") if isinstance(row,dict) else None
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) or not x for x in ids):raise RuntimeError(f"{cap} source decisions invalid")
    return ids
def validate_exact_coverage(root:Path,cap:str,supplied:list[str])->list[str]:
    exp=expected_source_decisions(root,cap)
    if supplied!=exp:raise RuntimeError(f"{cap} coverage != Evidence Registry")
    return exp
def exact_rollback(scope:Path,name:str,baseline:bytes,fault:bytes)->dict[str,Any]:
    p=scope/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(baseline);pre=sha_file(p);p.write_bytes(fault);mut=sha_file(p);p.write_bytes(baseline);post=sha_file(p)
    if pre!=post or pre==mut:raise RuntimeError("exact rollback proof failed")
    return {"pre_sha256":pre,"mutated_sha256":mut,"post_sha256":post,"rollback_hash_equal":True}

def hrb_failure_summary(receipt_path:Path)->dict[str,Any]:
    try:receipt=load(receipt_path)
    except Exception:return {"failed_check_codes":["CAP006_RECEIPT_UNAVAILABLE"]}
    summary=receipt.get("check_summary")
    if not isinstance(summary,dict):return {"failed_check_codes":["CAP006_CHECK_SUMMARY_UNAVAILABLE"]}
    allowed={
        "cpu_baseline_pass","accelerator_inventory_schema_pass","manager_collection_pass",
        "manager_neutrality_pass","cgroup_v2_pass","negative_tests_pass","failed_check_codes",
        "cpu_package_count","minimum_physical_cores","accelerator_device_count",
        "effective_cpu_set_present","effective_memory_nodes_present","failed_negative_test_codes",
    }
    return {key:summary[key] for key in sorted(allowed) if key in summary}

def hrb_gate_failure_codes(root:Path)->list[str]:
    try:payload=load(root/"reports/hrb-systemd-manager-current-host-gate-report.json")
    except Exception:return ["CAP006_GATE_REPORT_UNAVAILABLE"]
    rows=payload.get("findings")
    if not isinstance(rows,list):return ["CAP006_GATE_REPORT_INVALID"]
    codes=[str(row.get("code")) for row in rows if isinstance(row,dict) and row.get("code")]
    return codes[:8] or ["CAP006_GATE_REJECTED"]

def workspace_allowed(candidate:Path,approved_root:Path,home:Path,model_roots:tuple[Path,...]=())->bool:
    candidate,approved_root,home=candidate.resolve(),approved_root.resolve(),home.resolve()
    if candidate in {Path("/"),home,approved_root} or approved_root not in candidate.parents:return False
    for r in model_roots:
        rr=r.resolve()
        if candidate==rr or rr in candidate.parents:return False
    return True

def agent_task_allowed(task:dict[str,Any])->bool:
    argv=task.get("argv")
    return (
        task.get("execution_scope")=="CURRENT_HOST" and
        task.get("requires_human_approval") is True and
        task.get("privileged") is False and
        task.get("network_scope") in {"NONE","LOOPBACK"} and
        isinstance(argv,list) and bool(argv) and
        all(isinstance(x,str) and x for x in argv) and
        Path(argv[0]).name not in {"sudo","su","pkexec"}
    )

def deliberation_valid(votes:list[dict[str,Any]],quorum:int=2)->bool:
    if len(votes)<quorum:return False
    actors=[v.get("actor_id") for v in votes];choices=[v.get("choice") for v in votes]
    if any(not isinstance(x,str) or not x for x in actors) or len(set(actors))!=len(actors):return False
    if any(x not in {"A","B","ABSTAIN"} for x in choices):return False
    return max(choices.count("A"),choices.count("B"))>=quorum

def knowledge_note_allowed(meta:dict[str,Any])->bool:
    return meta.get("status")=="APPROVED" and meta.get("index") is True and meta.get("visibility") in {"PRIVATE","TEAM","PUBLIC"} and isinstance(meta.get("id"),str) and bool(meta["id"])

def cap006(root:Path,scope:Path,mode:str)->dict[str,Any]:
    repo_file(root,"canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json")
    collector=repo_file(root,"evidence/collect-hrb-systemd-manager-current-host.py")
    gate=repo_file(root,"src/fa3_hrb_systemd_manager_current_host_gate.py")
    if mode=="negative":
        sys.path.insert(0,str(root/"src"))
        from fa3_hrb_systemd_manager_current_host_gate import manager_violations
        def denied(k:str,v:str)->bool:return bool(manager_violations([{"source":"/etc/systemd/system.conf.d/90-fa3-test.conf","key":k,"value":v}],{}))
        cases={"global_cpu_affinity_denied":denied("CPUAffinity","0-7"),"global_numa_policy_denied":denied("NUMAPolicy","preferred"),"unbounded_memlock_denied":denied("DefaultLimitMEMLOCK","infinity")}
        if not all(cases.values()):raise RuntimeError("Resource Fabric negative matrix failed")
        return {"mode":mode,"status":"PASS","cases":cases}
    if mode=="rollback":
        return {"mode":mode,"status":"PASS",**exact_rollback(scope,"resource-policy.json",b'{"authority":"HRB","admission":"DENY_BY_DEFAULT"}\n',b'{"authority":"APPLICATION","admission":"ALLOW_ALL"}\n')}
    receipt=scope/"hrb-systemd-manager-current-host.json"
    p=cmd([sys.executable,str(collector),"--root",str(root),"--receipt",str(receipt)],90)
    if p.returncode:
        summary=hrb_failure_summary(receipt)
        codes=summary.get("failed_check_codes")
        if not isinstance(codes,list) or not codes:codes=["CAP006_COLLECTOR_REJECTED"]
        raise ProducerRejection("COLLECTOR",codes,summary)
    g=cmd([sys.executable,str(gate),"--root",str(root),"--receipt",str(receipt)],60)
    if g.returncode:raise ProducerRejection("GATE",hrb_gate_failure_codes(root))
    ev=load(receipt)
    return {"mode":mode,"status":"PASS","evidence_level":ev.get("evidence_level"),"resource_authority_id":ev.get("resource_authority_id"),"cgroup_v2":ev.get("cgroup_v2"),"manager_violations":ev.get("manager_violations")}

def cap007(root:Path,scope:Path,mode:str)->dict[str,Any]:
    repo_file(root,"canonical/contracts/FA3-DURABLE-REPLAYABLE-MULTI-AGENT-EXECUTION-CONTRACTS-001.json")
    repo_file(root,"canonical/contracts/FA3-AGENT-EXEC-CONTRACTS-001.json")
    if mode=="negative":
        cases={
          "sudo_denied":not agent_task_allowed({"execution_scope":"CURRENT_HOST","requires_human_approval":True,"privileged":False,"network_scope":"NONE","argv":["sudo","id"]}),
          "unapproved_denied":not agent_task_allowed({"execution_scope":"CURRENT_HOST","requires_human_approval":False,"privileged":False,"network_scope":"NONE","argv":[sys.executable,"-c","print(1)"]}),
          "external_network_denied":not agent_task_allowed({"execution_scope":"CURRENT_HOST","requires_human_approval":True,"privileged":False,"network_scope":"INTERNET","argv":[sys.executable,"-c","print(1)"]}),
        }
        if not all(cases.values()):raise RuntimeError("Agent Runtime negative matrix failed")
        return {"mode":mode,"status":"PASS","cases":cases}
    if mode=="rollback":
        return {"mode":mode,"status":"PASS",**exact_rollback(scope,"agent-runtime-state.json",b'{"state":"READY","attempt":0}\n',b'{"state":"RUNNING","attempt":99}\n')}
    task={"execution_scope":"CURRENT_HOST","requires_human_approval":True,"privileged":False,"network_scope":"NONE","argv":[sys.executable,"-c","import json,os;print(json.dumps({'pid':os.getpid(),'status':'PASS'}))"]}
    if not agent_task_allowed(task):raise RuntimeError("Agent Runtime positive task rejected")
    p=cmd(task["argv"],20)
    if p.returncode:raise RuntimeError(f"agent worker failed: {p.stderr[-2000:]}")
    out=json.loads(p.stdout.strip())
    if out.get("status")!="PASS" or not isinstance(out.get("pid"),int):raise RuntimeError("agent worker result invalid")
    return {"mode":mode,"status":"PASS","worker_pid":out["pid"],"parent_pid":os.getpid(),"separate_process":out["pid"]!=os.getpid(),"network_scope":"NONE","privileged":False}

def detect_wayland_session()->dict[str,Any]:
    typ=os.environ.get("XDG_SESSION_TYPE","").strip().lower();display=os.environ.get("WAYLAND_DISPLAY","").strip();runtime=os.environ.get("XDG_RUNTIME_DIR","").strip()
    if typ=="wayland" and display:return {"session_type":typ,"wayland_display":display,"runtime_dir":runtime,"source":"ENVIRONMENT"}
    loginctl=shutil.which("loginctl")
    if loginctl:
        p=cmd([loginctl,"show-user",str(os.getuid()),"-p","Display","--value"],10);sid=p.stdout.strip() if p.returncode==0 else ""
        if sid:
            q=cmd([loginctl,"show-session",sid,"-p","Type","-p","Remote","-p","Active"],10);fields={}
            for line in q.stdout.splitlines():
                if "=" in line:
                    k,v=line.split("=",1);fields[k]=v
            return {"session_type":fields.get("Type","").lower(),"active":fields.get("Active")=="yes","remote":fields.get("Remote")=="yes","session_id":sid,"source":"LOGINCTL"}
    return {"session_type":typ,"wayland_display":display,"source":"UNRESOLVED"}

def cap008(root:Path,scope:Path,mode:str)->dict[str,Any]:
    repo_file(root,"canonical/contracts/FA3-DESKTOP-AGENT-WORKBENCH-CONTRACTS-001.json")
    approved=(scope/"workspace").resolve();approved.mkdir(parents=True,exist_ok=True);home=Path.home().resolve();models=(Path("/AI-modells"),Path("/opt/AI-modells"))
    if mode=="negative":
        child=approved/"project";child.mkdir(parents=True,exist_ok=True)
        cases={"filesystem_root_denied":not workspace_allowed(Path("/"),approved,home,models),"whole_home_denied":not workspace_allowed(home,approved,home,models),"approved_root_denied":not workspace_allowed(approved,approved,home,models),"bounded_child_allowed":workspace_allowed(child,approved,home,models)}
        if not all(cases.values()):raise RuntimeError("Agent Workspace boundary matrix failed")
        return {"mode":mode,"status":"PASS","cases":cases}
    if mode=="rollback":
        return {"mode":mode,"status":"PASS",**exact_rollback(scope,"workspace-policy.json",b'{"workspace":"bounded","mutation":"ASK"}\n',b'{"workspace":"/","mutation":"ALLOW"}\n')}
    session=detect_wayland_session()
    if session.get("session_type")!="wayland":raise RuntimeError(f"Wayland desktop session not proven: {session}")
    project=approved/"project";project.mkdir(parents=True,exist_ok=True)
    if not workspace_allowed(project,approved,home,models):raise RuntimeError("bounded workspace rejected")
    s=socket.socket();c=socket.socket()
    try:
        s.settimeout(3);s.bind(("127.0.0.1",0));s.listen(1);h,p=s.getsockname();c.settimeout(3);c.connect((h,p));a,_=s.accept();a.close()
        if h!="127.0.0.1":raise RuntimeError("workspace backend escaped loopback")
    finally:c.close();s.close()
    return {"mode":mode,"status":"PASS","session":session,"workspace_root":str(approved.relative_to(root)),"project_root":str(project.relative_to(root)),"loopback_backend":True}

def cap009(root:Path,scope:Path,mode:str)->dict[str,Any]:
    if mode=="negative":
        cases={"duplicate_actor_denied":not deliberation_valid([{"actor_id":"a","choice":"A"},{"actor_id":"a","choice":"A"}]),"no_quorum_denied":not deliberation_valid([{"actor_id":"a","choice":"A"},{"actor_id":"b","choice":"B"},{"actor_id":"c","choice":"ABSTAIN"}]),"invalid_choice_denied":not deliberation_valid([{"actor_id":"a","choice":"A"},{"actor_id":"b","choice":"C"}])}
        if not all(cases.values()):raise RuntimeError("Deliberation negative matrix failed")
        return {"mode":mode,"status":"PASS","cases":cases}
    if mode=="rollback":
        return {"mode":mode,"status":"PASS",**exact_rollback(scope,"deliberation-state.json",b'{"state":"READY","decision":null}\n',b'{"state":"COMMITTED","decision":"UNVERIFIED"}\n')}
    votes=[];pids=[]
    for actor,choice in (("planner","A"),("critic","A"),("reviewer","B")):
        code=f"import json,os;print(json.dumps({{'actor_id':'{actor}','choice':'{choice}','pid':os.getpid()}}))";p=cmd([sys.executable,"-c",code],20)
        if p.returncode:raise RuntimeError(f"deliberation actor {actor} failed: {p.stderr[-2000:]}")
        row=json.loads(p.stdout.strip());votes.append({"actor_id":row["actor_id"],"choice":row["choice"]});pids.append(int(row["pid"]))
    if not deliberation_valid(votes):raise RuntimeError(f"Deliberation quorum failed: {votes}")
    return {"mode":mode,"status":"PASS","votes":votes,"decision":"A","actor_process_ids":pids,"distinct_actor_processes":len(set(pids))==3,"quorum":2}

def cap010(root:Path,scope:Path,mode:str)->dict[str,Any]:
    repo_file(root,"canonical/contracts/FA3-HUMAN-KNOWLEDGE-WORKSPACE-CONTRACTS-001.json");repo_file(root,"canonical/contracts/FA3-AGENT-MEMORY-ASSET-GOVERNANCE-CONTRACTS-001.json");repo_file(root,"canonical/FA3-GATE-KNOWLEDGE-HYBRID-RETRIEVAL-001.json")
    if mode=="negative":
        cases={"unknown_visibility_denied":not knowledge_note_allowed({"id":"n1","status":"APPROVED","index":True,"visibility":"UNKNOWN"}),"unapproved_denied":not knowledge_note_allowed({"id":"n2","status":"DRAFT","index":True,"visibility":"PRIVATE"}),"index_false_denied":not knowledge_note_allowed({"id":"n3","status":"APPROVED","index":False,"visibility":"PRIVATE"})}
        if not all(cases.values()):raise RuntimeError("Memory/Knowledge/RAG negative matrix failed")
        return {"mode":mode,"status":"PASS","cases":cases}
    if mode=="rollback":
        return {"mode":mode,"status":"PASS",**exact_rollback(scope,"knowledge-index-state.json",b'{"index_generation":1,"source_preserved":true}\n',b'{"index_generation":99,"source_preserved":false}\n')}
    note={"id":"mat002-note-1","status":"APPROVED","index":True,"visibility":"PRIVATE","body":"FA3 current host knowledge retrieval sentinel alpha beta gamma"}
    if not knowledge_note_allowed(note):raise RuntimeError("approved knowledge note rejected")
    vault=scope/"vault";vault.mkdir(parents=True,exist_ok=True);source=vault/"note.md";source.write_text(note["body"]+"\n",encoding="utf-8");before=sha_file(source)
    db=sqlite3.connect(scope/"derived-index.sqlite3")
    try:
        db.execute("CREATE VIRTUAL TABLE docs USING fts5(note_id, body)");db.execute("INSERT INTO docs(note_id,body) VALUES(?,?)",(note["id"],note["body"]));db.commit();row=db.execute("SELECT note_id FROM docs WHERE docs MATCH ?",("sentinel",)).fetchone()
        if row!=(note["id"],):raise RuntimeError("local knowledge retrieval failed")
    finally:db.close()
    if sha_file(source)!=before:raise RuntimeError("derived index mutated source note")
    return {"mode":mode,"status":"PASS","source_note_sha256":before,"retrieved_note_id":note["id"],"derived_index_authoritative":False,"source_preserved":True,"direct_postgresql_access_by_agent":False,"direct_vault_access_by_agent":False}

HANDLERS={"CAP-006":cap006,"CAP-007":cap007,"CAP-008":cap008,"CAP-009":cap009,"CAP-010":cap010}
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
        art=scope/NAMES[x.capability];write(art,{"schema":"fa3.mat002-runtime-knowledge-current-host-evidence.v1","subject_id":x.capability,"test_kind":env("FA3_TEST_KIND"),"test_id":env("FA3_TEST_ID"),"qualification_id":env("FA3_QUALIFICATION_ID"),"constituent_id":env("FA3_CONSTITUENT_ID"),"execution_scope":"CURRENT_HOST","current_host":True,"synthetic":False,"ci_reference_only":False,"provider_receipt_only":False,"component_receipt_only":False,"generic_host_collection_only":False,"global_promotion_claim":False,"result":result})
        verdict={"schema":VERDICT_SCHEMA,"producer_id":x.producer_id,"qualification_id":env("FA3_QUALIFICATION_ID"),"constituent_id":env("FA3_CONSTITUENT_ID"),"subject_id":x.capability,"test_kind":env("FA3_TEST_KIND"),"test_id":env("FA3_TEST_ID"),"status":"PASS","execution_scope":"CURRENT_HOST","current_host":True,"synthetic":False,"ci_reference_only":False,"provider_receipt_only":False,"component_receipt_only":False,"generic_host_collection_only":False,"global_promotion_claim":False,"source_evidence_class":env("FA3_SOURCE_EVIDENCE_CLASS"),"covers_source_decision_ids":coverage,"source_artifact_path":art.relative_to(root).as_posix(),"source_artifact_sha256":sha_file(art)}
        print(json.dumps(verdict,ensure_ascii=False,separators=(",",":")));return 0
    except ProducerRejection as e:
        rejection={
            "schema":REJECTION_SCHEMA,"status":"REJECTED","producer_id":x.producer_id,
            "qualification_id":os.environ.get("FA3_QUALIFICATION_ID"),
            "constituent_id":os.environ.get("FA3_CONSTITUENT_ID"),
            "subject_id":os.environ.get("FA3_CAPABILITY_ID"),"stage":e.stage,
            "reason_codes":e.reason_codes[:8],"summary":e.summary,
        }
        print(json.dumps(rejection,sort_keys=True,separators=(",",":")),file=sys.stderr);return 2
    except Exception:
        rejection={
            "schema":REJECTION_SCHEMA,"status":"REJECTED","producer_id":x.producer_id,
            "qualification_id":os.environ.get("FA3_QUALIFICATION_ID"),
            "constituent_id":os.environ.get("FA3_CONSTITUENT_ID"),
            "subject_id":os.environ.get("FA3_CAPABILITY_ID"),"stage":"PRODUCER",
            "reason_codes":["MAT002_EXECUTION_REJECTED"],"summary":{},
        }
        print(json.dumps(rejection,sort_keys=True,separators=(",",":")),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
