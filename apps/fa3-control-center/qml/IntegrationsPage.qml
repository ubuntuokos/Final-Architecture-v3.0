import QtQuick
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
