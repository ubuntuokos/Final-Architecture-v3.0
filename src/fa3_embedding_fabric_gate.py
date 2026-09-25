#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count

PROFILE_ID="FA3-EMBEDDING-FABRIC-001"
CONTRACT_ID="FA3-EMBEDDING-FABRIC-CONTRACTS-001"
GATE_ID="FA3-EMBEDDING-FABRIC-GATESET-001"
PROVIDERS=("FA3-PROVIDER-TEI-001","FA3-PROVIDER-MODEL2VEC-001","FA3-PROVIDER-FLAG-EMBEDDING-001")
CAPABILITY_COUNT=module_active_capability_count(__file__)
SPACE_FIELDS=("model_family","immutable_model_revision","tokenizer_revision","pooling","normalization","query_template","document_template","dimension","semantic_role","modality")

def loadj(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def writej(path:Path,obj:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def finding(code:str,message:str,**details:Any)->dict[str,Any]:
    return {"code":code,"severity":"P0","message":message,**details}

def embedding_space_identity(desc:dict[str,Any])->str:
    missing=[k for k in SPACE_FIELDS if k not in desc]
    if missing: raise ValueError("missing embedding-space fields: "+",".join(missing))
    payload={k:desc[k] for k in SPACE_FIELDS}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(raw).hexdigest()

def direct_similarity_allowed(left_space_id:str,right_space_id:str)->bool:
    return bool(left_space_id and left_space_id==right_space_id)

def migration_cutover_allowed(receipt:dict[str,Any])->bool:
    return bool(
        receipt.get("shadow_reembed") is True
        and receipt.get("new_index") is True
        and receipt.get("dual_query_comparison") is True
        and receipt.get("quality_result")=="PASS"
        and receipt.get("performance_result")=="PASS"
        and receipt.get("controlled_cutover") is True
        and receipt.get("old_index_retirement") is True
    )

def gate(root:Path)->dict[str,Any]:
    findings=[]
    paths={
      "profile":root/"canonical/profiles/FA3-EMBEDDING-FABRIC-001.json",
      "contract":root/"canonical/contracts/FA3-EMBEDDING-FABRIC-CONTRACTS-001.json",
      "decision":root/"canonical/decisions/FA3-DEC-EMBEDDING-FABRIC-2026-09-25.json",
      "enforcement":root/"canonical/embedding-fabric-enforcement.json",
      "gate":root/"canonical/FA3-GATE-EMBEDDING-FABRIC-001.json",
      "intent":root/"canonical/intents/FA3-EMBEDDING-FABRIC-APPLICATION-INTENT-001.json",
      "assessment":root/"canonical/assessments/FA3-EMBEDDING-FABRIC-REUSE-ASSESSMENT-001.json",
    }
    provider_paths=[root/f"canonical/providers/{pid}.json" for pid in PROVIDERS]
    for name,path in list(paths.items())+[(p.name,p) for p in provider_paths]:
        if not path.is_file(): findings.append(finding("EMB-001","required artifact missing",artifact=name,path=str(path.relative_to(root))))
    if findings:
        report={"schema":"fa3.embedding-fabric-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings,"current_host_runtime_promotion_claim":False}
        writej(root/"reports/embedding-fabric-gate-report.json",report); return report

    profile,contract,decision,enf,gate_record,intent,assessment=[loadj(paths[k]) for k in ("profile","contract","decision","enforcement","gate","intent","assessment")]
    if not (profile.get("id")==PROFILE_ID and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count")==CAPABILITY_COUNT):
        findings.append(finding("EMB-010","profile capability/authority invariant drift"))
    if profile.get("authority_boundaries",{}).get("model_routing")!="FA3-AUTH-MODEL-ROUTER-001" or profile.get("authority_boundaries",{}).get("host_resources")!="FA3-AUTH-HOST-RESOURCE-BROKER-001":
        findings.append(finding("EMB-011","router/HRB authority boundary drift"))
    if contract.get("id")!=CONTRACT_ID or contract.get("provider_neutral") is not True:
        findings.append(finding("EMB-012","provider-neutral contract drift"))
    space=contract.get("EmbeddingSpaceIdentity",{})
    if space.get("cross_space_direct_similarity")!="DENY_FAIL_CLOSED":
        findings.append(finding("EMB-013","cross-space similarity is not fail-closed"))
    if contract.get("EmbeddingProjectionDescriptor",{}).get("native_masquerade")!="DENY":
        findings.append(finding("EMB-014","projected vector may masquerade as native"))
    if decision.get("new_capabilities")!=0 or decision.get("new_architectural_authorities")!=0 or decision.get("capability_count_after")!=CAPABILITY_COUNT:
        findings.append(finding("EMB-015","decision changed capability/authority baseline"))
    if gate_record.get("current_host_runtime_promotion_claim") is not False or gate_record.get("global_promotion_claim") is not False:
        findings.append(finding("EMB-016","static gate claims runtime/global promotion"))
    if assessment.get("result")!="PASS":
        findings.append(finding("EMB-017","mandatory Reuse Discovery assessment not PASS"))
    ha=intent.get("hardware_audit",{})
    if not (ha.get("vendor_neutral") is True and ha.get("cpu_only_viable") is True and ha.get("accelerator_cardinality")=="0..N"):
        findings.append(finding("EMB-018","hardware audit baseline drift"))

    for ppath in provider_paths:
        p=loadj(ppath)
        if p.get("architectural_authority") is not False or p.get("new_architectural_authority") is not False:
            findings.append(finding("EMB-020","embedding provider gained authority",provider_id=p.get("id")))
        semantics_only = p.get("provider_role") == "OPTIONAL_EMBEDDING_AND_RERANK_MODEL_SEMANTICS_PROVIDER"
        if semantics_only:
            if p.get("serving_runtime_authority") is not False or p.get("runtime_selection") != "MODEL_ROUTER_PLUS_INFERENCE_PORTABILITY_ONLY":
                findings.append(finding("EMB-021","model-semantics provider runtime boundary drift",provider_id=p.get("id")))
        elif p.get("runtime_profile")!="FA3-PROVIDER-RUNTIME-001":
            findings.append(finding("EMB-021","serving provider runtime profile missing",provider_id=p.get("id")))
        if p.get("current_host_production_evidence")!="PENDING_REAL_CURRENT_HOST_EXECUTION":
            findings.append(finding("EMB-022","provider falsely claims current-host evidence",provider_id=p.get("id")))
        co=p.get("coexistence",{})
        if co.get("upstream_uninstall_required") is not False or co.get("global_environment_mutation") is not False:
            findings.append(finding("EMB-023","software coexistence invariant violated",provider_id=p.get("id")))

    sample={
      "model_family":"bge-m3","immutable_model_revision":"rev-1","tokenizer_revision":"tok-1",
      "pooling":"cls","normalization":"l2","query_template":"q:{text}","document_template":"d:{text}",
      "dimension":1024,"semantic_role":"retrieval","modality":"text"
    }
    sid=embedding_space_identity(sample)
    if not direct_similarity_allowed(sid,sid) or direct_similarity_allowed(sid,"sha256:different"):
        findings.append(finding("EMB-030","direct similarity fail-closed regression"))
    good={"shadow_reembed":True,"new_index":True,"dual_query_comparison":True,"quality_result":"PASS","performance_result":"PASS","controlled_cutover":True,"old_index_retirement":True}
    if not migration_cutover_allowed(good) or migration_cutover_allowed({**good,"quality_result":"UNKNOWN"}):
        findings.append(finding("EMB-031","migration cutover fail-closed regression"))

    report={
      "schema":"fa3.embedding-fabric-gate-report.v1","gate_id":GATE_ID,"profile_id":PROFILE_ID,
      "provider_ids":list(PROVIDERS),"capability_count":CAPABILITY_COUNT,
      "result":"PASS" if not findings else "FAIL","findings":findings,
      "mode":"STATIC_CANONICAL_AND_NEGATIVE_REGRESSION",
      "current_host_runtime_promotion_claim":False,"global_promotion_claim":False,
      "runtime_status":"PENDING_REAL_CURRENT_HOST_E2E"
    }
    writej(root/"reports/embedding-fabric-gate-report.json",report)
    return report

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args(); report=gate(Path(args.root).resolve()); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
