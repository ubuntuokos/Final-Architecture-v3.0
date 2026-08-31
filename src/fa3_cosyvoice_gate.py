#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_cosyvoice_provider import (
    CAPS, MODEL_ID, MODEL_REVISION, PROVIDER_ID, PROFILE_ID, UPSTREAM_COMMIT,
    run_executable_conformance, sha256_file
)

GATE_ID="FA3-COSYVOICE-GATESET-001"

def _load(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def _write(p:Path,obj:dict[str,Any])->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def finding(code:str,message:str,**details:Any)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":message,**details}

def reference_check(root:Path)->dict[str,Any]:
    files={
        "profile":root/"canonical/profiles/FA3-VOICE-001.json",
        "contracts":root/"canonical/contracts/FA3-VOICE-CONTRACTS-001.json",
        "provider":root/"canonical/providers/FA3-PROVIDER-COSYVOICE-001.json",
        "decision":root/"canonical/decisions/FA3-DEC-COSYVOICE-2026-08-31.json",
        "allowlist":root/"canonical/FA3-COSYVOICE-MODEL-ALLOWLIST-001.json",
        "runtime":root/"canonical/FA3-COSYVOICE-RUNTIME-CONFORMANCE-001.json",
        "enforcement":root/"canonical/cosyvoice-enforcement.json",
        "reference":root/"canonical/references/FA3-COSYVOICE-UPSTREAM-REFERENCE-2026-08-31.json",
        "evidence":root/"evidence/reference/cosyvoice-ci-2026-08-31.json"
    }
    fs=[]
    for i,p in enumerate(files.values(),1):
        if not p.is_file():
            fs.append(finding(f"COSY-REF-{i:03d}",f"Missing CosyVoice artifact: {p.relative_to(root)}"))
    if fs:
        return {"result":"FAIL","findings":fs}
    o={k:_load(v) for k,v in files.items()}
    if o["profile"].get("id")!=PROFILE_ID or o["profile"].get("capability_count")!=CAPS:
        fs.append(finding("COSY-REF-020","Voice profile identity/capability invariant drift"))
    if o["provider"].get("id")!=PROVIDER_ID or any(o["provider"].get(k) is not False for k in ("canonical_root","architectural_authority","new_capability")):
        fs.append(finding("COSY-REF-021","CosyVoice provider authority/root invariant drift"))
    if o["decision"].get("new_capabilities")!=0 or o["decision"].get("new_architectural_authorities")!=0 or o["decision"].get("capability_count_after")!=CAPS:
        fs.append(finding("COSY-REF-022","CosyVoice decision changed capability/authority invariants"))
    if o["decision"].get("upstream_repository_commit")!=UPSTREAM_COMMIT or o["decision"].get("model_revision")!=MODEL_REVISION:
        fs.append(finding("COSY-REF-023","CosyVoice immutable source/model decision pin drift"))
    model=o["allowlist"].get("models",{}).get(MODEL_ID,{})
    if o["allowlist"].get("policy")!="ALLOWLIST_ONLY_FAIL_CLOSED" or model.get("revision")!=MODEL_REVISION:
        fs.append(finding("COSY-REF-024","CosyVoice model allowlist drift"))
    if "hu" not in model.get("experimental_languages",[]) or "hu" in model.get("official_languages",[]):
        fs.append(finding("COSY-REF-025","Hungarian experimental-language boundary drift"))
    if o["runtime"].get("current_host_status")!="PENDING_REAL_HOST_EXECUTION" or o["runtime"].get("production_promotion_claim") is not False:
        fs.append(finding("COSY-REF-026","Current-host runtime state claimed without real execution"))
    if o["enforcement"].get("gate_id")!=GATE_ID or o["enforcement"].get("mandatory_rule_count")!=21 or o["enforcement"].get("fail_closed") is not True:
        fs.append(finding("COSY-REF-027","CosyVoice enforcement identity/count/fail-closed drift"))
    if o["reference"].get("repository_commit")!=UPSTREAM_COMMIT or o["reference"].get("model",{}).get("revision")!=MODEL_REVISION or o["reference"].get("floating_main_allowed") is not False:
        fs.append(finding("COSY-REF-028","CosyVoice upstream reference pin drift"))
    if o["evidence"].get("result")!="PASS" or o["evidence"].get("current_host_production_claim") is not False:
        fs.append(finding("COSY-REF-029","CosyVoice CI evidence state drift"))
    return {"result":"PASS" if not fs else "FAIL","findings":fs}

def gate(root:Path)->dict[str,Any]:
    ref=reference_check(root)
    conf=run_executable_conformance(root)
    ok=ref["result"]=="PASS" and conf["result"]=="PASS"
    report={
        "schema":"fa3.cosyvoice-gate-report.v1",
        "gate_id":GATE_ID,
        "provider_id":PROVIDER_ID,
        "profile_id":PROFILE_ID,
        "capability_count":CAPS,
        "result":"PASS" if ok else "FAIL",
        "reference":ref,
        "conformance":conf,
        "current_host_production_status":"PENDING_REAL_HOST_EXECUTION",
        "current_host_production_claim":False,
        "hungarian_status":"EXPERIMENTAL_DEDICATED_QUALITY_EVIDENCE_REQUIRED",
        "promotion_effect":"MANDATORY_PROVIDER_INVARIANTS_WHEN_USED; OPTIONAL_PROVIDER_RUNTIME_NOT_GLOBAL_BLOCKER"
    }
    _write(root/"reports/cosyvoice-gate-report.json",report)
    return report

def current_host_gate(root:Path)->dict[str,Any]:
    receipt=root/"evidence/receipts/cosyvoice-current-host.json"
    fs=[]
    if not receipt.is_file():
        fs.append(finding("COSY-HOST-001","CosyVoice current-host receipt missing"))
    else:
        r=_load(receipt)
        if r.get("schema")!="fa3.cosyvoice-current-host-evidence.v1" or r.get("status")!="CURRENT_HOST_COSYVOICE_E2E_PASS":
            fs.append(finding("COSY-HOST-002","CosyVoice current-host receipt schema/status mismatch"))
        if r.get("provider_id")!=PROVIDER_ID or r.get("current_host") is not True or r.get("production_e2e") is not True:
            fs.append(finding("COSY-HOST-003","CosyVoice receipt identity/current-host/production flag mismatch"))
        audio=Path(str(r.get("output_audio_path","")))
        if not audio.is_file() or sha256_file(audio)!=r.get("output_audio_sha256"):
            fs.append(finding("COSY-HOST-004","CosyVoice output audio evidence missing/hash mismatch"))
        if r.get("sample_rate_hz")!=24000 or r.get("channels")!=1:
            fs.append(finding("COSY-HOST-005","CosyVoice current-host audio contract mismatch"))
        if not r.get("consent_provenance_ref"):
            fs.append(finding("COSY-HOST-006","CosyVoice consent provenance evidence missing"))
    out={"schema":"fa3.cosyvoice-current-host-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not fs else "FAIL","findings":fs}
    _write(root/"reports/cosyvoice-current-host-gate-report.json",out)
    return out

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--current-host",action="store_true")
    a=ap.parse_args()
    root=Path(a.root).resolve()
    r=current_host_gate(root) if a.current_host else gate(root)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0 if r["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
