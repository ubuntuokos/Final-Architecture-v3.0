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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10
        Label { text: "External Project Radar"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
        Label { text: "Pinned awesome-jev-projects snapshot · " + fa3DecisionFabric.snapshotCommit; color: root.accent; font.pixelSize: 10; font.bold: true }
        Label { text: "LISTED ≠ FA3 VERIFIED. A katalógus kutatási/provenance forrás; runtime admission külön source/license/security/current-host gate-et igényel."; color: root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        TextField { id: filter; Layout.fillWidth: true; placeholderText: "Szűrés név, kategória vagy repository szerint" }
        Label { text: fa3DecisionFabric.radarProjects.length + " parsed projects in pinned snapshot"; color: root.textMuted }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 5
            model: fa3DecisionFabric.radarProjects
            delegate: Rectangle {
                required property var modelData
                property bool matches: filter.text.length === 0 ||
                    (modelData.name || "").toLowerCase().indexOf(filter.text.toLowerCase()) >= 0 ||
                    (modelData.category || "").toLowerCase().indexOf(filter.text.toLowerCase()) >= 0 ||
                    (modelData.repository || "").toLowerCase().indexOf(filter.text.toLowerCase()) >= 0
                visible: matches
                height: matches ? 78 : 0
                width: ListView.view.width
                radius: 7; color: root.panel; border.color: root.border
                ColumnLayout { anchors.fill: parent; anchors.margins: 9; spacing: 2
                    RowLayout { Layout.fillWidth: true
                        Label { text: modelData.name || ""; color: root.textPrimary; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Label { text: modelData.status || ""; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                    Label { text: modelData.category || ""; color: root.accent; font.pixelSize: 9 }
                    Label { text: modelData.repository || ""; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideMiddle }
                }
            }
        }
    }
}
