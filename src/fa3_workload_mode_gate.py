#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
from fa3_release_baseline import load_active_release_baseline

GATESET_ID="FA3-WORKLOAD-MODE-GATESET-001"
P={
 "profile":"canonical/profiles/FA3-WORKLOAD-MODE-FRAMEWORK-001.json",
 "contract":"canonical/contracts/FA3-WORKLOAD-MODE-CONTRACTS-001.json",
 "intent":"canonical/intents/FA3-WORKLOAD-MODE-APPLICATION-INTENT-001.json",
 "assessment":"canonical/assessments/FA3-WORKLOAD-MODE-REUSE-ASSESSMENT-001.json",
 "decision":"canonical/decisions/FA3-DEC-WORKLOAD-MODE-MANDATORY-2026-10-02.json",
 "integration":"canonical/integrations/FA3-WORKLOAD-MODE-INTEGRATION-001.json",
 "materialization":"canonical/materialization/FA3-WORKLOAD-MODE-MATERIALIZATION-001.json",
 "mandatory":"canonical/FA3-MANDATORY-CORE-COMPONENTS-001.json",
 "gate":"canonical/FA3-GATE-WORKLOAD-MODE-001.json",
 "gate_registry":"canonical/FA3-GATE-REGISTRY-001.json",
 "policy":"canonical/enforcement-policy.json",
 "gui_registry":"canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
 "daemon_h":"apps/workload-mode/src/ModeManager.h",
 "daemon_cpp":"apps/workload-mode/src/ModeManager.cpp",
 "daemon_main":"apps/workload-mode/src/main.cpp",
 "ctl":"apps/workload-mode/src/workmodectl.cpp",
 "run":"apps/workload-mode/src/workmoderun.cpp",
 "bridge":"apps/workload-mode/src/fa3_workload_mode_bridge.cpp",
 "blender":"apps/workload-mode/integrations/blender/workload_mode_addon.py",
 "standalone_installer":"deployment/workload-mode/install.sh",
 "service":"deployment/workload-mode/workmoded.service",
 "bridge_service":"deployment/workload-mode/fa3-workload-mode-bridge.service",
 "current_host_collector":"evidence/collect-workload-mode-current-host.py",
 "current_host_gate":"src/fa3_workload_mode_current_host_gate.py",
 "gui_state_h":"apps/fa3-control-center/src/WorkloadModeStateService.h",
 "gui_state_cpp":"apps/fa3-control-center/src/WorkloadModeStateService.cpp",
 "gui_indicator":"apps/fa3-control-center/qml/WorkloadModeIndicator.qml",
 "gui_main":"apps/fa3-control-center/qml/Main.qml",
 "gui_cmake":"apps/fa3-control-center/CMakeLists.txt",
 "gui_cpp":"apps/fa3-control-center/src/main.cpp",
 "gui_installer":"deployment/fa3-gui/install.sh",
}
MANDATORY_PROFILES={"FULL","HOBBY","MINIMAL","HEADLESS","SINGLE_HOST","MULTI_HOST","CPU_ONLY","ACCELERATOR_ENABLED"}
CRITICAL={"SAFE_MODE","DEGRADED","CONFLICT","RESOURCE_PRESSURE","AUTHORITY_LOST"}

def load(root:Path,key:str)->dict[str,Any]:
    data=json.loads((root/P[key]).read_text(encoding="utf-8"))
    if not isinstance(data,dict): raise ValueError(key)
    return data

def gate(root:Path)->dict[str,Any]:
    root=root.resolve(); findings=[]
    missing=[v for v in P.values() if not (root/v).is_file()]
    if missing:
        return {"schema":"fa3.workload-mode-gate-report.v1","gate_id":GATESET_ID,"result":"FAIL","findings":[{"code":"WM-000","message":"required files missing","paths":missing}],"current_host_runtime_promotion_claim":False}
    try:
        d={k:load(root,k) for k in ("profile","contract","intent","assessment","decision","integration","materialization","mandatory","gate","gate_registry","policy","gui_registry")}
    except Exception as exc:
        return {"schema":"fa3.workload-mode-gate-report.v1","gate_id":GATESET_ID,"result":"FAIL","findings":[{"code":"WM-001","message":str(exc)}],"current_host_runtime_promotion_claim":False}
    count=load_active_release_baseline(root).capability_count
    p,c,i,a,dec,integ,mat,mandatory=(d[x] for x in ("profile","contract","intent","assessment","decision","integration","materialization","mandatory"))
    comp=next((x for x in mandatory.get("components",[]) if x.get("id")=="workload-mode"),{})
    rules=d["gui_registry"].get("rules",{})
    checks=[
      (count==175==p.get("capability_count")==c.get("capability_count")==a.get("capability_count_after")==dec.get("capability_count_after")==integ.get("capability_count")==mandatory.get("capability_count"),"WM-002","175 capability baseline drift"),
      (p.get("new_capability") is False and p.get("new_architectural_authority") is False and dec.get("new_capabilities")==0 and dec.get("new_architectural_authorities")==0 and integ.get("authority_delta")==0,"WM-003","capability or authority delta"),
      (i.get("declared_new_capabilities")==[] and i.get("proposed_authority_roles")==[] and a.get("result")=="PASS","WM-004","Reuse Discovery admission invalid"),
      (p.get("authority",{}).get("when_fa3_present")=="FA3-AUTH-HOST-RESOURCE-BROKER-001" and p.get("authority",{}).get("fa3_parallel_resource_authority_forbidden") is True,"WM-005","HRB exclusive authority boundary lost"),
      (set(mandatory.get("profiles",[]))>=MANDATORY_PROFILES and comp.get("requirement")=="MUST" and comp.get("optional") is False and comp.get("bypassable") is False and comp.get("required_for_all_profiles") is True,"WM-006","Workload Mode is not mandatory in every FA3 install profile"),
      (comp.get("game_mode_runtime_dependency") is False and comp.get("game_mode_bridge_support_required") is True,"WM-007","GameMode optional-runtime/mandatory-bridge boundary invalid"),
      (mandatory.get("installer_policy",{}).get("user_may_deselect_workload_mode") is False and mandatory.get("installer_policy",{}).get("first_use_install_for_workload_mode") is False and mandatory.get("installer_policy",{}).get("package_dependency_required") is True,"WM-008","mandatory installer policy weakened"),
      (p.get("safety",{}).get("automatic_overclock")=="DENY" and p.get("safety",{}).get("voltage_increase")=="DENY" and p.get("safety",{}).get("power_limit_increase")=="DENY" and p.get("safety",{}).get("persistent_sysctl_automatic")=="DENY","WM-009","Hardware Safety invariant weakened"),
      (p.get("hardware_audit",{}).get("cpu_only_viable") is True if isinstance(p.get("hardware_audit"),dict) else True,"WM-010","hardware audit invalid"),
      (integ.get("bindings",[{},{}])[1].get("authority")=="FA3-AUTH-HOST-RESOURCE-BROKER-001","WM-011","integration no longer delegates FA3 physical resources to HRB"),
      (mat.get("production_promotion_from_materialization") is False and mat.get("current_host_runtime_promotion_claim") is False and p.get("current_host",{}).get("current_host_runtime_promotion_claim") is False,"WM-012","document/static materialization overclaims current-host runtime"),
      (rules.get("workload_mode_indicator_required_on_all_primary_surfaces") is True and rules.get("workload_mode_indicator_inherited_from_common_shell") is True and rules.get("workload_mode_indicator_event_driven") is True and rules.get("workload_mode_indicator_color_only_forbidden") is True,"WM-013","global shared indicator registry rule missing"),
      (set(rules.get("workload_mode_critical_states_always_visible",[]))>=CRITICAL,"WM-014","critical mode states can be hidden"),
      (GATESET_ID in d["gate_registry"].get("mandatory_reference_gates",[]) and d["gate_registry"].get("mandatory_reference_gates")==d["policy"].get("mandatory_reference_gates"),"WM-015","mandatory Gate Registry/enforcement-policy mirror missing"),
      (a.get("current_host_runtime_promotion_claim") is False and a.get("global_promotion_claim") is False,"WM-016","Reuse Assessment overclaims promotion"),
      (p.get("gpu_telemetry",{}).get("hard_vram_quota_portable_guarantee") is False,"WM-017","portable hard VRAM quota is falsely claimed"),
    ]
    texts={k:(root/P[k]).read_text(encoding="utf-8") for k in ("daemon_h","daemon_cpp","daemon_main","ctl","run","bridge","blender","standalone_installer","service","bridge_service","current_host_collector","current_host_gate","gui_state_h","gui_state_cpp","gui_indicator","gui_main","gui_cmake","gui_cpp","gui_installer")}
    source_checks=[
      ("org.workloadmode.Manager1" in texts["daemon_h"] and "org.workloadmode.Manager1" in texts["daemon_main"],"WM-020","standalone D-Bus service contract missing"),
      ("com.feralinteractive.GameMode" in texts["daemon_cpp"] and "QueryStatus" in texts["daemon_cpp"],"WM-021","GameMode D-Bus observation bridge missing"),
      ("FA3-AUTH-HOST-RESOURCE-BROKER-001" in texts["bridge"] and 'peer"), QStringLiteral("FA3")' in texts["bridge"],"WM-022","FA3 bidirectional handshake source missing"),
      ("OBSERVED" in texts["daemon_cpp"] and "COORDINATED" in texts["daemon_cpp"] and "MANAGED" in texts["daemon_cpp"],"WM-023","external workload state taxonomy missing"),
      ("SYS_pidfd_open" in texts["daemon_cpp"] and "QSocketNotifier" in texts["daemon_h"],"WM-023A","pidfd process lifetime tracking missing"),
      ("--domain AI|RENDER|GAME" in texts["run"] and "QProcess" in texts["run"],"WM-024","generic coordinated workload wrapper missing"),
      ("render_init" in texts["blender"] and "render_complete" in texts["blender"] and "render_cancel" in texts["blender"],"WM-025","Blender/Bforartists render lifecycle adapter missing"),
      ("--fa3-required" in texts["standalone_installer"] and "enable --now workmoded.service" in texts["standalone_installer"],"WM-026","standalone/FA3-required installer path missing"),
      ("fa3-workload-mode-bridge.service" in texts["standalone_installer"],"WM-027","mandatory FA3 bridge service installation missing"),
      ("fa3WorkloadMode" in texts["gui_cpp"] and "WorkloadModeStateService" in texts["gui_cpp"],"WM-028","Control Center real backing state provider missing"),
      ("StateChanged" in texts["gui_state_cpp"] and "QDBusServiceWatcher" in texts["gui_state_h"] and "Hello" in texts["gui_state_cpp"],"WM-029","event-driven GUI handshake/state propagation missing"),
      ("WorkloadModeIndicator {" in texts["gui_main"] and "stateProvider: fa3WorkloadMode" in texts["gui_main"],"WM-030","shared shell indicator not mounted"),
      ("Accessible.name" in texts["gui_indicator"] and "ToolTip" in texts["gui_indicator"] and "Popup" in texts["gui_indicator"],"WM-031","indicator accessibility/detail surface incomplete"),
      ("deployment/workload-mode/install.sh\" --fa3-required" in texts["gui_installer"],"WM-032","existing FA3 GUI installer does not enforce mandatory Workload Mode install"),
      ("qml/WorkloadModeIndicator.qml" in texts["gui_cmake"] and "WorkloadModeStateService.cpp" in texts["gui_cmake"],"WM-033","GUI build does not include shared Workload Mode UI/state components"),
    ]
    checks.extend(source_checks)
    for ok,code,msg in checks:
        if not ok: findings.append({"code":code,"message":msg})
    return {"schema":"fa3.workload-mode-gate-report.v1","gate_id":GATESET_ID,"result":"PASS" if not findings else "FAIL","findings":findings,"capability_delta":0,"authority_delta":0,"current_host_runtime_promotion_claim":False}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--json",action="store_true");ns=ap.parse_args()
    r=gate(Path(ns.root));print(json.dumps(r,indent=2,sort_keys=True) if ns.json else f"{GATESET_ID}: {r['result']}");return 0 if r["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
