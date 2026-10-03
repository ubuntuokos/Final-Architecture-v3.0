#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
L="canonical/FA3-OPERATING-LEVEL-MODEL-001.json";P="canonical/FA3-APPLICATION-PORTFOLIO-001.json";D="canonical/FA3-DOMAIN-PACK-REGISTRY-001.json";R="canonical/FA3-APPLICATION-DEPENDENCY-REGISTRY-001.json";C="canonical/FA3-PRODUCT-CATALOG-001.json";E="canonical/FA3-ENTITLEMENT-POLICY-001.json";A="canonical/FA3-APPLICATION-DONOR-LINKS-001.json";X="canonical/FA3-AI-STUDIO-APP-CATALOG-001.json";F="canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json"
def load(root,p): return json.loads((root/p).read_text(encoding="utf-8"))
def validate(root):
    lv,po,dm,dp,ca,ep,ad,xc,pf=[load(root,x) for x in (L,P,D,R,C,E,A,X,F)]; f=[]; order=lv.get("order",[]); rank={x:i for i,x in enumerate(order)}
    if order!=["MINIMAL","PERSONAL","PROFESSIONAL","STUDIO","BUSINESS","ENTERPRISE"]: f.append("OPERATING_LEVEL_ORDER_INVALID")
    if any(x.get("capability_count")!=175 for x in (lv,po,ep,pf)): f.append("CAPABILITY_BASELINE_NOT_175")
    states=set(po.get("portfolio_states",[])); classes=set(po.get("application_classes",[])); domains=set(dm.get("domains",[])); ids=set()
    families={x["family_id"] for x in pf.get("product_families",[])}; placements={x["application_id"]:x for x in pf.get("application_placements",[])}
    for a in po.get("applications",[]):
        aid=a.get("application_id")
        if not isinstance(aid,str) or not aid or aid in ids: f.append("DUPLICATE_OR_INVALID_APPLICATION_ID:"+str(aid))
        ids.add(aid)
        if a.get("portfolio_state") not in states: f.append("INVALID_PORTFOLIO_STATE:"+str(aid))
        if a.get("application_class") not in classes: f.append("INVALID_APPLICATION_CLASS:"+str(aid))
        m=a.get("minimum_operating_level")
        if m not in rank: f.append("INVALID_OPERATING_LEVEL:"+str(aid)); continue
        if a.get("supported_operating_levels")!=order[rank[m]:]: f.append("OPERATING_LEVEL_INHERITANCE_INVALID:"+str(aid))
        if a.get("primary_domain") not in domains: f.append("INVALID_DOMAIN:"+str(aid))
        if a.get("individually_entitleable") is not True: f.append("INDIVIDUAL_ENTITLEMENT_REQUIRED:"+str(aid))
        pl=placements.get(aid)
        if not pl: f.append("PRODUCT_FAMILY_PLACEMENT_MISSING:"+str(aid))
        elif a.get("primary_product_family")!=pl.get("primary_family") or pl.get("primary_family") not in families: f.append("PRODUCT_FAMILY_PLACEMENT_MISMATCH:"+str(aid))
    components=set(dp.get("platform_components",[]))
    for aid,req in dp.get("application_dependencies",{}).items():
        if aid not in ids: f.append("DEPENDENCY_APPLICATION_UNKNOWN:"+aid)
        for dep in req:
            if dep not in components: f.append("UNKNOWN_PLATFORM_DEPENDENCY:"+aid+":"+dep)
    for b in ca.get("bundles",[]):
        if b.get("optional") is not True: f.append("BUNDLE_NOT_OPTIONAL:"+str(b.get("id")))
        for aid in b.get("applications",[]):
            if aid not in ids: f.append("BUNDLE_APPLICATION_UNKNOWN:"+aid)
    for row in ad.get("applications",[]):
        if row.get("kind")=="INTERNAL_APPLICATION" and row.get("application_id") not in ids: f.append("APPLICATION_DONOR_INTERNAL_MISSING:"+str(row.get("application_id")))
    by={a["application_id"]:a for a in po.get("applications",[])}
    for row in xc.get("applications",[]):
        eid="studio."+str(row.get("id"))
        if eid not in ids: f.append("CURATED_EXTERNAL_APPLICATION_MISSING:"+eid)
        elif by[eid].get("fa3_entitlement_does_not_grant_upstream_rights") is not True: f.append("EXTERNAL_UPSTREAM_RIGHTS_BOUNDARY_MISSING:"+eid)
    if not ep.get("rules",{}).get("higher_operating_level_does_not_grant_apps"): f.append("TIER_APP_LOCKIN_POLICY_MISSING")
    if not ep.get("rules",{}).get("product_family_is_context_not_permission"): f.append("PRODUCT_FAMILY_PERMISSION_SEPARATION_MISSING")
    if not dp.get("rules",{}).get("platform_dependency_never_grants_application_entitlement"): f.append("DEPENDENCY_ENTITLEMENT_SEPARATION_MISSING")
    return sorted(set(f))
def resolve(root,apps,level=None):
    lv,po,dp=[load(root,x) for x in (L,P,R)];order=lv["order"];rank={x:i for i,x in enumerate(order)};by={a["application_id"]:a for a in po["applications"]};unknown=sorted(set(apps)-set(by))
    if unknown: raise ValueError("UNKNOWN_APPLICATION:"+",".join(unknown))
    req=max([rank[by[a]["minimum_operating_level"]] for a in apps] or [0])
    if level is not None:
        if level not in rank: raise ValueError("INVALID_OPERATING_LEVEL:"+level)
        if rank[level]<req: raise ValueError("APPLICATION_BELOW_MINIMUM_OPERATING_LEVEL")
        req=max(req,rank[level])
    components=set()
    for aid in apps: components.update(dp.get("application_dependencies",{}).get(aid,[]))
    return {"operating_level":order[req],"applications":apps,"platform_dependencies":sorted(components)}
def main():
    q=argparse.ArgumentParser();q.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));q.add_argument("--check",action="store_true");q.add_argument("--apps",nargs="*");q.add_argument("--level");a=q.parse_args();root=Path(a.root).resolve();f=validate(root)
    if f: print(json.dumps({"result":"FAIL","findings":f},indent=2));return 2
    if a.apps is not None:
        try:r=resolve(root,a.apps,a.level)
        except ValueError as e: print(json.dumps({"result":"DENY","finding":str(e)},indent=2));return 2
        print(json.dumps({"result":"PASS",**r},indent=2));return 0
    print(json.dumps({"result":"PASS","findings":[]},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
