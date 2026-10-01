#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from fa3_release_baseline import module_active_capability_count
from fa3_communications_contacts import reference_cases

PROFILE_ID = "FA3-COMMUNICATIONS-CONTACTS-SHARED-001"
CONTRACT_ID = "FA3-COMMUNICATIONS-CONTACTS-SHARED-CONTRACTS-001"
GATE_ID = "FA3-COMMUNICATIONS-CONTACTS-GATESET-001"
CURRENT_HOST_GATE_ID = "FA3-GATE-COMMUNICATIONS-CONTACTS-CURRENT-HOST-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)
P0_RULES = ["COMMUNICATIONS_FULL_STANDALONE_CONTEXT_LIMITED_EMBEDDED","COMMUNICATIONS_EMBEDDED_SCOPE_IS_INTERSECTION_NOT_UNION","COMMUNICATIONS_SECURITY_GATE_CHAIN_FAIL_CLOSED","COMMUNICATIONS_DIRECT_PROTOCOL_BYPASS_FORBIDDEN","COMMUNICATIONS_SECRET_BROKER_ONLY","COMMUNICATIONS_ATTACHMENT_SECURITY_REQUIRED","COMMUNICATIONS_DLP_REQUIRED_FOR_EGRESS_AND_EXPORT","COMMUNICATIONS_UNTRUSTED_MESSAGE_CONTENT_NEVER_SYSTEM_INSTRUCTION","COMMUNICATIONS_AI_OPTIONAL_AND_EXPLICIT","COMMUNICATIONS_AI_CONTEXT_MINIMIZATION_REQUIRED","COMMUNICATIONS_AI_PROMPT_INJECTION_GATE_REQUIRED","COMMUNICATIONS_AI_MODEL_ROUTER_AND_PROVIDER_ADMISSION_REQUIRED","COMMUNICATIONS_AI_HRB_REQUIRED_FOR_COMPUTE","COMMUNICATIONS_NO_SILENT_PROVIDER_OR_DEVICE_FALLBACK","COMMUNICATIONS_AGENT_SEND_DELETE_EXPORT_ADMIN_SEPARATELY_AUTHORIZED","COMMUNICATIONS_PLUGIN_PERMISSIONS_CONTEXT_SCOPED","COMMUNICATIONS_AUDIT_EVIDENCE_REQUIRED","COMMUNICATIONS_CURRENT_HOST_PHYSICAL_EVIDENCE_REQUIRED_FOR_PROMOTION","COMMUNICATIONS_SOFTWARE_COEXISTENCE_REQUIRED","COMMUNICATIONS_HARDWARE_SAFETY_REQUIRED","COMMUNICATIONS_ALL_INTERNAL_APPLICATIONS_HAVE_EXPLICIT_BINDING","COMMUNICATIONS_CAPABILITY_AND_AUTHORITY_COUNT_INVARIANT"]

def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}

def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    fs: list[dict[str, Any]] = []
    required = [
        "canonical/profiles/FA3-COMMUNICATIONS-CONTACTS-SHARED-001.json",
        "canonical/contracts/FA3-COMMUNICATIONS-CONTACTS-SHARED-CONTRACTS-001.json",
        "canonical/intents/FA3-COMMUNICATIONS-CONTACTS-SHARED-APPLICATION-INTENT-001.json",
        "canonical/assessments/FA3-COMMUNICATIONS-CONTACTS-SHARED-REUSE-ASSESSMENT-001.json",
        "canonical/decisions/FA3-DEC-COMMUNICATIONS-CONTACTS-SHARED-2026-09-30.json",
        "canonical/communications-contacts-enforcement.json",
        "canonical/FA3-GATE-COMMUNICATIONS-CONTACTS-001.json",
        "canonical/communications-contacts-current-host-enforcement.json",
        "canonical/FA3-GATE-COMMUNICATIONS-CONTACTS-CURRENT-HOST-001.json",
        "canonical/FA3-COMMUNICATIONS-CONTACTS-APPLICATION-BINDINGS-001.json",
        "src/fa3_communications_contacts.py",
        "src/fa3_communications_contacts_current_host_gate.py",
        "apps/fa3-communications-hub/CMakeLists.txt",
        "apps/fa3-communications-hub/qml/Main.qml",
        "apps/fa3-communications-hub/qml/CommunicationsSurface.qml",
        "docs/communications-contacts-shared.md",
    ]
    missing = [x for x in required if not (root / x).is_file()]
    if missing:
        fs.append(finding("CCS-001", "required materialization artifact missing", missing=missing))
    if fs:
        return {"schema":"fa3.communications-contacts-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":fs}

    p = loadj(root / required[0]); c = loadj(root / required[1]); a = loadj(root / required[3])
    enf = loadj(root / "canonical/communications-contacts-enforcement.json")
    sgr = loadj(root / "canonical/FA3-GATE-COMMUNICATIONS-CONTACTS-001.json")
    ch = loadj(root / "canonical/communications-contacts-current-host-enforcement.json")
    gr = loadj(root / "canonical/FA3-GATE-REGISTRY-001.json")
    pol = loadj(root / "canonical/enforcement-policy.json"); apps = loadj(root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json")

    if p.get("id") != PROFILE_ID or p.get("capability_count") != CAPABILITY_COUNT or p.get("new_capability") is not False or p.get("new_architectural_authority") is not False:
        fs.append(finding("CCS-002", "profile capability/authority invariant drift"))
    if p.get("surfaces", {}).get("standalone", {}).get("mode") != "FULL" or p.get("surfaces", {}).get("embedded", {}).get("mode") != "CONTEXT_LIMITED" or p.get("surfaces", {}).get("embedded", {}).get("scope_semantics") != "INTERSECTION":
        fs.append(finding("CCS-003", "full/embedded surface semantics drift"))
    if c.get("id") != CONTRACT_ID or c.get("capability_delta") != 0 or c.get("authority_delta") != 0 or c.get("no_silent_fallback") is not True:
        fs.append(finding("CCS-004", "contract identity/delta/fallback invariant drift"))
    expected_failure = {"UNKNOWN":"DENY","ERROR":"DENY","TIMEOUT":"DENY","NO_EVIDENCE":"DENY","POLICY_CONFLICT":"DENY"}
    if c.get("failure_policy") != expected_failure:
        fs.append(finding("CCS-005", "fail-closed failure policy drift"))
    if c.get("ai_untrusted_input_policy", {}).get("message_text_never_becomes_system_instruction") is not True:
        fs.append(finding("CCS-006", "untrusted message AI authority boundary weakened"))
    if a.get("result") != "PASS" or a.get("donor_review") != "REVIEWED_NO_MATCH" or a.get("donor_registry_sha256") != "740593d1df5c64bf0ff6e87f7baddbd0d01789e479e840af3f22f1e5d3abf1dd" or a.get("adopted_donors") != []:
        fs.append(finding("CCS-007", "reuse assessment is not bound to published main registry/no-match result"))
    if enf.get("gate_id") != GATE_ID or enf.get("fail_closed") is not True or enf.get("p0_invariants") != P0_RULES or enf.get("mandatory_rule_count") != len(P0_RULES):
        fs.append(finding("CCS-008", "static enforcement invariant drift"))
    if sgr.get("gateset_id") != GATE_ID or sgr.get("fail_closed") is not True or sgr.get("current_host_runtime_promotion_claim") is not False:
        fs.append(finding("CCS-008A", "static gate record boundary drift"))
    if ch.get("gate_id") != CURRENT_HOST_GATE_ID or ch.get("fail_closed") is not True or ch.get("simulated_evidence_accepted") is not False or ch.get("runtime_promotion_claim") is not False:
        fs.append(finding("CCS-008B", "current-host evidence boundary drift"))
    if GATE_ID not in gr.get("mandatory_reference_gates", []) or gr.get("mandatory_reference_gates") != pol.get("mandatory_reference_gates"):
        fs.append(finding("CCS-009", "global gate registry/enforcement mirror missing or drifted"))
    if pol.get("communications_contacts_mandatory_p0_rules") != P0_RULES:
        fs.append(finding("CCS-010", "global P0 rule binding drift"))
    app = {x.get("application_id"): x for x in apps.get("applications", [])}
    if "fa3.communications-hub" not in app:
        fs.append(finding("CCS-011", "Communications Hub missing from application inventory"))
    bindings = loadj(root / "canonical/FA3-COMMUNICATIONS-CONTACTS-APPLICATION-BINDINGS-001.json")
    internal_ids = {x.get("application_id") for x in apps.get("applications", []) if x.get("kind") == "INTERNAL_APPLICATION"}
    bound_ids = {x.get("application_id") for x in bindings.get("bindings", [])}
    if internal_ids != bound_ids or bindings.get("default_policy", {}).get("every_internal_application_requires_explicit_binding") is not True or bindings.get("default_policy", {}).get("effective_permission_semantics") != "INTERSECTION":
        fs.append(finding("CCS-011A", "internal application Communications binding coverage drift", internal=sorted(internal_ids), bound=sorted(bound_ids)))
    for row in bindings.get("bindings", []):
        if row.get("application_id") != "fa3.communications-hub" and (row.get("surface_mode") != "CONTEXT_LIMITED" or row.get("administrative_global_operations_available") is not False):
            fs.append(finding("CCS-011B", "embedded application binding may expose global/admin surface", application_id=row.get("application_id")))
    qml = (root / "apps/fa3-communications-hub/qml/CommunicationsSurface.qml").read_text(encoding="utf-8")
    for token in ("CONTEXT_LIMITED", "contextId", "openFullHub", "scope is the intersection"):
        if token not in qml:
            fs.append(finding("CCS-012", "embedded surface invariant token missing", token=token))
    cases = reference_cases()
    if not all(cases.values()):
        fs.append(finding("CCS-013", "executable authorization regressions failed", cases=cases))
    return {
        "schema":"fa3.communications-contacts-gate-report.v1","gate_id":GATE_ID,
        "profile_id":PROFILE_ID,"result":"PASS" if not fs else "FAIL","findings":fs,
        "regressions":cases,"capability_count":CAPABILITY_COUNT,"capability_delta":0,
        "authority_delta":0,"current_host_runtime_claim":False,
    }

if __name__ == "__main__":
    import sys
    report = gate(Path(__file__).resolve().parents[1])
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
