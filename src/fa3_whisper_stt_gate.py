#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_whisper_stt_provider import (
    MODEL_ALLOWLIST_ID,
    PINNED_WHISPER_VERSION,
    PROVIDER_ID,
    PROVIDER_VERSION,
    run_executable_conformance,
)

GATE_ID="FA3-WHISPER-STT-GATESET-001"
PROFILE_ID="FA3-STT-MEDIA-001"
CAPS=143
REFERENCE_RELEASE="v20250625"
REFERENCE_COMMIT="31243bad24cc746f07d4c8bfdd2d974872cb1803"
SOURCE_BLOBS={
    "whisper/__init__.py":"f284ec0453b2c5efb025963f6a56a5dc404f78a7",
    "whisper/transcribe.py":"0a4cc3623991154263814409f20bd44e8c6ad394",
    "whisper/version.py":"67426aa1c9e68af9408a51fff224c3ac566634a4",
    "pyproject.toml":"21b90e737abc3fea0bf0270deb81e6e79e03e4d7",
}

def _load(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path:Path,obj:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _finding(code:str,message:str,**details:Any)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":message,**details}

def reference_check(root:Path)->dict[str,Any]:
    findings:list[dict[str,Any]]=[]
    paths={
        "decision":root/"canonical/decisions/FA3-DEC-WHISPER-STT-MATERIALIZATION-2026-08-30.json",
        "provider":root/"canonical/providers/FA3-PROVIDER-WHISPER-001.json",
        "allowlist":root/"canonical/FA3-WHISPER-MODEL-ALLOWLIST-001.json",
        "runtime":root/"canonical/FA3-WHISPER-STT-RUNTIME-CONFORMANCE-001.json",
        "enforcement":root/"canonical/whisper-stt-enforcement.json",
        "reference":root/"evidence/reference/whisper-v20250625.json",
        "profile":root/"canonical/profiles/FA3-STT-MEDIA-001.json",
    }
    for idx,p in enumerate(paths.values(),1):
        if not p.exists():
            findings.append(_finding(f"WHISPER-REF-{idx:03d}",f"Missing required Whisper STT artifact: {p.relative_to(root)}"))
    if findings:
        return {"result":"FAIL","findings":findings}

    decision=_load(paths["decision"])
    provider=_load(paths["provider"])
    allowlist=_load(paths["allowlist"])
    runtime=_load(paths["runtime"])
    enforcement=_load(paths["enforcement"])
    reference=_load(paths["reference"])
    profile=_load(paths["profile"])

    if decision.get("status")!="CANONICAL_CLOSED" or decision.get("decision")!="IMPLEMENT":
        findings.append(_finding("WHISPER-REF-010","Whisper STT materialization decision not closed IMPLEMENT"))
    if decision.get("new_capabilities")!=0 or decision.get("new_architectural_authorities")!=0 or decision.get("capability_count_after")!=CAPS:
        findings.append(_finding("WHISPER-REF-011","Whisper decision changed capability/authority invariant"))
    if provider.get("id")!=PROVIDER_ID or provider.get("capability_count")!=CAPS:
        findings.append(_finding("WHISPER-REF-012","Whisper provider identity/capability invariant mismatch"))
    if any(provider.get(k) is not False for k in ("canonical_root","architectural_authority","new_capability")):
        findings.append(_finding("WHISPER-REF-013","Whisper promoted to forbidden root/authority/capability"))
    if provider.get("model_allowlist")!=MODEL_ALLOWLIST_ID:
        findings.append(_finding("WHISPER-REF-014","Whisper provider model allowlist binding drift"))
    if provider.get("global_runtime_promotion_required_when_disabled") is not False:
        findings.append(_finding("WHISPER-REF-015","Optional Whisper runtime became global promotion dependency"))

    if allowlist.get("id")!=MODEL_ALLOWLIST_ID or allowlist.get("policy")!="ALLOWLIST_ONLY_FAIL_CLOSED":
        findings.append(_finding("WHISPER-REF-016","Whisper model allowlist identity/policy drift"))
    if allowlist.get("runtime_version")!=PINNED_WHISPER_VERSION:
        findings.append(_finding("WHISPER-REF-017","Whisper runtime version pin drift"))
    if allowlist.get("arbitrary_local_checkpoint_paths_allowed") is not False or allowlist.get("network_fetch_default") is not False:
        findings.append(_finding("WHISPER-REF-018","Whisper model trust surface widened"))
    models=allowlist.get("models",{})
    if "turbo" not in models or models["turbo"].get("production_role")!="PRIMARY_LOCAL_LONGFORM":
        findings.append(_finding("WHISPER-REF-019","Whisper turbo primary model binding drift"))

    if enforcement.get("gate_id")!=GATE_ID or enforcement.get("provider_id")!=PROVIDER_ID or enforcement.get("profile_id")!=PROFILE_ID:
        findings.append(_finding("WHISPER-REF-020","Whisper gate/provider/profile identity drift"))
    if enforcement.get("mandatory_rule_count")!=18 or len(enforcement.get("p0_invariants",[]))!=18:
        findings.append(_finding("WHISPER-REF-021","Whisper mandatory invariant count drift"))
    if enforcement.get("fail_closed") is not True or enforcement.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("WHISPER-REF-022","Whisper fail-closed/immutable-reference policy drift"))
    if enforcement.get("runtime_provider_required_for_global_promotion") is not False:
        findings.append(_finding("WHISPER-REF-023","Whisper runtime became mandatory while disabled"))

    if runtime.get("id")!="FA3-WHISPER-STT-RUNTIME-CONFORMANCE-001" or len(runtime.get("required_cases",[]))!=18:
        findings.append(_finding("WHISPER-REF-024","Whisper runtime conformance manifest drift"))
    if runtime.get("current_host_status")!="PENDING_REAL_HOST_EXECUTION":
        findings.append(_finding("WHISPER-REF-025","Whisper current-host state claimed without host execution"))

    stable=reference.get("stable_reference",{})
    if stable.get("release")!=REFERENCE_RELEASE or stable.get("commit_sha")!=REFERENCE_COMMIT or stable.get("runtime_version")!=PINNED_WHISPER_VERSION:
        findings.append(_finding("WHISPER-REF-026","Whisper immutable upstream reference drift"))
    if stable.get("source_blobs")!=SOURCE_BLOBS:
        findings.append(_finding("WHISPER-REF-027","Whisper upstream source blob drift"))
    if reference.get("floating_main_allowed") is not False:
        findings.append(_finding("WHISPER-REF-028","Whisper evidence permits floating main"))

    if profile.get("id")!=PROFILE_ID or profile.get("subprofile_of")!="FA3-STT-001":
        findings.append(_finding("WHISPER-REF-029","FA3-STT-MEDIA-001 profile identity drift"))
    production=profile.get("production_providers",[])
    if PROVIDER_ID not in production:
        findings.append(_finding("WHISPER-REF-030","Whisper provider not registered in FA3-STT-MEDIA-001 production provider projection"))

    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root:Path)->dict[str,Any]:
    ref=reference_check(root)
    conf=run_executable_conformance(root)
    ok=ref["result"]=="PASS" and conf["result"]=="PASS"
    report={
        "schema":"fa3.whisper-stt-gate-report.v1",
        "gate_id":GATE_ID,
        "provider_id":PROVIDER_ID,
        "provider_version":PROVIDER_VERSION,
        "profile_id":PROFILE_ID,
        "capability_count":CAPS,
        "result":"PASS" if ok else "FAIL",
        "reference":ref,
        "conformance":conf,
        "runtime_provider_required":False,
        "current_host_production_status":"PENDING_REAL_HOST_EXECUTION",
        "promotion_effect":"MANDATORY_PROVIDER_INVARIANTS_WHEN_USED_CURRENT_HOST_REQUIRED_FOR_PROVIDER_PRODUCTION_PROMOTION",
    }
    _write(root/"reports/whisper-stt-gate-report.json",report)
    _write(root/"reports/whisper-stt-conformance-report.json",conf)
    return report

def main()->int:
    ap=argparse.ArgumentParser(description="FA3 Whisper STT canonical + executable gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    result=gate(Path(args.root).resolve())
    print(json.dumps(result,indent=2))
    return 0 if result["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
