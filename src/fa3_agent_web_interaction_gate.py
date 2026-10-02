#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count

GATE_ID="FA3-AGENT-WEB-INTERACTION-GATESET-001"
PROFILE="FA3-SHARED-AGENT-WEB-INTERACTION-001"
CONTRACT="FA3-SHARED-AGENT-WEB-INTERACTION-CONTRACTS-001"
RAILS={"NATIVE_AGENT_CONTRACT","SEMANTIC_HTTP_BRIDGE","BROWSER_VISUAL"}
PROFILE_INVARIANTS={
 "NO_SILENT_RAIL_FALLBACK","LOWER_ASSURANCE_RAIL_CANNOT_INHERIT_HIGHER_ASSURANCE_AUTHORITY",
 "NATIVE_BEARER_OR_SECRET_CANNOT_SILENTLY_CROSS_TO_HTTP_OR_BROWSER_RAIL",
 "HTTP_SUCCESS_REDIRECT_OR_COOKIE_DOES_NOT_PROVE_BUSINESS_SUCCESS",
 "AMBIGUOUS_EFFECT_REQUIRES_RECONCILIATION_BEFORE_REDISPATCH",
 "NON_DELEGABLE_HUMAN_ACTION_NOT_EXPOSED_AS_AGENT_EXECUTABLE_CAPABILITY"
}
CONTRACTS={"AgentWebRailSelection","AgentWebEffectPreview","AgentWebApprovalBinding","AgentWebNativeReceipt","AgentWebSemanticHttpPlan","AgentWebAttemptReceipt","AgentWebOutcomeVerification","AgentWebReconciliationRequest","AgentWebNonDelegableHumanBoundary"}

def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError(str(p))
 return v

def gate(root:Path)->dict[str,Any]:
 root=root.resolve(); findings=[]
 req=[
  "canonical/profiles/FA3-SHARED-AGENT-WEB-INTERACTION-001.json",
  "canonical/contracts/FA3-SHARED-AGENT-WEB-INTERACTION-CONTRACTS-001.json",
  "canonical/profiles/FA3-WEB-AI-001.json","canonical/contracts/FA3-WEB-AI-CONTRACTS-001.json",
  "canonical/profiles/FA3-BROWSER-ACTION-RUNTIME-001.json","canonical/contracts/FA3-BROWSER-ACTION-RUNTIME-CONTRACTS-001.json",
  "canonical/profiles/FA3-SHARED-TOOL-ACTION-MEDIATION-001.json","canonical/contracts/FA3-SHARED-TOOL-ACTION-MEDIATION-CONTRACTS-001.json",
  "canonical/profiles/FA3-SHARED-CONVERSATION-SESSION-001.json","canonical/contracts/FA3-SHARED-CONVERSATION-SESSION-CONTRACTS-001.json",
  "canonical/profiles/FA3-SHARED-MULTIMODAL-SOURCE-001.json","canonical/contracts/FA3-SHARED-MULTIMODAL-SOURCE-CONTRACTS-001.json",
  "canonical/profiles/FA3-MCP-GATEWAY-001.json","canonical/contracts/FA3-MCP-GATEWAY-CONTRACTS-001.json"
 ]
 for rel in req:
  if not (root/rel).is_file(): findings.append({"code":"AWI-001","message":"required artifact missing","path":rel})
 if findings:return _report(findings)
 active=module_active_capability_count(__file__)
 p=load(root/req[0]); c=load(root/req[1])
 if p.get("id")!=PROFILE or p.get("capability_count")!=active or p.get("new_capability") is not False or p.get("new_architectural_authority") is not False: findings.append({"code":"AWI-002","message":"shared profile baseline/identity drift"})
 if c.get("id")!=CONTRACT or c.get("capability_count")!=active or c.get("new_capability") is not False or c.get("new_architectural_authority") is not False: findings.append({"code":"AWI-003","message":"shared contract baseline/identity drift"})
 if set(p.get("execution_rails",{}))!=RAILS: findings.append({"code":"AWI-004","message":"three-rail contract drift"})
 if not PROFILE_INVARIANTS.issubset(set(p.get("invariants",[]))): findings.append({"code":"AWI-005","message":"required fail-closed invariants missing"})
 if not CONTRACTS.issubset(set(c.get("contracts",[]))): findings.append({"code":"AWI-006","message":"required contract family incomplete"})
 for rel in [req[2],req[3],req[4],req[5],req[6],req[7],req[8],req[9],req[10],req[11],req[12],req[13]]:
  if load(root/rel).get("capability_count")!=active: findings.append({"code":"AWI-007","message":"active capability baseline drift","path":rel})
 med=load(root/req[6]); medc=load(root/req[7])
 for token in ["ACTION_PREVIEW_BINDS_CURRENT_STATE_OR_REVISION","DISPATCH_EFFECT_AND_OUTCOME_EVIDENCE_ARE_DISTINCT","AMBIGUOUS_EXTERNAL_EFFECT_REQUIRES_RECONCILIATION_BEFORE_REDISPATCH","NON_DELEGABLE_HUMAN_ACTION_NOT_AGENT_EXECUTABLE"]:
  if token not in med.get("invariants",[]): findings.append({"code":"AWI-008","message":"tool/action hardening missing","token":token})
 for token in ["EffectPreview","ApprovalBinding","EffectReceipt","OutcomeVerification","ExternalEffectReconciliation","NonDelegableHumanActionBoundary"]:
  if token not in medc.get("contracts",[]): findings.append({"code":"AWI-009","message":"tool/action contract hardening missing","token":token})
 conv=load(root/req[8]); convc=load(root/req[9])
 if "PRIVATE_CONTEXT_IS_NOT_SHARED_CONVERSATION_STATE" not in conv.get("invariants",[]): findings.append({"code":"AWI-010","message":"minimum-disclosure invariant missing"})
 for token in ["PrivateParticipantContext","MinimumDisclosureProjection","StructuredCoordinationSignal","SharedProposal","RatificationState"]:
  if token not in convc.get("contracts",[]): findings.append({"code":"AWI-011","message":"minimum-disclosure contract missing","token":token})
 mm=load(root/req[10]); mmc=load(root/req[11])
 if "DIRECT_STRUCTURED_SOURCE_PREFERRED_WHEN_RENDERED_PIXELS_ARE_NOT_EVIDENCE" not in mm.get("invariants",[]): findings.append({"code":"AWI-012","message":"direct semantic media invariant missing"})
 for token in ["DirectSemanticMediaReference","BoundedMediaRegion","StructuredVisualData","RenderedEvidenceRequirement"]:
  if token not in mmc.get("contracts",[]): findings.append({"code":"AWI-013","message":"direct semantic media contract missing","token":token})
 mcp=load(root/req[12]); mcpc=load(root/req[13])
 if mcp.get("remote_endpoint_admission",{}).get("tool_execution_during_default_diagnostics") is not False: findings.append({"code":"AWI-014","message":"MCP diagnostics may execute tools"})
 if mcpc.get("remote_endpoint_compatibility",{}).get("transport_success_is_business_success") is not False: findings.append({"code":"AWI-015","message":"MCP transport/business outcome boundary missing"})
 return _report(findings)

def _report(findings:list[dict[str,Any]])->dict[str,Any]:
 return {"schema":"fa3.agent-web-interaction-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not findings else "FAIL","findings":findings,"capability_count":module_active_capability_count(__file__),"capability_delta":0,"authority_delta":0,"runtime_promotion_claim":False}

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--report",default="reports/agent-web-interaction-gate-report.json"); a=ap.parse_args()
 r=gate(Path(a.root)); p=Path(a.root)/a.report; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print(json.dumps(r,indent=2,ensure_ascii=False)); return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
