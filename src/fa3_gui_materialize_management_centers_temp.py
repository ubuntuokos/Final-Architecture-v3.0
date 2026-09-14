from pathlib import Path

MAIN = Path("apps/fa3-control-center/qml/Main.qml")
CMAKE = Path("apps/fa3-control-center/CMakeLists.txt")
GATE = Path("src/fa3_gui_gate.py")
TOKEN = Path("apps/fa3-control-center/qml/TokenControlCenterPage.qml")
WORKFLOW = Path(".github/workflows/fa3-management-centers-materialize-temp.yml")
SELF = Path(__file__)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


s = MAIN.read_text(encoding="utf-8")
s = replace_once(
    s,
    '        {title: "Model Manager", detail: "Modellek felderítése és nyilvántartása", category: "FUNCTION", pageIndex: 6},\n',
    '        {title: "Model Manager", detail: "Modellek felderítése és nyilvántartása", category: "FUNCTION", pageIndex: 6},\n'
    '        {title: "Checkpoint Manager", detail: "Checkpoint, LoRA, VAE és adapter artifact governance", category: "FUNCTION", pageIndex: 20},\n'
    '        {title: "External Providers Setup", detail: "Külső/fizetős provider engedélyezés, budget és credential state", category: "FUNCTION", pageIndex: 21},\n'
    '        {title: "Token Control Center", detail: "Credential és AI token governance, budget, audit és költség", category: "FUNCTION", pageIndex: 22},\n',
    "search index",
)
s = replace_once(
    s,
    '                        NavButton { iconText: "☁"; label: "Remote AI Hub"; pageIndex: 1 }\n                        NavButton { iconText: "◉"; label: "RTD Providers"; pageIndex: 17 }\n',
    '                        NavButton { iconText: "☁"; label: "Remote AI Hub"; pageIndex: 1 }\n'
    '                        NavButton { iconText: "⇄"; label: "External Providers Setup"; pageIndex: 21 }\n'
    '                        NavButton { iconText: "◉"; label: "RTD Providers"; pageIndex: 17 }\n',
    "external provider nav",
)
s = replace_once(
    s,
    '                        NavButton { iconText: "▦"; label: "Model Manager"; pageIndex: 6 }\n                        NavButton { iconText: "⌕"; label: "Keresés"; pageIndex: 7 }\n',
    '                        NavButton { iconText: "▦"; label: "Model Manager"; pageIndex: 6 }\n'
    '                        NavButton { iconText: "◧"; label: "Checkpoint Manager"; pageIndex: 20 }\n'
    '                        NavButton { iconText: "#"; label: "Token Control Center"; pageIndex: 22 }\n'
    '                        NavButton { iconText: "⌕"; label: "Keresés"; pageIndex: 7 }\n',
    "checkpoint token nav",
)
chat = '''                ChatWorkspace {
                    role: window.askRole
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                    onCloseRequested: window.chatWorkspaceOpen = false
                    onNavigateRequested: function(pageIndex) {
                        window.chatWorkspaceOpen = false
                        window.webWorkspaceOpen = false
                        window.selectedIndex = pageIndex
                    }
                }
'''
centers = chat + '''
                CheckpointManagerPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                ExternalProvidersSetupPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                TokenControlCenterPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }
'''
s = replace_once(s, chat, centers, "stack pages")
MAIN.write_text(s, encoding="utf-8")

s = CMAKE.read_text(encoding="utf-8")
s = replace_once(
    s,
    'set_source_files_properties(qml/ChatWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS ChatWorkspace.qml)\n',
    'set_source_files_properties(qml/ChatWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS ChatWorkspace.qml)\n'
    'set_source_files_properties(qml/CheckpointManagerPage.qml PROPERTIES QT_RESOURCE_ALIAS CheckpointManagerPage.qml)\n'
    'set_source_files_properties(qml/ExternalProvidersSetupPage.qml PROPERTIES QT_RESOURCE_ALIAS ExternalProvidersSetupPage.qml)\n'
    'set_source_files_properties(qml/TokenControlCenterPage.qml PROPERTIES QT_RESOURCE_ALIAS TokenControlCenterPage.qml)\n',
    "cmake aliases",
)
s = replace_once(
    s,
    '        qml/ChatWorkspace.qml\n',
    '        qml/ChatWorkspace.qml\n'
    '        qml/CheckpointManagerPage.qml\n'
    '        qml/ExternalProvidersSetupPage.qml\n'
    '        qml/TokenControlCenterPage.qml\n',
    "cmake qml files",
)
CMAKE.write_text(s, encoding="utf-8")

s = GATE.read_text(encoding="utf-8")
s = replace_once(
    s,
    '    "chat_qml": ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml",\n',
    '    "chat_qml": ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml",\n'
    '    "checkpoint_qml": ROOT / "apps/fa3-control-center/qml/CheckpointManagerPage.qml",\n'
    '    "external_providers_qml": ROOT / "apps/fa3-control-center/qml/ExternalProvidersSetupPage.qml",\n'
    '    "token_control_qml": ROOT / "apps/fa3-control-center/qml/TokenControlCenterPage.qml",\n',
    "gate required files",
)
s = replace_once(
    s,
    'NAVIGATION = ["Command Center", "RTD Providers", "Projects", "AI Studio", "Agents & Workflows", "Models & Providers", "Architecture", "Resources", "Security & Approvals", "Observability", "Evidence", "Integrations", "System"]',
    'NAVIGATION = ["Command Center", "RTD Providers", "Projects", "AI Studio", "Agents & Workflows", "Models & Providers", "Checkpoint Manager", "External Providers Setup", "Token Control Center", "Architecture", "Resources", "Security & Approvals", "Observability", "Evidence", "Integrations", "System"]',
    "gate navigation",
)
anchor = '''    if "property bool chatWorkspaceOpen" not in qml or "ChatWorkspace" not in qml or "window.chatWorkspaceOpen ? 19" not in qml:
        failures.append("qml-role-chat-workspace-wiring-missing")
'''
checks = anchor + '''
    checkpoint_qml = REQUIRED["checkpoint_qml"].read_text(encoding="utf-8")
    for token in ["Checkpoint Manager", "SHA-256", "serialization/security", "lineage", "runtime compatibility", "EVIDENCE-GATED", "MODEL_CHECKPOINT_GOVERNANCE"]:
        if token not in checkpoint_qml: failures.append(f"qml-checkpoint-manager-surface-missing:{token}")
    external_qml = REQUIRED["external_providers_qml"].read_text(encoding="utf-8")
    for token in ["External Providers Setup", "externalProviders/enabled", "BROKER / SECRETREF ONLY", "FORBIDDEN IN GUI STORAGE", "FAIL-CLOSED", "monthlyBudget"]:
        if token not in external_qml: failures.append(f"qml-external-provider-setup-missing:{token}")
    token_qml = REQUIRED["token_control_qml"].read_text(encoding="utf-8")
    for token in ["Token Control Center", "FA3-TOKEN-GOVERNANCE-001", "Credentialek", "AI tokenhasználat", "Budgetek", "Költségek", "Audit", "Riasztások", "Házirendek", "VAULT / BROKER", "Plaintext secret storage forbidden"]:
        if token not in token_qml: failures.append(f"qml-token-control-center-missing:{token}")
    for token in ["CheckpointManagerPage", "ExternalProvidersSetupPage", "TokenControlCenterPage", 'pageIndex: 20', 'pageIndex: 21', 'pageIndex: 22']:
        if token not in qml: failures.append(f"qml-management-center-wiring-missing:{token}")
'''
s = replace_once(s, anchor, checks, "gate management checks")
GATE.write_text(s, encoding="utf-8")

s = TOKEN.read_text(encoding="utf-8").replace("External Providers Setup megnyitása", "Provider-token reconciliation tervezet")
TOKEN.write_text(s, encoding="utf-8")

if WORKFLOW.exists():
    WORKFLOW.unlink()
if SELF.exists():
    SELF.unlink()
