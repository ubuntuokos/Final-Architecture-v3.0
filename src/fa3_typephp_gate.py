#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any

PROVIDER_ID="FA3-PROVIDER-TYPEPHP-001"
CONTRACT_ID="FA3-AOT-NATIVE-COMPILATION-CONTRACTS-001"
DECISION_ID="FA3-DEC-TYPEPHP-2026-09-07"
REFERENCE_ID="FA3-TYPEPHP-UPSTREAM-REFERENCE-2026-09-07"
GATE_ID="FA3-GATE-TYPEPHP-AOT-NATIVE-001"
EVIDENCE_ID="FA3-EVIDENCE-TYPEPHP-AOT-CI-2026-09-07"
UPSTREAM_COMMIT="72b7ce9bf43d5ae1d641539bedb38ae0e2977d45"
CAPABILITY_COUNT=143
P0_INVARIANTS=["AOT_SEMANTIC_COMPATIBILITY_EXPLICIT","AOT_UNKNOWN_COMPATIBILITY_FAIL_CLOSED","AOT_SOURCE_AND_TOOLCHAIN_IMMUTABLY_PINNED","AOT_RUNTIME_ABI_MATCH_REQUIRED","AOT_BUILD_RECIPE_DIGEST_REQUIRED","AOT_NATIVE_ARTIFACT_HASH_REQUIRED","AOT_SBOM_AND_PROVENANCE_REQUIRED","AOT_IN_PROCESS_LOAD_EXPLICITLY_AUTHORIZED","AOT_UNTRUSTED_NATIVE_EXECUTION_SANDBOXED","AOT_NETWORK_BOOTSTRAP_EXPLICITLY_AUTHORIZED","AOT_FALLBACK_EXPLICIT_AND_SEMANTICALLY_VALIDATED","AOT_PROVIDER_NOT_AUTHORITY"]

def _load(p:Path): return json.loads(p.read_text(encoding="utf-8"))
def _failure(code,msg,**kw): return {"code":code,"severity":"P0","message":msg,**kw}
def _sha(v): return bool(re.fullmatch(r"[0-9a-f]{64}",v or ""))
def _commit(v): return bool(re.fullmatch(r"[0-9a-f]{40}",v or ""))

def semantic_compatibility_valid(status): return status in {"COMPATIBLE","TYPEPHP_SUBSET_CONFIRMED"}
def source_toolchain_pin_valid(*,source_commit,php_version,native_compiler,cmake_version,dependency_lock_present):
    return _commit(source_commit) and php_version in {"8.4","8.5"} and bool(native_compiler and cmake_version and dependency_lock_present)
def abi_valid(*,build_mode,runtime_abi_match): return build_mode in {"bin","ext","lib","wasi"} and (build_mode=="wasi" or bool(runtime_abi_match))
def build_recipe_valid(*,recipe_sha256,immutable_source_ref): return _sha(recipe_sha256) and _commit(immutable_source_ref)
def artifact_trust_valid(*,artifact_sha256,source_sha256,sbom_present,provenance_present): return _sha(artifact_sha256) and _sha(source_sha256) and bool(sbom_present and provenance_present)
def in_process_load_valid(*,build_mode,explicitly_authorized,abi_match): return build_mode not in {"ext","lib"} or bool(explicitly_authorized and abi_match)
def sandbox_valid(*,untrusted_native_artifact,sandboxed): return (not untrusted_native_artifact) or bool(sandboxed)
def network_bootstrap_valid(*,network_used,explicitly_authorized,receipt_present): return (not network_used) or bool(explicitly_authorized and receipt_present)
def fallback_valid(*,fallback_mode,declared,semantic_equivalence_verified):
    return fallback_mode=="FAIL_CLOSED" or bool(declared and semantic_equivalence_verified and fallback_mode in {"PHP_INTERPRETER","OTHER_ADMITTED_PROVIDER"})
def provider_authority_valid(*,canonical_root,architectural_authority): return canonical_root is False and architectural_authority is False

def run_regressions():
    h="0"*64
    cases=[
      ("unknown_semantics",not semantic_compatibility_valid("UNKNOWN")),
      ("incompatible_semantics",not semantic_compatibility_valid("INCOMPATIBLE")),
      ("unpinned_source",not source_toolchain_pin_valid(source_commit="master",php_version="8.5",native_compiler="gcc-14",cmake_version="3.31",dependency_lock_present=True)),
      ("php_outside_range",not source_toolchain_pin_valid(source_commit=UPSTREAM_COMMIT,php_version="8.3",native_compiler="gcc-14",cmake_version="3.31",dependency_lock_present=True)),
      ("abi_mismatch",not abi_valid(build_mode="ext",runtime_abi_match=False)),
      ("missing_recipe_digest",not build_recipe_valid(recipe_sha256="",immutable_source_ref=UPSTREAM_COMMIT)),
      ("missing_artifact_provenance",not artifact_trust_valid(artifact_sha256=h,source_sha256=h,sbom_present=False,provenance_present=True)),
      ("unauthorized_extension_load",not in_process_load_valid(build_mode="ext",explicitly_authorized=False,abi_match=True)),
      ("untrusted_unsandboxed_native",not sandbox_valid(untrusted_native_artifact=True,sandboxed=False)),
      ("unauthorized_network_bootstrap",not network_bootstrap_valid(network_used=True,explicitly_authorized=False,receipt_present=False)),
      ("implicit_unverified_fallback",not fallback_valid(fallback_mode="PHP_INTERPRETER",declared=True,semantic_equivalence_verified=False)),
      ("provider_authority_promotion",not provider_authority_valid(canonical_root=False,architectural_authority=True)),
    ]
    failed=[name for name,ok in cases if not ok]
    return {"result":"PASS" if not failed else "FAIL","passed":len(cases)-len(failed),"total":len(cases),"failed":failed}

def reference_check(root:Path):
    paths={"provider":root/"canonical/providers/FA3-PROVIDER-TYPEPHP-001.json","contract":root/"canonical/contracts/FA3-AOT-NATIVE-COMPILATION-CONTRACTS-001.json","decision":root/"canonical/decisions/FA3-DEC-TYPEPHP-2026-09-07.json","reference":root/"canonical/references/FA3-TYPEPHP-UPSTREAM-REFERENCE-2026-09-07.json","enforcement":root/"canonical/typephp-aot-enforcement.json","evidence":root/"evidence/reference/typephp-aot-ci-2026-09-07.json"}
    findings=[]
    for name,p in paths.items():
        if not p.exists(): findings.append(_failure("TYPEPHP-REF-001",f"missing {name}",file=str(p)))
    if findings: return {"result":"FAIL","findings":findings}
    p,c,d,r,e,ev=(_load(paths[k]) for k in ("provider","contract","decision","reference","enforcement","evidence"))
    if not (p.get("id")==PROVIDER_ID and p.get("canonical_root") is False and p.get("architectural_authority") is False and p.get("new_capability") is False and p.get("new_architectural_authority") is False and p.get("capability_count")==CAPABILITY_COUNT and p.get("activation_mode")=="OPTIONAL_DISABLED_BY_DEFAULT" and p.get("current_host_runtime_evidence")=="NOT_CLAIMED"): findings.append(_failure("TYPEPHP-REF-002","provider invariant drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count")==CAPABILITY_COUNT and c.get("p0_invariants")==P0_INVARIANTS): findings.append(_failure("TYPEPHP-REF-003","contract invariant drift"))
    if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("capability_count_after")==CAPABILITY_COUNT and d.get("current_host_typephp_runtime_status")=="NOT_CLAIMED"): findings.append(_failure("TYPEPHP-REF-004","decision invariant drift"))
    if not (r.get("id")==REFERENCE_ID and r.get("snapshot_commit")==UPSTREAM_COMMIT and r.get("snapshot_commit_signature_verified") is True and r.get("fa3_disposition",{}).get("floating_master_allowed_as_promotion_evidence") is False): findings.append(_failure("TYPEPHP-REF-005","upstream pin drift"))
    if not (e.get("id")==GATE_ID and e.get("fail_closed") is True and e.get("p0_invariants")==P0_INVARIANTS and e.get("current_host_runtime_claim") is False): findings.append(_failure("TYPEPHP-REF-006","enforcement drift"))
    if not (ev.get("id")==EVIDENCE_ID and ev.get("status")=="PASS" and ev.get("regression_cases")=={"passed":12,"total":12} and ev.get("live_typephp_compiler_executed") is False and ev.get("current_host_runtime_evidence")=="NOT_CLAIMED"): findings.append(_failure("TYPEPHP-REF-007","offline evidence drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

AUTH_KEYS=("identity_authority","authorization_authority","secrets_authority","mcp_authority","model_routing_authority","workflow_authority","orchestration_authority","evidence_authority","host_resource_authority","developer_execution_authority","artifact_trust_authority","registry_authority","network_egress_authority")
def _is_typephp(v:Any):
    if isinstance(v,str): return "TYPEPHP" in v.upper() or "SWOOLE/TYPEPHP" in v.upper()
    if isinstance(v,list): return any(_is_typephp(x) for x in v)
    if isinstance(v,dict): return any(_is_typephp(x) for x in v.values())
    return False
def _scan(v:Any,file_path,path="$"):
    out=[]
    if isinstance(v,dict):
        scoped=any(_is_typephp(v.get(k)) for k in ("id","provider_id","subject","name") if k in v)
        if scoped and v.get("canonical_root") is True: out.append(_failure("TYPEPHP-AUTH-001","TypePHP promoted to canonical root",file=file_path,path=path))
        if scoped and v.get("architectural_authority") is True: out.append(_failure("TYPEPHP-AUTH-002","TypePHP promoted to architectural authority",file=file_path,path=path))
        for k,x in v.items():
            nk=k.lower().replace("-","_")
            if (nk in AUTH_KEYS or nk.endswith("_authority")) and _is_typephp(x): out.append(_failure("TYPEPHP-AUTH-003","TypePHP assigned to authority-bearing field",file=file_path,path=path+"."+k))
            out.extend(_scan(x,file_path,path+"."+k))
    elif isinstance(v,list):
        for i,x in enumerate(v): out.extend(_scan(x,file_path,f"{path}[{i}]"))
    return out
def authority_scan(root:Path):
    findings=[]; scanned=0; c=root/"canonical"
    if not c.exists(): return {"result":"FAIL","scanned_json_files":0,"findings":[_failure("TYPEPHP-AUTH-000","canonical directory missing")]}
    for p in sorted(c.rglob("*.json")):
        scanned+=1
        try: findings.extend(_scan(_load(p),str(p.relative_to(root))))
        except Exception as exc: findings.append(_failure("TYPEPHP-AUTH-004","JSON parse failure",file=str(p),error=str(exc)))
    return {"result":"PASS" if not findings else "FAIL","scanned_json_files":scanned,"findings":findings}

def gate(root:Path):
    refs=reference_check(root); regs=run_regressions(); auth=authority_scan(root)
    ok=refs["result"]==regs["result"]==auth["result"]=="PASS"
    return {"gate_id":GATE_ID,"result":"PASS" if ok else "FAIL","reference_check":refs,"regressions":regs,"authority_scan":auth,"current_host_runtime_evidence":"NOT_CLAIMED","runtime_promotion":"PENDING_SEPARATE_LIVE_TYPEPHP_CANARY"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--json",action="store_true"); args=ap.parse_args()
    result=gate(Path(args.root).resolve()); print(json.dumps(result,indent=2)); raise SystemExit(0 if result["result"]=="PASS" else 1)
if __name__=="__main__": main()
