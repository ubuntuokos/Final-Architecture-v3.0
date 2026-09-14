from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"marker not found: {label}")
    return text.replace(old, new, 1)


# C++ authority-neutral MCP request service.
(ROOT / "apps/fa3-control-center/src/McpControlService.h").write_text(r'''#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class McpControlService final : public QObject
{
    Q_OBJECT
public:
    explicit McpControlService(QObject *parent = nullptr);

    Q_INVOKABLE QVariantList targets() const;
    Q_INVOKABLE QVariantMap authoritySnapshot(const QString &targetId) const;
    Q_INVOKABLE QVariantMap createDraftRequest(const QString &mode,
                                                const QString &targetId,
                                                const QString &prompt,
                                                const QString &attachmentsJson,
                                                const QString &riskHint) const;

private:
    bool isKnownTarget(const QString &targetId) const;
};
''', encoding="utf-8")

(ROOT / "apps/fa3-control-center/src/McpControlService.cpp").write_text(r'''#include "McpControlService.h"

#include <QDateTime>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUuid>

namespace {
QVariantMap targetRecord(const QString &id,
                         const QString &name,
                         const QString &adapter,
                         const QString &capabilities)
{
    return {
        {QStringLiteral("id"), id},
        {QStringLiteral("name"), name},
        {QStringLiteral("adapter"), adapter},
        {QStringLiteral("capabilities"), capabilities},
        {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")},
        {QStringLiteral("liveHealth"), QStringLiteral("N/A")},
        {QStringLiteral("executionAuthority"), false}
    };
}

QVariantMap stageRecord(const QString &id, const QString &state, const QString &detail)
{
    return {
        {QStringLiteral("id"), id},
        {QStringLiteral("state"), state},
        {QStringLiteral("detail"), detail}
    };
}
}

McpControlService::McpControlService(QObject *parent)
    : QObject(parent)
{
}

QVariantList McpControlService::targets() const
{
    return {
        targetRecord(QStringLiteral("AUTO"), QStringLiteral("Auto / FA3 router"), QStringLiteral("central-mcp-gateway"), QStringLiteral("Capability-based routing; no direct app invocation from GUI")),
        targetRecord(QStringLiteral("GIMP"), QStringLiteral("GIMP"), QStringLiteral("gimp-mcp"), QStringLiteral("Image edit, tools, layers, export")),
        targetRecord(QStringLiteral("KRITA"), QStringLiteral("Krita"), QStringLiteral("krita-mcp"), QStringLiteral("Canvas, layers, paint/edit, export")),
        targetRecord(QStringLiteral("BLENDER"), QStringLiteral("Blender"), QStringLiteral("blender-mcp"), QStringLiteral("Scene, objects, materials, camera, render")),
        targetRecord(QStringLiteral("BFORARTIST"), QStringLiteral("Bforartist"), QStringLiteral("blender-compatible-mcp"), QStringLiteral("Blender-compatible DCC capability surface")),
        targetRecord(QStringLiteral("KDENLIVE"), QStringLiteral("Kdenlive"), QStringLiteral("kdenlive-mcp"), QStringLiteral("Project, bin, timeline, effects, render")),
        targetRecord(QStringLiteral("OPENSHOT"), QStringLiteral("OpenShot"), QStringLiteral("openshot-mcp"), QStringLiteral("Project, clips, timeline, transitions, export")),
        targetRecord(QStringLiteral("INKSCAPE"), QStringLiteral("Inkscape"), QStringLiteral("inkscape-mcp"), QStringLiteral("SVG document, objects, paths, export")),
        targetRecord(QStringLiteral("ARDOUR"), QStringLiteral("Ardour"), QStringLiteral("ardour-mcp"), QStringLiteral("Session, transport, mixer, plugin parameters"))
    };
}

bool McpControlService::isKnownTarget(const QString &targetId) const
{
    const auto rows = targets();
    for (const auto &value : rows) {
        if (value.toMap().value(QStringLiteral("id")).toString() == targetId)
            return true;
    }
    return false;
}

QVariantMap McpControlService::authoritySnapshot(const QString &targetId) const
{
    const QString effectiveTarget = isKnownTarget(targetId) ? targetId : QStringLiteral("AUTO");
    QVariantList stages {
        stageRecord(QStringLiteral("CAPTURE"), QStringLiteral("READY"), QStringLiteral("GUI captures operator intent only")),
        stageRecord(QStringLiteral("PLANNER"), QStringLiteral("ADAPTER-GATED"), QStringLiteral("Model/tool planner must produce typed capability calls")),
        stageRecord(QStringLiteral("POLICY"), QStringLiteral("REQUIRED"), QStringLiteral("Central policy authority classifies and authorizes requested capabilities")),
        stageRecord(QStringLiteral("APPROVAL"), QStringLiteral("REQUIRED"), QStringLiteral("Mutating, destructive and external-side-effect actions require explicit approval")),
        stageRecord(QStringLiteral("MCP GATEWAY"), QStringLiteral("ADAPTER-GATED"), QStringLiteral("Only the central gateway may route an admitted tool call")),
        stageRecord(QStringLiteral("TARGET"), QStringLiteral("NOT-INVOKED"), effectiveTarget),
        stageRecord(QStringLiteral("EVIDENCE"), QStringLiteral("REQUIRED"), QStringLiteral("Execution result, artifact and provenance receipt must be recorded"))
    };

    return {
        {QStringLiteral("profileId"), QStringLiteral("FA3-MCP-CONTROL-CHAT-001")},
        {QStringLiteral("target"), effectiveTarget},
        {QStringLiteral("canExecute"), false},
        {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")},
        {QStringLiteral("reason"), QStringLiteral("Planner/gateway/app adapters do not yet provide verified runtime admission to this GUI")),
        {QStringLiteral("stages"), stages}
    };
}

QVariantMap McpControlService::createDraftRequest(const QString &mode,
                                                  const QString &targetId,
                                                  const QString &prompt,
                                                  const QString &attachmentsJson,
                                                  const QString &riskHint) const
{
    const QString normalizedMode = mode.trimmed().toUpper();
    if (normalizedMode != QStringLiteral("MCP CONTROL") && normalizedMode != QStringLiteral("WORKFLOW")) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unsupported MCP chat mode")}};
    }
    if (!isKnownTarget(targetId)) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unknown MCP target")}};
    }

    QJsonParseError parseError;
    QJsonDocument attachmentsDoc = QJsonDocument::fromJson(attachmentsJson.toUtf8(), &parseError);
    QJsonArray attachments;
    if (parseError.error == QJsonParseError::NoError && attachmentsDoc.isArray())
        attachments = attachmentsDoc.array();

    if (prompt.trimmed().isEmpty() && attachments.isEmpty()) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Prompt or attachment is required")}};
    }

    QString base = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    if (base.isEmpty())
        base = QDir::homePath() + QStringLiteral("/.local/share/fa3-control-center");
    const QString requestDir = base + QStringLiteral("/mcp-control/requests");
    if (!QDir().mkpath(requestDir)) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unable to create MCP request directory")}};
    }

    const QString requestId = QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QString path = requestDir + QLatin1Char('/') + requestId + QStringLiteral(".json");

    QJsonArray authority;
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("GUI_CAPTURE")}, {QStringLiteral("state"), QStringLiteral("READY")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("PLANNER")}, {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("POLICY")}, {QStringLiteral("state"), QStringLiteral("REQUIRED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("APPROVAL")}, {QStringLiteral("state"), QStringLiteral("REQUIRED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("MCP_GATEWAY")}, {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("TARGET")}, {QStringLiteral("state"), QStringLiteral("NOT-INVOKED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("EVIDENCE")}, {QStringLiteral("state"), QStringLiteral("REQUIRED")}});

    QJsonObject request {
        {QStringLiteral("schema_version"), 1},
        {QStringLiteral("request_id"), requestId},
        {QStringLiteral("profile_id"), QStringLiteral("FA3-MCP-CONTROL-CHAT-001")},
        {QStringLiteral("created_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("state"), QStringLiteral("DRAFT_NOT_SUBMITTED")},
        {QStringLiteral("mode"), normalizedMode},
        {QStringLiteral("target"), targetId},
        {QStringLiteral("prompt"), prompt},
        {QStringLiteral("attachments"), attachments},
        {QStringLiteral("risk_hint"), riskHint.trimmed().isEmpty() ? QStringLiteral("AUTO") : riskHint.trimmed().toUpper()},
        {QStringLiteral("authority_chain"), authority},
        {QStringLiteral("direct_tool_invocation_allowed"), false},
        {QStringLiteral("gui_self_approval_allowed"), false},
        {QStringLiteral("execution_without_policy_allowed"), false},
        {QStringLiteral("execution_without_evidence_allowed"), false}
    };

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unable to open MCP request draft for writing")}};
    }
    file.write(QJsonDocument(request).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unable to commit MCP request draft")}};
    }

    return {
        {QStringLiteral("ok"), true},
        {QStringLiteral("requestId"), requestId},
        {QStringLiteral("path"), path},
        {QStringLiteral("state"), QStringLiteral("DRAFT_NOT_SUBMITTED")},
        {QStringLiteral("target"), targetId},
        {QStringLiteral("summary"), QStringLiteral("Intent captured; planner, policy, approval, gateway and evidence stages remain authoritative and fail-closed.")}
    };
}
''', encoding="utf-8")

# Dedicated Integrations surface.
(ROOT / "apps/fa3-control-center/qml/IntegrationsPage.qml").write_text(r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property var mcpTargets: fa3McpControl.targets()

    signal openMcpControlRequested(string targetId)

    component Card: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        ColumnLayout {
            width: parent.width
            spacing: 14

            Item { Layout.preferredHeight: 8 }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                spacing: 3
                Label { text: "Integrations"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    Layout.fillWidth: true
                    text: "Desktop, DCC, editor, MCP és provider kapcsolatok. Az MCP Control Chat természetes nyelvű intentet rögzít, de nem kerülheti meg a planner → policy → approval → gateway → evidence authority-láncot."
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 156
                border.color: root.accent
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 18
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        RowLayout {
                            Label { text: "MCP Control Chat"; color: root.textPrimary; font.pixelSize: 17; font.bold: true }
                            Rectangle {
                                radius: 11
                                implicitWidth: mcpState.implicitWidth + 18
                                implicitHeight: 22
                                color: "#2a2113"
                                border.color: root.orange
                                Label { id: mcpState; anchors.centerIn: parent; text: "ADAPTER-GATED"; color: root.orange; font.pixelSize: 8; font.bold: true }
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "GIMP, Krita, Blender/Bforartist, Kdenlive, OpenShot, Inkscape, Ardour és további MCP-adapterek egységes beszélgetési vezérlőfelülete. A GUI csak intentet és terv-vázlatot készít; végrehajtási authority nincs benne."
                            color: root.textMuted
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                        Label { text: "FA3-MCP-CONTROL-CHAT-001"; color: root.accent; font.pixelSize: 9; font.bold: true }
                    }
                    Button { text: "MCP Control megnyitása"; onClicked: root.openMcpControlRequested("AUTO") }
                }
            }

            Label {
                Layout.leftMargin: 18
                text: "MCP célalkalmazások"
                color: root.textPrimary
                font.pixelSize: 13
                font.bold: true
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                columns: root.width > 1100 ? 3 : 2
                columnSpacing: 10
                rowSpacing: 10

                Repeater {
                    model: root.mcpTargets
                    delegate: Card {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 124
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 5
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: modelData.name; color: root.textPrimary; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true }
                                Label { text: modelData.state; color: root.orange; font.pixelSize: 8; font.bold: true }
                            }
                            Label { text: modelData.adapter; color: root.accent; font.pixelSize: 9 }
                            Label { Layout.fillWidth: true; text: modelData.capabilities; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap }
                            Item { Layout.fillHeight: true }
                            Button {
                                text: modelData.id === "AUTO" ? "Auto routing chat" : "Chat ezzel az appal"
                                onClicked: root.openMcpControlRequested(modelData.id)
                            }
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 138
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 16
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label { text: "Egyéb integrációk"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label { text: "Agent Clients · Goose / Open WebUI / OpenYak"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "RTD Adapters · REST / WebSocket / RSS / webhook / MCP"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Journal Share · e-mail és chat/export handoff"; color: root.textMuted; font.pixelSize: 9 }
                    }
                    Label {
                        text: "MCP adapter health: N/A\nNo fabricated CONNECTED state"
                        color: root.orange
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }

            Item { Layout.preferredHeight: 18 }
        }
    }
}
''', encoding="utf-8")

# Canonical authority contract.
contract = {
    "id": "FA3-MCP-CONTROL-CHAT-001",
    "title": "FA3 MCP Control Chat",
    "tier": "P0/MUST",
    "status": "CANONICAL",
    "new_capability": False,
    "new_architectural_authority": False,
    "capability_count_delta": 0,
    "purpose": "Natural-language intent capture and operator-facing orchestration surface for FA3 MCP-controlled desktop/DCC/editor applications.",
    "authority_chain": [
        {"stage": "GUI_CAPTURE", "authority": False, "rule": "Capture intent, attachments, target and risk hint only."},
        {"stage": "PLANNER", "authority": False, "rule": "Produce typed capability calls; adapter required."},
        {"stage": "POLICY", "authority": True, "rule": "Existing central policy authority classifies and admits capabilities."},
        {"stage": "APPROVAL", "authority": True, "rule": "Existing approval authority gates mutating/destructive/external-side-effect operations."},
        {"stage": "MCP_GATEWAY", "authority": True, "rule": "Existing central MCP mediation is the sole tool-routing boundary."},
        {"stage": "TARGET_ADAPTER", "authority": False, "rule": "App-specific MCP adapter executes only admitted typed calls."},
        {"stage": "EVIDENCE", "authority": True, "rule": "Existing observability/evidence authority records result, artifact and provenance."},
    ],
    "risk_policy": {
        "READ_ONLY": "Policy may admit without interactive approval only when the capability manifest proves read-only semantics.",
        "MUTATING": "Explicit operator approval required before gateway invocation.",
        "DESTRUCTIVE": "Preview/diff plus explicit operator approval required; fail closed if unavailable.",
        "EXTERNAL_SIDE_EFFECT": "Explicit approval and egress/provider policy required.",
        "UNKNOWN": "Fail closed and require planner classification plus explicit approval.",
    },
    "prohibited": [
        "GUI self-approval",
        "direct MCP tool invocation from QML",
        "shell or privilege bypass",
        "fabricated CONNECTED/PASS state",
        "execution without policy outcome",
        "execution without evidence receipt",
    ],
    "targets": ["AUTO", "GIMP", "KRITA", "BLENDER", "BFORARTIST", "KDENLIVE", "OPENSHOT", "INKSCAPE", "ARDOUR"],
    "runtime_state": "ADAPTER-GATED",
    "production_admitted": False,
}
(ROOT / "canonical/FA3-MCP-CONTROL-CHAT-001.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Build wiring.
cmake_path = ROOT / "apps/fa3-control-center/CMakeLists.txt"
cmake = cmake_path.read_text(encoding="utf-8")
cmake = replace_once(cmake,
    "    src/ModelLibraryService.cpp\n    src/ModelLibraryService.h\n",
    "    src/ModelLibraryService.cpp\n    src/ModelLibraryService.h\n    src/McpControlService.cpp\n    src/McpControlService.h\n",
    "cmake cpp")
cmake = replace_once(cmake,
    "set_source_files_properties(qml/LanguageControlPage.qml PROPERTIES QT_RESOURCE_ALIAS LanguageControlPage.qml)\n",
    "set_source_files_properties(qml/LanguageControlPage.qml PROPERTIES QT_RESOURCE_ALIAS LanguageControlPage.qml)\nset_source_files_properties(qml/IntegrationsPage.qml PROPERTIES QT_RESOURCE_ALIAS IntegrationsPage.qml)\n",
    "cmake qml alias")
cmake = replace_once(cmake,
    "        qml/LanguageControlPage.qml\n",
    "        qml/LanguageControlPage.qml\n        qml/IntegrationsPage.qml\n",
    "cmake qml module")
cmake_path.write_text(cmake, encoding="utf-8")

main_cpp_path = ROOT / "apps/fa3-control-center/src/main.cpp"
main_cpp = main_cpp_path.read_text(encoding="utf-8")
main_cpp = replace_once(main_cpp, '#include "ModelLibraryService.h"\n', '#include "ModelLibraryService.h"\n#include "McpControlService.h"\n', "main include")
main_cpp = replace_once(main_cpp, "    ModelLibraryService modelLibrary;\n", "    ModelLibraryService modelLibrary;\n    McpControlService mcpControl;\n", "main instance")
main_cpp = replace_once(main_cpp,
    '    engine.rootContext()->setContextProperty("fa3ModelLibrary", &modelLibrary);\n',
    '    engine.rootContext()->setContextProperty("fa3ModelLibrary", &modelLibrary);\n    engine.rootContext()->setContextProperty("fa3McpControl", &mcpControl);\n',
    "main context")
main_cpp_path.write_text(main_cpp, encoding="utf-8")

# Main shell wiring.
main_path = ROOT / "apps/fa3-control-center/qml/Main.qml"
main = main_path.read_text(encoding="utf-8")
main = replace_once(main,
    "    property bool chatWorkspaceOpen: false\n",
    "    property bool chatWorkspaceOpen: false\n    property string chatWorkspaceMode: \"ASSISTANT\"\n    property string mcpChatTarget: \"AUTO\"\n",
    "main chat props")
main = replace_once(main,
'''    function openRoleChat(roleName) {
        askRole = roleName
        webWorkspaceOpen = false
        chatWorkspaceOpen = true
    }
''',
'''    function openRoleChat(roleName) {
        askRole = roleName
        chatWorkspaceMode = "ASSISTANT"
        mcpChatTarget = "AUTO"
        webWorkspaceOpen = false
        chatWorkspaceOpen = true
    }

    function openMcpChat(targetId) {
        chatWorkspaceMode = "MCP CONTROL"
        mcpChatTarget = targetId && targetId.length > 0 ? targetId : "AUTO"
        webWorkspaceOpen = false
        chatWorkspaceOpen = true
    }
''', "main open chat functions")
main = replace_once(main,
    '        {title: "Integrations", detail: "Desktop, MCP és provider integrációk", category: "FUNCTION", pageIndex: 14},\n',
    '        {title: "Integrations", detail: "Desktop, MCP és provider integrációk", category: "FUNCTION", pageIndex: 14},\n        {title: "MCP Control Chat", detail: "GIMP, Krita, Blender, Kdenlive, OpenShot és más MCP-vezérelt alkalmazások természetes nyelvű orchestration felülete", category: "FUNCTION", pageIndex: 14},\n',
    "main search index")
main = replace_once(main,
    '                                    MenuItem { text: "Tanácsadó"; onTriggered: window.openRoleChat("Tanácsadó") }\n',
    '                                    MenuItem { text: "Tanácsadó"; onTriggered: window.openRoleChat("Tanácsadó") }\n                                    MenuSeparator {}\n                                    MenuItem { text: "MCP Control Chat"; onTriggered: window.openMcpChat("AUTO") }\n',
    "main ask menu")
old_integrations = '''                ModulePage {
                    pageTitle: "Integrations"
                    pageSubtitle: "Desktop, DCC, editor, MCP and provider connections"
                    cards: [
                        {title: "Creative Apps", subtitle: "Krita, GIMP, Kdenlive, Bforartist/Blender, Natron/Gaffer.", badge: "DESKTOP", tone: window.magenta},
                        {title: "Agent Clients", subtitle: "Goose, Open WebUI, OpenYak and related projections.", badge: "ROUTED", tone: window.accent},
                        {title: "MCP", subtitle: "Capabilities mediated through the central gateway.", badge: "GATED", tone: window.orange},
                        {title: "RTD Adapters", subtitle: "REST, WebSocket, RSS, webhook, MCP és local adapter kapcsolatok az RTD Providers számára.", badge: "ADAPTER", tone: window.cyan},
                        {title: "Journal Share", subtitle: "E-mail adapter and chat/export bundle handoff.", badge: "ADAPTER", tone: window.green}
                    ]
                }
'''
new_integrations = '''                IntegrationsPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    cyan: window.cyan
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                    onOpenMcpControlRequested: function(targetId) { window.openMcpChat(targetId) }
                }
'''
main = replace_once(main, old_integrations, new_integrations, "main integrations page")
main = replace_once(main,
    '''                ChatWorkspace {
                    role: window.askRole
''',
    '''                ChatWorkspace {
                    role: window.askRole
                    workspaceMode: window.chatWorkspaceMode
                    requestedMcpTarget: window.mcpChatTarget
''', "chat workspace props")
main = replace_once(main,
    '''                    magenta: window.magenta
                    onCloseRequested: window.chatWorkspaceOpen = false
''',
    '''                    magenta: window.magenta
                    onModeChangeRequested: function(mode) { window.chatWorkspaceMode = mode }
                    onCloseRequested: window.chatWorkspaceOpen = false
''', "chat mode signal")
main_path.write_text(main, encoding="utf-8")

# ChatWorkspace modes.
chat_path = ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml"
chat = chat_path.read_text(encoding="utf-8")
chat = replace_once(chat,
    "    property bool operationFailed: false\n",
    '''    property bool operationFailed: false
    property string workspaceMode: "ASSISTANT"
    property string requestedMcpTarget: "AUTO"
    property string mcpTarget: requestedMcpTarget
    property string mcpRiskHint: "AUTO"
    property var mcpTargets: fa3McpControl.targets()
    property var mcpAuthority: fa3McpControl.authoritySnapshot(mcpTarget)
''', "chat mcp props")
chat = replace_once(chat,
    "    signal closeRequested()\n    signal navigateRequested(int pageIndex)\n",
    "    signal closeRequested()\n    signal navigateRequested(int pageIndex)\n    signal modeChangeRequested(string mode)\n",
    "chat signal")
role_end = '''        return "FA3 szerepalapú beszélgetési munkatér."
    }
'''
chat = replace_once(chat, role_end, role_end + r'''

    function isMcpMode() {
        return workspaceMode === "MCP CONTROL" || workspaceMode === "WORKFLOW"
    }

    function workspaceTitle() {
        if (workspaceMode === "MCP CONTROL") return "MCP Control Chat"
        if (workspaceMode === "WORKFLOW") return "MCP Workflow Chat"
        return "Kérdezd: " + role
    }

    function workspaceDescription() {
        if (workspaceMode === "MCP CONTROL") return "Természetes nyelvű, policy-gated alkalmazásvezérlés a központi MCP authority-láncon keresztül."
        if (workspaceMode === "WORKFLOW") return "Több alkalmazáson átívelő terv és artifact-handoff előkészítése; végrehajtás csak admission után."
        return roleDescription(role)
    }

    function indexForTarget(id) {
        for (var i = 0; i < mcpTargets.length; ++i) {
            if (String(mcpTargets[i].id) === id) return i
        }
        return 0
    }
''', "chat mode functions")

reset_start = chat.index("    function resetSession() {")
draft_start = chat.index("    function draftPrompt() {", reset_start)
if reset_start < 0 or draft_start < 0:
    raise SystemExit("chat reset/draft markers not found")
new_reset = r'''    function resetSession() {
        attachmentModel.clear()
        composer.clear()
        chatModel.clear()
        if (root.isMcpMode()) {
            chatModel.append({
                kind: "SYSTEM",
                author: "FA3 MCP Control",
                body: root.workspaceTitle() + " megnyitva. Target: " + root.mcpTarget + ". A GUI intent-capture felület; nem execution authority.",
                state: "READY",
                attachmentsJson: "[]"
            })
            chatModel.append({
                kind: "SYSTEM",
                author: "MCP Authority",
                body: "CAPTURE → PLANNER → POLICY → APPROVAL → MCP GATEWAY → TARGET ADAPTER → EVIDENCE. Planner/gateway/app adapter runtime jelenleg nincs hitelesítetten bekötve, ezért végrehajtás fail-closed.",
                state: "ADAPTER-GATED",
                attachmentsJson: "[]"
            })
        } else {
            chatModel.append({
                kind: "SYSTEM",
                author: "FA3",
                body: role + " chat munkatér megnyitva. " + roleDescription(role),
                state: "READY",
                attachmentsJson: "[]"
            })
            chatModel.append({
                kind: "SYSTEM",
                author: "Runtime",
                body: "Nincs hitelesített role-chat provider adapter hozzárendelve. A felület ezért nem állít elő mesterséges választ és nem jelöl hamisan ONLINE állapotot.",
                state: "ADAPTER-GATED",
                attachmentsJson: "[]"
            })
        }
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

    function draftMcpRequest() {
        var text = composer.text.trim()
        if (text.length === 0 && attachmentModel.count === 0) return
        var attachmentJson = root.pendingAttachmentsJson()
        chatModel.append({
            kind: "USER",
            author: "Te",
            body: text.length > 0 ? text : "Csatolmány(ok) hozzáadva az MCP intenthez.",
            state: "MCP-INTENT",
            attachmentsJson: attachmentJson
        })
        var result = fa3McpControl.createDraftRequest(root.workspaceMode, root.mcpTarget, text, attachmentJson, root.mcpRiskHint)
        composer.clear()
        attachmentModel.clear()
        if (result.ok) {
            chatModel.append({
                kind: "SYSTEM",
                author: "MCP Authority",
                body: "Request " + result.requestId + " · target " + result.target + " · " + result.summary + " A vázlat helyben rögzítve; nincs elküldve és nincs target alkalmazás meghívva.",
                state: result.state,
                attachmentsJson: "[]"
            })
        } else {
            chatModel.append({
                kind: "SYSTEM",
                author: "MCP Authority",
                body: result.error || "Az MCP request-vázlat nem hozható létre.",
                state: "REJECTED",
                attachmentsJson: "[]"
            })
        }
        root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

'''
chat = chat[:reset_start] + new_reset + chat[draft_start:]
chat = replace_once(chat,
    "    function draftPrompt() {\n        var text = composer.text.trim()\n",
    "    function draftPrompt() {\n        if (root.isMcpMode()) { root.draftMcpRequest(); return }\n        var text = composer.text.trim()\n",
    "chat draft dispatch")
chat = replace_once(chat,
    "    onRoleChanged: resetSession()\n    Component.onCompleted: resetSession()\n",
    '''    onRoleChanged: { if (!root.isMcpMode()) resetSession() }
    onWorkspaceModeChanged: resetSession()
    onRequestedMcpTargetChanged: {
        root.mcpTarget = requestedMcpTarget && requestedMcpTarget.length > 0 ? requestedMcpTarget : "AUTO"
        root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
    }
    onMcpTargetChanged: root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
    Component.onCompleted: {
        root.mcpTarget = requestedMcpTarget && requestedMcpTarget.length > 0 ? requestedMcpTarget : "AUTO"
        root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
        resetSession()
    }
''', "chat lifecycle")

header_start = chat.index("        Surface {\n            Layout.fillWidth: true\n            Layout.preferredHeight: 72\n")
body_surface = chat.index("        Surface {\n            Layout.fillWidth: true\n            Layout.fillHeight: true\n", header_start)
if header_start < 0 or body_surface < 0:
    raise SystemExit("chat header surface markers not found")
new_header = r'''        Surface {
            Layout.fillWidth: true
            Layout.preferredHeight: root.isMcpMode() ? 126 : 104

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 7

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label { text: root.workspaceTitle(); color: root.textPrimary; font.pixelSize: 19; font.bold: true }
                        Label { text: root.workspaceDescription(); color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Rectangle {
                        radius: 12
                        implicitWidth: modeState.implicitWidth + 20
                        implicitHeight: 24
                        color: "#2a2113"
                        border.color: root.orange
                        Label { id: modeState; anchors.centerIn: parent; text: root.isMcpMode() ? "MCP · ADAPTER-GATED" : root.adapterState; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                    HelpBubble {
                        helpText: root.isMcpMode()
                                  ? "Authority: GUI capture → planner → policy → approval → central MCP gateway → app adapter → evidence. A GUI nem hagyhat jóvá és nem hívhat közvetlenül MCP toolt."
                                  : "A chatfelület használható vázlatokhoz és csatolmányok előkészítéséhez. Valódi AI-válasz csak hitelesített role-chat provider/runtime adapterrel engedélyezhető."
                        bubbleText: root.textPrimary
                        bubbleBorder: root.border
                    }
                    ToolButton { text: "✕"; onClicked: root.closeRequested() }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    Button { text: "Asszisztens"; checkable: true; checked: root.workspaceMode === "ASSISTANT"; onClicked: root.modeChangeRequested("ASSISTANT") }
                    Button { text: "MCP Control"; checkable: true; checked: root.workspaceMode === "MCP CONTROL"; onClicked: root.modeChangeRequested("MCP CONTROL") }
                    Button { text: "Workflow"; checkable: true; checked: root.workspaceMode === "WORKFLOW"; onClicked: root.modeChangeRequested("WORKFLOW") }
                    Rectangle { width: 1; height: 28; color: root.border; visible: root.isMcpMode() }
                    Label { visible: root.isMcpMode(); text: "Target"; color: root.textMuted; font.pixelSize: 9 }
                    ComboBox {
                        visible: root.isMcpMode()
                        Layout.preferredWidth: 190
                        model: root.mcpTargets
                        textRole: "name"
                        valueRole: "id"
                        currentIndex: root.indexForTarget(root.mcpTarget)
                        onActivated: root.mcpTarget = String(currentValue)
                    }
                    Label { visible: root.isMcpMode(); text: "Risk"; color: root.textMuted; font.pixelSize: 9 }
                    ComboBox {
                        visible: root.isMcpMode()
                        Layout.preferredWidth: 160
                        model: ["AUTO", "READ_ONLY", "MUTATING", "DESTRUCTIVE", "EXTERNAL_SIDE_EFFECT"]
                        currentIndex: Math.max(0, model.indexOf(root.mcpRiskHint))
                        onActivated: root.mcpRiskHint = currentText
                    }
                    Item { Layout.fillWidth: true }
                    Button { text: "Models & Providers"; onClicked: root.navigateRequested(5) }
                    Button { text: "Integrations"; onClicked: root.navigateRequested(14) }
                }
            }
        }

'''
chat = chat[:header_start] + new_header + chat[body_surface:]

list_marker = '''                ListView {
                    id: messageList
'''
authority_ui = r'''                Rectangle {
                    visible: root.isMcpMode()
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? 66 : 0
                    radius: 7
                    color: root.panelRaised
                    border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "MCP Authority"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Label { text: root.mcpAuthority.state || "ADAPTER-GATED"; color: root.orange; font.pixelSize: 8; font.bold: true }
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 5
                            Repeater {
                                model: root.mcpAuthority && root.mcpAuthority.stages ? root.mcpAuthority.stages : []
                                delegate: Rectangle {
                                    required property var modelData
                                    width: stageText.implicitWidth + 16
                                    height: 23
                                    radius: 10
                                    color: modelData.state === "READY" ? "#103528" : "#2a2113"
                                    border.color: modelData.state === "READY" ? root.green : root.orange
                                    Label {
                                        id: stageText
                                        anchors.centerIn: parent
                                        text: modelData.id + " · " + modelData.state
                                        color: modelData.state === "READY" ? root.green : root.orange
                                        font.pixelSize: 7
                                        font.bold: true
                                    }
                                    ToolTip.visible: stageMouse.containsMouse
                                    ToolTip.text: modelData.detail
                                    MouseArea { id: stageMouse; anchors.fill: parent; hoverEnabled: true }
                                }
                            }
                        }
                    }
                }

                ListView {
                    id: messageList
'''
chat = replace_once(chat, list_marker, authority_ui, "chat authority strip")
chat = replace_once(chat,
    '                        placeholderText: "Írj a(z) " + root.role + " szerepnek… Fájlt ide is húzhatsz."\n',
    '                        placeholderText: root.isMcpMode() ? ("Írj MCP utasítást · target: " + root.mcpTarget + "… Fájlt ide is húzhatsz.") : ("Írj a(z) " + root.role + " szerepnek… Fájlt ide is húzhatsz.")\n',
    "chat placeholder")
chat = replace_once(chat,
'''                    Button {
                        text: "Vázlat"
                        enabled: composer.text.trim().length > 0 || attachmentModel.count > 0
                        onClicked: root.draftPrompt()
                    }
                    Button {
                        text: "Küldés"
                        enabled: false
                    }
                    HelpBubble {
                        helpText: "A Küldés csak aktív és hitelesített role-chat provider/runtime adapter után lesz engedélyezve. Addig a szöveg és a csatolmányok helyi vázlatként készíthetők elő."
''',
'''                    Button {
                        text: root.isMcpMode() ? "MCP request vázlat" : "Vázlat"
                        enabled: composer.text.trim().length > 0 || attachmentModel.count > 0
                        onClicked: root.draftPrompt()
                    }
                    Button {
                        text: root.isMcpMode() ? "Végrehajtás" : "Küldés"
                        enabled: false
                    }
                    HelpBubble {
                        helpText: root.isMcpMode()
                                  ? "Végrehajtás csak akkor engedélyezhető, ha a planner typed tool-call tervet ad, a policy outcome PASS, a szükséges approval megvan, a központi MCP gateway és a target adapter hitelesítetten elérhető, majd evidence receipt készül. Jelenleg fail-closed."
                                  : "A Küldés csak aktív és hitelesített role-chat provider/runtime adapter után lesz engedélyezve. Addig a szöveg és a csatolmányok helyi vázlatként készíthetők elő."
''', "chat footer actions")
chat_path.write_text(chat, encoding="utf-8")

# Permanent GUI gate.
gate_path = ROOT / "src/fa3_gui_gate.py"
gate = gate_path.read_text(encoding="utf-8")
gate = replace_once(gate,
    '    "language_control_qml": ROOT / "apps/fa3-control-center/qml/LanguageControlPage.qml",\n',
    '    "language_control_qml": ROOT / "apps/fa3-control-center/qml/LanguageControlPage.qml",\n    "integrations_qml": ROOT / "apps/fa3-control-center/qml/IntegrationsPage.qml",\n    "mcp_control_service": ROOT / "apps/fa3-control-center/src/McpControlService.cpp",\n    "mcp_control_contract": ROOT / "canonical/FA3-MCP-CONTROL-CHAT-001.json",\n',
    "gate required")
gate = replace_once(gate,
    '    token_qml = REQUIRED["token_control_qml"].read_text(encoding="utf-8")\n',
'''    integrations_qml = REQUIRED["integrations_qml"].read_text(encoding="utf-8")
    for token in ["MCP Control Chat", "fa3McpControl.targets()", "openMcpControlRequested", "ADAPTER-GATED", "No fabricated CONNECTED state"]:
        if token not in integrations_qml: failures.append(f"qml-mcp-integrations-surface-missing:{token}")
    mcp_contract = load_json(REQUIRED["mcp_control_contract"])
    if mcp_contract.get("id") != "FA3-MCP-CONTROL-CHAT-001" or mcp_contract.get("new_architectural_authority") is not False or mcp_contract.get("capability_count_delta") != 0:
        failures.append("mcp-control-authority-contract-invalid")
    for token in ["MCP CONTROL", "WORKFLOW", "MCP Authority", "createDraftRequest", "MCP request vázlat", "Végrehajtás", "DRAFT_NOT_SUBMITTED"]:
        if token not in chat_qml: failures.append(f"qml-mcp-control-chat-missing:{token}")
    for token in ["function openMcpChat", "MCP Control Chat", "IntegrationsPage", "workspaceMode: window.chatWorkspaceMode", "requestedMcpTarget: window.mcpChatTarget"]:
        if token not in qml: failures.append(f"qml-mcp-control-wiring-missing:{token}")

    token_qml = REQUIRED["token_control_qml"].read_text(encoding="utf-8")
''', "gate mcp checks")
gate = replace_once(gate,
    '    chat_file_cpp = REQUIRED["chat_file_service"].read_text(encoding="utf-8")\n',
'''    mcp_cpp = REQUIRED["mcp_control_service"].read_text(encoding="utf-8")
    for token in ["DRAFT_NOT_SUBMITTED", "direct_tool_invocation_allowed", "gui_self_approval_allowed", "ADAPTER-GATED", "authoritySnapshot"]:
        if token not in mcp_cpp: failures.append(f"mcp-control-service-missing:{token}")
    chat_file_cpp = REQUIRED["chat_file_service"].read_text(encoding="utf-8")
''', "gate mcp cpp")
gate = replace_once(gate,
'''    if "ChatFileService" not in main_cpp or 'setContextProperty("fa3ChatFiles"' not in main_cpp:
        failures.append("chat-file-service-qml-wiring-missing")
''',
'''    if "ChatFileService" not in main_cpp or 'setContextProperty("fa3ChatFiles"' not in main_cpp:
        failures.append("chat-file-service-qml-wiring-missing")
    if "McpControlService" not in main_cpp or 'setContextProperty("fa3McpControl"' not in main_cpp:
        failures.append("mcp-control-service-qml-wiring-missing")
''', "gate main cpp mcp")
gate = replace_once(gate,
    '        if token in model_cpp or token in device_cpp or token in preference_cpp or token in chat_file_cpp: failures.append(f"backend-forbidden-token:{token}")\n',
    '        if token in model_cpp or token in device_cpp or token in preference_cpp or token in chat_file_cpp or token in mcp_cpp: failures.append(f"backend-forbidden-token:{token}")\n',
    "gate forbidden mcp")
gate = replace_once(gate,
    '    for token in ["QuickDialogs2", "ChatFileService.cpp", "HelpBubble.qml"]:\n',
    '    for token in ["QuickDialogs2", "ChatFileService.cpp", "HelpBubble.qml", "McpControlService.cpp", "IntegrationsPage.qml"]:\n',
    "gate cmake mcp")
gate_path.write_text(gate, encoding="utf-8")

# Unit regression.
test_path = ROOT / "tests/test_fa3_gui_gate.py"
tests = test_path.read_text(encoding="utf-8")
anchor = '\n\nif __name__ == "__main__":\n'
method = r'''
    def test_mcp_control_chat_is_authority_gated_and_integrated(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        chat = (ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml").read_text(encoding="utf-8")
        integrations = (ROOT / "apps/fa3-control-center/qml/IntegrationsPage.qml").read_text(encoding="utf-8")
        service = (ROOT / "apps/fa3-control-center/src/McpControlService.cpp").read_text(encoding="utf-8")
        contract = (ROOT / "canonical/FA3-MCP-CONTROL-CHAT-001.json").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")

        for token in ["function openMcpChat", "MCP Control Chat", "IntegrationsPage", "workspaceMode: window.chatWorkspaceMode"]:
            self.assertIn(token, main)
        for token in ["MCP CONTROL", "WORKFLOW", "MCP Authority", "MCP request vázlat", "Végrehajtás", "createDraftRequest"]:
            self.assertIn(token, chat)
        for token in ["GIMP", "Krita", "Blender", "Kdenlive", "OpenShot", "Inkscape", "Ardour", "No fabricated CONNECTED state"]:
            self.assertIn(token, integrations)
        for token in ["DRAFT_NOT_SUBMITTED", "direct_tool_invocation_allowed", "gui_self_approval_allowed", "execution_without_policy_allowed", "execution_without_evidence_allowed"]:
            self.assertIn(token, service)
        self.assertIn('"new_architectural_authority": false', contract)
        self.assertIn('"capability_count_delta": 0', contract)
        self.assertIn("McpControlService.cpp", cmake)
        self.assertIn("IntegrationsPage.qml", cmake)
'''
if "test_mcp_control_chat_is_authority_gated_and_integrated" not in tests:
    if anchor not in tests:
        raise SystemExit("tests anchor not found")
    tests = tests.replace(anchor, "\n" + method + anchor, 1)
    test_path.write_text(tests, encoding="utf-8")
