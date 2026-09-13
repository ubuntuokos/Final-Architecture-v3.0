import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property var settings
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language

    property var results: []
    property var conversationStatus: fa3SearchIndex.conversationIndexStatus()
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    function runSearch() {
        if (scope.currentIndex === 0) {
            results = repository.searchRecords(query.text.trim())
        } else if (scope.currentIndex === 1) {
            results = fa3SearchIndex.searchProjects(settings.value("paths/projects", ""), query.text.trim(), 100)
        } else {
            results = []
            conversationStatus = fa3SearchIndex.conversationIndexStatus()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14
        Label { text: root.t("Keresés", "Search"); font.pixelSize: root.px(24); font.bold: true }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("Szolgáltatások, projektek és — canonical adapter rendelkezésre állásakor — beszélgetések read-only keresése.", "Read-only search across services, projects and — when a canonical adapter is available — conversations.") }
        RowLayout {
            Layout.fillWidth: true
            ComboBox { id: scope; model: [root.t("Szolgáltatás", "Service"), root.t("Projekt", "Project"), root.t("Beszélgetés", "Conversation")]; onActivated: root.runSearch() }
            TextField { id: query; Layout.fillWidth: true; placeholderText: root.t("Keresési kifejezés…", "Search…"); onAccepted: root.runSearch() }
            Button { text: root.t("Keresés", "Search"); onClicked: root.runSearch() }
        }
        Rectangle {
            visible: scope.currentIndex === 2 && !root.conversationStatus.available
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            radius: 8
            color: root.surface1
            Column { anchors.fill: parent; anchors.margins: 12; spacing: 5
                Label { text: root.t("Beszélgetés-keresés nem érhető el", "Conversation search unavailable"); font.bold: true }
                Label { width: parent.width; wrapMode: Text.WordWrap; color: root.textMuted; text: root.conversationStatus.reason + " — " + root.conversationStatus.detail }
            }
        }
        ScrollView {
            visible: scope.currentIndex !== 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 8
                Repeater {
                    model: root.results
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        radius: 8
                        color: root.surface1
                        RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 10
                            ColumnLayout { Layout.fillWidth: true
                                Label { Layout.fillWidth: true; font.bold: true; elide: Text.ElideRight; text: modelData.id || modelData.name || "—" }
                                Label { Layout.fillWidth: true; color: root.textMuted; elide: Text.ElideMiddle; text: modelData.title || modelData.path || modelData.category || "" }
                            }
                            Label { text: modelData.status || modelData.type || "READ"; color: root.accent }
                        }
                    }
                }
            }
        }
    }
}
