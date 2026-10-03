#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""FA3 product entitlement resolver and static portfolio validator."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

LEVELS=("MINIMAL","PERSONAL","PROFESSIONAL","STUDIO","BUSINESS","ENTERPRISE")
RANK={name:i for i,name in enumerate(LEVELS)}
FILES={
 "portfolio":"canonical/FA3-APPLICATION-PORTFOLIO-001.json",
 "levels":"canonical/FA3-OPERATING-LEVEL-MODEL-001.json",
 "packs":"canonical/FA3-DOMAIN-PACK-REGISTRY-001.json",
 "policy":"canonical/FA3-ENTITLEMENT-POLICY-001.json",
 "deps":"canonical/FA3-APPLICATION-DEPENDENCY-REGISTRY-001.json",
 "catalog":"canonical/FA3-PRODUCT-CATALOG-001.json",
}

def _read(root:Path, rel:str)->dict[str,Any]:
    value=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError("OBJECT_REQUIRED:"+rel)
    return value

def load(root:Path)->dict[str,dict[str,Any]]:
    return {key:_read(root,rel) for key,rel in FILES.items()}

def _findings(model:dict[str,dict[str,Any]], root:Path|None=None)->list[dict[str,str]]:
    f:list[dict[str,str]]=[]
    for key,obj in model.items():
        if obj.get("capability_count")!=175: f.append({"code":"CAPABILITY_BASELINE_DRIFT","detail":key})
        if obj.get("authority") is not False: f.append({"code":"PRODUCT_POLICY_AUTHORITY_FORBIDDEN","detail":key})
        if obj.get("capability_delta",0)!=0 or obj.get("authority_delta",0)!=0: f.append({"code":"BASELINE_OR_AUTHORITY_DELTA_FORBIDDEN","detail":key})
    level_rows=model["levels"].get("levels",[])
    if [x.get("level_id") for x in level_rows]!=list(LEVELS) or [x.get("rank") for x in level_rows]!=list(range(6)):
        f.append({"code":"OPERATING_LEVEL_ORDER_INVALID","detail":"expected six ordered levels"})
    apps=model["portfolio"].get("applications",[])
    ids=[x.get("application_id") for x in apps if isinstance(x,dict)]
    if len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not x for x in ids):
        f.append({"code":"APPLICATION_ID_INVALID_OR_DUPLICATE","detail":"portfolio"})
    appmap={x["application_id"]:x for x in apps if isinstance(x,dict) and isinstance(x.get("application_id"),str)}
    states=set(model["portfolio"].get("portfolio_states",[]))
    classes=set(model["portfolio"].get("application_classes",[]))
    for aid,row in appmap.items():
        minimum=row.get("minimum_operating_level"); supported=row.get("supported_operating_levels")
        if row.get("portfolio_state") not in states: f.append({"code":"INVALID_PORTFOLIO_STATE","detail":aid})
        if row.get("application_class") not in classes: f.append({"code":"INVALID_APPLICATION_CLASS","detail":aid})
        if minimum not in RANK or not isinstance(supported,list) or minimum not in supported:
            f.append({"code":"INVALID_OPERATING_LEVEL_BINDING","detail":aid}); continue
        if supported!=list(LEVELS[RANK[minimum]:]):
            f.append({"code":"SUPPORTED_LEVELS_MUST_BE_MONOTONIC_FROM_MINIMUM","detail":aid})
        if row.get("portfolio_state")=="RETIRED" and row.get("individually_entitleable") is True:
            f.append({"code":"RETIRED_APPLICATION_ENTITLEABLE","detail":aid})
        roots=row.get("repository_roots",[])
        if row.get("portfolio_state")=="PLANNED" and roots:
            f.append({"code":"PLANNED_APPLICATION_HAS_MATERIALIZED_ROOT","detail":aid})
    comps=model["deps"].get("platform_components",[])
    comp_ids={x.get("component_id") for x in comps if isinstance(x,dict)}
    for comp in comps:
        if comp.get("user_facing_application") is not False:
            f.append({"code":"TECHNICAL_DEPENDENCY_MAY_NOT_BE_USER_FACING_APPLICATION","detail":str(comp.get("component_id"))})
    dep_app_ids=set()
    for row in model["deps"].get("application_dependencies",[]):
        aid=row.get("application_id"); dep_app_ids.add(aid)
        if aid not in appmap: f.append({"code":"DEPENDENCY_UNKNOWN_APPLICATION","detail":str(aid)})
        for dep in row.get("required_platform_dependencies",[]):
            if dep not in comp_ids: f.append({"code":"UNKNOWN_PLATFORM_DEPENDENCY","detail":str(dep)})
            if dep in appmap: f.append({"code":"APPLICATION_AS_TECHNICAL_DEPENDENCY_FORBIDDEN","detail":str(dep)})
    for aid,row in appmap.items():
        if row.get("application_class")!="REFERENCE_ONLY_APPLICATION" and aid not in dep_app_ids:
            f.append({"code":"APPLICATION_DEPENDENCY_RECORD_MISSING","detail":aid})
    pack_ids=set()
    for pack in model["packs"].get("domain_packs",[]):
        pid=pack.get("pack_id")
        if pid in pack_ids or not isinstance(pid,str): f.append({"code":"DOMAIN_PACK_ID_INVALID_OR_DUPLICATE","detail":str(pid)})
        pack_ids.add(pid)
        for aid in pack.get("applications",[]):
            if aid not in appmap: f.append({"code":"DOMAIN_PACK_UNKNOWN_APPLICATION","detail":str(aid)})
            elif appmap[aid].get("individually_entitleable") is not True:
                f.append({"code":"DOMAIN_PACK_NON_ENTITLEABLE_APPLICATION","detail":aid})
    rules=model["packs"].get("rules",{})
    if rules.get("technical_dependency") is not False or rules.get("bundle_purchase_required_for_application") is not False or rules.get("individual_selection_alternative_required") is not True:
        f.append({"code":"BUNDLE_LOCK_IN_POLICY_INVALID","detail":"FA3-DOMAIN-PACK-REGISTRY-001"})
    principles=model["policy"].get("principles",{})
    required={"individual_application_selection":True,"higher_operating_level_auto_unlocks_unrelated_applications":False,"required_platform_dependency_grants_user_facing_application":False,"bundle_required_for_application":False,"silent_fallback":False}
    for key,val in required.items():
        if principles.get(key)!=val: f.append({"code":"ENTITLEMENT_INVARIANT_INVALID","detail":key})
    if model["policy"].get("lower_precedence_layer_may_widen") is not False:
        f.append({"code":"LOWER_POLICY_WIDENING_FORBIDDEN","detail":"precedence"})
    if root is not None:
        policy=model["portfolio"].get("filesystem_policy",{})
        ignored=set(policy.get("ignored_immediate_roots",[]))
        bound={}
        for aid,row in appmap.items():
            for rel in row.get("repository_roots",[]): bound[Path(rel).name]=aid
        apps_root=root/"apps"
        if apps_root.is_dir():
            for child in apps_root.iterdir():
                if not child.is_dir() or child.name in ignored: continue
                if child.name not in bound: f.append({"code":"UNCLASSIFIED_MATERIALIZED_APPLICATION_ROOT","detail":child.name})
        links_path=root/"canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
        if links_path.is_file():
            links=_read(root,"canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
            declared={x.get("application_id") for x in links.get("applications",[]) if isinstance(x,dict)}
            governed_classes={"INTERNAL_APPLICATION","SYSTEM_APPLICATION","COMPANION_APPLICATION"}
            for aid,row in appmap.items():
                if row.get("application_class") in governed_classes and row.get("portfolio_state")!="RETIRED" and aid not in declared:
                    f.append({"code":"APPLICATION_INVENTORY_DECLARATION_MISSING","detail":aid})
            for aid in declared:
                if aid not in appmap:
                    f.append({"code":"PORTFOLIO_RECORD_MISSING_FOR_DECLARED_APPLICATION","detail":str(aid)})
        family_path=root/"canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json"
        if family_path.is_file():
            family=_read(root,"canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json")
            valid={x.get("family_id") for x in family.get("product_families",[]) if isinstance(x,dict)}
            placements={x.get("application_id"):x for x in family.get("application_placements",[]) if isinstance(x,dict)}
            for aid,row in appmap.items():
                primary=row.get("primary_product_family")
                if primary not in valid: f.append({"code":"PRODUCT_FAMILY_UNKNOWN","detail":aid})
                placed=placements.get(aid)
                if placed is None:
                    f.append({"code":"PRODUCT_FAMILY_PLACEMENT_MISSING","detail":aid})
                elif placed.get("primary_family")!=primary or sorted(placed.get("secondary_families",[]))!=sorted(row.get("secondary_product_families",[])):
                    f.append({"code":"PRODUCT_FAMILY_PLACEMENT_DRIFT","detail":aid})
    return f

def validate(root:Path)->list[dict[str,str]]:
    return _findings(load(root),root)

def resolve(root:Path, selected:list[str], requested_level:str|None=None, features:list[str]|None=None, packs:list[str]|None=None)->dict[str,Any]:
    model=load(root); findings=_findings(model,root)
    if findings: return {"schema":"fa3.entitlement-resolution.v1","status":"BLOCKED_MODEL_INVALID","findings":findings}
    appmap={x["application_id"]:x for x in model["portfolio"]["applications"]}
    chosen:list[str]=[]; pack_ids=packs or []
    packmap={x["pack_id"]:x for x in model["packs"].get("domain_packs",[])}
    for pid in pack_ids:
        pack=packmap.get(pid)
        if not pack: return {"schema":"fa3.entitlement-resolution.v1","status":"REJECTED","reason":"UNKNOWN_DOMAIN_PACK","domain_pack":pid}
        for aid in pack.get("applications",[]):
            if aid not in chosen: chosen.append(aid)
    for aid in selected:
        if aid not in chosen: chosen.append(aid)
    required_rank=0; rejected=[]
    for aid in chosen:
        row=appmap.get(aid)
        if not row: rejected.append({"application_id":aid,"reason":"UNKNOWN_APPLICATION"}); continue
        if row.get("portfolio_state")=="RETIRED": rejected.append({"application_id":aid,"reason":"RETIRED_APPLICATION"}); continue
        if row.get("individually_entitleable") is not True: rejected.append({"application_id":aid,"reason":"NON_ENTITLEABLE_APPLICATION"}); continue
        required_rank=max(required_rank,RANK[row["minimum_operating_level"]])
    for feature in features or []:
        minimum=model["levels"].get("feature_minimums",{}).get(feature)
        if minimum is None: rejected.append({"feature":feature,"reason":"UNKNOWN_OPERATING_FEATURE"})
        else: required_rank=max(required_rank,RANK[minimum])
    if rejected: return {"schema":"fa3.entitlement-resolution.v1","status":"REJECTED","rejections":rejected}
    minimum_level=LEVELS[required_rank]
    effective=minimum_level
    if requested_level:
        if requested_level not in RANK: return {"schema":"fa3.entitlement-resolution.v1","status":"REJECTED","reason":"UNKNOWN_REQUESTED_LEVEL"}
        if RANK[requested_level]<required_rank: return {"schema":"fa3.entitlement-resolution.v1","status":"REJECTED","reason":"REQUESTED_LEVEL_BELOW_MINIMUM","minimum_required_operating_level":minimum_level}
        for aid in chosen:
            if requested_level not in appmap[aid]["supported_operating_levels"]:
                return {"schema":"fa3.entitlement-resolution.v1","status":"REJECTED","reason":"APPLICATION_DOES_NOT_SUPPORT_REQUESTED_LEVEL","application_id":aid}
        effective=requested_level
    depmap={x["application_id"]:x.get("required_platform_dependencies",[]) for x in model["deps"].get("application_dependencies",[])}
    components=sorted({d for aid in chosen for d in depmap.get(aid,[])})
    return {
      "schema":"fa3.entitlement-resolution.v1","status":"ENTITLEMENT_INTENT_READY",
      "selected_applications":chosen,"selected_domain_packs":pack_ids,
      "minimum_required_operating_level":minimum_level,"effective_operating_level":effective,
      "required_platform_dependencies":components,
      "technical_dependencies_grant_additional_application_entitlements":False,
      "bundle_required":False,"implicit_application_unlocks":[],
      "execution_requested":False,"runtime_authorization_granted":False,
      "authority_precedence":model["policy"].get("authority_precedence",[])
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--select",action="append",default=[])
    p.add_argument("--pack",action="append",default=[])
    p.add_argument("--feature",action="append",default=[])
    p.add_argument("--requested-level",choices=LEVELS)
    p.add_argument("--check",action="store_true")
    a=p.parse_args(); root=Path(a.root).resolve()
    if a.check:
        fs=validate(root); out={"schema":"fa3.product-entitlement-check.v1","result":"PASS" if not fs else "FAIL","findings":fs}
        print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if not fs else 2
    out=resolve(root,a.select,a.requested_level,a.feature,a.pack)
    print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out.get("status")=="ENTITLEMENT_INTENT_READY" else 2

if __name__=="__main__": raise SystemExit(main())
