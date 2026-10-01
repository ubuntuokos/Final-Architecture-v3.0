#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count
from fa3_shared_capability_fabric import capability_id_valid, internal_application_ids, universal_surface_consumers

GATESET_ID = "FA3-SHARED-CAPABILITY-FABRIC-GATESET-001"

def loadj(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def gate(root: Path) -> dict:
    root = Path(root).resolve()
    required = {
        "registry": root / "canonical/FA3-SHARED-CAPABILITY-FABRIC-001.json",
        "contracts": root / "canonical/contracts/FA3-SHARED-CAPABILITY-CONTRACTS-001.json",
        "bindings": root / "canonical/FA3-SHARED-CAPABILITY-APPLICATION-BINDINGS-001.json",
        "current_host": root / "canonical/FA3-SHARED-CAPABILITY-CURRENT-HOST-001.json",
        "gate": root / "canonical/FA3-GATE-SHARED-CAPABILITY-FABRIC-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-SHARED-CAPABILITY-FABRIC-2026-09-30.json",
        "plugin_bindings": root / "canonical/FA3-PLUGIN-EXTENSION-UI-BINDINGS-001.json",
        "docs": root / "docs/shared-capability-fabric.md",
        "email_action": root / "canonical/actions/email.send.json",
        "ui_component_profile": root / "canonical/profiles/FA3-UI-COMPONENT-FABRIC-001.json",
        "ui_component_contract": root / "canonical/contracts/FA3-UI-COMPONENT-FABRIC-CONTRACTS-001.json",
        "application_links": root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
    }
    findings: list[str] = []
    for name, path in required.items():
        if not path.is_file():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"schema":"fa3.shared-capability-gate-report.v1","gate_id":GATESET_ID,"result":"FAIL","findings":findings}

    registry=loadj(required["registry"])
    contracts=loadj(required["contracts"])
    bindings=loadj(required["bindings"])
    current_host=loadj(required["current_host"])
    gate_record=loadj(required["gate"])
    decision=loadj(required["decision"])
    plugin_bindings=loadj(required["plugin_bindings"])
    email_action=loadj(required["email_action"])
    ui_profile=loadj(required["ui_component_profile"])
    ui_contract=loadj(required["ui_component_contract"])
    baseline=module_active_capability_count(__file__)
    slices=registry.get("slices", [])
    ids=[item.get("id") for item in slices]
    keys=[item.get("key") for item in slices]
    caps=[cap for item in slices for cap in item.get("capability_ids", [])]
    email=next((item for item in slices if item.get("key")=="email.management"), {})
    internal_apps=internal_application_ids(root)
    email_consumers=universal_surface_consumers(root, "email.send")

    checks=[
        (baseline==175, "capability-baseline"),
        (registry.get("status")=="CANONICAL" and registry.get("capability_baseline")==175, "registry-canonical-baseline"),
        (registry.get("slice_count")==45 and len(slices)==45, "slice-count"),
        (len(ids)==len(set(ids)) and len(keys)==len(set(keys)), "slice-identity-unique"),
        (all(capability_id_valid(cap, baseline) for cap in caps), "existing-capability-bindings-only"),
        (registry.get("new_capabilities")==0 and registry.get("new_architectural_authorities")==0 and registry.get("authority") is False, "registry-authority-neutral"),
        (contracts.get("fail_closed") is True and contracts.get("new_capabilities")==0 and contracts.get("new_architectural_authorities")==0, "contracts-boundary"),
        (bindings.get("scope")=="ALL_FA3_APPLICATIONS" and bindings.get("application_local_duplicate_service_forbidden_when_shared_equivalent_verified") is True, "all-app-bindings"),
        (any(item.get("operation")=="email.send" and item.get("all_fa3_applications") is True for item in bindings.get("universal_surfaces", [])), "email-send-all-apps-binding"),
        (email.get("all_applications_send_surface") is True and "email.send" in email.get("universal_operations", []), "email-slice-universal-send"),
        (len(internal_apps)>0 and set(email_consumers)==set(internal_apps), "email-all-registered-internal-apps"),
        (email_action.get("schema")=="fa3.uaf.action-contract.v1" and email_action.get("id")=="email.send" and email_action.get("semantics",{}).get("mutating") is True and email_action.get("security",{}).get("authorization")=="required" and email_action.get("provider",{}).get("direct_surface_provider_bypass") is False, "email-action-contract"),
        ("email.send" in ui_profile.get("shared_action_projection",{}).get("universal_actions",[]) and ui_profile.get("shared_action_projection",{}).get("direct_qml_execution") is False and "ALL_FA3_APPLICATIONS" in ui_profile.get("consumer_surfaces",[]), "email-ui-component-projection"),
        ("email.send" in ui_contract.get("shared_action_surface",{}).get("universal_actions",[]) and ui_contract.get("shared_action_surface",{}).get("direct_network_or_provider_execution") is False, "email-ui-component-contract"),
        (registry.get("profile_policy", {}).get("hobby_is_not_external_service_denial") is True and registry.get("profile_policy", {}).get("external_service_workflows_allowed_in_hobby") is True, "hobby-external-service-access"),
        (registry.get("profile_policy", {}).get("silent_purchase_forbidden") is True, "silent-purchase-forbidden"),
        ({"color.management","source.management","texture.management","render","expense.request","expense.settlement","rfq.request","purchase.order","email.management"}.issubset(set(keys)), "late-added-slices-present"),
        (current_host.get("status")=="PENDING_CURRENT_HOST" and current_host.get("production_admitted") is False and current_host.get("current_host_runtime_promotion_claim") is False, "current-host-pending"),
        (gate_record.get("fail_closed") is True and gate_record.get("capability_count_after")==175, "gate-record"),
        (decision.get("status")=="CANONICAL_CLOSED" and decision.get("capability_delta")==0 and decision.get("authority_delta")==0, "decision-boundary"),
        (plugin_bindings.get("applicability_filter", {}).get("normal_view_not_applicable_hidden") is True, "plugin-not-applicable-hidden"),
        (plugin_bindings.get("applicability_filter", {}).get("same_resolver_for_shared_packages") is True, "plugin-shared-package-filter"),
    ]
    findings.extend(name for ok,name in checks if not ok)
    return {
        "schema":"fa3.shared-capability-gate-report.v1",
        "gate_id":GATESET_ID,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "slice_count":len(slices),
        "capability_count":baseline,
        "new_capabilities":0,
        "new_architectural_authorities":0,
        "current_host_runtime_promotion_claim":False,
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    result=gate(Path(args.root))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["result"]=="PASS" else 2)
