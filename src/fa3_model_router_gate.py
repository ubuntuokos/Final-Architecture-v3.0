#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
GATE_ID = "FA3-MODEL-ROUTER-GATESET-001"
REQUIRED_ROUTES = {
    "fa3-text-primary",
    "fa3-text-secondary",
    "fa3-pageindex-index",
    "fa3-pageindex-reason",
}
REQUIRED_RULES = {
    "ONE_CENTRAL_MODEL_ROUTER_AUTHORITY",
    "LITELLM_IS_DATA_PLANE_NOT_SECOND_ROUTING_AUTHORITY",
    "CANONICAL_ROUTES_MUST_NOT_PIN_PHYSICAL_PROVIDER",
    "CANONICAL_ROUTES_MUST_NOT_PIN_PHYSICAL_MODEL",
    "RUNTIME_PROVIDER_REQUIRES_CURRENT_HOST_ADMISSION_RECEIPT",
    "NO_SILENT_LOCAL_TO_CLOUD_FALLBACK",
    "NO_SILENT_PROVIDER_TO_PROVIDER_FALLBACK",
    "BUILTIN_PROVIDER_ADAPTER_DISCOVERY_IS_NON_EXHAUSTIVE",
    "EXPLICIT_ADMITTED_RUNTIME_REGISTRY_SUPPORTED",
    "ROUTING_DOES_NOT_GRANT_AI_COMMUNICATION_AUTHORITY",
    "ROUTER_CANNOT_EXPAND_CLOSED_APPLICATION_PARTICIPANT_SET",
    "AGENT_NATIVE_DIRECT_PROVIDER_OR_PHYSICAL_MODEL_PATH_FORBIDDEN",
    "AGENT_NATIVE_TYPED_ACTIONS_USE_UAF",
    "DECISION_FABRIC_ADVISORY_ONLY_NO_ROUTING_AUTHORITY",
    "DECISION_FABRIC_MODEL_CALLS_USE_CENTRAL_MODEL_ROUTER",
    "ROUTER_COMPONENT_PASS_CANNOT_CLAIM_FULL_429_RUNTIME_CLOSURE",
    "ROUTER_COMPONENT_PASS_CANNOT_PROMOTE_GLOBAL_RELEASE",
    "HRB_REMAINS_SOLE_RESOURCE_PLACEMENT_ACCELERATOR_AUTHORITY",
    "SECRET_AUTHORITY_REMAINS_SEPARATE_FROM_MODEL_ROUTER",
    "HARDWARE_AUDIT_VENDOR_NEUTRAL_NO_ACCELERATOR_VENDOR_REQUIREMENT",
    "CROSS_APP_AI_COMMUNICATION_DEFAULT_DENY_NOT_MODEL_ROUTER_AUTHORITY",
    "SECURITY_EMERGENCY_WAKE_CANNOT_BYPASS_ROUTER_OR_PROTECTED_GATEWAY",
    "AI_TO_AI_AUTHORITATIVE_SEMANTICS_MUST_REMAIN_HUMAN_AUDITABLE",
    "PRIVATE_MODEL_LANGUAGE_CODEBOOK_OR_SLANG_FORBIDDEN",
    "JEV_DECISION_FABRIC_APPLICABILITY_ASSESSMENT_REQUIRED",
    "JEV_ADAPTER_ONLY_AFTER_MODEL_ROUTER_CLOSURE",
    "CURRENT_HOST_ROUTER_RECEIPT_REQUIRED_FOR_CONSUMER_ADMISSION",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "authority": root / "canonical/FA3-AUTH-MODEL-ROUTER-001.json",
        "routes": root / "deployment/model-router/routes.json",
        "enforcement": root / "canonical/model-router-enforcement.json",
        "gateway": root / "canonical/profiles/FA3-LLM-GATEWAY-001.json",
        "baseline": root / "deployment/litellm/config.yaml",
        "service": root / "deployment/model-router/fa3-model-router.service.in",
        "materializer": root / "src/fa3_model_router_materialize.py",
        "provider_discovery": root / "src/fa3_model_router_provider_discovery.py",
        "collector": root / "evidence/collect-model-router-current-host.py",
        "host_gate": root / "src/fa3_model_router_current_host_gate.py",
        "installer": root / "bin/fa3-model-router-install",
        "workflow": root / ".github/workflows/fa3-model-router-current-host.yml",
    }
    missing = [str(p.relative_to(root)) for p in paths.values() if not p.is_file()]
    if missing:
        findings.append(finding("MR-000", "required Model Router artifact missing", missing=missing))
        return {"schema":"fa3.model-router-gate.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}

    authority = loadj(paths["authority"])
    routes = loadj(paths["routes"])
    enforcement = loadj(paths["enforcement"])
    gateway = loadj(paths["gateway"])
    baseline = paths["baseline"].read_text(encoding="utf-8")
    service = paths["service"].read_text(encoding="utf-8")
    materializer = paths["materializer"].read_text(encoding="utf-8")
    provider_discovery = paths["provider_discovery"].read_text(encoding="utf-8")
    workflow = paths["workflow"].read_text(encoding="utf-8")

    if authority.get("id") != AUTHORITY or authority.get("status") != "CANONICAL":
        findings.append(finding("MR-001", "central Model Router authority record mismatch"))
    if authority.get("materializes_existing_authority") is not True or authority.get("new_architectural_authority") is not False:
        findings.append(finding("MR-002", "Model Router must materialize the existing authority without authority delta"))
    data_plane = authority.get("data_plane", {})
    if data_plane.get("profile") != "FA3-LLM-GATEWAY-001" or data_plane.get("reference_runtime") != "LiteLLM Proxy" or data_plane.get("single_routing_plane") is not True:
        findings.append(finding("MR-003", "LiteLLM must be the single Model Router data plane"))
    if routes.get("authority") != AUTHORITY or routes.get("physical_provider_pins") is not False or routes.get("physical_model_pins") is not False:
        findings.append(finding("MR-004", "canonical routes must be authority-bound and physical-pin free"))
    route_rows = routes.get("routes", [])
    route_names = {str(x.get("route")) for x in route_rows if isinstance(x, dict)}
    if route_names != REQUIRED_ROUTES:
        findings.append(finding("MR-005", "required logical route set mismatch", routes=sorted(route_names)))
    for row in route_rows:
        if not isinstance(row, dict):
            findings.append(finding("MR-006", "route row is not an object"))
            continue
        if row.get("locality") != "LOCAL_ONLY" or row.get("external_fallback") != "DENY":
            findings.append(finding("MR-007", "baseline logical route must remain local-only without external fallback", route=row.get("route")))
        forbidden = {"provider_id","runtime_id","api_base","model","physical_model","physical_provider"}
        if forbidden.intersection(row):
            findings.append(finding("MR-008", "canonical logical route contains physical routing state", route=row.get("route")))
    if not REQUIRED_RULES.issubset(set(enforcement.get("rules", []))):
        findings.append(finding("MR-009", "Model Router enforcement rules incomplete"))
    bindings = gateway.get("authority_bindings", {})
    if bindings.get("provider_model_routing") != AUTHORITY:
        findings.append(finding("MR-010", "LLM Gateway is not bound to central Model Router authority"))
    if gateway.get("reference_implementation") != "LiteLLM Proxy":
        findings.append(finding("MR-011", "LiteLLM reference runtime drift"))
    if "model_list: []" not in baseline:
        findings.append(finding("MR-012", "committed LiteLLM baseline must not carry physical/runtime route materialization"))
    if "model:" in "\n".join(line for line in baseline.splitlines() if not line.lstrip().startswith("#")):
        findings.append(finding("MR-013", "committed LiteLLM baseline contains a model pin"))
    if "ExecStartPre=" not in service or "fa3_model_router_materialize.py" not in service or "fa3-model-router-serve" not in service:
        findings.append(finding("MR-014", "Model Router service does not materialize runtime selection before LiteLLM start"))
    if "IPAddressDeny=any" not in service or "IPAddressAllow=localhost" not in service:
        findings.append(finding("MR-015", "baseline Model Router service is not loopback-egress constrained"))
    required_materializer = (
        "receipt_proves_provider",
        "canonical_provider_ok",
        "fetch_models",
        "select_bindings",
        "physical_backend_pinned",
        "physical_model_pinned",
    )
    if any(token not in materializer for token in required_materializer):
        findings.append(finding("MR-016", "runtime materializer lacks provider admission/discovery/selection invariants"))
    required_discovery = (
        "CURRENT_HOST_LIVE_ENDPOINT_DISCOVERY",
        "provider_neutral",
        "physical_model_pins",
        "provider_set_exhaustive",
        "BUILTIN_REFERENCE_ADAPTERS_ONLY",
        "explicit_admitted_runtime_registry_supported",
    )
    if any(token not in provider_discovery for token in required_discovery):
        findings.append(finding("MR-017", "built-in current-host discovery is not explicitly non-exhaustive/provider-neutral"))

    invariants = authority.get("routing_invariants", {})
    if not (
        invariants.get("silent_provider_to_provider_fallback") == "FORBIDDEN"
        and invariants.get("routing_grants_ai_communication_authority") is False
        and invariants.get("routing_may_expand_application_participant_set") is False
        and invariants.get("consumer_direct_provider_or_physical_model_path") == "FORBIDDEN"
        and invariants.get("explicit_admitted_runtime_registry_supported") is True
        and invariants.get("builtin_provider_adapter_discovery_is_exhaustive") is False
    ):
        findings.append(finding("MR-018", "new provider/AI communication authority boundaries are incomplete"))

    consumers = authority.get("consumer_boundaries", {})
    agent_native = consumers.get("agent_native", {})
    decision_fabric = consumers.get("decision_fabric", {})
    ai_comms = consumers.get("ai_communication", {})
    if not (
        agent_native.get("model_access") == "CENTRAL_MODEL_ROUTER_ONLY"
        and agent_native.get("typed_action_contracts") == "FA3-UNIFIED-ACTION-FABRIC-001"
        and agent_native.get("direct_provider_or_physical_model_access") == "FORBIDDEN"
        and decision_fabric.get("mode") == "BOUNDED_ADVISORY_ONLY"
        and decision_fabric.get("deterministic_first") is True
        and decision_fabric.get("shadow_first") is True
        and decision_fabric.get("candidate_set_autonomous_expansion") == "FORBIDDEN"
        and decision_fabric.get("model_access") == "CENTRAL_MODEL_ROUTER_ONLY"
        and decision_fabric.get("physical_provider_or_model_selection") == "FORBIDDEN"
        and decision_fabric.get("context_envelope_required") is True
        and decision_fabric.get("decision_receipt_required") is True
        and decision_fabric.get("provenance_required") is True
        and decision_fabric.get("failure_policy_required") is True
        and decision_fabric.get("hitl_escalation_supported") is True
        and decision_fabric.get("project_radar_review_required") is True
        and ai_comms.get("policy") == "FA3-AI-COMMS-001"
        and ai_comms.get("router_grants_communication_authority") is False
        and ai_comms.get("router_may_expand_participant_set") is False
        and ai_comms.get("cross_application_default") == "DENY"
        and ai_comms.get("protected_gateway_required_for_cross_app") is True
        and ai_comms.get("router_is_cross_app_communication_gateway") is False
        and ai_comms.get("security_emergency_wake_bypass") is False
        and ai_comms.get("human_auditable_authoritative_semantics_required") is True
        and ai_comms.get("private_model_language_codebook_or_slang") == "FORBIDDEN"
    ):
        findings.append(finding("MR-019", "Agent Native / Decision Fabric / AI communication consumer boundaries drift"))

    jev = authority.get("decision_fabric_applicability", {})
    if not (
        jev.get("assessment_status") == "COMPLETED"
        and jev.get("applicable_to_router_core") is False
        and jev.get("applicable_to_router_consumers") is True
        and jev.get("integration_timing") == "AFTER_MODEL_ROUTER_CLOSURE"
        and jev.get("closed_candidate_set") == "NONE_IN_ROUTER_CORE"
        and jev.get("shadow_mode_for_future_adapter") is True
        and jev.get("admission_gate_required") is True
        and jev.get("provenance_license_security_supply_chain_gate_required") is True
        and jev.get("project_radar_review_required") is True
    ):
        findings.append(finding("MR-024", "Jev / Decision Fabric applicability assessment is incomplete or leaks into Router core"))

    evidence_boundaries = authority.get("evidence_boundaries", {})
    if not (
        evidence_boundaries.get("router_current_host_pass_scope") == "COMPONENT_CURRENT_HOST_ONLY"
        and evidence_boundaries.get("full_429_runtime_closure_claim") is False
        and evidence_boundaries.get("global_release_promotion_claim") is False
        and evidence_boundaries.get("provider_or_component_receipt_substitutes_global_evidence") is False
    ):
        findings.append(finding("MR-020", "component current-host evidence is not separated from FULL-429/release promotion"))

    hardware = authority.get("hardware_audit", {})
    if not (
        hardware.get("vendor_neutral") is True
        and hardware.get("cpu_only_supported_when_capability_allows") is True
        and hardware.get("required_accelerator_vendor") is None
        and hardware.get("required_accelerator_runtime") is None
        and hardware.get("resource_placement_and_accelerator_authority") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and hardware.get("silent_resource_fallback") == "FORBIDDEN"
    ):
        findings.append(finding("MR-021", "Hardware Audit / HRB authority boundary drift"))

    workflow_tokens = (
        "FA3_MODEL_ROUTER_PROVIDERS",
        ".config/fa3/model-router/providers.json",
        "explicit_admitted_registry",
        "builtin_reference_discovery",
        "if: steps.provider_source.outputs.mode == 'builtin_reference_discovery'",
    )
    if any(token not in workflow for token in workflow_tokens):
        findings.append(finding("MR-022", "current-host workflow still makes built-in provider adapters effectively mandatory"))

    if "provider_failover_performed" not in materializer or "silent provider->provider fallback" not in materializer:
        findings.append(finding("MR-023", "materializer does not fail closed against silent provider-to-provider fallback"))
    return {
        "schema": "fa3.model-router-gate.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "logical_routes": sorted(route_names),
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_claim": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
