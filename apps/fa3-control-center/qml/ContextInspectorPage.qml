import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color panel: "#0b1728"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 10
        Label { text: "Context Inspector"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
        Label { text: "FA3-CONTEXT-SELECTION-001 · PROTECTED / ACTIVE / HIDDEN / ARCHIVED"; color: root.accent; font.pixelSize: 10; font.bold: true }
        Label { text: "HIDDEN ≠ DELETE · ARCHIVED ≠ DELETE · az eredeti Journal/artifact source authority változatlan."; color: root.green; font.bold: true }
        Label {
            visible: fa3DecisionFabric.contextItems.length === 0
            text: "Nincs aktív context-projection. A GUI nem hoz létre vagy módosít kontextust; csak a runtime által kiírt projectiont olvassa."
            color: root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 5
            model: fa3DecisionFabric.contextItems
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width; height: 76
                radius: 7; color: root.panel; border.color: root.border
                RowLayout {
                    anchors.fill: parent; anchors.margins: 10
                    ColumnLayout { Layout.fillWidth: true
                        Label { text: modelData.id || ""; color: root.textPrimary; font.bold: true }
                        Label { text: modelData.kind || ""; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: modelData.text || ""; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: 9 }
                    }
                    Label {
                        text: modelData.state || "UNKNOWN"
                        color: modelData.state === "PROTECTED" ? root.magenta : modelData.state === "ACTIVE" ? root.green : root.orange
                        font.bold: true
                    }
                }
            }
        }
    }
}
