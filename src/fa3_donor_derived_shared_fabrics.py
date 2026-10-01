#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

INTEGRATION="canonical/FA3-DONOR-DERIVED-SHARED-FABRICS-001.json"
ASSESSMENT="canonical/assessments/FA3-DONOR-DERIVED-SHARED-FABRICS-REUSE-ASSESSMENT-001.json"
DECISION="canonical/decisions/FA3-DEC-DONOR-DERIVED-SHARED-FABRICS-2026-10-01.json"
INTENT="canonical/intents/FA3-DONOR-DERIVED-SHARED-FABRICS-APPLICATION-INTENT-001.json"
IMPACT="canonical/FA3-DONOR-DERIVED-SHARED-FABRICS-CURRENT-HOST-IMPACT-001.json"
DONORS="canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
OPENHANDS_PROVIDER="canonical/providers/FA3-PROVIDER-OPENHANDS-001.json"
OPENHANDS_REF="canonical/references/FA3-OPENHANDS-UPSTREAM-REFERENCE-2026-09-01.json"

def load(path: Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(path)
    return value

def validate(root: Path)->dict[str,Any]:
    root=root.resolve(); findings=[]
    def fail(code,detail): findings.append({"code":code,"detail":detail})
    integration=load(root/INTEGRATION); assessment=load(root/ASSESSMENT); decision=load(root/DECISION)
    intent=load(root/INTENT); impact=load(root/IMPACT); donors=load(root/DONORS)
    if integration.get("id")!="FA3-DONOR-DERIVED-SHARED-FABRICS-001": fail("INTEGRATION_ID",str(integration.get("id")))
    for obj,label in ((integration,"integration"),(assessment,"assessment"),(impact,"impact")):
        baseline=obj.get("capability_baseline")
        if baseline is not None and baseline!=175: fail("CAPABILITY_BASELINE_DRIFT",f"{label}:{baseline}")
    if integration.get("new_capability") is not False or integration.get("new_architectural_authority") is not False:
        fail("AUTHORITY_OR_CAPABILITY_DELTA","integration")
    if integration.get("authority") is not False: fail("INTEGRATION_AUTHORITY_FORBIDDEN","authority")
    policy=integration.get("source_policy",{})
    for key in ("donor_registry_is_only_identity_authority","new_source_requires_literal_owner_donornak_marker","analysis_source_cannot_create_donor_usage_edge","analysis_source_cannot_authorize_code_import","analysis_source_cannot_authorize_runtime","discovery_is_not_admission"):
        if policy.get(key) is not True: fail("SOURCE_POLICY_MISSING",key)
    sources=integration.get("sources",[])
    seen=set(); locators=set(); existing=0
    for row in sources:
        sid=row.get("id"); loc=row.get("locator"); status=row.get("registration_status")
        if not isinstance(sid,str) or sid in seen: fail("SOURCE_ID_INVALID",str(sid))
        else: seen.add(sid)
        if not isinstance(loc,str) or not loc.startswith("https://") or loc in locators: fail("SOURCE_LOCATOR_INVALID",str(loc))
        else: locators.add(loc)
        if status=="EXISTING_CANONICAL_REFERENCE":
            existing+=1
            if loc!="https://github.com/OpenHands/software-agent-sdk": fail("UNEXPECTED_EXISTING_REFERENCE",loc)
        elif status!="OWNER_MARKER_REQUIRED": fail("SOURCE_STATUS_INVALID",f"{sid}:{status}")
        if "donor_id" in row: fail("FORGED_DONOR_ID",sid)
    if existing!=1: fail("EXISTING_REFERENCE_COUNT",str(existing))
    if len(sources)!=13: fail("SOURCE_COUNT",str(len(sources)))
    if donors.get("backfill",{}).get("entry_count")!=integration.get("donor_registry_entry_count"):
        fail("DONOR_REGISTRY_COUNT_DRIFT",f'{donors.get("backfill",{}).get("entry_count")}:{integration.get("donor_registry_entry_count")}')
    if assessment.get("donor_registry_blob_sha")!=integration.get("donor_registry_blob_sha"):
        fail("ASSESSMENT_REGISTRY_BINDING","blob")
    if assessment.get("adoption_authorized") is not False or assessment.get("code_import_authorized") is not False or assessment.get("runtime_admission_authorized") is not False:
        fail("UNAUTHORIZED_ADOPTION","assessment")
    if decision.get("status")!="OWNER_APPROVED_MATERIALIZATION": fail("OWNER_DECISION","status")
    if intent.get("declared_new_capabilities")!=[] or intent.get("proposed_authority_roles")!=[]: fail("INTENT_DELTA","intent")
    if impact.get("status")!="NO_RUNTIME_IMPACT" or impact.get("runtime_change") is not False or impact.get("physical_current_host_pass_claimed") is not False:
        fail("CURRENT_HOST_FALSE_PROMOTION","impact")
    provider=load(root/OPENHANDS_PROVIDER); ref=load(root/OPENHANDS_REF)
    if provider.get("id")!="FA3-PROVIDER-OPENHANDS-001" or ref.get("id")!="FA3-OPENHANDS-UPSTREAM-REFERENCE-2026-09-01":
        fail("OPENHANDS_EXISTING_REFERENCE_MISSING","OpenHands")
    components=integration.get("shared_compositions",[])
    if len(components)!=5: fail("COMPONENT_COUNT",str(len(components)))
    for row in components:
        pid=row.get("profile_id"); cid=row.get("contract_id")
        try: profile=load(root/"canonical/profiles"/f"{pid}.json")
        except Exception: fail("PROFILE_MISSING",str(pid)); continue
        try: contract=load(root/"canonical/contracts"/f"{cid}.json")
        except Exception: fail("CONTRACT_MISSING",str(cid)); continue
        for obj,label in ((profile,"profile"),(contract,"contract")):
            if obj.get("capability_count")!=175: fail("COMPONENT_CAPABILITY_COUNT",f"{pid}:{label}")
            if obj.get("new_capability") is not False or obj.get("new_architectural_authority") is not False: fail("COMPONENT_DELTA",f"{pid}:{label}")
            if obj.get("provider_neutral") is not True: fail("PROVIDER_NEUTRAL_REQUIRED",f"{pid}:{label}")
        pcaps=profile.get("capability_bindings",[]); ccaps=contract.get("capability_bindings",[])
        if pcaps!=ccaps: fail("CAPABILITY_BINDING_PARITY",pid)
        for cap in pcaps:
            if not isinstance(cap,str) or not cap.startswith("CAP-"): fail("CAPABILITY_ID",f"{pid}:{cap}"); continue
            try: n=int(cap.split("-",1)[1])
            except Exception: n=0
            if n<1 or n>175: fail("CAPABILITY_OUT_OF_BASELINE",f"{pid}:{cap}")
        runtime=profile.get("runtime_materialization",{})
        for key in ("new_service","new_daemon","new_port","new_socket","new_package_dependency","provider_activation","model_selection","hardware_mutation"):
            if runtime.get(key) is not False: fail("STATIC_RUNTIME_ACTIVATION",f"{pid}:{key}")
    if integration.get("license_boundaries",{}).get("no_third_party_source_copied") is not True:
        fail("LICENSE_BOUNDARY","source copied")
    return {"schema":"fa3.donor-derived-shared-fabrics-validation.v1","id":integration.get("id"),"sources":len(sources),"components":len(components),"capability_baseline":175,"validation":{"result":"PASS" if not findings else "FAIL","findings":findings}}

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--root",default="."); p.add_argument("--check",action="store_true"); p.add_argument("--summary",action="store_true"); a=p.parse_args()
    report=validate(Path(a.root)); print(json.dumps(report,indent=2,ensure_ascii=False))
    return 1 if a.check and report["validation"]["result"]!="PASS" else 0
if __name__=="__main__": raise SystemExit(main())
