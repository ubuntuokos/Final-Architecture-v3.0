#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
GATE_ID="FA3-BROWSER-SESSION-INTERACTION-GATESET-001"
PROFILE_ID="FA3-BROWSER-SESSION-INTERACTION-001"
PROVIDER_ID="FA3-PROVIDER-BROWSER-SESSION-BRIDGE-001"
EXPECTED_EXTENSION_ID="hkcdjepmkpeglfgejcejjdpdidinipdc"
ACTION_IDS={"browser.session.start","browser.session.stop","browser.tab.list","browser.tab.borrow","browser.tab.return","browser.human_assistance.request","browser.human_assistance.cancel"}
REQUIRED_PROFILE_INVARIANTS={"USER_BROWSER_WINDOWS_OUT_OF_SCOPE_BY_DEFAULT","AGENT_WINDOW_SEPARATE_FROM_USER_WINDOWS","EXISTING_TAB_ACCESS_REQUIRES_EXPLICIT_TTL_BORROW","BORROW_DOES_NOT_GRANT_BROWSER_WIDE_ACCESS","PAGE_CONTENT_REMAINS_UNTRUSTED_EXTERNAL_INPUT","CREDENTIAL_COOKIE_TOKEN_EXPORT_FORBIDDEN","POPUP_OR_NEW_TAB_DOES_NOT_INHERIT_AUTHORITY","HUMAN_ASSISTANCE_DOES_NOT_EXPAND_AGENT_AUTHORITY","SESSION_STOP_OR_FAILURE_RETURNS_OR_REVOKES_BORROWED_TABS","RESUME_AFTER_HUMAN_ASSISTANCE_REQUIRES_FRESH_OBSERVATION_AND_AUTHORIZATION","REMOTE_BROWSER_SESSION_NOT_ADMITTED_BY_THIS_PROFILE"}
def loadj(path:Path)->dict[str,Any]:
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):raise ValueError(f"object required: {path}")
    return obj
def gate(root:Path)->dict[str,Any]:
    root=root.resolve();findings=[]
    required=["canonical/profiles/FA3-BROWSER-SESSION-INTERACTION-001.json","canonical/contracts/FA3-BROWSER-SESSION-INTERACTION-CONTRACTS-001.json","canonical/intents/FA3-BROWSER-SESSION-INTERACTION-APPLICATION-INTENT-001.json","canonical/assessments/FA3-BROWSER-SESSION-INTERACTION-REUSE-ASSESSMENT-001.json","canonical/providers/FA3-PROVIDER-BROWSER-SESSION-BRIDGE-001.json","canonical/browser-session-current-host-enforcement.json","canonical/FA3-GATE-BROWSER-SESSION-CURRENT-HOST-001.json","browser/fa3-session-extension/manifest.json","browser/fa3-session-extension/service_worker.js","libexec/fa3-browser-session-native-host.py","src/fa3_browser_session_bridge.py","src/fa3_browser_session_provider.py","src/fa3_browser_session_current_host_gate.py",".github/workflows/fa3-browser-session-current-host.yml","tests/test_browser_session_bridge.py","tests/test_browser_session_gate.py","docs/browser-session-interaction.md"]+[f"canonical/actions/{a}.json" for a in sorted(ACTION_IDS)]
    for rel in required:
        if not(root/rel).is_file():findings.append({"code":"BSI-001","message":"required artifact missing","path":rel})
    if findings:return{"schema":"fa3.browser-session-gate-report.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}
    p=loadj(root/"canonical/profiles/FA3-BROWSER-SESSION-INTERACTION-001.json")
    if p.get("id")!=PROFILE_ID or p.get("parent_profile")!="FA3-BROWSER-ACTION-RUNTIME-001":findings.append({"code":"BSI-002","message":"profile identity/parent drift"})
    if p.get("capability_count")!=143 or p.get("new_capability") is not False or p.get("new_architectural_authority") is not False:findings.append({"code":"BSI-003","message":"capability/authority invariant broken"})
    miss=sorted(REQUIRED_PROFILE_INVARIANTS-set(p.get("invariants",[])))
    if miss:findings.append({"code":"BSI-004","message":"profile invariants missing","missing":miss})
    hw=p.get("hardware_audit",{})
    if not(hw.get("vendor_neutral") is True and hw.get("cpu_only_viable") is True and hw.get("accelerator_cardinality")=="0..N"):findings.append({"code":"BSI-005","message":"Hardware Audit drift"})
    coexist=p.get("software_coexistence",{})
    if not(coexist.get("upstream_uninstall_required") is False and coexist.get("global_browser_config_hijack") is False and coexist.get("fixed_port") is False):findings.append({"code":"BSI-006","message":"software coexistence weakened"})
    c=loadj(root/"canonical/contracts/FA3-BROWSER-SESSION-INTERACTION-CONTRACTS-001.json");lease=c.get("lease",{})
    if not(lease.get("ttl_required") is True and lease.get("origin_scope_required") is True and lease.get("action_scope_required") is True and lease.get("explicit_human_or_policy_approval_required") is True):findings.append({"code":"BSI-007","message":"tab lease scope/approval contract incomplete"})
    if lease.get("logical_borrow_without_tab_reparenting_preferred") is not True:findings.append({"code":"BSI-008","message":"non-interfering logical borrow invariant missing"})
    tr=c.get("transport",{})
    if tr.get("preferred_existing_profile_bridge")!="BROWSER_EXTENSION_NATIVE_MESSAGING_TO_FA3_NAMESPACED_UNIX_SOCKET" or tr.get("fixed_tcp_listener_required") is not False:findings.append({"code":"BSI-009","message":"transport boundary drift"})
    intent=loadj(root/"canonical/intents/FA3-BROWSER-SESSION-INTERACTION-APPLICATION-INTENT-001.json");ns=intent.get("namespace_claims",{})
    if ns.get("socket_namespace")!="fa3/browser-session" or ns.get("upstream_uninstall_required") is not False or ns.get("default_port") is not None:findings.append({"code":"BSI-010","message":"ApplicationIntent coexistence namespace drift"})
    reuse=loadj(root/"canonical/assessments/FA3-BROWSER-SESSION-INTERACTION-REUSE-ASSESSMENT-001.json")
    if reuse.get("result")!="PASS" or reuse.get("new_authority_required") is not False:findings.append({"code":"BSI-011","message":"ReuseAssessment missing or not PASS"})
    provider=loadj(root/"canonical/providers/FA3-PROVIDER-BROWSER-SESSION-BRIDGE-001.json")
    if provider.get("architectural_authority") is not False or provider.get("parent_profile")!=PROFILE_ID or provider.get("cpu_only_supported") is not True:findings.append({"code":"BSI-012","message":"provider boundary invalid"})
    pt=provider.get("transport",{})
    if pt.get("browser_to_host")!="CHROMIUM_NATIVE_MESSAGING" or pt.get("host_to_fa3")!="NAMESPACED_UNIX_DOMAIN_SOCKET" or pt.get("fixed_tcp_port") is not False or pt.get("remote_browser")!="DENY":findings.append({"code":"BSI-013","message":"provider transport invalid"})
    if set(provider.get("action_ids",[]))!=ACTION_IDS|{"browser.action.execute"}:findings.append({"code":"BSI-014","message":"provider typed action surface drift"})
    m=loadj(root/"browser/fa3-session-extension/manifest.json");perms=set(m.get("permissions",[]))
    if m.get("manifest_version")!=3 or not{"nativeMessaging","tabs","windows","scripting"}.issubset(perms):findings.append({"code":"BSI-015","message":"MV3/native messaging extension permissions incomplete"})
    forbidden=perms&{"cookies","history","downloads","webRequest","webRequestBlocking","debugger"}
    if forbidden:findings.append({"code":"BSI-016","message":"forbidden broad extension permissions","permissions":sorted(forbidden)})
    if m.get("host_permissions")!=["http://127.0.0.1/*","http://localhost/*"]:findings.append({"code":"BSI-017","message":"default extension host permissions must remain loopback-only"})
    if set(m.get("optional_host_permissions",[]))!={"https://*/*","http://*/*"}:findings.append({"code":"BSI-018","message":"non-loopback host access must remain optional"})
    worker=(root/"browser/fa3-session-extension/service_worker.js").read_text()
    for token in("connectNative","logical_borrow_without_reparenting","ORIGIN_SCOPE_MISMATCH","APPROVAL_REQUIRED","lease.expired","PENDING_HUMAN","human_completion_claim"):
        if token not in worker:findings.append({"code":"BSI-019","message":"extension invariant token missing","token":token})
    bad=[x for x in("chrome.cookies","chrome.history","chrome.downloads","new WebSocket(","fetch(") if x in worker]
    if bad:findings.append({"code":"BSI-020","message":"extension direct broad/network surface forbidden","tokens":bad})
    native=(root/"libexec/fa3-browser-session-native-host.py").read_text()
    if "AF_UNIX" not in native or "FA3_BROWSER_SESSION_SOCKET" not in native or "XDG_RUNTIME_DIR" not in native:findings.append({"code":"BSI-021","message":"native host UDS namespace binding missing"})
    if "AF_INET" in native or "create_connection((" in native:findings.append({"code":"BSI-022","message":"native host TCP transport forbidden"})
    cur=loadj(root/"canonical/browser-session-current-host-enforcement.json")
    for key in("fail_closed","physical_browser_required","fa3_native_extension_required","native_messaging_required","namespaced_unix_socket_required","temporary_home_native_host_registration_required","real_hrb_admission_authorization_required","policy_approved_borrow_return_required","logical_borrow_without_tab_reparenting_required","bounded_browser_action_runtime_required","stale_binding_negative_required","origin_scope_negative_required","missing_approval_negative_required","lease_expiry_negative_required","human_assistance_overlay_required","cpu_only_viable","vendor_neutral"):
        if cur.get(key) is not True:findings.append({"code":"BSI-023","message":"current-host enforcement invariant missing","field":key})
    if cur.get("persistent_global_browser_config_mutation")!="DENY" or cur.get("synthetic_human_completion_claim")!="DENY" or cur.get("global_promotion_claim") is not False:findings.append({"code":"BSI-024","message":"current-host non-claim/coexistence invariant broken"})
    for aid in sorted(ACTION_IDS):
        a=loadj(root/"canonical/actions"/f"{aid}.json")
        if a.get("id")!=aid or a.get("resources",{}).get("hrb_required") is not True or a.get("resources",{}).get("accelerator_required") is not False or a.get("evidence",{}).get("required") is not True:findings.append({"code":"BSI-025","message":"typed action HRB/evidence boundary invalid","action":aid})
    for aid in("browser.tab.borrow","browser.human_assistance.request"):
        if loadj(root/"canonical/actions"/f"{aid}.json").get("security",{}).get("approval")!="explicit":findings.append({"code":"BSI-026","message":"explicit approval missing","action":aid})
    impl=(root/"src/fa3_browser_session_current_host_gate.py").read_text()
    for token in("/usr/local/bin/fa3-host-resource-broker-admission","--headless=new","temporary_profile_scope","human_assistance_completion_proven","real_existing_user_profile_login_proven","global_promotion_claim"):
        if token not in impl:findings.append({"code":"BSI-027","message":"physical gate evidence boundary token missing","token":token})
    return{"schema":"fa3.browser-session-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not findings else"FAIL","findings":findings,"capability_count":143,"capability_delta":0,"authority_delta":0,"current_host_runtime_claim":False,"human_completion_claim":False,"global_promotion_claim":False}
def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--report",default="reports/browser-session-gate-report.json");a=ap.parse_args()
    root=Path(a.root).resolve();r=gate(root);p=root/a.report;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2));return 0 if r["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
