#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from urllib.parse import urlparse
from typing import Any
AUTHORITY="SECURITY_GOVERNANCE_POLICY_PLANE"
CLOUD_UPLOAD_PROVIDERS={"FA3-PROVIDER-PAGEINDEX-MCP-001"}
ALLOWED_ORIGINS={"https://app.pageindex.ai","https://api.pageindex.ai"}
def _sha(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def evaluate(request:dict[str,Any])->dict[str,Any]:
    forbidden={"secret","secrets","credential","token","api_key","apikey"}
    if forbidden.intersection({str(k).lower() for k in request}): raise ValueError("inline secret material forbidden")
    rid=str(request.get("request_id","")).strip(); source_ref=str(request.get("source_ref","")).strip()
    source_sha=str(request.get("source_sha256","")).strip().lower(); data_class=str(request.get("data_class","")).strip().upper()
    provider=str(request.get("destination_provider","")).strip(); uri=str(request.get("destination_uri","")).strip(); purpose=str(request.get("purpose","")).strip()
    approval=request.get("approval")
    if not all((rid,source_ref,provider,uri,purpose)) or len(source_sha)!=64 or not data_class: raise ValueError("incomplete asset egress request")
    parsed=urlparse(uri); origin=f"{parsed.scheme}://{parsed.netloc}".lower()
    status="DENY"; reason="LOCAL_ASSET_EGRESS_DEFAULT_DENY"; approval_id=None
    if provider in CLOUD_UPLOAD_PROVIDERS and origin in ALLOWED_ORIGINS and parsed.scheme=="https":
        if isinstance(approval,dict) and approval.get("status")=="APPROVED" and isinstance(approval.get("approval_id"),str) and approval["approval_id"].strip():
            status="ALLOW"; reason="EXPLICIT_APPROVED_PROVIDER_EGRESS"; approval_id=approval["approval_id"].strip()
        else: reason="EXPLICIT_APPROVAL_REQUIRED"
    material={"request_id":rid,"source_sha256":source_sha,"destination_provider":provider,"destination_origin":origin,"purpose":purpose,"status":status}
    return {"schema":"fa3.asset-egress-decision.v1","decision_id":"FA3-EGRESS-"+_sha(material)[:24].upper(),"authority":AUTHORITY,"status":status,"reason_code":reason,"request_id":rid,"source_ref":source_ref,"source_sha256":source_sha,"data_class":data_class,"destination_provider":provider,"destination_origin":origin,"purpose":purpose,"approval_id":approval_id,"global_promotion_claim":False}
def validate_decision(decision:dict[str,Any],*,source_sha256:str,provider_id:str)->None:
    if not isinstance(decision,dict) or decision.get("authority")!=AUTHORITY or decision.get("status")!="ALLOW": raise ValueError("asset egress decision not allowed")
    if decision.get("source_sha256")!=source_sha256.lower() or decision.get("destination_provider")!=provider_id: raise ValueError("asset egress decision scope mismatch")
