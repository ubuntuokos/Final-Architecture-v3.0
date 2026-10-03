#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count
POLICY="canonical/FA3-UNIVERSAL-CAPABILITY-ACCESS-001.json"; GATE="canonical/FA3-GATE-UNIVERSAL-CAPABILITY-ACCESS-001.json"; AUDIT="canonical/universal-capability-access-audit-status.json"; REGISTRY="canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"; LINKS="canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
GATE_ID="FA3-GATE-UNIVERSAL-CAPABILITY-ACCESS-001"; GATESET_ID="FA3-SUPPLY-RUNTIME-HARDENING-GATESET-001"
CLASSES={"GLOBAL_DIRECT_REUSE","GLOBAL_CONDITIONAL_REUSE","RESTRICTED_REFERENCE","DISCOVERY_INDEX","UNVERIFIED_REFERENCE_ONLY"}; MATERIAL_KINDS={"CODE_REUSE","RUNTIME_DEPENDENCY"}; MATERIAL_FLAGS=("code_imported","runtime_dependency","provider_admission","model_admission")
RESTRICTED=("does not apply in","territory","territorial","noncommercial","non-commercial","research only","research-only","academic only","commercial use prohibited","geo-restricted","geographic restriction","jurisdiction restricted"); UNKNOWN=("unknown","unverified","review_required","review required","not observed","no root license"); DISCOVERY=("topic","organization","profile","collection","discovery")
def loadj(p:Path)->dict[str,Any]:
 r=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(r,dict): raise ValueError(str(p))
 return r
def f(code,msg,**kw): return {"code":code,"severity":"P0","message":msg,**kw}
def classify_donor(d):
 explicit=d.get("universal_access") or d.get("accessibility") or {}
 if isinstance(explicit,dict) and explicit.get("classification") in CLASSES: return explicit["classification"]
 lic=d.get("license") or {}; src=d.get("source") or {}; modes=[str(x).casefold() for x in d.get("donor_modes",[])]; kind=str(src.get("kind","")).casefold(); status=str(lic.get("status","")).casefold()
 if status=="collection_index" or "discovery_index" in modes or any(x in kind for x in DISCOVERY): return "DISCOVERY_INDEX"
 text=json.dumps({"license":lic,"notes":d.get("notes"),"source":src},sort_keys=True,ensure_ascii=False).casefold()
 if any(x in text for x in RESTRICTED): return "RESTRICTED_REFERENCE"
 declared=str(lic.get("declared","")).strip()
 if not lic or not declared or declared.casefold() in {"unknown","n/a","not_applicable","not applicable"} or any(x in text for x in UNKNOWN): return "UNVERIFIED_REFERENCE_ONLY"
 return "GLOBAL_CONDITIONAL_REUSE"
def is_material_usage(u): return u.get("usage_kind") in MATERIAL_KINDS or any(u.get(x) is True for x in MATERIAL_FLAGS)
def evaluate_usage(u,cls):
 if not is_material_usage(u): return []
 uid=str(u.get("id","UNKNOWN_USAGE")); ua=u.get("universal_access") or {}
 if cls=="DISCOVERY_INDEX": return [f("UCA-USE-001","discovery index cannot be a material dependency",usage_id=uid)]
 if cls=="UNVERIFIED_REFERENCE_ONLY": return [f("UCA-USE-002","unknown or unverified access rights block material adoption",usage_id=uid)]
 rights=ua.get("rights_evidence_refs",[]) if isinstance(ua,dict) else []; out=[]
 if cls=="RESTRICTED_REFERENCE":
  subs=ua.get("global_substitute_refs",[]) if isinstance(ua,dict) else []
  if ua.get("classification")!="OPTIONAL_RESTRICTED_WITH_GLOBAL_SUBSTITUTE": out.append(f("UCA-USE-003","restricted material usage missing required classification",usage_id=uid))
  if not isinstance(subs,list) or not subs: out.append(f("UCA-USE-004","restricted material usage missing global substitute references",usage_id=uid))
  if ua.get("restriction_circumvention_forbidden") is not True: out.append(f("UCA-USE-005","restriction circumvention must be forbidden",usage_id=uid))
  if not isinstance(rights,list) or not rights: out.append(f("UCA-USE-006","restricted material usage missing rights evidence",usage_id=uid))
  return out
 if cls in {"GLOBAL_DIRECT_REUSE","GLOBAL_CONDITIONAL_REUSE"}:
  if not isinstance(rights,list) or not rights: out.append(f("UCA-USE-007","material donor usage requires explicit rights evidence",usage_id=uid))
  return out
 return [f("UCA-USE-008","unsupported donor access class",usage_id=uid,donor_class=cls)]
def gate(root:Path):
 root=root.resolve(); findings=[]
 try: policy,gr,audit,reg,links=(loadj(root/x) for x in (POLICY,GATE,AUDIT,REGISTRY,LINKS))
 except Exception as e: return write(root,{"schema":"fa3.universal-capability-access-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,"result":"FAIL","blocking_findings":1,"findings":[f("UCA-000","required materialization unreadable",error=repr(e))]})
 count=module_active_capability_count(__file__)
 if count!=175: findings.append(f("UCA-001","capability baseline drift",observed=count))
 if policy.get("id")!="FA3-UNIVERSAL-CAPABILITY-ACCESS-POLICY-001" or policy.get("status")!="CANONICAL_FAIL_CLOSED": findings.append(f("UCA-002","policy drift"))
 if policy.get("capability_baseline")!=175 or policy.get("new_capability") is not False or policy.get("new_architectural_authority") is not False: findings.append(f("UCA-003","capability/authority drift"))
 b=policy.get("global_baseline",{})
 if b.get("cpu_only_path_required") is not True or b.get("accelerator_cardinality")!="0..N": findings.append(f("UCA-004","global hardware baseline drift"))
 if policy.get("restricted_material_usage",{}).get("restriction_circumvention_forbidden") is not True: findings.append(f("UCA-005","circumvention prohibition missing"))
 if gr.get("id")!=GATE_ID or gr.get("parent_gate_id")!="FA3-GATE-LICENSE-RIGHTS-001" or gr.get("gateset_id")!=GATESET_ID or gr.get("fail_closed") is not True: findings.append(f("UCA-006","gate binding drift"))
 if audit.get("scope")!="ALL_CURRENT_AND_FUTURE_DONOR_REFERENCE_RECORDS" or audit.get("full_record_classification_at_gate_runtime") is not True: findings.append(f("UCA-007","retroactive scope drift"))
 donors=reg.get("entries",[])
 if reg.get("id")!="FA3-DONOR-REFERENCE-REGISTRY-001" or reg.get("backfill",{}).get("entry_count")!=len(donors): findings.append(f("UCA-008","registry drift"))
 by={}; rows=[]; counts={x:0 for x in CLASSES}
 for d in donors:
  did=d.get("donor_id")
  if not isinstance(did,str) or not did: findings.append(f("UCA-009","donor without stable id")); continue
  if did in by: findings.append(f("UCA-010","duplicate donor id",donor_id=did)); continue
  cls=classify_donor(d); by[did]=cls; counts[cls]=counts.get(cls,0)+1; rows.append({"donor_id":did,"classification":cls})
 if len(rows)!=len(donors): findings.append(f("UCA-011","not every donor classified",registry_count=len(donors),classified=len(rows)))
 hw=links.get("hardware_audit",{})
 if hw.get("cpu_only_viable") is not True or hw.get("global_accelerator_requirement") is not False or hw.get("accelerator_cardinality")!="0..N": findings.append(f("UCA-012","application/donor hardware baseline drift"))
 material=0; restricted_material=0
 for u in links.get("donor_usage_records",[]):
  did=u.get("donor_id")
  if did not in by: findings.append(f("UCA-013","usage references missing donor",usage_id=u.get("id"),donor_id=did)); continue
  if is_material_usage(u):
   material+=1
   if by[did]=="RESTRICTED_REFERENCE": restricted_material+=1
  findings.extend(evaluate_usage(u,by[did]))
 digest=hashlib.sha256(json.dumps(sorted(rows,key=lambda x:x["donor_id"]),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
 return write(root,{"schema":"fa3.universal-capability-access-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,"result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"capability_count":count,"new_architectural_authorities":0,"registry_entry_count":len(donors),"audited_record_count":len(rows),"classification_counts":counts,"classification_sha256":digest,"material_usage_count":material,"restricted_material_usage_count":restricted_material,"restriction_circumvention":"FORBIDDEN","physical_current_host_pass_claimed":False})
def write(root,r):
 p=root/"reports/universal-capability-access-gate-report.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); return r
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); r=gate(Path(ap.parse_args().root)); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
