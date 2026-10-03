#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse,json
from pathlib import Path
from fa3_application_portfolio import validate
from fa3_release_baseline import load_active_release_baseline
GATESET_ID="FA3-PRODUCT-ENTITLEMENT-GATESET-001";SUBGATES=["FA3-GATE-APPLICATION-PORTFOLIO-001","FA3-GATE-APPLICATION-PORTFOLIO-DRIFT-001","FA3-GATE-PRODUCT-ENTITLEMENT-001","FA3-GATE-OPERATING-LEVEL-DEPENDENCY-001"];GATE_FILES=["canonical/FA3-GATE-APPLICATION-PORTFOLIO-001.json","canonical/FA3-GATE-APPLICATION-PORTFOLIO-DRIFT-001.json","canonical/FA3-GATE-PRODUCT-ENTITLEMENT-001.json","canonical/FA3-GATE-OPERATING-LEVEL-DEPENDENCY-001.json"]
def load(root,rel):return json.loads((root/rel).read_text(encoding="utf-8"))
def gate(root):
 f=[];baseline=load_active_release_baseline(root).capability_count;pf=validate(root)
 if pf:f.append({"code":"PET-001","message":"portfolio validation failed","details":pf})
 for eid,rel in zip(SUBGATES,GATE_FILES):
  r=load(root,rel)
  if r.get("id")!=eid or r.get("fail_closed") is not True or r.get("capability_count")!=baseline or r.get("new_capability") is not False or r.get("new_architectural_authority") is not False or r.get("parent_gateset_id")!=GATESET_ID or r.get("runtime_promotion_claim") is not False:f.append({"code":"PET-002","message":"subgate contract invalid","path":rel})
 gr=load(root,"canonical/FA3-GATE-REGISTRY-001.json");pol=load(root,"canonical/enforcement-policy.json");gl=gr.get("mandatory_reference_gates",[]);pl=pol.get("mandatory_reference_gates",[])
 if gl!=pl or GATESET_ID not in gl:f.append({"code":"PET-003","message":"global mandatory gate binding or mirror missing"})
 cat=load(root,"canonical/FA3-PRODUCT-CATALOG-001.json")
 if {r.get("class") for r in cat.get("optional_addons",[])}!={"ENGINE","PROVIDER","CAPACITY","SUPPORT"}:f.append({"code":"PET-004","message":"optional addon model incomplete"})
 ent=load(root,"canonical/FA3-ENTITLEMENT-POLICY-001.json")
 if ent.get("authority") is not False or ent.get("rules",{}).get("silent_fallback") is not False:f.append({"code":"PET-005","message":"entitlement authority or fallback boundary invalid"})
 if ent.get("rules",{}).get("entitlement_may_restrict_but_never_override_authority") is not True:f.append({"code":"PET-006","message":"authority narrowing rule missing"})
 dep=load(root,"canonical/FA3-APPLICATION-DEPENDENCY-REGISTRY-001.json")
 if dep.get("rules",{}).get("runtime_dependency_is_not_application_entitlement") is not True:f.append({"code":"PET-007","message":"runtime dependency separation missing"})
 if dep.get("rules",{}).get("restricted_donor_may_not_be_sole_required_dependency") is not True:f.append({"code":"PET-008","message":"restricted donor sole dependency guard missing"})
 return {"gate_id":GATESET_ID,"result":"PASS" if not f else "FAIL","capability_count":baseline,"findings":f,"current_host_runtime_promotion_claim":False,"release_eligibility_claim":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));a=p.parse_args();r=gate(Path(a.root).resolve());print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
