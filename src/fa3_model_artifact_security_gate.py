#!/usr/bin/env python3
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

GATE_ID = "FA3-GATE-MODEL-ARTIFACT-SECURITY-001"
PROFILE_ID = "FA3-MODEL-ARTIFACT-SECURITY-001"
CONTRACT_ID = "FA3-MODEL-ARTIFACT-SECURITY-CONTRACTS-001"
PROVIDER_ID = "FA3-PROVIDER-MODEL-ARTIFACT-SECURITY-STACK-001"
DECISION_ID = "FA3-DEC-MODEL-ARTIFACT-SECURITY-2026-09-07"
MODEL_MANAGER_ID = "FA3-MODEL-MANAGER-001"
AISEC_ID = "FA3-AI-SEC-VALIDATION-001"
CAPABILITY_COUNT = 143
EVIDENCE_PATH = "evidence/reference/model-artifact-security-ci-2026-09-07.json"
DANGEROUS_EXTENSIONS = {".pkl", ".pickle", ".pt", ".pth", ".bin", ".ckpt"}
RULES = [
"MODEL_SECURITY_ADMISSION_REQUIRED_FOR_ALL_ACQUISITION_IMPORT_PROMOTION",
"MODEL_DOWNLOAD_LANDS_IN_QUARANTINE",
"IMMUTABLE_SOURCE_REVISION_AND_SHA256_REQUIRED",
"SAFE_FORMAT_PREFERENCE_DOES_NOT_CONFER_TRUST",
"REMOTE_CODE_DENY_BY_DEFAULT_EXPLICIT_EXCEPTION_ONLY",
"MODELAUDIT_PRIMARY_STATIC_SCAN_REQUIRED",
"CLAMAV_AND_YARA_BASELINE_SCAN_REQUIRED",
"REPOSITORY_SURFACE_TRIVY_REQUIRED_WHEN_PRESENT",
"PYTHON_CODE_BANDIT_REQUIRED_WHEN_PRESENT",
"PYTHON_DEPENDENCY_PIP_AUDIT_REQUIRED_WHEN_PRESENT",
"DANGEROUS_SERIALIZATION_REQUIRES_MODELSCAN_PICKLESCAN_FICKLING",
"SCANNER_ERROR_INCOMPLETE_UNSUPPORTED_SKIPPED_FAILS_CLOSED",
"APPLICABLE_SCANNER_MISSING_FAILS_CLOSED",
"NOT_APPLICABLE_REQUIRES_TYPED_POLICY_REASON",
"SCANNER_PASS_IS_EVIDENCE_NOT_PROMOTION_AUTHORITY",
"SCANNER_AND_RULESET_IDENTITY_VERSION_DIGEST_REQUIRED",
"SECURITY_SCAN_NETWORK_EGRESS_DENIED",
"MODELAUDIT_TELEMETRY_DISABLED",
"ISOLATED_FIRST_LOAD_REQUIRED",
"ISOLATED_FIRST_LOAD_NO_SECRETS_NO_NETWORK_UNPRIVILEGED",
"GARAK_REQUIRED_FOR_SUPPORTED_GENERATIVE_LLM_BEHAVIOR_GATE",
"BEHAVIOR_NOT_APPLICABLE_REQUIRES_TYPED_REASON",
"COSIGN_SIGNATURE_VERIFICATION_REQUIRED_WHEN_ATTESTATION_PRESENT",
"UNRESOLVED_CRITICAL_SECURITY_FINDING_BLOCKS_PROMOTION",
"SECURITY_EVIDENCE_ATTESTATION_REQUIRED_BEFORE_MODEL_MANAGER_PROMOTION",
"SCANNER_STACK_NOT_SECURITY_OR_PROMOTION_AUTHORITY",
"NO_NEW_CAPABILITY_OR_ARCHITECTURAL_AUTHORITY",
"CURRENT_HOST_TOOLCHAIN_PASS_NOT_DOCUMENT_DERIVED",
"RUNTIME_PROVIDER_DOWNLOAD_BYPASS_FORBIDDEN",
]
ALWAYS = {"modelaudit", "clamav", "yara"}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _sha256(v: Any) -> bool:
    return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None

def _floating_revision(v: Any) -> bool:
    return not isinstance(v, str) or not v or v.lower() in {"main", "master", "latest", "head"}

def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}

def _scanner_map(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["scanner_id"]: r for r in receipt.get("scanners", []) if isinstance(r, dict) and isinstance(r.get("scanner_id"), str)}

def _scanner_identity_valid(row: dict[str, Any]) -> bool:
    return bool(row.get("version") and _sha256(row.get("binary_or_package_digest")) and row.get("ruleset_id") and _sha256(row.get("ruleset_digest")) and _sha256(row.get("target_sha256")))

def _scanner_pass(row: dict[str, Any]) -> bool:
    return bool(row.get("applicability") == "APPLICABLE" and row.get("status") == "PASS" and row.get("network_egress") is False and _scanner_identity_valid(row))

def _typed_na(row: dict[str, Any]) -> bool:
    return bool(row.get("applicability") == "NOT_APPLICABLE" and row.get("status") == "NOT_APPLICABLE" and isinstance(row.get("policy_reason"), str) and row.get("policy_reason").startswith("FA3-POLICY:") and row.get("network_egress") is False and _scanner_identity_valid(row))

def _required_scanners(receipt: dict[str, Any]) -> set[str]:
    required = set(ALWAYS)
    surface, artifact, model = receipt.get("surface", {}), receipt.get("artifact", {}), receipt.get("model", {})
    if surface.get("repository_surface") is True: required.add("trivy")
    if surface.get("python_code") is True: required.add("bandit")
    if surface.get("python_dependency_manifest") is True: required.add("pip-audit")
    if artifact.get("dangerous_serialization") is True or str(artifact.get("extension", "")).lower() in DANGEROUS_EXTENSIONS:
        required |= {"modelscan", "picklescan", "fickling"}
    if model.get("class") in {"LLM", "CHAT", "TEXT_GENERATION", "AGENTIC_TEXT_MODEL"}: required.add("garak")
    if receipt.get("source", {}).get("upstream_signature_or_attestation_present") is True: required.add("cosign")
    return required

def remote_code_valid(receipt: dict[str, Any]) -> bool:
    rc = receipt.get("remote_code", {})
    if rc.get("enabled") is not True:
        return rc.get("enabled") is False
    exc = rc.get("exception", {})
    return bool(exc.get("policy_authority") == "FA3-AUTH-SECURITY-GOV-001" and exc.get("policy_decision_id") and not _floating_revision(exc.get("immutable_code_revision")) and _sha256(exc.get("code_sha256")) and exc.get("static_code_security_evidence") is True and exc.get("network_denied_isolated_first_load") is True)

def isolated_first_load_valid(receipt: dict[str, Any]) -> bool:
    x = receipt.get("isolated_first_load", {})
    return bool(x.get("status") == "PASS" and x.get("unprivileged") is True and x.get("network_egress") is False and x.get("secret_access") is False and x.get("host_socket_access") is False and x.get("read_only_model_input") is True)

def behavior_valid(receipt: dict[str, Any]) -> bool:
    x, cls = receipt.get("behavior_security", {}), receipt.get("model", {}).get("class")
    if cls in {"LLM", "CHAT", "TEXT_GENERATION", "AGENTIC_TEXT_MODEL"}:
        return bool(x.get("applicability") == "APPLICABLE" and x.get("status") == "PASS" and x.get("scanner_id") == "garak")
    return bool(x.get("applicability") == "NOT_APPLICABLE" and x.get("status") == "NOT_APPLICABLE" and isinstance(x.get("policy_reason"), str) and x.get("policy_reason").startswith("FA3-POLICY:"))

def admission_valid(receipt: dict[str, Any]) -> bool:
    source, artifact = receipt.get("source", {}), receipt.get("artifact", {})
    quarantine, execution = receipt.get("quarantine", {}), receipt.get("scan_execution", {})
    promotion, att = receipt.get("promotion", {}), receipt.get("security_attestation", {})
    scanners = _scanner_map(receipt)
    if _floating_revision(source.get("immutable_revision")) or not _sha256(artifact.get("sha256")): return False
    if quarantine.get("state") != "QUARANTINED_UNTRUSTED" or quarantine.get("promoted_store_visible") is not False: return False
    if artifact.get("format_classified") is not True: return False
    if artifact.get("format") == "safetensors" and artifact.get("trusted_because_safe_format") is True: return False
    if not remote_code_valid(receipt): return False
    if execution.get("network_egress") is not False or execution.get("telemetry") is not False: return False
    required = _required_scanners(receipt)
    if not required.issubset(scanners): return False
    for sid in required:
        if not _scanner_pass(scanners[sid]): return False
    for row in scanners.values():
        if row.get("status") in {"ERROR", "INCOMPLETE", "SKIPPED", "UNSUPPORTED"} and row.get("applicability") != "NOT_APPLICABLE": return False
        if row.get("applicability") == "NOT_APPLICABLE" and not _typed_na(row): return False
        if row.get("applicability") == "APPLICABLE" and not _scanner_pass(row): return False
    if not isolated_first_load_valid(receipt) or not behavior_valid(receipt): return False
    if int(receipt.get("findings", {}).get("unresolved_critical", -1)) != 0: return False
    if not (att.get("status") == "PASS" and att.get("scanner_output_is_authority") is False and att.get("security_policy_authority") == "FA3-AUTH-SECURITY-GOV-001" and att.get("evidence_authority") == "FA3-AUTH-OBS-EVIDENCE-001" and isinstance(att.get("evidence_ids"), list) and att.get("evidence_ids")): return False
    return bool(promotion.get("security_state") == "SECURITY_ADMITTED" and promotion.get("model_manager_promotion_eligible") is True and promotion.get("policy_decision_id") and promotion.get("security_attestation_id") and promotion.get("direct_runtime_store_download_bypass") is False)

def _base_receipt(model_class: str = "DIFFUSION", dangerous: bool = False) -> dict[str, Any]:
    target = "a" * 64
    r = {
        "schema":"fa3.model-artifact-security-receipt.v1",
        "source":{"immutable_revision":"0123456789abcdef","upstream_signature_or_attestation_present":False},
        "artifact":{"sha256":target,"extension":".ckpt" if dangerous else ".safetensors","format":"pickle" if dangerous else "safetensors","format_classified":True,"dangerous_serialization":dangerous,"trusted_because_safe_format":False},
        "quarantine":{"state":"QUARANTINED_UNTRUSTED","promoted_store_visible":False},
        "surface":{"repository_surface":True,"python_code":True,"python_dependency_manifest":True},
        "model":{"class":model_class},"remote_code":{"enabled":False},
        "scan_execution":{"network_egress":False,"telemetry":False},"scanners":[],
        "isolated_first_load":{"status":"PASS","unprivileged":True,"network_egress":False,"secret_access":False,"host_socket_access":False,"read_only_model_input":True},
        "behavior_security":{"applicability":"APPLICABLE" if model_class in {"LLM","CHAT","TEXT_GENERATION","AGENTIC_TEXT_MODEL"} else "NOT_APPLICABLE","status":"PASS" if model_class in {"LLM","CHAT","TEXT_GENERATION","AGENTIC_TEXT_MODEL"} else "NOT_APPLICABLE","scanner_id":"garak" if model_class in {"LLM","CHAT","TEXT_GENERATION","AGENTIC_TEXT_MODEL"} else None,"policy_reason":None if model_class in {"LLM","CHAT","TEXT_GENERATION","AGENTIC_TEXT_MODEL"} else "FA3-POLICY:BEHAVIOR_SCANNER_NOT_APPLICABLE_TO_MODEL_CLASS"},
        "findings":{"unresolved_critical":0},
        "security_attestation":{"status":"PASS","scanner_output_is_authority":False,"security_policy_authority":"FA3-AUTH-SECURITY-GOV-001","evidence_authority":"FA3-AUTH-OBS-EVIDENCE-001","evidence_ids":["EVID-MODEL-SEC-1"]},
        "promotion":{"security_state":"SECURITY_ADMITTED","model_manager_promotion_eligible":True,"policy_decision_id":"POLICY-1","security_attestation_id":"ATTEST-1","direct_runtime_store_download_bypass":False}}
    all_ids={"modelaudit","clamav","yara","trivy","bandit","pip-audit","modelscan","picklescan","fickling","garak","cosign"}
    required=_required_scanners(r)
    for sid in sorted(all_ids):
        applicable=sid in required
        r["scanners"].append({"scanner_id":sid,"version":"pinned-test-version","binary_or_package_digest":hashlib.sha256((sid+"-binary").encode()).hexdigest(),"ruleset_id":sid+":rules","ruleset_digest":hashlib.sha256((sid+"-rules").encode()).hexdigest(),"target_sha256":target,"applicability":"APPLICABLE" if applicable else "NOT_APPLICABLE","status":"PASS" if applicable else "NOT_APPLICABLE","policy_reason":None if applicable else "FA3-POLICY:SCANNER_NOT_APPLICABLE_TO_DISCOVERED_SURFACE","network_egress":False})
    return r

def current_host_receipt_valid(receipt: dict[str, Any]) -> bool:
    return bool(receipt.get("evidence_level") == "CURRENT_HOST_PRODUCTION_E2E_PASS" and receipt.get("synthetic_scanner") is False and receipt.get("synthetic_target") is False and receipt.get("real_tool_execution") is True and receipt.get("runtime_promotion_eligible") is True)

def run_regressions() -> dict[str, Any]:
    base, pickle_llm = _base_receipt(), _base_receipt("LLM", dangerous=True)
    def bad(mutator):
        x=copy.deepcopy(base); mutator(x); return not admission_valid(x)
    signed=copy.deepcopy(base); signed["source"]["upstream_signature_or_attestation_present"]=True; next(s for s in signed["scanners"] if s["scanner_id"]=="cosign").update(applicability="APPLICABLE",status="PASS",policy_reason=None)
    no_pickle=copy.deepcopy(pickle_llm); no_pickle["scanners"]=[s for s in no_pickle["scanners"] if s["scanner_id"]!="picklescan"]
    no_yara=copy.deepcopy(base); no_yara["scanners"]=[s for s in no_yara["scanners"] if s["scanner_id"]!="yara"]
    no_cosign=copy.deepcopy(signed); no_cosign["scanners"]=[s for s in no_cosign["scanners"] if s["scanner_id"]!="cosign"]
    cases=[
      (RULES[0],admission_valid(base),bad(lambda x:x["promotion"].update(model_manager_promotion_eligible=False))),
      (RULES[1],admission_valid(base),bad(lambda x:x["quarantine"].update(state="BYPASSED"))),
      (RULES[2],admission_valid(base),bad(lambda x:x["source"].update(immutable_revision="latest"))),
      (RULES[3],admission_valid(base),bad(lambda x:x["artifact"].update(trusted_because_safe_format=True))),
      (RULES[4],admission_valid(base),bad(lambda x:x["remote_code"].update(enabled=True))),
      (RULES[5],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="modelaudit").update(status="ERROR"))),
      (RULES[6],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="clamav").update(status="SKIPPED"))),
      (RULES[7],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="trivy").update(status="UNSUPPORTED"))),
      (RULES[8],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="bandit").update(status="INCOMPLETE"))),
      (RULES[9],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="pip-audit").update(status="ERROR"))),
      (RULES[10],admission_valid(pickle_llm),not admission_valid(no_pickle)),
      (RULES[11],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="modelaudit").update(status="INCOMPLETE"))),
      (RULES[12],admission_valid(base),not admission_valid(no_yara)),
      (RULES[13],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="cosign").update(policy_reason=""))),
      (RULES[14],admission_valid(base),bad(lambda x:x["security_attestation"].update(scanner_output_is_authority=True))),
      (RULES[15],admission_valid(base),bad(lambda x:next(s for s in x["scanners"] if s["scanner_id"]=="modelaudit").update(binary_or_package_digest="latest"))),
      (RULES[16],admission_valid(base),bad(lambda x:x["scan_execution"].update(network_egress=True))),
      (RULES[17],admission_valid(base),bad(lambda x:x["scan_execution"].update(telemetry=True))),
      (RULES[18],admission_valid(base),bad(lambda x:x["isolated_first_load"].update(status="SKIPPED"))),
      (RULES[19],admission_valid(base),bad(lambda x:x["isolated_first_load"].update(secret_access=True))),
      (RULES[20],admission_valid(pickle_llm),not admission_valid((lambda x:(next(s for s in x["scanners"] if s["scanner_id"]=="garak").update(status="SKIPPED") or x))(copy.deepcopy(pickle_llm)))),
      (RULES[21],admission_valid(base),bad(lambda x:x["behavior_security"].update(policy_reason=""))),
      (RULES[22],admission_valid(signed),not admission_valid(no_cosign)),
      (RULES[23],admission_valid(base),bad(lambda x:x["findings"].update(unresolved_critical=1))),
      (RULES[24],admission_valid(base),bad(lambda x:x["security_attestation"].update(evidence_ids=[]))),
      (RULES[25],admission_valid(base),bad(lambda x:x["security_attestation"].update(scanner_output_is_authority=True))),
      (RULES[26],CAPABILITY_COUNT==143,True),
      (RULES[27],current_host_receipt_valid({"evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS","synthetic_scanner":False,"synthetic_target":False,"real_tool_execution":True,"runtime_promotion_eligible":True}),not current_host_receipt_valid({"evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS","synthetic_scanner":True,"synthetic_target":False,"real_tool_execution":False,"runtime_promotion_eligible":True})),
      (RULES[28],admission_valid(base),bad(lambda x:x["promotion"].update(direct_runtime_store_download_bypass=True))),]
    rows=[]
    for invariant,positive,negative in cases:
        ok=bool(positive and negative); rows.append({"invariant":invariant,"status":"PASS" if ok else "FAIL","positive_case":bool(positive),"negative_case":bool(negative)})
    passed=sum(r["status"]=="PASS" for r in rows)
    return {"schema":"fa3.model-artifact-security-regression-report.v1","result":"PASS" if passed==len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def scan_authority_assignments(root: Path) -> dict[str, Any]:
    findings=[]
    for path in (root/"canonical").rglob("*.json"):
        try: obj=_load(path)
        except Exception: continue
        def walk(v: Any, trail: tuple[str,...]=()):
            if isinstance(v,dict):
                for k,val in v.items():
                    lk=k.lower()
                    if (lk=="authority" or lk.endswith("_authority")) and val==PROVIDER_ID:
                        findings.append(_finding("MODEL-SEC-AUTH-001","Model artifact security scanner stack assigned architectural authority",path=str(path.relative_to(root)),key=".".join(trail+(k,)),value=val))
                    walk(val,trail+(k,))
            elif isinstance(v,list):
                for i,val in enumerate(v): walk(val,trail+(str(i),))
        walk(obj)
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def reference_check(root: Path) -> dict[str, Any]:
    findings=[]
    paths={"profile":root/"canonical/profiles/FA3-MODEL-ARTIFACT-SECURITY-001.json","contract":root/"canonical/contracts/FA3-MODEL-ARTIFACT-SECURITY-CONTRACTS-001.json","provider":root/"canonical/providers/FA3-PROVIDER-MODEL-ARTIFACT-SECURITY-STACK-001.json","decision":root/"canonical/decisions/FA3-DEC-MODEL-ARTIFACT-SECURITY-2026-09-07.json","enforcement":root/"canonical/model-artifact-security-enforcement.json","model_manager":root/"canonical/profiles/FA3-MODEL-MANAGER-001.json","aisec":root/"canonical/profiles/FA3-AI-SEC-VALIDATION-001.json","evidence":root/EVIDENCE_PATH}
    for key,path in paths.items():
        if not path.is_file(): findings.append(_finding("MODEL-SEC-REF-001","Missing mandatory artifact",artifact=key,path=str(path.relative_to(root))))
    if findings: return {"result":"FAIL","findings":findings}
    p,c,pr,d,enf,mm,ai,evid=(_load(paths[k]) for k in ("profile","contract","provider","decision","enforcement","model_manager","aisec","evidence"))
    if not (p.get("id")==PROFILE_ID and p.get("priority")=="P0" and p.get("requirement")=="MUST-FOR-ALL-MODEL-ACQUISITION-IMPORT-AND-PROMOTION" and p.get("target_profile")==MODEL_MANAGER_ID and p.get("invariants")==RULES and p.get("capability_count")==CAPABILITY_COUNT and p.get("new_capability") is False and p.get("new_architectural_authority") is False): findings.append(_finding("MODEL-SEC-REF-010","Security profile identity/mandatory binding drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("capability_count")==CAPABILITY_COUNT and c.get("invariants")==RULES): findings.append(_finding("MODEL-SEC-REF-011","Security contract drift"))
    comp={x.get("id"):x for x in pr.get("components",[])}; required_components={"modelaudit","clamav","yara","trivy","modelscan","picklescan","fickling","bandit","pip-audit","garak","cosign"}
    if not (pr.get("id")==PROVIDER_ID and pr.get("free_open_source_only") is True and pr.get("paid_service_required") is False and pr.get("cloud_scanner_required") is False and pr.get("architectural_authority") is False and set(comp)==required_components and all(x.get("license_class")=="FOSS" for x in comp.values())): findings.append(_finding("MODEL-SEC-REF-012","Mandatory FOSS scanner-stack provider drift"))
    if not (pr.get("modelaudit_environment",{}).get("PROMPTFOO_DISABLE_TELEMETRY")=="1" and pr.get("modelaudit_environment",{}).get("NO_ANALYTICS")=="1"): findings.append(_finding("MODEL-SEC-REF-013","ModelAudit telemetry-disable drift"))
    if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("mandatory") is True and d.get("mandatory_rule_ids")==RULES and d.get("architecture_effect",{}).get("new_capabilities")==0 and d.get("architecture_effect",{}).get("new_architectural_authorities")==0 and d.get("architecture_effect",{}).get("capability_count_after")==CAPABILITY_COUNT): findings.append(_finding("MODEL-SEC-REF-014","Canonical decision drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("fail_closed") is True and enf.get("mandatory") is True and enf.get("all_model_manager_acquisition_paths_mediated") is True and enf.get("p0_invariants")==RULES and enf.get("scanner_pass_is_promotion_authority") is False and enf.get("runtime_provider_direct_download_to_promoted_store")=="FORBIDDEN"): findings.append(_finding("MODEL-SEC-REF-015","Fail-closed enforcement drift"))
    sx=mm.get("security_extension",{})
    if not (mm.get("id")==MODEL_MANAGER_ID and PROFILE_ID in mm.get("dependencies",[]) and sx.get("profile_id")==PROFILE_ID and sx.get("required_gate_id")==GATE_ID and sx.get("mandatory_before_promotion") is True and sx.get("admission_state_required")=="SECURITY_ADMITTED"): findings.append(_finding("MODEL-SEC-REF-016","Model Manager mandatory security binding drift"))
    if not (ai.get("id")==AISEC_ID and ai.get("priority")=="P0" and ai.get("new_architectural_authority") is False): findings.append(_finding("MODEL-SEC-REF-017","AI Security parent binding drift"))
    if not (evid.get("gate_id")==GATE_ID and evid.get("status") in {"PENDING_CI","PASS"} and evid.get("regression_cases")==len(RULES) and evid.get("current_host_runtime_promotion_claim") is False and evid.get("capability_count_after")==CAPABILITY_COUNT): findings.append(_finding("MODEL-SEC-REF-018","Reference evidence drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    refs,auth,reg=reference_check(root),scan_authority_assignments(root),run_regressions()
    result="PASS" if all(x["result"]=="PASS" for x in (refs,auth,reg)) else "FAIL"
    return {"schema":"fa3.model-artifact-security-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,"provider_id":PROVIDER_ID,"result":result,"reference_check":refs["result"],"authority_scan":auth["result"],"regression_result":reg["result"],"regression_cases":reg["total"],"capability_count":CAPABILITY_COUNT,"current_host_runtime_promotion_claim":False,"findings":refs.get("findings",[])+auth.get("findings",[])}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--json",action="store_true"); args=ap.parse_args()
    report=gate(Path(args.root)); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
