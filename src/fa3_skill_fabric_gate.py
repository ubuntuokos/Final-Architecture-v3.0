#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json, posixpath, re
from pathlib import Path
from typing import Any
from fa3_distribution_compliance_gate import classification_valid
from fa3_release_baseline import load_active_release_baseline
from fa3_skill_ecosystem_gate import evaluate as skill_ecosystem_gate
from fa3_skill_fabric_v13 import activation_preview_allowed, context_budget_allowed, evaluate as skill_fabric_v13_gate, interface_allowed, provenance_attestation_allowed\nfrom fa3_skill_execution_closure import evaluate as skill_execution_closure_gate
PROFILE="canonical/profiles/FA3-SKILL-FABRIC-001.json"; CONTRACT="canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json"
DISCOVERY_CONTRACT="canonical/contracts/FA3-SKILL-DISCOVERY-CONTRACTS-001.json"
MATERIALIZATION_CONTRACT="canonical/contracts/FA3-SKILL-MATERIALIZATION-CONTRACTS-001.json"
GATE_ID="FA3-GATE-SKILL-FABRIC-001"; GATESET_ID="FA3-SKILL-FABRIC-GATESET-001"
SHA40=re.compile(r"^[0-9a-f]{40}$"); SHA256=re.compile(r"^[0-9a-f]{64}$")
def loadj(path: Path) -> dict[str,Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError("top-level object required")
    return obj
def _safe_relpath(path: str) -> bool:
    if not isinstance(path,str) or not path or path.startswith("/"): return False
    n=posixpath.normpath(path); return n not in (".","..") and not n.startswith("../") and "/../" not in f"/{n}/"
def good_package() -> dict[str,Any]:
    content="a"*64
    return {"package_id":"fa3.example.skill","provider_id":"FA3-NATIVE-TEST",
      "source":{"repository":"fa3/native","commit":"1"*40,"floating_ref_allowed":False,"auto_update":False},
      "digests":{"content_sha256":content,"manifest_sha256":"b"*64},"hash_attestation":{"sha256":content},
      "license":{"name":"MIT","snapshot_present":True,"spdx_expression":"MIT","source":"LICENSE","evidence_digest":"c"*64,
        "commercial_use":"ALLOW","redistribution":"ALLOW","modification":"ALLOW","source_distribution_required":False,
        "attribution_required":True,"notice_required":False,"patent_terms":"NONE_DECLARED","copyleft_scope":"NONE"},
      "distribution":{"class":"EXTERNAL_REDISTRIBUTABLE","product_bundle_allowed":False,
        "fa3_distribution_compatible":True,"decision_receipt":"dist:test:1"},
      "entrypoints":[{"name":"example","version":"1.0.0","path":"skills/example/SKILL.md","trigger":"task.example"}],
      "dependencies":{"explicit":True,"nodes":["example"],"edges":[],"digest_sha256":"d"*64},
      "evaluation":{"required":True,"behavioral":True,"negative":True,"adversarial_injection":True,
        "result":"PASS","bound_content_sha256":content},
      "review":{"status":"PASS","skipped":False,"security":"PASS","license":"PASS"},
      "scope":{"on_demand":True,"task_scoped":True,"global_auto_injection":False},
      "execution":{"mode":"INERT_DATA_ONLY","shell_interpolation_exec_allowed":False,"script_auto_execute":False,
        "remote_fetch_during_admission":False,"remote_fetch_during_activation":False,
        "direct_credential_access":False,"direct_external_mutation":False},
      "tool_boundary":{"central_mcp_required":True,"discovery_is_authorization":False},
      "permissions":{"network":False,"filesystem_write":False,"exec":False,"secrets":False},
      "interface":{"typed":True,"inputs":[{"name":"input","type":"text/plain"}],"outputs":[{"name":"output","type":"text/plain"}],"preconditions":["task_scope_bound"],"postconditions":["acceptance_checked"],"grants_authority":False},
      "context_budget":{"metadata_max_tokens":256,"instructions_max_tokens":2048,"references_max_tokens":4096,"metadata_used_tokens":64,"instructions_used_tokens":512,"references_used_tokens":0,"overflow_policy":"FAIL_CLOSED"},
      "activation_preview":{"result":"PASS","side_effects_performed":False,"authority_expansion":False,"allowed_tools_is_authorization":False,"admitted_permissions":{"network":False,"filesystem_write":False,"exec":False,"secrets":False},"requested_permissions":{"network":False,"filesystem_write":False,"exec":False,"secrets":False},"routes":{"tool":"FA3-AUTH-MCP-GATEWAY-001","model":"FA3-AUTH-MODEL-ROUTER-001","resource":"FA3-AUTH-HOST-RESOURCE-BROKER-001","secret":"FA3-AUTH-SECRETS"}},
      "provenance_attestation":{"present":False,"required":False},
      "compatibility":{"apps":["developer"],"agents":["generic"],"task_classes":["task.example"]},
      "hardware":{"portable":True,"exact_host_model_required":False},"files":["skills/example/SKILL.md"],"symlinks":[]}
def good_use_receipt() -> dict[str,Any]:
    return {"package_admission_status":"PASS","materialization_state":"ACTIVE_FOR_TASK",
      "selection_receipt_ref":"skill-select:test:1","admission_receipt_ref":"skill-admit:test:1",
      "skill_name":"example","skill_version":"1.0.0","content_sha256":"a"*64,"dependency_digest_sha256":"d"*64,
      "task_scope":"task.example","unsandboxed_execution":False,
      "tool_intent":{"via_central_mcp":True,"mutating":False,"authorization_receipt":None},
      "model_intent":{"via_model_router":True},"resource_intent":{"via_hrb":True},
      "secret_intent":{"via_secret_broker":True},"candidate_expanded_after_eligibility":False}
def _acyclic(dep: dict[str,Any]) -> bool:
    nodes=set(dep.get("nodes",[])); graph={n:[] for n in nodes}
    for e in dep.get("edges",[]):
        a=e.get("from"); b=e.get("to")
        if a not in nodes or b not in nodes: return False
        graph[a].append(b)
    seen=set(); stack=set()
    def visit(n):
        if n in stack: return False
        if n in seen: return True
        stack.add(n)
        if any(not visit(m) for m in graph[n]): return False
        stack.remove(n); seen.add(n); return True
    return all(visit(n) for n in nodes)
def package_admission_allowed(p: dict[str,Any]) -> bool:
    try:
      src=p["source"]; dig=p["digests"]; lic=p["license"]; dist=p["distribution"]
      if not SHA40.fullmatch(str(src.get("commit",""))) or src.get("floating_ref_allowed") or src.get("auto_update"): return False
      if not SHA256.fullmatch(str(dig.get("content_sha256",""))) or not SHA256.fullmatch(str(dig.get("manifest_sha256",""))): return False
      if p.get("hash_attestation",{}).get("sha256")!=dig["content_sha256"]: return False
      dd={"origin":"EXTERNAL" if dist.get("class")!="FA3_NATIVE" else "FA3_NATIVE","hash_attestation":p["hash_attestation"],"license":lic,"distribution":dist}
      if not classification_valid(dd) or dist.get("class") in ("REFERENCE_ONLY","BLOCKED"): return False
      if lic.get("snapshot_present") is not True: return False
      dep=p["dependencies"]
      if dep.get("explicit") is not True or not SHA256.fullmatch(str(dep.get("digest_sha256",""))) or not _acyclic(dep): return False
      ev=p["evaluation"]
      if not (ev.get("required") and ev.get("behavioral") and ev.get("negative") and ev.get("adversarial_injection")
        and ev.get("result")=="PASS" and ev.get("bound_content_sha256")==dig["content_sha256"]): return False
      review=p.get("review",{})
      if review.get("skipped") is not False or review.get("status")!="PASS" or review.get("security")!="PASS" or review.get("license")!="PASS": return False
      scope=p["scope"]
      if not scope.get("on_demand") or not scope.get("task_scoped") or scope.get("global_auto_injection"): return False
      ex=p["execution"]
      if ex.get("mode")!="INERT_DATA_ONLY" or any(ex.get(k) for k in ("shell_interpolation_exec_allowed","script_auto_execute","remote_fetch_during_admission","remote_fetch_during_activation","direct_credential_access","direct_external_mutation")): return False
      tb=p["tool_boundary"]
      if tb.get("central_mcp_required") is not True or tb.get("discovery_is_authorization") is not False: return False
      perms=p.get("permissions")
      if not isinstance(perms,dict) or any(v not in (True,False) for v in perms.values()): return False
      if not interface_allowed(p.get("interface",{})): return False
      if not context_budget_allowed(p.get("context_budget",{})): return False
      if not activation_preview_allowed(p.get("activation_preview",{})): return False
      if not provenance_attestation_allowed(p.get("provenance_attestation",{"present":False,"required":False})): return False
      comp=p.get("compatibility",{})
      if not all(isinstance(comp.get(k),list) and comp.get(k) for k in ("apps","agents","task_classes")): return False
      if p.get("hardware",{}).get("exact_host_model_required"): return False
      if any(not _safe_relpath(x) for x in p.get("files",[])): return False
      return True
    except (KeyError,TypeError,AttributeError): return False
def skill_use_allowed(u: dict[str,Any]) -> bool:
    if u.get("package_admission_status")!="PASS" or u.get("materialization_state")!="ACTIVE_FOR_TASK": return False
    if not u.get("selection_receipt_ref") or not u.get("admission_receipt_ref") or not u.get("task_scope"): return False
    if u.get("unsandboxed_execution") or u.get("candidate_expanded_after_eligibility"): return False
    ti=u.get("tool_intent",{})
    if ti.get("via_central_mcp") is not True or (ti.get("mutating") and not ti.get("authorization_receipt")): return False
    if u.get("model_intent",{}).get("via_model_router") is not True or u.get("resource_intent",{}).get("via_hrb") is not True or u.get("secret_intent",{}).get("via_secret_broker") is not True: return False
    return bool(SHA256.fullmatch(str(u.get("content_sha256","")))) and bool(SHA256.fullmatch(str(u.get("dependency_digest_sha256",""))))
def _mut(obj,fn): x=copy.deepcopy(obj);fn(x);return x
def run_regressions() -> dict[str,Any]:
    g=good_package();u=good_use_receipt()
    checks=[package_admission_allowed(g),
      not package_admission_allowed(_mut(g,lambda x:x["source"].update(commit="main"))),
      not package_admission_allowed(_mut(g,lambda x:x["source"].update(floating_ref_allowed=True))),
      not package_admission_allowed(_mut(g,lambda x:x["source"].update(auto_update=True))),
      not package_admission_allowed(_mut(g,lambda x:x["digests"].update(content_sha256=""))),
      not package_admission_allowed(_mut(g,lambda x:x["digests"].update(manifest_sha256=""))),
      not package_admission_allowed(_mut(g,lambda x:x["hash_attestation"].update(sha256="f"*64))),
      not package_admission_allowed(_mut(g,lambda x:x["license"].update(snapshot_present=False))),
      not package_admission_allowed(_mut(g,lambda x:x["license"].update(spdx_expression="UNKNOWN"))),
      not package_admission_allowed(_mut(g,lambda x:x["license"].update(commercial_use="DENY"))),
      not package_admission_allowed(_mut(g,lambda x:x["license"].update(redistribution="DENY"))),
      not package_admission_allowed(_mut(g,lambda x:x["license"].update(evidence_digest=""))),
      not package_admission_allowed(_mut(g,lambda x:x["distribution"].update({"class":"REFERENCE_ONLY","product_bundle_allowed":False}))),
      not package_admission_allowed(_mut(g,lambda x:x["distribution"].update({"class":"BLOCKED","product_bundle_allowed":False}))),
      package_admission_allowed(_mut(g,lambda x:x["distribution"].update({"class":"USER_LOCAL_EXTERNAL","product_bundle_allowed":False}))),
      not package_admission_allowed(_mut(g,lambda x:x["dependencies"].update(explicit=False))),
      not package_admission_allowed(_mut(g,lambda x:x["dependencies"].update(edges=[{"from":"example","to":"example"}]))),
      not package_admission_allowed(_mut(g,lambda x:x["dependencies"].update(digest_sha256=""))),
      not package_admission_allowed(_mut(g,lambda x:x["evaluation"].update(required=False))),
      not package_admission_allowed(_mut(g,lambda x:x["evaluation"].update(behavioral=False))),
      not package_admission_allowed(_mut(g,lambda x:x["evaluation"].update(negative=False))),
      not package_admission_allowed(_mut(g,lambda x:x["evaluation"].update(adversarial_injection=False))),
      not package_admission_allowed(_mut(g,lambda x:x["evaluation"].update(result="FAIL"))),
      not package_admission_allowed(_mut(g,lambda x:x["evaluation"].update(bound_content_sha256="e"*64))),
      not package_admission_allowed(_mut(g,lambda x:x["review"].update(skipped=True))),
      not package_admission_allowed(_mut(g,lambda x:x["review"].update(status="PENDING"))),
      not package_admission_allowed(_mut(g,lambda x:x["scope"].update(on_demand=False))),
      not package_admission_allowed(_mut(g,lambda x:x["scope"].update(task_scoped=False))),
      not package_admission_allowed(_mut(g,lambda x:x["scope"].update(global_auto_injection=True))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(mode="ACTIVE_EXECUTION"))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(shell_interpolation_exec_allowed=True))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(script_auto_execute=True))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(remote_fetch_during_admission=True))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(remote_fetch_during_activation=True))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(direct_credential_access=True))),
      not package_admission_allowed(_mut(g,lambda x:x["execution"].update(direct_external_mutation=True))),
      not package_admission_allowed(_mut(g,lambda x:x["tool_boundary"].update(central_mcp_required=False))),
      not package_admission_allowed(_mut(g,lambda x:x["tool_boundary"].update(discovery_is_authorization=True))),
      not package_admission_allowed(_mut(g,lambda x:x["files"].append("../escape"))),
      not package_admission_allowed(_mut(g,lambda x:x["files"].append("/absolute"))),
      not package_admission_allowed(_mut(g,lambda x:x["hardware"].update(exact_host_model_required=True))),
      skill_use_allowed(u),not skill_use_allowed(_mut(u,lambda x:x.update(materialization_state="SELECTED"))),
      not skill_use_allowed(_mut(u,lambda x:x.update(selection_receipt_ref=""))),
      not skill_use_allowed(_mut(u,lambda x:x.update(candidate_expanded_after_eligibility=True))),
      not skill_use_allowed(_mut(u,lambda x:x["tool_intent"].update(via_central_mcp=False))),
      not skill_use_allowed(_mut(u,lambda x:x["tool_intent"].update(mutating=True,authorization_receipt=None))),
      not skill_use_allowed(_mut(u,lambda x:x["model_intent"].update(via_model_router=False))),
      not skill_use_allowed(_mut(u,lambda x:x["resource_intent"].update(via_hrb=False))),
      not skill_use_allowed(_mut(u,lambda x:x["secret_intent"].update(via_secret_broker=False)))]
    cases=[{"case_id":f"SKF-{i:03d}","status":"PASS" if ok else "FAIL"} for i,ok in enumerate(checks,1)]
    return {"result":"PASS" if all(checks) else "FAIL","total":len(cases),"passed":sum(c["status"]=="PASS" for c in cases),"case_ids_exact":[c["case_id"] for c in cases]==[f"SKF-{i:03d}" for i in range(1,len(cases)+1)],"cases":cases}
def canonical_check(root: Path) -> list[str]:
    findings=[];cap=load_active_release_baseline(root).capability_count;p=loadj(root/PROFILE);ct=loadj(root/CONTRACT);d=loadj(root/DISCOVERY_CONTRACT);m=loadj(root/MATERIALIZATION_CONTRACT)
    if not (p.get("id")=="FA3-SKILL-FABRIC-001" and p.get("provider_neutral") is True and p.get("capability_count")==cap and p.get("new_capability") is False and p.get("new_architectural_authority") is False): findings.append("skill fabric governance drift")
    s=p.get("selection_and_composition",{})
    for k in ("smallest_matching_skill_set_required","progressive_disclosure_required","deterministic_eligibility_before_advisory_selection","decision_fabric_candidate_expansion_forbidden","unadmitted_skill_activation_forbidden","task_scoped_materialization_required"):
        if s.get(k) is not True: findings.append(f"missing skill selection invariant: {k}")
    if ct.get("distribution_governance",{}).get("contract_id")!="FA3-DISTRIBUTION-COMPLIANCE-CONTRACTS-001": findings.append("distribution contract binding missing")
    if ct.get("review_governance",{}).get("skipped_review_may_pass") is not False: findings.append("skipped review could pass")
    if d.get("discovery_semantics",{}).get("remote_fetch") is not False: findings.append("discovery remote fetch enabled")
    if not m.get("invariants"): findings.append("materialization contract missing")
    return findings
def gate(root: Path) -> dict[str,Any]:
    root=Path(root).resolve();cap=load_active_release_baseline(root).capability_count;findings=canonical_check(root);regressions=run_regressions();ecosystem=skill_ecosystem_gate(root);v13=skill_fabric_v13_gate(root);execution_closure=skill_execution_closure_gate(root)
    result="PASS" if not findings and regressions["result"]=="PASS" and ecosystem["result"]=="PASS" and v13["result"]=="PASS" and execution_closure["result"]=="PASS" else "FAIL"
    report={"schema":"fa3.skill-fabric-gate-report.v1","gate_id":GATE_ID,"gateset_id":GATESET_ID,"result":result,"findings":findings,"regressions":regressions,"agent_skills_ecosystem":ecosystem,"skill_fabric_v13":v13,"skill_execution_closure":execution_closure,"provider_specific":False,"capability_count":cap,"current_host_runtime_claim":False}
    out=root/"reports/skill-fabric-gate-report.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return report
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]));a=ap.parse_args();report=gate(Path(a.root));print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
