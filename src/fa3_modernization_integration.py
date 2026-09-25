#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

MODEL_ROUTER="FA3-AUTH-MODEL-ROUTER-001"
HRB="FA3-AUTH-HOST-RESOURCE-BROKER-001"
SECURITY="FA3-AUTH-SECURITY-GOV-001"
KNOWLEDGE="FA3-KNOWLEDGE-001"
PROVIDER_RUNTIME="FA3-PROVIDER-RUNTIME-001"
AGENT_FEDERATION="FA3-AGENT-FEDERATION-001"

def _parse_utc(value:str)->datetime:
    text=str(value).strip()
    if text.endswith("Z"): text=text[:-1]+"+00:00"
    out=datetime.fromisoformat(text)
    if out.tzinfo is None: out=out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)

def inference_execution_valid(d:dict[str,Any])->bool:
    if d.get("model_router_authority")!=MODEL_ROUTER or d.get("resource_authority")!=HRB: return False
    if d.get("provider_runtime_profile")!=PROVIDER_RUNTIME or d.get("supply_chain_admitted") is not True: return False
    if d.get("silent_fallback") is not False or d.get("canonical_route_contains_physical_model_id") is not False: return False
    if bool(d.get("accelerator_requested",False)) and not str(d.get("hrb_lease_id","")).strip(): return False
    return True

def runtime_enforcement_valid(d:dict[str,Any])->bool:
    if d.get("security_authority")!=SECURITY or d.get("provider_is_authority") is not False: return False
    if d.get("direct_unscoped_host_mutation") is not False: return False
    phase=d.get("phase")
    if phase not in {"OBSERVE","SHADOW_ENFORCE","ENFORCE"}: return False
    if phase=="ENFORCE" and not (d.get("policy_authorized") is True and d.get("operation_prevention_proven") is True and str(d.get("policy_receipt","")).strip()): return False
    return True

def usage_rights_valid(asset:dict[str,Any],*,requested_purpose:str,now:datetime|None=None)->bool:
    required={"rights_asset_id","subject_ref","asset_type","issuer","valid_from","valid_until","allowed_purposes","forbidden_purposes","source_asset_hashes","signature","signature_key_id","evidence_refs"}
    if not required.issubset(asset): return False
    if asset.get("signature_verified") is not True or asset.get("issuer_trusted") is not True: return False
    if asset.get("revocation_checked") is not True or asset.get("revoked") is True: return False
    if not str(asset.get("signature","")).strip() or not str(asset.get("signature_key_id","")).strip(): return False
    hashes=asset.get("source_asset_hashes")
    if not isinstance(hashes,list) or not hashes: return False
    allowed=asset.get("allowed_purposes"); forbidden=asset.get("forbidden_purposes")
    if not isinstance(allowed,list) or not isinstance(forbidden,list): return False
    if requested_purpose in forbidden or requested_purpose not in allowed: return False
    try: start=_parse_utc(str(asset["valid_from"])); end=_parse_utc(str(asset["valid_until"]))
    except Exception: return False
    current=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return end>start and start<=current<end

def knowledge_accelerator_valid(d:dict[str,Any])->bool:
    return all([d.get("knowledge_authority")==KNOWLEDGE,d.get("provider_is_authority") is False,d.get("derived_rebuildable") is True,d.get("native_source_preserved") is True,d.get("embedding_model_self_selected") is False,d.get("direct_application_bypass") is False])

def finops_projection_valid(d:dict[str,Any])->bool:
    if d.get("hrb_financial_authority") is not False or d.get("derived_projection") is not True or d.get("authoritative_promotion_evidence") is not False: return False
    if d.get("tariff_source") in {None,"","HARDCODED"} or d.get("exchange_rate_source") in {None,"","HARDCODED"} or d.get("amortization_policy_source") in {None,"","HARDCODED"}: return False
    return bool(str(d.get("usage_receipt_ref","")).strip())

def ai_quality_evaluator_valid(d:dict[str,Any])->bool:
    return all([d.get("advisory_only") is True,d.get("model_router_authority")==MODEL_ROUTER,d.get("single_score_truth_authority") is False,bool(str(d.get("evaluation_trace_ref","")).strip())])

def cross_host_execution_valid(d:dict[str,Any])->bool:
    if d.get("coordination_profile")!=AGENT_FEDERATION or d.get("federation_is_resource_authority") is not False: return False
    if d.get("remote_resource_authority")!=HRB or d.get("remote_provider_runtime_admitted") is not True: return False
    if not str(d.get("remote_hrb_receipt","")).strip(): return False
    if not all(d.get(k) is True for k in ("authenticated_transport","signed_envelope","hop_bounded")): return False
    if d.get("production_cross_host_claim") is True:
        if d.get("distinct_host_identities_proven") is not True or d.get("cross_host_transport_proven") is not True: return False
        if d.get("local_multi_node_only") is True: return False
    return True

def structured_knowledge_metadata_valid(d:dict[str,Any])->bool:
    required={"schema_version","document_id","content_type","source_type","created_at","provenance","language","approval_state","evidence_refs"}
    if d.get("knowledge_authority")!=KNOWLEDGE or d.get("metadata_is_derived_projection") is not True: return False
    if d.get("native_source_preserved") is not True or d.get("domain_extension_replaces_core") is not False: return False
    if not required.issubset(d): return False
    if not str(d.get("document_id","")).strip() or not isinstance(d.get("evidence_refs"),list): return False
    if not isinstance(d.get("ai_generated"),bool) or not isinstance(d.get("human_modified"),bool): return False
    return True

def degraded_execution_valid(d:dict[str,Any])->bool:
    if d.get("silent_fallback") is not False or d.get("explicit_reroute_policy") is not True: return False
    if d.get("new_resource_admission") is not True: return False
    if not str(d.get("original_route_evidence","")).strip(): return False
    if not str(d.get("reroute_receipt","")).strip() or not str(d.get("execution_receipt","")).strip(): return False
    return True
