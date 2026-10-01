import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color panel: "#0b1728"
    property color panelRaised: "#10243a"
    property color border: "#1f3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#91a7bd"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    signal stageChangeRequest(string actionId, string target, string rationale)

    readonly property var profiles: [
        {id: "P1", name: "Director", detail: "Célbontás · feladatcsoport · prioritás"},
        {id: "P2", name: "Adaptive Conductor", detail: "Dinamikus részgráf · fork/join · replan"},
        {id: "P3", name: "Agent Workforce", detail: "Kompetencia · felelősség · delegálás"},
        {id: "P4", name: "Production", detail: "Kreatív és produkciós függőségek"},
        {id: "P5", name: "Distributed", detail: "Munkadarabolás · több-host koordináció"},
        {id: "P6", name: "Live Cue", detail: "Időkritikus, operátori cue-koordináció"},
        {id: "P7", name: "Event", detail: "Eseményfogadás · normalizált indítás"}
    ]

    Component.onCompleted: fa3OrchestrationMonitor.reload()

    ScrollView {
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Label {
                    Layout.fillWidth: true
                    text: "Orchestration Control & Monitoring"
                    color: root.textPrimary
                    font.pixelSize: 24
                    font.bold: true
                }
                Rectangle {
                    implicitWidth: 190
                    implicitHeight: 32
                    radius: 16
                    color: fa3OrchestrationMonitor.state === "LIVE_PROJECTION" ? "#143c35" : "#3c2e18"
                    border.color: fa3OrchestrationMonitor.state === "LIVE_PROJECTION" ? root.green : root.orange
                    Label {
                        anchors.centerIn: parent
                        text: fa3OrchestrationMonitor.state
                        color: parent.border.color
                        font.pixelSize: 10
                        font.bold: true
                    }
                }
                Button { text: "Frissítés"; onClicked: fa3OrchestrationMonitor.reload() }
            }

            Label {
                Layout.fillWidth: true
                text: "Temporal = egyetlen központi tartós workflow-hatóság · 31 feladatcsoport · 7 vezérlési profil · 175 rögzített képesség"
                color: root.textMuted
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: fa3OrchestrationMonitor.state !== "LIVE_PROJECTION"
                text: "Nincs igazolt élő orchestration-telemetria. A felület nem gyárt RUNNING/PASS állapotot. Forrás: " +
                      (fa3OrchestrationMonitor.sourcePath.length ? fa3OrchestrationMonitor.sourcePath : "nincs használható runtime path")
                color: root.orange
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Repeater {
                    model: [
                        {label: "Tartós motor", value: "Temporal", tone: root.green},
                        {label: "Feladatok", value: String(fa3OrchestrationMonitor.taskCount), tone: root.accent},
                        {label: "Routed", value: String(fa3OrchestrationMonitor.routedCount), tone: root.accent},
                        {label: "Figyelmet igényel", value: String(fa3OrchestrationMonitor.attentionRequired), tone: root.orange}
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 92
                        radius: 9
                        color: root.panel
                        border.color: root.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Label { text: modelData.label; color: root.textMuted; font.pixelSize: 10 }
                            Label { text: modelData.value; color: modelData.tone; font.pixelSize: 21; font.bold: true }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                radius: 9
                color: root.panel
                border.color: root.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Label { text: "Vezérlési profilok"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        rowSpacing: 8
                        columnSpacing: 8
                        Repeater {
                            model: root.profiles
                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 68
                                radius: 7
                                color: root.panelRaised
                                border.color: root.border
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    Label { text: modelData.id + " · " + modelData.name; color: root.textPrimary; font.bold: true }
                                    Label { Layout.fillWidth: true; text: modelData.detail; color: root.textMuted; font.pixelSize: 9; elide: Text.ElideRight }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    radius: 9
                    color: root.panel
                    border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: "Liveness"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                        Label {
                            visible: fa3OrchestrationMonitor.livenessRows.length === 0
                            text: "Nincs hiteles liveness-projekció."
                            color: root.textMuted
                        }
                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: fa3OrchestrationMonitor.livenessRows
                            delegate: RowLayout {
                                width: ListView.view.width
                                Label { Layout.fillWidth: true; text: modelData.state; color: root.textMuted }
                                Label { text: String(modelData.count); color: root.accent; font.bold: true }
                            }
                        }
                        Label {
                            text: "Utolsó projekció: " + (fa3OrchestrationMonitor.lastUpdated.length ? fa3OrchestrationMonitor.lastUpdated : "N/A")
                            color: root.textMuted
                            font.pixelSize: 9
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    radius: 9
                    color: root.panel
                    border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8
                        Label { text: "Felügyelt átállítás"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                        Label {
                            Layout.fillWidth: true
                            text: "DRAFT ONLY — a kérés a tulajdonos hatósághoz kerül; a monitor nem hajt végre közvetlen változtatást."
                            color: root.orange
                            wrapMode: Text.WordWrap
                            font.pixelSize: 10
                        }
                        ComboBox {
                            id: actionType
                            Layout.fillWidth: true
                            model: [
                                "orchestration.pause-new-work",
                                "orchestration.priority-adjust",
                                "orchestration.parallelism-limit",
                                "orchestration.conductor-selection",
                                "orchestration.retry-limit",
                                "orchestration.resource-request"
                            ]
                        }
                        TextField { id: targetField; Layout.fillWidth: true; placeholderText: "Cél: workflow / task / profile ID" }
                        TextField { id: rationaleField; Layout.fillWidth: true; placeholderText: "Indoklás" }
                        Button {
                            text: "Draft kérelem"
                            enabled: targetField.text.length > 0 && rationaleField.text.length > 0
                            onClicked: root.stageChangeRequest(actionType.currentText, targetField.text, rationaleField.text)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 92
                radius: 9
                color: root.panelRaised
                border.color: root.border
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    Label { text: "Hatásköri határ"; color: root.textPrimary; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: "Monitor authority=false. Security/UAF/MCP, HRB, Model Router, Secret Broker és Evidence/Gate döntései külön kötelezőek. STOP után új delegálás vagy új gráfág nem indítható automatikusan."
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
