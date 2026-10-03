#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

from fa3_release_baseline import module_active_capability_count

ROOT = Path(__file__).resolve().parents[1]
CAP = module_active_capability_count(__file__)

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def gate():
    findings=[]
    mlt=load("canonical/profiles/FA3-MLT-EXTENDED-MEDIA-SERVICE-001.json")
    dh=load("canonical/profiles/FA3-DIGITAL-HUMAN-PROVIDER-FABRIC-001.json")
    mc=load("canonical/contracts/FA3-MLT-EXTENDED-MEDIA-SERVICE-CONTRACTS-001.json")
    dc=load("canonical/contracts/FA3-DIGITAL-HUMAN-PROVIDER-CONTRACTS-001.json")
    hp=load("canonical/providers/FA3-PROVIDER-HEYGEN-001.json")
    er=load("canonical/FA3-ENGINE-REGISTRY-001.json")
    ep=load("canonical/profiles/FA3-ENGINE-SELECTION-FABRIC-001.json")
    links=load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
    assess=load("canonical/assessments/FA3-MLT-HEYGEN-REUSE-ASSESSMENT-2026-10-03.json")
    enforce=load("canonical/mlt-heygen-enforcement.json")

    for name,row in (("mlt",mlt),("digital_human",dh),("mlt_contract",mc),("digital_contract",dc),("heygen",hp),("engine_registry",er),("engine_profile",ep),("enforcement",enforce)):
        if row.get("capability_count") != CAP:
            findings.append(f"{name}: capability baseline drift")

    by_engine={x["engine_id"]:x for x in er.get("engine_records",[])}
    for eid in ("FA3-ENGINE-MLT-001","FA3-ENGINE-HYPERFRAMES-001","FA3-ENGINE-HEYGEN-001","FA3-ENGINE-FA3-MEDIA-COMPOSITION-NATIVE-001"):
        if eid not in by_engine:
            findings.append(f"missing engine {eid}")
    if er.get("default_engine") is not None or er.get("default_fallback_mode") != "OFF":
        findings.append("engine selector default/fallback invariant drift")
    if by_engine.get("FA3-ENGINE-MLT-001",{}).get("permanent_parallel_option") is not True:
        findings.append("MLT permanent parallel option lost")
    if by_engine.get("FA3-ENGINE-HEYGEN-001",{}).get("health_state") in {"READY","AVAILABLE_CONDITIONAL"}:
        findings.append("HeyGen static projection became execution-ready")
    if hp.get("runtime_admission",{}).get("production_admitted") is not False:
        findings.append("HeyGen provider runtime admitted by static materialization")
    if hp.get("architectural_authority") is not False:
        findings.append("HeyGen provider became authority")
    if dc.get("provider_neutral") is not True or mc.get("provider_neutral") is not True:
        findings.append("provider-neutral contract invariant drift")
    if mc.get("hyperframes_boundary",{}).get("source_copy") is not False:
        findings.append("HyperFrames source-copy boundary drift")
    usage=next((x for x in links.get("donor_usage_records",[]) if x.get("id")=="FA3-USAGE-HYPERFRAMES-MLT-EXTENDED-MEDIA-001"),None)
    if not usage:
        findings.append("missing HyperFrames usage edge")
    else:
        if usage.get("donor_id")!="FA3-DONOR-HYPERFRAMES-001" or usage.get("usage_kind")!="ARCHITECTURE_PATTERN":
            findings.append("HyperFrames usage edge identity/type drift")
        if usage.get("code_imported") is not False or usage.get("runtime_dependency") is not False:
            findings.append("HyperFrames static pattern boundary drift")
    if assess.get("pending_or_unmerged_donors_consumed") is not False:
        findings.append("pending donor consumed")
    if assess.get("donor_planning_snapshot",{}).get("donor_registry_entry_count") != 1357:
        findings.append("planning snapshot donor count drift")
    if assess.get("new_capabilities") != 0 or assess.get("new_architectural_authorities") != 0:
        findings.append("capability/authority delta drift")
    if enforce.get("current_host_runtime_promotion_claim") is not False:
        findings.append("static materialization claimed Current Host promotion")
    return {"schema":"fa3.mlt-heygen-gate-report.v1","result":"PASS" if not findings else "FAIL","capability_count":CAP,"findings":findings}

if __name__=="__main__":
    report=gate()
    print(json.dumps(report,indent=2,sort_keys=True))
    raise SystemExit(0 if report["result"]=="PASS" else 1)
