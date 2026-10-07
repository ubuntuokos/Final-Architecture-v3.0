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

    function reusableRecords() {
        return fa3Repository.searchRecords("REUSE").concat(fa3Repository.searchRecords("PATTERN"))
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        Label { text: "External Project Radar"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
        Label { text: "Pinned upstream references + FA3 reusable-assets projection"; color: root.accent; font.pixelSize: 10; font.bold: true }
        Label {
            text: "LISTED ≠ FA3 VERIFIED. Reusable Assets is derived/read-only; no candidate, pattern or agent recommendation grants admission or authority."
            color: root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "External Projects" }
            TabButton { text: "Reusable Assets" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
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

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    TextField { id: reuseFilter; Layout.fillWidth: true; placeholderText: "Szűrés canonical reusable asset szerint" }
                    Label {
                        text: "FA3-REUSE-CATALOG-001 · derived / rebuildable / non-authoritative"
                        color: root.green; font.pixelSize: 9; font.bold: true
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 5
                        model: root.reusableRecords()
                        delegate: Rectangle {
                            required property var modelData
                            property bool matches: reuseFilter.text.length === 0 ||
                                (modelData.id || "").toLowerCase().indexOf(reuseFilter.text.toLowerCase()) >= 0 ||
                                (modelData.title || "").toLowerCase().indexOf(reuseFilter.text.toLowerCase()) >= 0 ||
                                (modelData.path || "").toLowerCase().indexOf(reuseFilter.text.toLowerCase()) >= 0
                            visible: matches
                            height: matches ? 64 : 0
                            width: ListView.view.width
                            radius: 7; color: root.panel; border.color: root.border
                            ColumnLayout { anchors.fill: parent; anchors.margins: 9; spacing: 2
                                Label { text: modelData.id || modelData.title || ""; color: root.textPrimary; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: (modelData.category || "CANONICAL") + " · " + (modelData.status || ""); color: root.accent; font.pixelSize: 9 }
                                Label { text: modelData.path || ""; color: root.textMuted; font.pixelSize: 8; Layout.fillWidth: true; elide: Text.ElideMiddle }
                            }
                        }
                    }
                }
            }
        }
    }
}
