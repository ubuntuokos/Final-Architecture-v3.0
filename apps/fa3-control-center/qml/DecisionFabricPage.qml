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
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 14
            Item { Layout.preferredHeight: 8 }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Label { text: "Decision Fabric"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "FA3-DECISION-FABRIC-001 · structured judgment, not authority"; color: root.accent; font.pixelSize: 10; font.bold: true }
                Label { text: "A modell/providerek csak korlátozott candidate-seten adnak judgmentot. A végső döntés mindig a meglévő FA3 policy ownernél marad."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                columns: 4
                rowSpacing: 10; columnSpacing: 10
                Repeater {
                    model: [
                        {t:"State", v:fa3DecisionFabric.state, c:root.green},
                        {t:"Default rollout", v:"SHADOW", c:root.orange},
                        {t:"Mandatory Jev", v:"NO", c:root.green},
                        {t:"Authority", v:"FALSE", c:root.green}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 100
                        radius: 8; color: root.panel; border.color: root.border
                        ColumnLayout { anchors.fill: parent; anchors.margins: 12
                            Label { text: modelData.t; color: root.textMuted; font.pixelSize: 9 }
                            Label { text: modelData.v; color: modelData.c; font.bold: true; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
                Layout.preferredHeight: 230; radius: 8; color: root.panel; border.color: root.border
                ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 7
                    Label { text: "Authority boundaries"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                    Label { text: "Model routing → FA3-AUTH-MODEL-ROUTER-001"; color: root.textMuted }
                    Label { text: "MCP/capability boundary → FA3-AUTH-MCP-GATEWAY-001"; color: root.textMuted }
                    Label { text: "Resources → FA3-AUTH-HOST-RESOURCE-BROKER-001"; color: root.textMuted }
                    Label { text: "Security → FA3-SCS-001"; color: root.textMuted }
                    Label { text: "Candidate expansion → DENY"; color: root.magenta; font.bold: true }
                    Label { text: "Direct tool execution → DENY"; color: root.magenta; font.bold: true }
                    Button { text: "Refresh read-only projection"; onClicked: fa3DecisionFabric.refresh() }
                }
            }
            Label { visible: fa3DecisionFabric.lastError.length > 0; Layout.leftMargin: 18; Layout.rightMargin: 18; Layout.fillWidth: true; text: fa3DecisionFabric.lastError; color: root.orange; wrapMode: Text.WordWrap }
        }
    }
}
