#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
from fa3_release_baseline import load_active_release_baseline
LEVELS="canonical/FA3-OPERATING-LEVEL-MODEL-001.json";PORTFOLIO="canonical/FA3-APPLICATION-PORTFOLIO-001.json";DOMAINS="canonical/FA3-DOMAIN-PACK-REGISTRY-001.json";DEPENDENCIES="canonical/FA3-APPLICATION-DEPENDENCY-REGISTRY-001.json";CATALOG="canonical/FA3-PRODUCT-CATALOG-001.json";ENTITLEMENT="canonical/FA3-ENTITLEMENT-POLICY-001.json";APP_DONOR="canonical/FA3-APPLICATION-DONOR-LINKS-001.json";APP_LIFECYCLE="canonical/FA3-APP-LIFECYCLE-001.json";EXTERNAL_CATALOG="canonical/FA3-AI-STUDIO-APP-CATALOG-001.json";PRODUCT_FAMILY="canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json";GUI="canonical/FA3-GUI-SURFACE-REGISTRY-001.json"
SCHEMAS={"canonical/schemas/FA3-APPLICATION-PORTFOLIO-SCHEMA-001.json":"FA3-APPLICATION-PORTFOLIO-001","canonical/schemas/FA3-OPERATING-LEVEL-MODEL-SCHEMA-001.json":"FA3-OPERATING-LEVEL-MODEL-001","canonical/schemas/FA3-PRODUCT-CATALOG-SCHEMA-001.json":"FA3-PRODUCT-CATALOG-001","canonical/schemas/FA3-DOMAIN-PACK-REGISTRY-SCHEMA-001.json":"FA3-DOMAIN-PACK-REGISTRY-001","canonical/schemas/FA3-ENTITLEMENT-POLICY-SCHEMA-001.json":"FA3-ENTITLEMENT-POLICY-001","canonical/schemas/FA3-APPLICATION-DEPENDENCY-REGISTRY-SCHEMA-001.json":"FA3-APPLICATION-DEPENDENCY-REGISTRY-001"}
EXPECTED_LEVELS=["MINIMAL","PERSONAL","PROFESSIONAL","STUDIO","BUSINESS","ENTERPRISE"];EXPECTED_ADDON_CLASSES={"ENGINE","PROVIDER","CAPACITY","SUPPORT"}
def load(root,rel):
 v=json.loads((root/rel).read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError("JSON_OBJECT_REQUIRED:"+rel)
 return v
def physical_application_ids(root):
 a=root/"apps";found=set()
 if not a.is_dir(): return found
 for p in a.iterdir():
  if not p.is_dir() or p.name=="shared": continue
  if p.name.startswith("fa3-"): found.add("fa3."+p.name[4:])
  elif p.name=="workload-mode": found.add("fa3.workload-mode")
 return found
def validate(root):
 lv,po,dm,dp,ca,ep,ad,pl,xc,pf,gui=[load(root,r) for r in (LEVELS,PORTFOLIO,DOMAINS,DEPENDENCIES,CATALOG,ENTITLEMENT,APP_DONOR,APP_LIFECYCLE,EXTERNAL_CATALOG,PRODUCT_FAMILY,GUI)]
 f=[];baseline=load_active_release_baseline(root).capability_count;order=lv.get("order",[])
 if order!=EXPECTED_LEVELS:f.append("OPERATING_LEVEL_ORDER_INVALID")
 rank={v:i for i,v in enumerate(order)}
 for rel,rec in {LEVELS:lv,PORTFOLIO:po,DOMAINS:dm,DEPENDENCIES:dp,CATALOG:ca,ENTITLEMENT:ep}.items():
  if rec.get("authority") is not False:f.append("AUTHORITY_BYPASS:"+rel)
  if rec.get("new_architectural_authority") not in (None,False):f.append("NEW_ARCHITECTURAL_AUTHORITY_FORBIDDEN:"+rel)
  if rec.get("new_capability") not in (None,False):f.append("NEW_CAPABILITY_FORBIDDEN:"+rel)
  if "capability_count" in rec and rec.get("capability_count")!=baseline:f.append("CAPABILITY_BASELINE_DRIFT:"+rel)
 for rel,eid in SCHEMAS.items():
  if load(root,rel).get("properties",{}).get("id",{}).get("const")!=eid:f.append("SCHEMA_ID_BINDING_INVALID:"+rel)
 operational=lv.get("operational_requirements",{})
 if not isinstance(operational,dict) or not operational:f.append("OPERATING_REQUIREMENTS_MISSING")
 else:
  for req,minimum in operational.items():
   if not isinstance(req,str) or not req or minimum not in rank:f.append("OPERATING_REQUIREMENT_LEVEL_INVALID:"+str(req))
 states=set(po.get("portfolio_states",[]));classes=set(po.get("application_classes",[]));domains=set(dm.get("domains",[]));families={r["family_id"] for r in pf.get("product_families",[])};placements={r["application_id"]:r for r in pf.get("application_placements",[])};surfaces={r.get("route_id") for r in gui.get("surfaces",[]) if r.get("route_id")};dmap=dp.get("application_dependencies",{});components=set(dp.get("platform_components",[]))
 if po.get("provisioning_lifecycle_ref")!=pl.get("id") or pl.get("id")!="FA3-APP-LIFECYCLE-001":f.append("PROVISIONING_LIFECYCLE_BINDING_INVALID")
 if states.intersection(set(pl.get("states",[]))):f.append("PORTFOLIO_AND_PROVISIONING_STATE_SPACES_MUST_REMAIN_SEPARATE")
 bm={};bids=set()
 for b in ca.get("bundles",[]):
  bid=b.get("id");bids.add(bid)
  if b.get("optional") is not True:f.append("BUNDLE_NOT_OPTIONAL:"+str(bid))
  for aid in b.get("applications",[]):bm.setdefault(aid,[]).append(bid)
 for p in dm.get("packs",[]):
  if p.get("optional") is not True or p.get("bundle_id") not in bids:f.append("DOMAIN_PACK_BINDING_INVALID:"+str(p.get("pack_id")))
 addons=ca.get("optional_addons",[]);ac={r.get("class") for r in addons if isinstance(r,dict)}
 if ac!=EXPECTED_ADDON_CLASSES or len(addons)!=4:f.append("OPTIONAL_ADDON_CLASSES_INVALID")
 for a in addons:
  if a.get("optional") is not True or a.get("authority") is not False or a.get("grants_application_entitlement") is not False or a.get("runtime_activation_grant") is not False or a.get("upstream_rights_grant") is not False:f.append("OPTIONAL_ADDON_BOUNDARY_INVALID:"+str(a.get("class")))
 ids=set();by={}
 for app in po.get("applications",[]):
  aid=app.get("application_id")
  if not isinstance(aid,str) or not aid or aid in ids:f.append("DUPLICATE_OR_INVALID_APPLICATION_ID:"+str(aid));continue
  ids.add(aid);by[aid]=app
  if aid in surfaces:f.append("GUI_SURFACE_AS_APPLICATION:"+aid)
  if app.get("portfolio_state") not in states:f.append("INVALID_PORTFOLIO_STATE:"+aid)
  if app.get("application_class") not in classes:f.append("INVALID_APPLICATION_CLASS:"+aid)
  minimum=app.get("minimum_operating_level")
  if minimum not in rank:f.append("INVALID_OPERATING_LEVEL_BINDING:"+aid)
  elif app.get("supported_operating_levels")!=order[rank[minimum]:]:f.append("SUPPORTED_LEVELS_MUST_BE_MONOTONIC_FROM_MINIMUM:"+aid)
  if app.get("primary_domain") not in domains:f.append("INVALID_DOMAIN:"+aid)
  if app.get("individually_entitleable") is not True:f.append("INDIVIDUAL_ENTITLEMENT_REQUIRED:"+aid)
  placement=placements.get(aid)
  if not placement:f.append("PRODUCT_FAMILY_PLACEMENT_MISSING:"+aid)
  elif app.get("primary_product_family")!=placement.get("primary_family") or placement.get("primary_family") not in families:f.append("PRODUCT_FAMILY_PLACEMENT_MISMATCH:"+aid)
  if aid not in dmap:f.append("MISSING_DEPENDENCY_DECLARATION:"+aid)
  else:
   required=dmap[aid]
   if not isinstance(required,list):f.append("INVALID_DEPENDENCY_DECLARATION:"+aid)
   else:
    for did in required:
     if did not in components:f.append("UNKNOWN_PLATFORM_DEPENDENCY:"+aid+":"+str(did))
    if sorted(app.get("required_platform_dependencies",[]))!=sorted(required):f.append("DEPENDENCY_PROJECTION_DRIFT:"+aid)
  if sorted(app.get("available_in_bundles",[]))!=sorted(bm.get(aid,[])):f.append("BUNDLE_MEMBERSHIP_DRIFT:"+aid)
  cls=app.get("application_class");state=app.get("portfolio_state");markers=app.get("implementation_markers",[])
  if cls in {"INTERNAL_APPLICATION","SYSTEM_APPLICATION","COMPANION_APPLICATION"} and state=="EXISTING":
   if not markers:f.append("EXISTING_IMPLEMENTATION_MARKER_REQUIRED:"+aid)
   for m in markers:
    if not (root/m).exists():f.append("IMPLEMENTATION_MARKER_MISSING:"+aid+":"+m)
  if cls in {"INTERNAL_APPLICATION","COMPANION_APPLICATION"} and state=="IN_PROGRESS" and not app.get("active_work_refs",[]):f.append("IN_PROGRESS_WORK_REF_REQUIRED:"+aid)
 for aid,required in dmap.items():
  if aid not in ids:f.append("DEPENDENCY_APPLICATION_UNKNOWN:"+aid)
  if isinstance(required,list):
   for did in required:
    if did in ids:f.append("APPLICATION_AS_TECHNICAL_DEPENDENCY_FORBIDDEN:"+aid+":"+did)
 for aid in bm:
  if aid not in ids:f.append("BUNDLE_APPLICATION_UNKNOWN:"+aid)
 for aid in physical_application_ids(root):
  if aid not in ids:f.append("ACTIVE_IMPLEMENTATION_WITHOUT_PORTFOLIO_RECORD:"+aid)
  elif by[aid].get("portfolio_state")!="EXISTING":f.append("PORTFOLIO_STATE_DRIFT:"+aid)
 declared={r.get("application_id"):r for r in ad.get("applications",[])}
 for app in po.get("applications",[]):
  aid=app["application_id"]
  if app.get("application_class") in {"INTERNAL_APPLICATION","COMPANION_APPLICATION"}:
   row=declared.get(aid)
   if not row:f.append("APPLICATION_DONOR_DECLARATION_MISSING:"+aid)
   elif row.get("lifecycle")!=app.get("portfolio_state"):f.append("APPLICATION_DONOR_PORTFOLIO_PROJECTION_DRIFT:"+aid)
 for aid,row in declared.items():
  if row.get("kind") in {"INTERNAL_APPLICATION","COMPANION_APPLICATION"} and row.get("lifecycle")!="REFERENCE_ONLY" and aid not in ids:f.append("APPLICATION_DECLARATION_WITHOUT_PORTFOLIO_RECORD:"+str(aid))
 for row in xc.get("applications",[]):
  aid="studio."+str(row.get("id"))
  if aid not in ids:f.append("CURATED_EXTERNAL_APPLICATION_MISSING:"+aid)
  elif by[aid].get("fa3_entitlement_does_not_grant_upstream_rights") is not True:f.append("EXTERNAL_UPSTREAM_RIGHTS_BOUNDARY_MISSING:"+aid)
 rules=ep.get("rules",{})
 for rule in ["higher_operating_level_does_not_grant_apps","product_family_is_context_not_permission","runtime_dependency_is_not_user_facing_entitlement","external_optional_application_entitlement_does_not_grant_upstream_rights","entitlement_may_restrict_but_never_override_authority","restricted_donor_may_not_be_sole_required_dependency"]:
  if rules.get(rule) is not True:f.append("ENTITLEMENT_POLICY_RULE_MISSING:"+rule)
 if rules.get("silent_fallback") is not False:f.append("SILENT_FALLBACK_FORBIDDEN")
 expected={"security":"FA3-AUTH-SECURITY-GOV-001","license_rights":"FA3-LICENSE-RIGHTS-001","host_resources":"FA3-AUTH-HOST-RESOURCE-BROKER-001","model_provider_routing":"FA3-AUTH-MODEL-ROUTER-001","engine_selection":"FA3-ENGINE-SELECTION-FABRIC-001","evidence":"FA3-AUTH-OBS-EVIDENCE-001"}
 if ep.get("authority_boundaries")!=expected:f.append("ENTITLEMENT_AUTHORITY_BOUNDARY_DRIFT")
 dr=dp.get("rules",{})
 for rule in ["platform_dependency_never_grants_application_entitlement","runtime_dependency_is_not_application_entitlement","application_entitlement_is_never_technical_dependency","restricted_donor_may_not_be_sole_required_dependency","external_optional_application_is_not_platform_dependency"]:
  if dr.get(rule) is not True:f.append("DEPENDENCY_ENTITLEMENT_SEPARATION_MISSING:"+rule)
 return sorted(set(f))
def resolve(root,application_ids,requested_level=None,operational_requirements=None):
 lv,po,dp=[load(root,r) for r in (LEVELS,PORTFOLIO,DEPENDENCIES)];order=lv["order"];rank={v:i for i,v in enumerate(order)};by={a["application_id"]:a for a in po["applications"]}
 unknown=sorted(set(application_ids)-set(by))
 if unknown:raise ValueError("UNKNOWN_APPLICATION:"+",".join(unknown))
 dmap=dp.get("application_dependencies",{});missing=sorted(set(application_ids)-set(dmap))
 if missing:raise ValueError("MISSING_DEPENDENCY_DECLARATION:"+",".join(missing))
 rr=max([rank[by[a]["minimum_operating_level"]] for a in application_ids] or [0]);reqs=operational_requirements or [];rmap=lv.get("operational_requirements",{});ur=sorted(set(reqs)-set(rmap))
 if ur:raise ValueError("UNKNOWN_OPERATIONAL_REQUIREMENT:"+",".join(ur))
 for req in reqs:rr=max(rr,rank[rmap[req]])
 if requested_level is not None:
  if requested_level not in rank:raise ValueError("INVALID_OPERATING_LEVEL:"+requested_level)
  if rank[requested_level]<rr:raise ValueError("APPLICATION_BELOW_MINIMUM_OPERATING_LEVEL")
  rr=max(rr,rank[requested_level])
 comps=set()
 for aid in application_ids:comps.update(dmap[aid])
 return {"operating_level":order[rr],"applications":application_ids,"operational_requirements":reqs,"platform_dependencies":sorted(comps)}
def reconcile_records(previous,current):
 prev={r["application_id"]:r for r in previous.get("applications",[])};cur={r["application_id"]:r for r in current.get("applications",[])};events=[]
 for aid in sorted(cur):
  if aid not in prev:events.append({"application_id":aid,"change":"ADDED","to":cur[aid].get("portfolio_state")})
  elif prev[aid].get("portfolio_state")!=cur[aid].get("portfolio_state"):events.append({"application_id":aid,"change":"PORTFOLIO_STATE_CHANGED","from":prev[aid].get("portfolio_state"),"to":cur[aid].get("portfolio_state")})
 for aid in sorted(set(prev)-set(cur)):events.append({"application_id":aid,"change":"REMOVED","from":prev[aid].get("portfolio_state"),"to":None})
 return events
def reconcile_from_git(root,base_ref):
 verify=subprocess.run(["git","-C",str(root),"rev-parse","--verify",base_ref+"^{commit}"],text=True,capture_output=True)
 if verify.returncode!=0:raise ValueError("UNKNOWN_RECONCILE_BASE:"+base_ref)
 show=subprocess.run(["git","-C",str(root),"show",base_ref+":"+PORTFOLIO],text=True,capture_output=True);current=load(root,PORTFOLIO)
 if show.returncode==0:
  try:previous=json.loads(show.stdout)
  except json.JSONDecodeError as e:raise ValueError("BASE_PORTFOLIO_INVALID_JSON") from e
  mode="INCREMENTAL"
 else:previous={"applications":[]};mode="BOOTSTRAP"
 events=reconcile_records(previous,current);findings=["PORTFOLIO_RECORD_REMOVED_USE_RETIRED:"+e["application_id"] for e in events if e["change"]=="REMOVED"]
 return {"mode":mode,"base_ref":base_ref,"events":events,"findings":findings}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));p.add_argument("--check",action="store_true");p.add_argument("--apps",nargs="*");p.add_argument("--level");p.add_argument("--requirement",action="append",default=[]);p.add_argument("--reconcile-from");a=p.parse_args();root=Path(a.root).resolve();findings=validate(root)
 if findings:print(json.dumps({"result":"FAIL","findings":findings},indent=2));return 2
 if a.reconcile_from:
  try:r=reconcile_from_git(root,a.reconcile_from)
  except ValueError as e:print(json.dumps({"result":"FAIL","finding":str(e)},indent=2));return 2
  if r["findings"]:print(json.dumps({"result":"FAIL",**r},indent=2));return 2
  print(json.dumps({"result":"PASS",**r},indent=2));return 0
 if a.apps is not None:
  try:r=resolve(root,a.apps,a.level,a.requirement)
  except ValueError as e:print(json.dumps({"result":"DENY","finding":str(e)},indent=2));return 2
  print(json.dumps({"result":"PASS",**r},indent=2));return 0
 print(json.dumps({"result":"PASS","findings":[]},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
