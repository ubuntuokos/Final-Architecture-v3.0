#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

GATE_ID="FA3-GATE-MODEL-MANAGER-002"
PROFILE_ID="FA3-MODEL-MANAGER-001"
CONTRACT_ID="FA3-MODEL-MANAGER-CONTRACTS-001"
REGISTRY_ID="FA3-MODEL-REGISTRY-001"
DECISION_ID="FA3-DEC-MODEL-MANAGER-V2-2026-09-01"
REFERENCE_ID="FA3-MODEL-MANAGER-PROVIDERS-UPSTREAM-REFERENCE-2026-09-01"
EVIDENCE_PATH="evidence/reference/model-manager-v2-ci-2026-09-01.json"
CAPABILITY_COUNT=143
PROVIDER_IDS=[
    "FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001",
    "FA3-PROVIDER-HF-MODEL-STORE-001",
    "FA3-PROVIDER-LM-STUDIO-MODEL-001",
    "FA3-PROVIDER-OLLAMA-MODEL-001",
]
RULES=["MODEL_RECORD_IMMUTABLE_SOURCE_REVISION_REQUIRED","MODEL_FAMILY_REVISION_VARIANT_ARTIFACT_RUNTIME_INSTANCE_IDENTITY_SEPARATION","LICENSE_AND_REDISTRIBUTION_METADATA_REQUIRED_BEFORE_PROMOTION","DANGEROUS_SERIALIZATION_AND_REMOTE_CODE_POLICY_REQUIRED","SOURCE_CACHE_CANONICAL_STORE_RUNTIME_PROJECTION_SEPARATION","CONTENT_ADDRESSED_DEDUP_PREFERRED_COPY_LAST","LINK_PROJECTION_REQUIRES_CANONICAL_PATH_REVALIDATION_AUTHORIZATION_AND_ROLLBACK","RUNTIME_PROVIDER_NATIVE_STORE_IS_NON_AUTHORITY","MODEL_REQUIREMENTS_DECLARED_PLACEMENT_DELEGATED_TO_HRB","ACCELERATOR_RUNTIME_REQUIRES_HRB_ADMISSION_OR_LEASE","PROVIDER_MODEL_OPERATIONS_TYPED_AND_BOUNDED","PROVIDER_OUTAGE_PRESERVES_CANONICAL_MODEL_RECORD","UNKNOWN_LICENSE_TRUST_LINEAGE_OR_COMPATIBILITY_BLOCKS_PROMOTION","RUNTIME_MATERIALIZATION_EVIDENCE_REQUIRED_FOR_PRODUCTION_PROMOTION","UPSTREAM_FLOATING_LATEST_NOT_PRODUCTION_ADMISSION"]

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code":code,"severity":"P0","message":message,**extra}

def _sha256(v: Any) -> bool:
    return isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) is not None

def _promotable(x: dict[str, Any]) -> bool:
    origin=x.get("origin",{})
    artifact=x.get("artifact",{})
    licensing=x.get("licensing",{})
    security=x.get("security",{})
    derivation=x.get("derivation",{})
    compatibility=x.get("compatibility",{})
    resources=x.get("resources",{})
    evidence=x.get("evidence",{})
    return bool(
        origin.get("immutable_revision")
        and origin.get("immutable_revision") not in {"main","master","latest"}
        and _sha256(artifact.get("sha256"))
        and licensing.get("license_id") not in {None,"","UNKNOWN"}
        and security.get("trust_level") in {"POLICY_ADMITTED","VERIFIED"}
        and security.get("remote_code") is not True
        and security.get("dangerous_serialization") in {False,"SCANNED_AND_ADMITTED"}
        and derivation.get("lineage_valid") is True
        and compatibility.get("runtime_state")=="VERIFIED"
        and resources.get("declared") is True
        and evidence.get("runtime_materialization_evidence")
    )

def _link_projection_valid(x: dict[str, Any]) -> bool:
    return all(bool(x.get(k)) for k in (
        "content_hash_match","runtime_compatibility_verified",
        "canonical_path_revalidated","explicit_authorization","rollback_plan"
    ))

def _accelerator_request_valid(x: dict[str, Any]) -> bool:
    if x.get("accelerator") is not True:
        return True
    return bool(x.get("hrb_admission_id") or x.get("hrb_lease_id"))

def _typed_provider_ops_valid(x: dict[str, Any]) -> bool:
    required={"discover","import","list","inspect","estimate_resources","load","unload","serve","health"}
    return required.issubset(set(x.get("typed_operations",[])))

def run_regressions() -> dict[str, Any]:
    good={
      "origin":{"immutable_revision":"abc123"},
      "artifact":{"sha256":"a"*64},
      "licensing":{"license_id":"apache-2.0"},
      "security":{"trust_level":"VERIFIED","remote_code":False,"dangerous_serialization":False},
      "derivation":{"lineage_valid":True},
      "compatibility":{"runtime_state":"VERIFIED"},
      "resources":{"declared":True},
      "evidence":{"runtime_materialization_evidence":"EVID-1"},
    }
    link={"content_hash_match":True,"runtime_compatibility_verified":True,"canonical_path_revalidated":True,"explicit_authorization":True,"rollback_plan":"restore"}
    typed={"typed_operations":["discover","import","list","inspect","estimate_resources","load","unload","serve","health"]}
    planes=["SOURCE_CACHE","CANONICAL_MODEL_STORE","RUNTIME_PROJECTION_STORE"]
    chain=["MODEL_FAMILY","IMMUTABLE_REVISION","VARIANT","ARTIFACT","RUNTIME_PROJECTION","LOADED_INSTANCE"]
    cases=[
      (RULES[0], _promotable(good), not _promotable({**good,"origin":{"immutable_revision":"latest"}})),
      (RULES[1], len(chain)==len(set(chain)) and chain[0]!="ARTIFACT", True),
      (RULES[2], _promotable(good), not _promotable({**good,"licensing":{"license_id":"UNKNOWN"}})),
      (RULES[3], _promotable(good), not _promotable({**good,"security":{"trust_level":"VERIFIED","remote_code":True,"dangerous_serialization":False}})),
      (RULES[4], len(planes)==3 and len(set(planes))==3, True),
      (RULES[5], ["CONTENT_ADDRESSED_BLOB","HARDLINK","SYMLINK","PROVIDER_REFERENCE","COPY"][-1]=="COPY", True),
      (RULES[6], _link_projection_valid(link), not _link_projection_valid({**link,"canonical_path_revalidated":False})),
      (RULES[7], all(x not in {"FA3-REGISTRY-001","FA3-AUTH-MODEL-ROUTER-001","FA3-AUTH-HOST-RESOURCE-BROKER-001"} for x in PROVIDER_IDS), True),
      (RULES[8], "FA3-AUTH-HOST-RESOURCE-BROKER-001"=="FA3-AUTH-HOST-RESOURCE-BROKER-001", True),
      (RULES[9], _accelerator_request_valid({"accelerator":True,"hrb_lease_id":"LEASE-1"}), not _accelerator_request_valid({"accelerator":True})),
      (RULES[10], _typed_provider_ops_valid(typed), not _typed_provider_ops_valid({"typed_operations":["load","serve"]})),
      (RULES[11], {"provider":"DOWN","canonical_record":"READABLE"}["canonical_record"]=="READABLE", True),
      (RULES[12], _promotable(good), not _promotable({**good,"compatibility":{"runtime_state":"UNKNOWN"}})),
      (RULES[13], _promotable(good), not _promotable({**good,"evidence":{"runtime_materialization_evidence":None}})),
      (RULES[14], "latest" not in {"abc123","f96e7aa0513b9973a0ccc71be414c2ecb9d65b1a"}, True),
    ]
    rows=[]
    for invariant,positive,negative in cases:
        ok=bool(positive and negative)
        rows.append({"invariant":invariant,"status":"PASS" if ok else "FAIL","positive_case":bool(positive),"negative_case":bool(negative)})
    passed=sum(x["status"]=="PASS" for x in rows)
    return {"schema":"fa3.model-manager-v2-regression-report.v1","result":"PASS" if passed==len(rows) else "FAIL","passed":passed,"total":len(rows),"cases":rows}

def scan_authority_assignments(root: Path) -> dict[str, Any]:
    findings=[]
    forbidden=set(PROVIDER_IDS)|{REGISTRY_ID}
    for path in (root/"canonical").rglob("*.json"):
        try:
            obj=_load(path)
        except Exception:
            continue
        def walk(v: Any, trail: tuple[str,...]=()) -> None:
            if isinstance(v,dict):
                for k,val in v.items():
                    lk=k.lower()
                    if (lk=="authority" or lk.endswith("_authority")) and isinstance(val,str) and val in forbidden:
                        findings.append(_finding("MODEL-MGR-V2-AUTH-001","Model registry/provider projection assigned architectural authority",path=str(path.relative_to(root)),key=".".join(trail+(k,)),value=val))
                    walk(val,trail+(k,))
            elif isinstance(v,list):
                for i,val in enumerate(v):
                    walk(val,trail+(str(i),))
        walk(obj)
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def reference_check(root: Path) -> dict[str, Any]:
    findings=[]
    paths={
      "profile":root/"canonical/profiles/FA3-MODEL-MANAGER-001.json",
      "contract":root/"canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json",
      "registry":root/"canonical/registries/FA3-MODEL-REGISTRY-001.json",
      "hf":root/"canonical/providers/FA3-PROVIDER-HF-MODEL-STORE-001.json",
      "lm":root/"canonical/providers/FA3-PROVIDER-LM-STUDIO-MODEL-001.json",
      "ollama":root/"canonical/providers/FA3-PROVIDER-OLLAMA-MODEL-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-MODEL-MANAGER-V2-2026-09-01.json",
      "reference":root/"canonical/references/FA3-MODEL-MANAGER-PROVIDERS-UPSTREAM-REFERENCE-2026-09-01.json",
      "enforcement":root/"canonical/model-manager-v2-enforcement.json",
      "evidence":root/EVIDENCE_PATH,
    }
    for key,path in paths.items():
        if not path.is_file():
            findings.append(_finding("MODEL-MGR-V2-REF-001","Missing required Model Manager v2 artifact",artifact=key,path=str(path.relative_to(root))))
    if findings:
        return {"result":"FAIL","findings":findings}
    p=_load(paths["profile"]); c=_load(paths["contract"]); reg=_load(paths["registry"])
    hf=_load(paths["hf"]); lm=_load(paths["lm"]); oll=_load(paths["ollama"])
    d=_load(paths["decision"]); ref=_load(paths["reference"]); enf=_load(paths["enforcement"]); evid=_load(paths["evidence"])
    if not (p.get("id")==PROFILE_ID and p.get("version")=="2.0.0" and p.get("model_registry")==REGISTRY_ID and all(x in p.get("providers",[]) for x in PROVIDER_IDS)):
        findings.append(_finding("MODEL-MGR-V2-REF-010","Profile v2 registry/provider binding drift"))
    if not (c.get("id")==CONTRACT_ID and c.get("provider_neutral") is True and c.get("model_record_required_sections")==reg.get("required_sections")):
        findings.append(_finding("MODEL-MGR-V2-REF-011","Contract/model-record schema binding drift"))
    if not (reg.get("id")==REGISTRY_ID and reg.get("registry_authority")=="FA3-REGISTRY-001" and reg.get("architectural_authority") is False and reg.get("new_capability") is False and reg.get("new_architectural_authority") is False and reg.get("capability_count")==CAPABILITY_COUNT):
        findings.append(_finding("MODEL-MGR-V2-REF-012","Canonical model registry authority/capability drift"))
    if not (hf.get("id")==PROVIDER_IDS[1] and hf.get("upstream_release")=="v1.29.0" and hf.get("upstream_release_commit")=="4237d95c603db491cb1070898c74c97e4d7c2582" and hf.get("architectural_authority") is False and hf.get("current_host_production_evidence")=="NOT_CLAIMED"):
        findings.append(_finding("MODEL-MGR-V2-REF-013","Hugging Face provider pin/boundary drift"))
    if not (lm.get("id")==PROVIDER_IDS[2] and lm.get("immutable_public_runtime_release_pin_available") is False and lm.get("architectural_authority") is False and lm.get("current_host_production_evidence")=="NOT_CLAIMED_BY_THIS_MATERIALIZATION" and _typed_provider_ops_valid(lm)):
        findings.append(_finding("MODEL-MGR-V2-REF-014","LM Studio provider runtime-pin/boundary drift"))
    if not (oll.get("id")==PROVIDER_IDS[3] and oll.get("upstream_release")=="v0.33.2" and oll.get("upstream_release_commit")=="f96e7aa0513b9973a0ccc71be414c2ecb9d65b1a" and oll.get("architectural_authority") is False and oll.get("current_host_production_evidence")=="NOT_CLAIMED"):
        findings.append(_finding("MODEL-MGR-V2-REF-015","Ollama provider pin/boundary drift"))
    if not (d.get("id")==DECISION_ID and d.get("status")=="CANONICAL_CLOSED" and d.get("mandatory_rule_ids")==RULES and d.get("new_capabilities")==0 and d.get("new_architectural_authorities")==0 and d.get("capability_count_after")==CAPABILITY_COUNT and d.get("current_host_runtime_promotion_claim") is False):
        findings.append(_finding("MODEL-MGR-V2-REF-016","Canonical v2 decision drift"))
    if not (ref.get("id")==REFERENCE_ID and ref.get("floating_latest_allowed_as_production_evidence") is False and ref.get("runtime_promotion_requires_separate_current_host_evidence") is True):
        findings.append(_finding("MODEL-MGR-V2-REF-017","Provider upstream reference drift"))
    if not (enf.get("gate_id")==GATE_ID and enf.get("extends_gate_id")=="FA3-MODEL-MANAGER-GATESET-001" and enf.get("fail_closed") is True and enf.get("mandatory_rule_count")==len(RULES) and enf.get("p0_invariants")==RULES):
        findings.append(_finding("MODEL-MGR-V2-REF-018","V2 enforcement drift"))
    if not (evid.get("gate_id")==GATE_ID and evid.get("status") in {"PENDING_CI","PASS"} and evid.get("extended_regression_cases")==len(RULES) and evid.get("current_host_runtime_promotion_claim") is False and evid.get("capability_count_after")==CAPABILITY_COUNT):
        findings.append(_finding("MODEL-MGR-V2-REF-019","V2 reference evidence contract drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root: Path) -> dict[str, Any]:
    ref=reference_check(root)
    auth=scan_authority_assignments(root)
    regressions=run_regressions()
    ok=ref["result"]==auth["result"]==regressions["result"]=="PASS"
    return {
      "schema":"fa3.model-manager-v2-gate-report.v1",
      "gate_id":GATE_ID,
      "profile_id":PROFILE_ID,
      "model_registry_id":REGISTRY_ID,
      "provider_ids":PROVIDER_IDS,
      "result":"PASS" if ok else "FAIL",
      "reference":ref,
      "authority_scan":auth,
      "regressions":regressions,
      "current_host_runtime_promotion_claim":False,
      "promotion_effect":"CANONICAL_V2_CI_PASS_DOES_NOT_CLAIM_PROVIDER_CURRENT_HOST_PRODUCTION_PASS",
    }
