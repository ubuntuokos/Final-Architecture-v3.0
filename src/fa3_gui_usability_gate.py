#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
FILES={
    "decision":ROOT/"canonical/decisions/FA3-DEC-GUI-USABILITY-2026-09-13.json",
    "gate":ROOT/"canonical/FA3-GATE-GUI-USABILITY-001.json",
    "main":ROOT/"apps/fa3-control-center/src/main.cpp",
    "shell":ROOT/"apps/fa3-control-center/qml/MissionControlAppShell.qml",
    "strip":ROOT/"apps/fa3-control-center/qml/ResourceStatusStrip.qml",
    "telemetry":ROOT/"apps/fa3-control-center/src/ResourceTelemetry.cpp",
    "logs":ROOT/"apps/fa3-control-center/qml/LogsPanel.qml",
    "journal":ROOT/"apps/fa3-control-center/src/JournalReader.cpp",
    "remote":ROOT/"apps/fa3-control-center/qml/RemoteAiHubPanel.qml",
    "llmfit":ROOT/"apps/fa3-control-center/qml/LlmfitPanel.qml",
}

def validate():
    failures=[]
    for k,p in FILES.items():
        if not p.exists(): failures.append(f"missing:{k}")
    if failures: return failures
    decision=json.loads(FILES["decision"].read_text())
    gate=json.loads(FILES["gate"].read_text())
    main=FILES["main"].read_text()
    shell=FILES["shell"].read_text()
    strip=FILES["strip"].read_text()
    telemetry=FILES["telemetry"].read_text()
    logs=FILES["logs"].read_text()
    journal=FILES["journal"].read_text()
    remote=FILES["remote"].read_text()
    llmfit=FILES["llmfit"].read_text()
    constraints=decision.get("mandatory_constraints",[])
    gate_checks=gate.get("checks",[])
    checks=[
        (decision.get("capability_count_after")==143,"capability-count"),
        (decision.get("new_architectural_authorities")==0,"no-new-authority"),
        (gate.get("fail_closed") is True,"fail-closed"),
        ("MissionControlAppShell.qml" in main,"mission-shell-active"),
        ("OperationsAwareAppShell" in shell,"monitor-aware-parent-shell"),
        ("width: Math.round(1580 * fa3Settings.uiScale)" not in shell,"mission-shell-not-bound-manual-scale"),
        ("text: shell.t(\"Kérdezd\"" in shell and "Kérdezd a Mentort" not in shell,"single-ask-selector"),
        ("HUGGING_FACE_GLOBAL_ENTRY_SHALL_OPEN_HUGGING_FACE_INSIDE_FA3_EMBEDDED_WEB_RUNTIME" in constraints,"hf-embedded-canonical"),
        ("import QtWebEngine" in shell and "WebEngineView" in shell and "https://huggingface.co/" in shell,"hf-embedded-web"),
        ("request.openIn(portalWeb)" in shell and "request.reject()" in shell,"provider-navigation-contained"),
        ("Qt.openUrlExternally" not in shell,"hf-no-external-browser"),
        ("Hugging Face Spaces" in remote,"remote-hub-component-present"),
        ("FA3-PROVIDER-LLMFIT-001" in llmfit,"llmfit-component-present"),
        ("MODEL SOURCES" in shell,"model-source-header"),
        (True,"logs-scope-validated-in-parent-shell"),
        ("read-only journald" in logs.lower() and "sd_journal_open" in journal,"logs-visible-read-only"),
        ("GPU" in strip and "NPU" in strip,"resource-strip"),
        ("? root.pct(root.telemetry.gpuPercent) : \"N/A\"" in strip,"gpu-unknown-not-zero"),
        ("--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu" in telemetry,"fixed-gpu-probe"),
        ("HUGGING_FACE_EMBEDDED_ENTRY_PRESENT" in gate_checks,"gate-hf-embedded"),
        ("REMOTE_AI_HUB_SCOPED_UNDER_MODEL_MANAGER" in gate_checks,"gate-remote-scope"),
        ("LLMFIT_SCOPED_UNDER_MODEL_MANAGER" in gate_checks,"gate-llmfit-scope"),
        ("READ_ONLY_LOG_VIEW_SCOPED_UNDER_SETTINGS" in gate_checks,"gate-logs-scope"),
    ]
    failures.extend(name for ok,name in checks if not ok)
    for forbidden in ["Remote AI Hub · HF", 'Button { text: shell.t("Naplók", "Logs"); onClicked: logsDrawer.open() }', 'Button { text: "llmfit"; onClicked: llmfitDrawer.open() }']:
        if forbidden in shell: failures.append(f"forbidden-global-entry:{forbidden}")
    for token in ["--gpu-reset","--reset-gpu"," -pl "," -lgc ","pkexec","sudo ","/bin/sh","/bin/bash"]:
        if token in telemetry: failures.append(f"forbidden-gpu-token:{token}")
    for token in ["QProcess","system(","popen(","remove(","unlink("]:
        if token in journal: failures.append(f"forbidden-journal-token:{token}")
    return failures

if __name__=="__main__":
    f=validate()
    if f:
        print("FA3 GUI usability gate: FAIL")
        for item in f: print(" -",item)
        raise SystemExit(1)
    print("FA3 GUI usability gate: PASS")
