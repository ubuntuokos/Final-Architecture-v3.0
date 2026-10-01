#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def evaluate():
 p=load(ROOT/"canonical/profiles/FA3-PROVIDER-MODEL-GATEWAY-ASSURANCE-001.json")
 c=load(ROOT/"canonical/contracts/FA3-PROVIDER-MODEL-GATEWAY-ASSURANCE-CONTRACTS-001.json")
 d=load(ROOT/"canonical/decisions/FA3-DEC-PROVIDER-MODEL-GATEWAY-ASSURANCE-2026-09-30.json")
 links=load(ROOT/"canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
 la=load(ROOT/"canonical/assessments/FA3-DONOR-LARAVEL-AI-ROUTER-DETAILED-ASSESSMENT-2026-10-01.json")
 rr=load(ROOT/"canonical/assessments/FA3-DONOR-AI-RESOURCE-RADAR-DETAILED-ASSESSMENT-2026-10-01.json")
 count=module_active_capability_count(__file__); f=[]
 def check(ok,code):
  if not ok:f.append(code)
 check(p.get("capability_count")==count and p.get("new_capability") is False and p.get("new_architectural_authority") is False,"BASELINE_DRIFT")
 a=p.get("authority_boundaries",{})
 check(a.get("model_provider_routing")=="FA3-AUTH-MODEL-ROUTER-001","MODEL_ROUTER_AUTHORITY_DRIFT")
 check(a.get("mcp_tool_mediation")=="FA3-AUTH-MCP-GATEWAY-001","MCP_AUTHORITY_DRIFT")
 check(a.get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","HRB_AUTHORITY_DRIFT")
 check(a.get("secrets")=="FA3-SECRET-BROKER-001","SECRET_AUTHORITY_DRIFT")
 routing=p.get("routing",{})
 check(routing.get("silent_fallback") is False and routing.get("route_exhaustion")=="FAIL_EXPLICITLY","SILENT_FALLBACK_NOT_DENIED")
 check(routing.get("random_or_implicit_provider_selection")=="DENY","DONOR_RANDOM_ROUTING_NOT_DENIED")
 check(routing.get("telemetry_inputs",{}).get("may_expand_candidate_set") is False,"TELEMETRY_EXPANDS_CANDIDATES")
 check(p.get("gateway_enforcement",{}).get("gateway_cannot_expand_router_candidate_set") is True,"GATEWAY_EXPANDS_ROUTER")
 check(p.get("credential_policy",{}).get("authority")=="FA3-SECRET-BROKER-001" and p.get("credential_policy",{}).get("donor_local_credential_database_adopted") is False,"DONOR_SECRET_STORE_ADOPTED")
 coll=p.get("provider_intelligence",{}).get("collection_policy",{})
 check(coll.get("official_and_community_evidence_separated") is True and coll.get("community_discovery_cannot_upgrade_verification") is True,"SOURCE_VERIFICATION_BOUNDARY_DRIFT")
 check(coll.get("parser_drift_keeps_last_trusted_value") is True and coll.get("removal_requires_successful_confirmation_count")==2,"SOURCE_FRESHNESS_POLICY_DRIFT")
 check(c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count")==count,"CONTRACT_BASELINE_DRIFT")
 for inv in ("NO_SILENT_PROVIDER_OR_MODEL_FALLBACK","DONOR_LOCAL_SECRET_STORE_NOT_ADOPTED","DONOR_RANDOM_ROUTING_NOT_AUTHORITY","COMMUNITY_DISCOVERY_IS_NOT_VERIFIED_ADMISSION"):
  check(inv in c.get("invariants",[]),"CONTRACT_INVARIANT_MISSING:"+inv)
 check(d.get("status")=="APPROVED_OWNER_POLICY" and d.get("capability_count")==count and d.get("current_host_runtime_promotion_claim") is False,"DECISION_DRIFT")
 for row,donor in ((la,"FA3-DONOR-FERDIUNAL-LARAVEL-AI-ROUTER-001"),(rr,"FA3-DONOR-AI-RESOURCE-RADAR-AI-RESOURCE-RADAR-001")):
  check(row.get("donor_id")==donor and row.get("result")=="APPROVED_FOR_PATTERN_REUSE_ONLY","DONOR_ASSESSMENT_DRIFT:"+donor)
  check(row.get("authority_delta")==0 and row.get("capability_delta")==0 and row.get("runtime_dependency") is False,"DONOR_SCOPE_DRIFT:"+donor)
 usage={row.get("id"):row for row in links.get("donor_usage_records",[])}
 for uid,donor in (("FA3-USAGE-LARAVEL-AI-ROUTER-ASSURANCE-001","FA3-DONOR-FERDIUNAL-LARAVEL-AI-ROUTER-001"),("FA3-USAGE-AI-RESOURCE-RADAR-ASSURANCE-001","FA3-DONOR-AI-RESOURCE-RADAR-AI-RESOURCE-RADAR-001")):
  row=usage.get(uid,{})
  check(row.get("donor_id")==donor and row.get("usage_kind")=="CAPABILITY_PATTERN" and row.get("status")=="ACTIVE","DONOR_USAGE_EDGE_MISSING:"+uid)
  check(row.get("current_host_impact",{}).get("classification")=="NO_RUNTIME_IMPACT","DONOR_USAGE_HOST_IMPACT_DRIFT:"+uid)
 return {"schema":"fa3.provider-model-gateway-assurance-gate-report.v1","result":"PASS" if not f else "FAIL","findings":f,"capability_count":count,"runtime_promotion":False,"evaluated_donor_patterns":2}
if __name__=="__main__":
 r=evaluate(); print(json.dumps(r,indent=2)); raise SystemExit(0 if r["result"]=="PASS" else 2)
