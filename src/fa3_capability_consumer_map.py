#!/usr/bin/env python3
"""Derived FA3 donor -> capability -> consumer map. It is not an authority."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count
DONOR="canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"; LINKS="canonical/FA3-APPLICATION-DONOR-LINKS-001.json"; APP="canonical/FA3-AI-STUDIO-APP-CATALOG-001.json"; GUI="canonical/FA3-GUI-SURFACE-REGISTRY-001.json"
CONSUMER_KINDS={"APPLICATION","SHARED_MODULE","PROFILE","AUTHORITY","GUI_SURFACE","TEST_HARNESS","CURRENT_HOST_PATH"}; CH_STATES={"NO_RUNTIME_IMPACT","STRUCTURAL_REASSESSMENT_REQUIRED","RUNTIME_REQUALIFICATION_REQUIRED"}
def load(path:Path)->dict[str,Any]:
 v=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError("JSON object required: "+str(path))
 return v
def canonical_bindings(root:Path)->dict[str,list[str]]:
 out={}
 for path in (root/"canonical").rglob("*.json"):
  try: row=load(path)
  except Exception: continue
  rid=row.get("id"); b=row.get("capability_bindings")
  if isinstance(rid,str) and isinstance(b,list) and all(isinstance(x,str) and x.startswith("CAP-") for x in b): out[rid]=sorted(set(b))
 return out
def build_map(root:Path)->dict[str,Any]:
 root=root.resolve(); donors=load(root/DONOR); links=load(root/LINKS); apps=load(root/APP); gui=load(root/GUI)
 donor_ids={d.get("donor_id") for d in donors.get("entries",[]) if d.get("donor_id")}
 app_ids={"studio."+str(a["id"]) for a in apps.get("applications",[])}; app_ids.update(a.get("application_id") for a in links.get("applications",[]) if a.get("application_id"))
 gui_ids={s.get("route_id") for s in gui.get("surfaces",[]) if s.get("route_id")}; bindings=canonical_bindings(root); errors=[]; edges=[]; seen=set()
 for raw in links.get("donor_usage_records",[]):
  if not isinstance(raw,dict): errors.append({"code":"INVALID_USAGE_EDGE","detail":"non-object"}); continue
  uid=raw.get("id"); did=raw.get("donor_id"); aid=raw.get("application_id")
  if not uid or uid in seen or did not in donor_ids or aid not in app_ids: errors.append({"code":"INVALID_USAGE_EDGE","detail":str(uid)}); continue
  seen.add(uid); fb=raw.get("fa3_bindings") or {}
  if fb.get("capability_ids"): errors.append({"code":"MANUAL_CAPABILITY_BINDING_FORBIDDEN","detail":uid})
  refs=[]
  for key in ("profile_ids","contract_ids"):
   value=fb.get(key,[])
   if not isinstance(value,list) or any(not isinstance(x,str) for x in value): errors.append({"code":"INVALID_BINDING_REFERENCE","detail":uid+":"+key}); value=[]
   refs.extend(value)
  derived=sorted({cap for ref in refs for cap in bindings.get(ref,[])}); unresolved=sorted({ref for ref in refs if ref not in bindings})
  if raw.get("usage_kind")=="CAPABILITY_PATTERN" and not derived: errors.append({"code":"UNRESOLVED_CAPABILITY_BINDING","detail":uid})
  consumers=[{"kind":"APPLICATION","id":aid,"relationship":"PRIMARY_APPLICATION"}]; extra=raw.get("consumers",[])
  if not isinstance(extra,list): errors.append({"code":"INVALID_CONSUMERS","detail":uid}); extra=[]
  for c in extra:
   if not isinstance(c,dict) or c.get("kind") not in CONSUMER_KINDS or not isinstance(c.get("id"),str) or not c["id"]: errors.append({"code":"INVALID_CONSUMER","detail":uid}); continue
   if c["kind"]=="APPLICATION" and c["id"] not in app_ids: errors.append({"code":"UNKNOWN_APPLICATION_CONSUMER","detail":uid+":"+c["id"]}); continue
   if c["kind"]=="GUI_SURFACE" and c["id"] not in gui_ids: errors.append({"code":"UNKNOWN_GUI_CONSUMER","detail":uid+":"+c["id"]}); continue
   consumers.append({"kind":c["kind"],"id":c["id"],"relationship":c.get("relationship","INDIRECT_SHARED")})
  uniq={(c["kind"],c["id"],c["relationship"]):c for c in consumers}; ch=(raw.get("current_host_impact") or {}).get("classification","NO_RUNTIME_IMPACT")
  if ch not in CH_STATES: errors.append({"code":"INVALID_CURRENT_HOST_IMPACT","detail":uid}); ch="STRUCTURAL_REASSESSMENT_REQUIRED"
  edges.append({"id":uid,"donor_id":did,"donor_capability_key":raw.get("donor_capability_key"),"usage_kind":raw.get("usage_kind"),"status":raw.get("status"),"fa3_bindings":{"profile_ids":sorted(set(fb.get("profile_ids",[]))),"contract_ids":sorted(set(fb.get("contract_ids",[]))),"authority_ids":sorted(set(fb.get("authority_ids",[]))),"shared_module_ids":sorted(set(fb.get("shared_module_ids",[]))),"capability_ids":derived,"unresolved_binding_ids":unresolved,"resolution":"RESOLVED" if refs and not unresolved and derived else "UNRESOLVED_CAPABILITY_BINDING" if unresolved or (raw.get("usage_kind")=="CAPABILITY_PATTERN" and not derived) else "NOT_REQUIRED"},"consumers":sorted(uniq.values(),key=lambda x:(x["kind"],x["id"],x["relationship"])),"current_host_impact":{"classification":ch},"provenance":raw.get("provenance",{})})
 by_donor={}; by_cap={}; by_consumer={}
 for e in edges:
  by_donor.setdefault(e["donor_id"],[]).append(e["id"])
  for cap in e["fa3_bindings"]["capability_ids"]: by_cap.setdefault(cap,[]).append(e["id"])
  for c in e["consumers"]: by_consumer.setdefault(c["kind"]+":"+c["id"],[]).append(e["id"])
 return {"schema":"fa3.capability-consumer-map.v1","derived":True,"authority":False,"capability_count":module_active_capability_count(__file__),"new_capability":False,"new_architectural_authority":False,"source_records":[DONOR,LINKS,APP,GUI],"edges":sorted(edges,key=lambda x:x["id"]),"views":{"by_donor":{k:sorted(v) for k,v in sorted(by_donor.items())},"by_capability":{k:sorted(v) for k,v in sorted(by_cap.items())},"by_consumer":{k:sorted(v) for k,v in sorted(by_consumer.items())}},"validation":{"result":"PASS" if not errors else "FAIL","findings":errors}}
def main()->int:
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument("--check",action="store_true"); p.add_argument("--output",type=Path); p.add_argument("--donor"); p.add_argument("--capability"); p.add_argument("--consumer"); a=p.parse_args(); r=build_map(a.root)
 key=None
 if a.donor:key=("by_donor",a.donor)
 elif a.capability:key=("by_capability",a.capability)
 elif a.consumer:key=("by_consumer",a.consumer)
 if key:
  ids=set(r["views"][key[0]].get(key[1],[])); r={**r,"edges":[e for e in r["edges"] if e["id"] in ids]}
 if a.output:
  dst=a.output if a.output.is_absolute() else a.root/a.output; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(r,ensure_ascii=False,indent=2)); return 2 if a.check and r["validation"]["result"]!="PASS" else 0
if __name__=="__main__": raise SystemExit(main())
