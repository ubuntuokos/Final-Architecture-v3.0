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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12
        Label { text: "Decision Inspector"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
        Label { text: "Read-only append-only Decision Trace projection · MODEL JUDGMENT ≠ FA3 FINAL DECISION"; color: root.accent; font.pixelSize: 10; font.bold: true }
        Label {
            visible: fa3DecisionFabric.recentDecisions.length === 0
            text: "Nincs runtime Decision Trace. Ez nem PASS és nem hiba: a felület nem gyárt szintetikus döntéseket."
            color: root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: fa3DecisionFabric.recentDecisions
            spacing: 8
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 132
                radius: 8
                color: root.panel
                border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 11; spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: modelData.contract || "UNKNOWN"; color: root.textPrimary; font.bold: true }
                        Label { text: modelData.status || "UNKNOWN"; color: (modelData.status === "DECIDED") ? root.green : root.orange; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Label { text: (modelData.latency_ms || 0) + " ms"; color: root.textMuted }
                    }
                    Label { text: modelData.purpose || ""; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: "Provider: " + (modelData.provider || ""); color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: "Final policy owner: " + (modelData.final_policy_owner || ""); color: root.accent; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: "authority=false · candidate_set_expanded=false"; color: root.green; font.pixelSize: 9; font.bold: true }
                }
            }
        }
    }
}
