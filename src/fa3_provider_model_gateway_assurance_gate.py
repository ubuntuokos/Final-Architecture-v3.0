#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def evaluate():
 p=load(ROOT/"canonical/profiles/FA3-PROVIDER-MODEL-GATEWAY-ASSURANCE-001.json"); c=load(ROOT/"canonical/contracts/FA3-PROVIDER-MODEL-GATEWAY-ASSURANCE-CONTRACTS-001.json"); d=load(ROOT/"canonical/decisions/FA3-DEC-DONOR-CAPABILITY-CONSUMER-GRAPH-2026-09-30.json"); f=[]
 def check(ok,code):
  if not ok:f.append(code)
 check(p.get("capability_count")==175 and p.get("new_capability") is False and p.get("new_architectural_authority") is False,"BASELINE_DRIFT")
 a=p.get("authority_boundaries",{}); check(a.get("model_provider_routing")=="FA3-AUTH-MODEL-ROUTER-001","MODEL_ROUTER_AUTHORITY_DRIFT"); check(a.get("mcp_tool_mediation")=="FA3-AUTH-MCP-GATEWAY-001","MCP_AUTHORITY_DRIFT"); check(a.get("host_resources")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","HRB_AUTHORITY_DRIFT")
 check(p.get("routing",{}).get("silent_fallback") is False and p.get("routing",{}).get("route_exhaustion")=="FAIL_EXPLICITLY","SILENT_FALLBACK_NOT_DENIED"); check(p.get("gateway_enforcement",{}).get("gateway_cannot_expand_router_candidate_set") is True,"GATEWAY_EXPANDS_ROUTER"); check(p.get("external_source_policy",{}).get("unregistered_analysis_sources_are_not_canonical_donors") is True,"UNREGISTERED_SOURCE_ADOPTION")
 check(c.get("new_capability") is False and c.get("new_architectural_authority") is False and c.get("capability_count")==175,"CONTRACT_BASELINE_DRIFT"); check("NO_SILENT_PROVIDER_OR_MODEL_FALLBACK" in c.get("invariants",[]),"CONTRACT_FALLBACK_DRIFT"); check(d.get("status")=="APPROVED_OWNER_POLICY" and d.get("capability_count")==175 and d.get("physical_runtime_promotion_claim") is False,"DECISION_DRIFT")
 return {"schema":"fa3.provider-model-gateway-assurance-gate-report.v1","result":"PASS" if not f else "FAIL","findings":f,"runtime_promotion":False}
if __name__=="__main__":
 r=evaluate(); print(json.dumps(r,indent=2)); raise SystemExit(0 if r["result"]=="PASS" else 2)
