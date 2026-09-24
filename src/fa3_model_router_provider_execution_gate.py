#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any
from fa3_model_router_provider_execution import CredentialCandidate, ExecutionDenied, ProviderExecutionManager, choose_credential, rebind_action, protocol_projection_status, execution_receipt

GATESET_ID="FA3-MODEL-ROUTER-PROVIDER-EXECUTION-GATESET-001"

def loadj(p: Path) -> dict[str, Any]:
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(f"object required: {p}")
    return v

def finding(code: str, message: str) -> dict[str, str]:
    return {"code":code,"severity":"P0","message":message}

def regressions() -> dict[str, Any]:
    good=[
      CredentialCandidate("FA3-PROVIDER-X-001","secretref:x/a","HEALTHY",True,2,0.2),
      CredentialCandidate("FA3-PROVIDER-X-001","secretref:x/b","QUOTA_LOW",True,0,0.8),
    ]
    checks=[]
    checks.append(("PEX-001", choose_credential(good,provider_id="FA3-PROVIDER-X-001").credential_ref=="secretref:x/a"))
    checks.append(("PEX-002", choose_credential(good,provider_id="FA3-PROVIDER-X-001",session_credential_ref="secretref:x/b").credential_ref=="secretref:x/b"))
    try:
        choose_credential([CredentialCandidate("FA3-PROVIDER-X-001","plaintext-key","HEALTHY",True)],provider_id="FA3-PROVIDER-X-001")
        checks.append(("PEX-003",False))
    except ExecutionDenied: checks.append(("PEX-003",True))
    checks.append(("PEX-004",rebind_action("RATE_LIMIT",True)=="INTRA_PROVIDER_REBIND"))
    checks.append(("PEX-005",rebind_action("RATE_LIMIT",False)=="MODEL_ROUTER_REEVALUATION_REQUIRED"))
    checks.append(("PEX-006",rebind_action("SECURITY_DENIED",True)=="FAIL_CLOSED"))
    checks.append(("PEX-007",protocol_projection_status(unsupported_fields=set(),security_relevant_fields={"pattern"})=="LOSSLESS"))
    checks.append(("PEX-008",protocol_projection_status(unsupported_fields={"pattern"},security_relevant_fields={"pattern"})=="UNSUPPORTED_FAIL_CLOSED"))
    checks.append(("PEX-009",protocol_projection_status(unsupported_fields={"maxLength"},security_relevant_fields=set())=="TRANSLATABLE_WITH_DECLARED_DEGRADATION"))
    receipt=execution_receipt(good[0],logical_route="chat-primary",physical_model="runtime-discovered",selection_reason="TEST")
    checks.append(("PEX-010","credential_ref_sha256" in receipt and "credential_ref" not in receipt and receipt["raw_credential_present"] is False))
    mgr=ProviderExecutionManager(good,lease_ttl_seconds=60,circuit_threshold=2,circuit_cooldown_seconds=10)
    first=mgr.select(provider_id="FA3-PROVIDER-X-001",session_id="s1",now=1.0)
    second=mgr.select(provider_id="FA3-PROVIDER-X-001",session_id="s1",now=2.0)
    checks.append(("PEX-011",first["credential_ref_sha256"]==second["credential_ref_sha256"] and second["reused_session_binding"] is True))
    rebound=mgr.record_failure(session_id="s1",error_class="RATE_LIMIT",now=3.0,retry_after_seconds=20)
    checks.append(("PEX-012",rebound["action"]=="INTRA_PROVIDER_REBIND" and rebound["cross_provider_transition"] is False and rebound["old_credential_ref_sha256"]!=rebound["new_credential_ref_sha256"]))
    one=ProviderExecutionManager([CredentialCandidate("P","secretref:p/only","HEALTHY",True)],circuit_threshold=1)
    one.select(provider_id="P",session_id="s2",now=1.0)
    cb=one.record_failure(session_id="s2",error_class="PROVIDER_5XX",now=2.0)
    checks.append(("PEX-013",cb["action"]=="MODEL_ROUTER_REEVALUATION_REQUIRED" and cb["cross_provider_transition"] is False))
    return {"result":"PASS" if all(v for _,v in checks) else "FAIL","total":len(checks),"passed":sum(v for _,v in checks),"cases":[{"case_id":k,"status":"PASS" if v else "FAIL"} for k,v in checks]}

def gate(root: Path) -> dict[str, Any]:
    f=[]
    router=loadj(root/"canonical/FA3-AUTH-MODEL-ROUTER-001.json")
    gateway=loadj(root/"canonical/profiles/FA3-LLM-GATEWAY-001.json")
    p=loadj(root/"canonical/profiles/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-001.json")
    proto=loadj(root/"canonical/profiles/FA3-LLM-PROTOCOL-COMPAT-001.json")
    enf=loadj(root/"canonical/model-router-provider-execution-enforcement.json")
    assessment=loadj(root/"canonical/assessments/FA3-ANTIGRAVITY-DERIVATION-ASSESSMENT-2026-09-24.json")
    decision=loadj(root/"canonical/decisions/FA3-DEC-ANTIGRAVITY-DERIVED-EXECUTION-MEDIATION-2026-09-24.json")
    decision_fabric=loadj(root/"canonical/profiles/FA3-DECISION-FABRIC-001.json")
    agent_definition=loadj(root/"canonical/profiles/FA3-AGENT-DEFINITION-001.json")
    gui=loadj(root/"canonical/FA3-GUI-SURFACE-REGISTRY-001.json")
    policy=loadj(root/"canonical/enforcement-policy.json")
    current_host=loadj(root/"canonical/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFORMANCE-001.json")
    if router.get("id")!="FA3-AUTH-MODEL-ROUTER-001" or router.get("data_plane",{}).get("single_routing_plane") is not True: f.append(finding("PEX-CANON-001","single Model Router authority drift"))
    if gateway.get("id")!="FA3-LLM-GATEWAY-001" or gateway.get("model_router_materialization",{}).get("role")!="REFERENCE_DATA_PLANE_ONLY": f.append(finding("PEX-CANON-002","LiteLLM data-plane boundary drift"))
    if p.get("parent_authority")!="FA3-AUTH-MODEL-ROUTER-001" or p.get("new_architectural_authority") is not False or p.get("capability_count")!=143: f.append(finding("PEX-CANON-003","provider execution profile governance drift"))
    if proto.get("parent_profile")!="FA3-LLM-GATEWAY-001" or proto.get("new_architectural_authority") is not False: f.append(finding("PEX-CANON-004","protocol compatibility boundary drift"))
    if enf.get("credential_policy",{}).get("raw_value_in_config") is not False or enf.get("credential_policy",{}).get("decision_fabric_secret_access") is not False: f.append(finding("PEX-SEC-001","credential secrecy boundary drift"))
    if enf.get("cross_provider_policy",{}).get("automatic_silent_transition") is not False: f.append(finding("PEX-ROUTE-001","silent cross-provider transition enabled"))
    if assessment.get("decision")!="REFERENCE_ONLY_CLEAN_ROOM_DERIVATION" or assessment.get("upstream_reference",{}).get("license")!="CC-BY-NC-SA-4.0": f.append(finding("PEX-LIC-001","clean-room license boundary missing"))
    if decision.get("capability_count")!=143 or decision.get("new_architectural_authority") is not False: f.append(finding("PEX-CANON-005","capability/authority accounting drift"))
    bind=decision_fabric.get("provider_execution_selection_binding",{})
    if bind.get("candidate_expansion")!="DENY" or bind.get("credential_value_access")!="DENY" or bind.get("provider_routing_authority") is not False: f.append(finding("PEX-DEC-001","Decision Fabric provider-execution boundary drift"))
    if "AGENT_DEFINITION_CANNOT_SELECT_PROVIDER_MODEL_OR_CREDENTIAL" not in agent_definition.get("invariants",[]): f.append(finding("PEX-AGENT-001","Agent Definition credential/provider boundary missing"))
    routes=gui.get("surfaces",[])
    model_route=next((r for r in routes if r.get("route_id")=="models.providers"),{})
    surface=next((r for r in model_route.get("children",[]) if r.get("surface_id")=="models.provider-execution"),{})
    if surface.get("direct_provider_execution") is not False or surface.get("direct_credential_entry") is not False or surface.get("credential_values_visible") is not False or surface.get("authority") is not False: f.append(finding("PEX-GUI-001","Provider Execution GUI boundary drift"))
    if GATESET_ID not in policy.get("mandatory_reference_gates",[]): f.append(finding("PEX-GLOBAL-001","provider execution gate not bound into global enforcement"))
    if current_host.get("status")!="EXECUTABLE_CURRENT_HOST_PRODUCER_MATERIALIZED_PENDING_REAL_PROVIDER_E2E" or current_host.get("synthetic_or_mock_provider_pass")!="FORBIDDEN" or current_host.get("global_promotion_claim") is not False: f.append(finding("PEX-CH-001","current-host fail-closed closure drift"))
    producer=root/"bin/fa3-model-router-provider-execution-current-host.py"
    config_schema=root/"canonical/contracts/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFIG-001.schema.json"
    workflow=root/".github/workflows/fa3-model-router-provider-execution-current-host.yml"
    provisioner=root/"bin/fa3-model-router-provider-execution-current-host-provision.sh"
    if not producer.is_file() or not config_schema.is_file() or not provisioner.is_file(): f.append(finding("PEX-CH-002","current-host producer/config/provisioning contract missing"))
    else:
        producer_text=producer.read_text(encoding="utf-8")
        provisioner_text=provisioner.read_text(encoding="utf-8")
        schema=loadj(config_schema)
        if "receipt_proves_provider" not in producer_text or "secret_broker_request" not in producer_text or '"projection": "UDS_SINGLE_SECRET"' not in producer_text or 'str(root / "bin/fa3-secretctl")' in producer_text or "credential_authentication_enforced" not in producer_text or "discover_working_chat_model" not in producer_text or "fa3.current-host-evidence-reference.v1" not in producer_text or schema.get("properties",{}).get("credentials",{}).get("minItems")!=2: f.append(finding("PEX-CH-003","real provider/direct Secret Broker peer/two-credential/auth-enforcement producer boundary missing"))
        if "evidence/reference/secret-broker-current-host-2026-09-24.json" not in provisioner_text or "/usr/local/libexec/fa3-secret-broker-current-host-root >/dev/null" in provisioner_text:
            f.append(finding("PEX-CH-005","provider probe must reuse admitted Secret Broker evidence instead of rerunning full Secret Broker qualification"))
        if "/var/lib/fa3/state/fa3-machine-state.img" not in provisioner_text or "/etc/credstore.encrypted/fa3-machine-state-key.cred" not in provisioner_text or "fa3-secret-vault-init" not in provisioner_text:
            f.append(finding("PEX-CH-006","provider probe must fail fast when the production Secret Broker vault is uninitialized"))
        if "cmp -s" not in provisioner_text or "fa3-secret-broker-install" not in provisioner_text:
            f.append(finding("PEX-CH-007","provider probe must fail fast when installed Secret Broker runtime drifts from repository HEAD"))
        if '"allowed_executables":[]' not in provisioner_text or '"allowed_systemd_units":[unit]' not in provisioner_text or '"allowed_executables":[python_exe]' in provisioner_text:
            f.append(finding("PEX-CH-008","provider secret consumer must bind dedicated user to exact transient systemd unit"))
    workflow_text=workflow.read_text(encoding="utf-8") if workflow.is_file() else ""
    if "fa3-model-router-provider-execution-current-host.py" not in workflow_text or "FA3_PROVIDER_EXECUTION_CURRENT_HOST_CONFIG" not in workflow_text: f.append(finding("PEX-CH-004","current-host workflow does not invoke producer/config path"))

    openai_provider_path=root/"canonical/providers/FA3-PROVIDER-OPENAI-API-001.json"
    openai_policy_path=root/"canonical/FA3-OPENAI-API-EXTERNAL-POLICY-001.json"
    openai_bridge=root/"bin/fa3-openai-loopback-bridge.py"
    openai_close=root/"bin/fa3-openai-provider-execution-current-host-close.sh"
    if not all(path.is_file() for path in (openai_provider_path,openai_policy_path,openai_bridge,openai_close)):
        f.append(finding("PEX-OPENAI-001","OpenAI explicit external provider evidence adapter is incomplete"))
    else:
        openai_provider=loadj(openai_provider_path)
        openai_policy=loadj(openai_policy_path)
        bridge_text=openai_bridge.read_text(encoding="utf-8")
        close_text=openai_close.read_text(encoding="utf-8")
        if not (
            openai_provider.get("architectural_authority") is False
            and openai_provider.get("normal_application_routing_enabled") is False
            and openai_provider.get("fa3_usage_policy",{}).get("silent_local_to_cloud_fallback")=="FORBIDDEN"
            and openai_provider.get("authority_boundaries",{}).get("model_routing")=="FA3-AUTH-MODEL-ROUTER-001"
            and openai_provider.get("authority_boundaries",{}).get("secrets")=="FA3-SECRET-BROKER-001"
        ):
            f.append(finding("PEX-OPENAI-002","OpenAI provider authority/routing/secrets boundary drift"))
        if not (
            openai_policy.get("provider_id")=="FA3-PROVIDER-OPENAI-API-001"
            and openai_policy.get("fail_closed") is True
            and openai_policy.get("activation",{}).get("automatic_activation") is False
            and openai_policy.get("activation",{}).get("silent_local_to_cloud_fallback") is False
            and openai_policy.get("egress",{}).get("host")=="api.openai.com"
            and openai_policy.get("secret_boundary",{}).get("authority")=="FA3-SECRET-BROKER-001"
        ):
            f.append(finding("PEX-OPENAI-003","OpenAI explicit external policy drift"))
        for token in ("https://api.openai.com/v1","/v1/models","/v1/chat/completions","fixed FA3 provider-execution probe content","credential_storage"):
            if token not in bridge_text:
                f.append(finding("PEX-OPENAI-004",f"OpenAI loopback bridge contract token missing: {token}"))
        for token in ("FA3-PROVIDER-OPENAI-API-001","FA3-OPENAI-API-EXTERNAL-POLICY-001","runtime discovery from this API project","fa3-model-router-provider-execution-current-host-provision.sh","/dev/tty","PROVISION_RC=$?","closure PASS withheld","fa3.model-router-provider-execution-current-host.v1","CURRENT_HOST_REAL_PROVIDER_EXECUTION_E2E_PASS","provisioning_cleanup_pass",'PROVIDER_RUN_ROOT="/run/fa3/model-router-provider-execution"','PROVIDER_RECEIPT="$PROVIDER_RUN_ROOT/current-host-receipt.json"'):
            if token not in close_text:
                f.append(finding("PEX-OPENAI-005",f"OpenAI closure harness contract token missing: {token}"))
        if "/run/fa3/model-router/provider-execution/current-host-receipt.json" in close_text or "trap cleanup EXIT INT TERM" in close_text:
            f.append(finding("PEX-OPENAI-006","OpenAI closure harness stale-receipt or non-exiting signal trap regression"))
        if "stale provider execution probe identity detected" not in provisioner_text or 'systemctl is-active --quiet "$PROBE_UNIT"' not in provisioner_text or 'pgrep -u "$PROBE_USER"' not in provisioner_text or 'userdel "$PROBE_USER"' not in provisioner_text or "stale reserved provider-execution SecretRef detected" not in provisioner_text or "stale reserved provider-execution policy detected" not in provisioner_text:
            f.append(finding("PEX-OPENAI-007","provider provisioner stale probe identity/SecretRef/policy recovery boundary missing"))
    reg=regressions()
    if reg["result"]!="PASS": f.append(finding("PEX-REG-001","provider execution regression matrix failed"))
    return {"schema":"fa3.gate-report.v1","gate_id":GATESET_ID,"result":"PASS" if not f else "FAIL","findings":f,"regressions":reg,"current_host_claim":False}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--report")
    a=ap.parse_args()
    report=gate(Path(a.root))
    out=Path(a.report) if a.report else Path(a.root)/"reports/model-router-provider-execution-gate-report.json"
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 0 if report["result"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
