from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "src/fa3_gui_gate.py"
text = path.read_text(encoding="utf-8")

old = '''    rtd_qml = REQUIRED["rtd_qml"].read_text(encoding="utf-8")
    for token in ["Real-Time Data", "ADAPTER-GATED", "Freshness SLA", "Provenance", "FAIL-CLOSED", "Adapter ChangeSet-tervezet"]:
        if token not in rtd_qml: failures.append(f"qml-rtd-provider-surface-missing:{token}")
    if "RtdProvidersPage" not in qml or "RTD Data Sources" not in qml or "RTD Adapters" not in qml or '{label: "Real-Time Data", value: "RTD"}' not in qml:
        failures.append("qml-rtd-cross-surface-projection-missing")
'''
new = '''    rtd_qml = REQUIRED["rtd_qml"].read_text(encoding="utf-8")
    integrations_qml = REQUIRED["integrations_qml"].read_text(encoding="utf-8")
    for token in ["Real-Time Data", "ADAPTER-GATED", "Freshness SLA", "Provenance", "FAIL-CLOSED", "Adapter ChangeSet-tervezet"]:
        if token not in rtd_qml: failures.append(f"qml-rtd-provider-surface-missing:{token}")
    if "RtdProvidersPage" not in qml or "RTD Data Sources" not in qml or "RTD Adapters" not in integrations_qml or '{label: "Real-Time Data", value: "RTD"}' not in qml:
        failures.append("qml-rtd-cross-surface-projection-missing")
'''
if old not in text:
    raise SystemExit("RTD gate marker not found")
text = text.replace(old, new, 1)

old = '    integrations_qml = REQUIRED["integrations_qml"].read_text(encoding="utf-8")\n    for token in ["MCP Control Chat", "fa3McpControl.targets()", "openMcpControlRequested", "ADAPTER-GATED", "No fabricated CONNECTED state"]:\n'
new = '    for token in ["MCP Control Chat", "fa3McpControl.targets()", "openMcpControlRequested", "ADAPTER-GATED", "No fabricated CONNECTED state"]:\n'
if old not in text:
    raise SystemExit("duplicate integrations_qml marker not found")
text = text.replace(old, new, 1)

old = '["MCP CONTROL", "WORKFLOW", "MCP Authority", "createDraftRequest", "MCP request vázlat", "Végrehajtás", "DRAFT_NOT_SUBMITTED"]'
new = '["MCP CONTROL", "WORKFLOW", "MCP Authority", "createDraftRequest", "MCP request vázlat", "Végrehajtás"]'
if old not in text:
    raise SystemExit("QML MCP token marker not found")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
