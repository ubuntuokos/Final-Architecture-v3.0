#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from fa3_release_baseline import module_active_capability_count

GATESET_ID = "FA3-PLUGIN-EXTENSION-MANAGEMENT-GATESET-001"

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def gate(root: Path) -> dict:
    root = Path(root).resolve()
    required = {
        "profile": root / "canonical/profiles/FA3-PLUGIN-EXTENSION-MANAGEMENT-001.json",
        "contracts": root / "canonical/contracts/FA3-PLUGIN-EXTENSION-CONTRACTS-001.json",
        "manifest": root / "canonical/contracts/FA3-PLUGIN-EXTENSION-MANIFEST-001.json",
        "bindings": root / "canonical/FA3-PLUGIN-EXTENSION-UI-BINDINGS-001.json",
        "current_host": root / "canonical/FA3-PLUGIN-EXTENSION-CURRENT-HOST-001.json",
        "gate": root / "canonical/FA3-GATE-PLUGIN-EXTENSION-MANAGEMENT-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-PLUGIN-EXTENSION-MANAGEMENT-2026-09-30.json",
        "intent": root / "canonical/intents/FA3-PLUGIN-EXTENSION-MANAGEMENT-APPLICATION-INTENT-001.json",
        "reuse": root / "canonical/assessments/FA3-PLUGIN-EXTENSION-MANAGEMENT-REUSE-ASSESSMENT-001.json",
        "decision_assessment": root / "canonical/assessments/FA3-PLUGIN-EXTENSION-MANAGEMENT-DECISION-ASSESSMENT-2026-09-30.json",
        "qml": root / "apps/fa3-control-center/qml/PluginExtensionManagerPage.qml",
        "main_qml": root / "apps/fa3-control-center/qml/Main.qml",
        "launcher": root / "apps/fa3-control-center/packaging/org.fa3.PluginExtensionManager.desktop",
    }
    findings: list[str] = []
    for name, path in required.items():
        if not path.is_file():
            findings.append(f"missing:{name}:{path.relative_to(root)}")
    if findings:
        return {"schema":"fa3.plugin-extension-gate-report.v1","gate_id":GATESET_ID,"result":"FAIL","findings":findings}

    p=_load(required["profile"]); c=_load(required["contracts"]); b=_load(required["bindings"])
    ch=_load(required["current_host"]); g=_load(required["gate"])
    intent=_load(required["intent"]); reuse=_load(required["reuse"]); decision_assessment=_load(required["decision_assessment"])
    count=module_active_capability_count(__file__)
    checks=[
        (count==175,"capability-baseline"),
        (p.get("capability_count")==175 and p.get("new_capability") is False and p.get("new_architectural_authority") is False,"profile-authority-count"),
        (c.get("fail_closed") is True and c.get("new_capabilities")==0 and c.get("new_architectural_authorities")==0,"contracts-boundary"),
        (b.get("scope")=="ALL_FA3_GUI_APPLICATIONS" and b.get("mandatory") is True,"all-app-binding"),
        (b.get("standalone_entry",{}).get("target_application_must_be_running") is False,"standalone-target-app"),
        (ch.get("production_admitted") is False and ch.get("current_host_runtime_promotion_claim") is False,"current-host-pending"),
        (g.get("fail_closed") is True and g.get("capability_count_after")==175,"gate-boundary"),
        (intent.get("schema")=="fa3.application-intent.v1" and intent.get("project_id")=="FA3-PLUGIN-EXTENSION-MANAGEMENT-001" and intent.get("declared_new_capabilities")==[] and intent.get("proposed_authority_roles")==[],"reuse-intent-boundary"),
        (reuse.get("schema")=="fa3.reuse-assessment.v1" and reuse.get("project_id")=="FA3-PLUGIN-EXTENSION-MANAGEMENT-001" and reuse.get("result")=="PASS" and reuse.get("new_capabilities")==0 and reuse.get("new_architectural_authorities")==0,"reuse-assessment-boundary"),
        (any(isinstance(x,dict) and x.get("source_family_id")=="FA3-KHRONOS-OPEN-STANDARDS-001" and x.get("review_status") in {"MATCHED","REVIEWED_NO_MATCH"} and x.get("authority") is False and x.get("automatic_selection") is False for x in reuse.get("mandatory_source_reviews",[])),"khronos-source-review"),
        (decision_assessment.get("schema")=="fa3.decision-fabric-assessment.v1" and "FA3-PLUGIN-EXTENSION-MANAGEMENT-001" in decision_assessment.get("covered_ids",[]) and decision_assessment.get("assessment")=="NOT_APPLICABLE","decision-adoption-boundary"),
    ]
    findings.extend(name for ok,name in checks if not ok)
    main=required["main_qml"].read_text(encoding="utf-8")
    page=required["qml"].read_text(encoding="utf-8")
    launcher=required["launcher"].read_text(encoding="utf-8")
    for token in ['"integrations.plugins-extensions"',"PluginExtensionManagerPage","Pluginok és extensionök"]:
        if token not in main:
            findings.append("main-qml:"+token)
    for token in ["ALL FA3","Installed","Catalog","Updates","Conflicts","Quarantine","Permissions","Evidence","AI"]:
        if token not in page:
            findings.append("manager-page:"+token)
    if "Exec=fa3-control-center --route integrations.plugins-extensions" not in launcher:
        findings.append("standalone-launcher")
    return {
        "schema":"fa3.plugin-extension-gate-report.v1",
        "gate_id":GATESET_ID,
        "result":"PASS" if not findings else "FAIL",
        "findings":findings,
        "capability_count":count,
        "new_capabilities":0,
        "new_architectural_authorities":0,
        "current_host_runtime_promotion_claim":False,
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    a=ap.parse_args()
    result=gate(Path(a.root))
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["result"]=="PASS" else 2)
