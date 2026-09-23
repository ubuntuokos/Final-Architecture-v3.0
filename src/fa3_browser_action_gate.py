#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
GATE_ID="FA3-BROWSER-ACTION-RUNTIME-GATESET-001"
UPSTREAM_REPO="browser-use/jev-ultrafast"
UPSTREAM_COMMIT="1231850a0bf1a0c0341fe408ef1668dbbfdfac46"
REQUIRED_INVARIANTS={"BROWSER_ACTION_SPACE_BOUNDED","MODEL_CANNOT_EMIT_EXECUTABLE_BROWSER_CODE","MODEL_CANNOT_EMIT_UNOBSERVED_TARGET","STALE_DECISION_EXECUTION_DENIED","BROWSER_MUTATION_NOT_BLINDLY_RETRIED","DONE_REQUIRES_INDEPENDENT_VERIFICATION","PAGE_CONTENT_UNTRUSTED","CPU_ONLY_SUPPORTED"}
REQUIRED_CONTRACTS={"BrowserObservation","BrowserObservedElement","BrowserActionCandidate","BrowserActionSpace","BrowserDecisionBinding","BrowserExecutionGuardResult","BrowserMutationReceipt","BrowserOutcomeVerification","BrowserCompletionClaim","BrowserTextGenerationRequest"}
def load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(f"object required: {path}")
    return v
def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); findings=[]
    required=["canonical/profiles/FA3-BROWSER-ACTION-RUNTIME-001.json","canonical/contracts/FA3-BROWSER-ACTION-RUNTIME-CONTRACTS-001.json","canonical/contracts/FA3-WEB-AI-CONTRACTS-001.json","canonical/profiles/FA3-WEB-AI-001.json","canonical/actions/browser.action.execute.json","canonical/providers/FA3-PROVIDER-JEV-DECISION-001.json","canonical/third-party/FA3-JEV-CODE-REUSE-001.json","canonical/FA3-GATE-BROWSER-ACTION-RUNTIME-001.json","canonical/browser-action-runtime-enforcement.json","src/fa3_browser_action_runtime.py","src/fa3_jev_decision_provider.py","tests/test_browser_action_runtime.py","docs/browser-action-runtime.md"]
    for rel in required:
        if not (root/rel).is_file(): findings.append({"code":"BAR-001","message":"required artifact missing","path":rel})
    if findings: return {"schema":"fa3.browser-action-runtime-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}
    p=load(root/"canonical/profiles/FA3-BROWSER-ACTION-RUNTIME-001.json")
    if p.get("new_capability") is not False or p.get("new_architectural_authority") is not False: findings.append({"code":"BAR-002","message":"capability/authority delta forbidden"})
    if p.get("capability_count")!=143 or p.get("capability_delta")!=0 or p.get("authority_delta")!=0: findings.append({"code":"BAR-003","message":"143/zero-delta invariant broken"})
    if p.get("cpu_only_supported") is not True or p.get("mandatory_accelerator") is not False: findings.append({"code":"BAR-004","message":"CPU-only portability broken"})
    if p.get("parent_profile")!="FA3-WEB-AI-001": findings.append({"code":"BAR-005","message":"Web-AI parent missing"})
    miss=sorted(REQUIRED_INVARIANTS-set(p.get("invariants",[])))
    if miss: findings.append({"code":"BAR-006","message":"invariants missing","missing":miss})
    c=load(root/"canonical/contracts/FA3-BROWSER-ACTION-RUNTIME-CONTRACTS-001.json")
    miss=sorted(REQUIRED_CONTRACTS-set(c.get("contracts",[])))
    if miss: findings.append({"code":"BAR-007","message":"contracts missing","missing":miss})
    w=load(root/"canonical/profiles/FA3-WEB-AI-001.json")
    if p["id"] not in w.get("subprofiles",[]): findings.append({"code":"BAR-008","message":"Web-AI subprofile binding missing"})
    if not {"BROWSER_RUNTIME_IS_EXECUTION_DOMAIN_NOT_AUTHORITY","BROWSER_ADAPTER_CANNOT_BYPASS_CENTRAL_GATEWAY_OR_ROUTER"}.issubset(set(w.get("invariants",[]))): findings.append({"code":"BAR-009","message":"existing Web-AI boundaries weakened"})
    j=load(root/"canonical/providers/FA3-PROVIDER-JEV-DECISION-001.json")
    if j.get("model_routing_authority")!="FA3-AUTH-MODEL-ROUTER-001": findings.append({"code":"BAR-010","message":"Jev Model Router binding missing"})
    if j.get("direct_external_model_call")!="DENY": findings.append({"code":"BAR-011","message":"direct Jev model call not denied"})
    s=(root/"src/fa3_jev_decision_provider.py").read_text(encoding="utf-8")
    found=[x for x in ["api.typesafe.ai","TYPESAFE_API_KEY","FA3_JEV_MODEL","FA3_JEV_API_URL","urllib.request"] if x in s]
    if found: findings.append({"code":"BAR-012","message":"direct routing residue","tokens":found})
    if "FA3-AUTH-MODEL-ROUTER-001" not in s or "router_transport" not in s: findings.append({"code":"BAR-013","message":"router transport boundary missing"})
    r=load(root/"canonical/third-party/FA3-JEV-CODE-REUSE-001.json")
    e=next((x for x in r.get("entries",[]) if isinstance(x,dict) and x.get("source_repository")==UPSTREAM_REPO and x.get("source_commit")==UPSTREAM_COMMIT),None)
    if e is None: findings.append({"code":"BAR-014","message":"jev-ultrafast provenance pin missing"})
    elif e.get("license")!="MIT" or e.get("security_review")!="PASS" or e.get("distribution_impact_review")!="PASS" or e.get("imports_architectural_authority") is not False: findings.append({"code":"BAR-015","message":"third-party provenance/review invalid"})
    a=load(root/"canonical/actions/browser.action.execute.json")
    if a.get("semantics",{}).get("mutating") is not True or a.get("semantics",{}).get("idempotent") is not False: findings.append({"code":"BAR-016","message":"mutation contract invalid"})
    if a.get("evidence",{}).get("required") is not True: findings.append({"code":"BAR-017","message":"evidence must be required"})
    pol=load(root/"canonical/enforcement-policy.json")
    if GATE_ID not in pol.get("mandatory_reference_gates",[]): findings.append({"code":"BAR-018","message":"global enforcement binding missing"})
    if pol.get("browser_action_runtime_global_static_required") is not True: findings.append({"code":"BAR-019","message":"global static gate disabled"})
    rt=(root/"src/fa3_browser_action_runtime.py").read_text(encoding="utf-8")
    for token,code in [("UNTRUSTED_EXTERNAL_CONTENT","BAR-020"),("BLIND_MUTATION_RETRY_DENIED","BAR-021"),("COMPLETION_CLAIM","BAR-022"),("VERIFIED_SUCCESS","BAR-023")]:
        if token not in rt: findings.append({"code":code,"message":"runtime invariant token missing","token":token})
    return {"schema":"fa3.browser-action-runtime-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","findings":findings,"upstream_pin":{"repository":UPSTREAM_REPO,"commit":UPSTREAM_COMMIT,"license":"MIT"},"capability_count":143,"capability_delta":0,"authority_delta":0,"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--report",default="reports/browser-action-runtime-gate-report.json"); args=ap.parse_args()
    root=Path(args.root).resolve(); report=gate(root); path=root/args.report; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
