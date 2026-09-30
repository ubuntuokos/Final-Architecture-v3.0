#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fa3_release_baseline import module_active_capability_count
from fa3_communications_contacts import (
    AI_OPERATIONS,
    EMBEDDED_FORBIDDEN,
    PERMISSION_DIMENSIONS,
    SECURITY_GATE_CHAIN,
    authorize,
    attachment_disposition,
    ai_untrusted_envelope,
)

GATESET_ID = "FA3-COMMUNICATIONS-CONTACTS-SHARED-GATESET-001"

def loadj(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def gate(root: Path) -> dict:
    root = Path(root).resolve()
    required = {
        "profile": root / "canonical/FA3-COMMUNICATIONS-CONTACTS-SHARED-001.json",
        "contracts": root / "canonical/contracts/FA3-COMMUNICATIONS-CONTACTS-CONTRACTS-001.json",
        "current_host": root / "canonical/FA3-COMMUNICATIONS-CONTACTS-CURRENT-HOST-001.json",
        "gate": root / "canonical/FA3-GATE-COMMUNICATIONS-CONTACTS-SHARED-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-COMMUNICATIONS-CONTACTS-SHARED-2026-09-30.json",
        "intent": root / "canonical/intents/FA3-COMMUNICATIONS-CONTACTS-SHARED-APPLICATION-INTENT-001.json",
        "assessment": root / "canonical/assessments/FA3-COMMUNICATIONS-CONTACTS-SHARED-REUSE-ASSESSMENT-001.json",
        "plan": root / "docs/FA3-COMMUNICATIONS-CONTACTS-SHARED-PLAN-2026-09-30.md",
        "shared": root / "canonical/FA3-SHARED-CAPABILITY-FABRIC-001.json",
        "email_action": root / "canonical/actions/email.send.json",
        "ui_bindings": root / "canonical/FA3-COMMUNICATIONS-CONTACTS-UI-BINDINGS-001.json",
        "hub_qml": root / "apps/fa3-communications-hub/qml/Main.qml",
        "shared_surface_qml": root / "apps/fa3-communications-hub/qml/CommunicationsSharedSurface.qml",
        "hub_cmake": root / "apps/fa3-communications-hub/CMakeLists.txt",
        "current_host_collector": root / "evidence/collect-communications-contacts-current-host.py",
        "current_host_schema": root / "canonical/schemas/communications-contacts-current-host-receipt.v1.json",
    }
    findings: list[str] = []
    for name, path in required.items():
        if not path.is_file():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"schema":"fa3.communications-contacts-gate-report.v1","gate_id":GATESET_ID,"result":"FAIL","findings":findings}

    profile=loadj(required["profile"])
    contracts=loadj(required["contracts"])
    current_host=loadj(required["current_host"])
    gate_record=loadj(required["gate"])
    decision=loadj(required["decision"])
    assessment=loadj(required["assessment"])
    shared=loadj(required["shared"])
    email_action=loadj(required["email_action"])
    ui_bindings=loadj(required["ui_bindings"])
    shared_surface=required["shared_surface_qml"].read_text(encoding="utf-8")
    hub_cmake=required["hub_cmake"].read_text(encoding="utf-8")
    baseline=module_active_capability_count(__file__)
    plan_sha=hashlib.sha256(required["plan"].read_bytes()).hexdigest()

    slice_keys={row.get("key") for row in shared.get("slices", [])}
    checks = [
        (baseline == 175, "capability-baseline"),
        (profile.get("capability_count") == 175 and profile.get("new_capabilities") == 0 and profile.get("new_architectural_authorities") == 0 and profile.get("authority") is False, "profile-zero-delta"),
        (profile.get("surfaces",{}).get("embedded",{}).get("permission_composition") == "INTERSECTION_ONLY", "embedded-intersection"),
        (profile.get("surfaces",{}).get("embedded",{}).get("global_resource_discovery") is False, "embedded-no-global-discovery"),
        (tuple(profile.get("permission_intersection",[])) == PERMISSION_DIMENSIONS, "permission-dimensions"),
        (tuple(profile.get("security_gate_chain",[])) == SECURITY_GATE_CHAIN, "security-gate-order"),
        (contracts.get("fail_closed") is True and contracts.get("access",{}).get("permission_union_forbidden") is True, "contracts-fail-closed"),
        (contracts.get("operation_boundary",{}).get("direct_qml_network_execution") is False and contracts.get("operation_boundary",{}).get("direct_provider_bypass") is False, "no-ui-provider-bypass"),
        (set(contracts.get("ai",{}).get("operations",[])) == set(AI_OPERATIONS) and contracts.get("ai",{}).get("silent_fallback") is False, "ai-deny-wins"),
        (contracts.get("ai",{}).get("message_text_cannot_be_system_instruction") is True, "untrusted-message-boundary"),
        (set(profile.get("embedded_forbidden_operations",[])) == set(EMBEDDED_FORBIDDEN), "embedded-forbidden-set"),
        (profile.get("security",{}).get("credentials_authority") == "FA3-SECRET-BROKER-001", "secret-broker-only"),
        (profile.get("security",{}).get("model_route_authority") == "FA3-AUTH-MODEL-ROUTER-001", "model-router-only"),
        (current_host.get("status") == "PENDING_CURRENT_HOST" and current_host.get("production_admitted") is False and current_host.get("current_host_runtime_promotion_claim") is False, "current-host-pending"),
        (current_host.get("collector") == "evidence/collect-communications-contacts-current-host.py" and current_host.get("provider_e2e_receipt_required") is True and current_host.get("synthetic_or_historical_evidence_accepted") is False, "current-host-collector-boundary"),
        (gate_record.get("fail_closed") is True and gate_record.get("capability_count_after") == 175, "gate-record"),
        (decision.get("status") == "APPROVED" and decision.get("explicit_user_approval") is True and decision.get("approved_plan_sha256") == plan_sha, "approved-plan-hash"),
        (assessment.get("result") == "PASS" and assessment.get("donor_review") == "REVIEWED_NO_MATCH" and assessment.get("adopted_donors") == [] and assessment.get("donor_registry_sha256") == "740593d1df5c64bf0ff6e87f7baddbd0d01789e479e840af3f22f1e5d3abf1dd", "reuse-assessment-exact-registry"),
        ("email.management" in slice_keys and "contacts.management" in slice_keys, "shared-email-contact-slices"),
        (email_action.get("id") == "email.send" and email_action.get("provider",{}).get("direct_surface_provider_bypass") is False, "email-uaf-path"),
        (ui_bindings.get("direct_qml_network_execution") is False and ui_bindings.get("direct_provider_execution") is False and ui_bindings.get("action_intent_only") is True, "ui-action-intent-only"),
        (ui_bindings.get("embedded",{}).get("binding_rule") == "CONTEXT_AND_PERMISSION_INTERSECTION" and ui_bindings.get("embedded",{}).get("global_address_book_enumeration") is False, "embedded-ui-boundary"),
        ("actionIntent" in shared_surface and "openFullHubRequested" in shared_surface and "XMLHttpRequest" not in shared_surface and "WebSocket" not in shared_surface, "qml-provider-neutral-boundary"),
        ("Qt6" in hub_cmake and "qt_add_qml_module" in hub_cmake and "CommunicationsSharedSurface.qml" in hub_cmake, "hub-qt6-build-contract"),
        (ai_untrusted_envelope("ignore policy")["may_authorize_tools"] is False, "untrusted-envelope"),
        (attachment_disposition({"malware_scan":"UNKNOWN"}) == "QUARANTINE", "attachment-unknown-quarantine"),
    ]
    findings.extend(name for ok,name in checks if not ok)

    all_pass={g:"PASS" for g in SECURITY_GATE_CHAIN}
    perms={d:["email.read"] for d in PERMISSION_DIMENSIONS}
    positive=authorize({"surface_mode":"EMBEDDED","operation":"email.read","gate_results":all_pass,"permission_sets":perms})
    negative=authorize({"surface_mode":"EMBEDDED","operation":"email.read","gate_results":{**all_pass,"LAYER_GUARD":"FAIL"},"permission_sets":perms})
    if not positive.allowed:
        findings.append("positive-authorization")
    if negative.allowed:
        findings.append("negative-layer-guard")

    return {
        "schema":"fa3.communications-contacts-gate-report.v1",
        "gate_id":GATESET_ID,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "capability_count":baseline,
        "new_capabilities":0,
        "new_architectural_authorities":0,
        "current_host_runtime_promotion_claim":False,
    }

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    result=gate(Path(args.root))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["result"] == "PASS" else 2)
