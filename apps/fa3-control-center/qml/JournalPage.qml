import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color surface1: palette.base
    property color surface2: palette.alternateBase
    property color accent: palette.highlight
    property color textPrimary: palette.windowText
    property color textMuted: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.62)
    property string selectedEventId: ""
    property string selectedArchiveFile: ""
    property string selectedArchiveId: ""
    property string actionResult: fa3Journal.lastResult

    function projectEvents(kind) {
        var all = fa3Journal.filteredEvents("ALL", eventSearch.text)
        return all.filter(function(v) {
            if (!v.project_id || v.project_id.length === 0) return false
            var state = (v.lifecycle || "").toUpperCase()
            if (kind === "ACTIVE") return ["IMPLEMENTING", "VALIDATING", "ACTIVE", "BLOCKED", "RUNNING"].indexOf(state) >= 0
            if (kind === "CLOSED") return ["COMPLETED", "CLOSED", "ARCHIVED", "REJECTED", "SUPERSEDED"].indexOf(state) >= 0
            if (kind === "PLANNED") return ["PROPOSED", "EVALUATING", "APPROVED", "PLANNED"].indexOf(state) >= 0
            return true
        })
    }

    component Panel: Rectangle {
        radius: 12
        color: root.surface1
        border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
    }

    component MetricCard: Panel {
        property string label: ""
        property string value: ""
        property string note: ""
        implicitWidth: 182
        implicitHeight: 100
        Column {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 5
            Label { text: parent.parent.label; color: root.textMuted; font.pixelSize: 11 }
            Label { text: parent.parent.value; font.pixelSize: 25; font.bold: true }
            Label { text: parent.parent.note; color: root.textMuted; font.pixelSize: 10; elide: Text.ElideRight; width: parent.width }
        }
    }

    component EventList: Panel {
        property var eventModel: []
        property string emptyText: "Nincs megjeleníthető bejegyzés."
        ListView {
            anchors.fill: parent
            anchors.margins: 8
            clip: true
            model: parent.eventModel
            delegate: ItemDelegate {
                width: ListView.view.width
                height: 68
                highlighted: root.selectedEventId === modelData.id
                onClicked: root.selectedEventId = modelData.id
                contentItem: RowLayout {
                    spacing: 10
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: modelData.domain || "EVENT"; color: root.accent; font.pixelSize: 10; font.bold: true }
                            Label { text: modelData.lifecycle || "RECORDED"; color: root.textMuted; font.pixelSize: 10 }
                            Item { Layout.fillWidth: true }
                            Label { text: modelData.timestamp || ""; color: root.textMuted; font.pixelSize: 10 }
                        }
                        Label { text: modelData.summary || modelData.id; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label {
                            text: (modelData.project_id ? modelData.project_id + " · " : "") + (modelData.details || "")
                            color: root.textMuted
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            font.pixelSize: 11
                        }
                    }
                }
            }
            Label {
                anchors.centerIn: parent
                visible: parent.count === 0
                text: parent.parent.emptyText
                color: root.textMuted
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "Napló / Journal"; font.pixelSize: 24; font.bold: true }
                Label { text: "Rendszer-, beszélgetés- és projektéletciklus-napló, archiválás és megosztás"; color: root.textMuted; font.pixelSize: 12 }
            }
            Button { text: "Új bejegyzés"; onClicked: eventDialog.open() }
            Button { text: "Frissítés"; onClicked: fa3Journal.refresh() }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 10
            MetricCard { label: "Aktív esemény"; value: fa3Journal.eventCount.toString(); note: "append-only journal" }
            MetricCard { label: "Archívum"; value: fa3Journal.archiveCount.toString(); note: "sealed + SHA-256" }
            MetricCard { label: "Aktív projekt"; value: fa3Journal.activeProjectCount.toString(); note: "implementation / validation" }
            MetricCard { label: "Lezárt projekt"; value: fa3Journal.closedProjectCount.toString(); note: "completed / archived" }
            MetricCard { label: "Bevezetendő"; value: fa3Journal.plannedProjectCount.toString(); note: "proposed → planned" }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: eventSearch
                Layout.fillWidth: true
                placeholderText: "Keresés naplóban: projekt, forrás, összefoglaló, részletek…"
            }
            Button { text: "Mentés / MD"; onClicked: root.actionResult = fa3Journal.exportJournal("md", eventSearch.text) }
            Button { text: "JSON"; onClicked: root.actionResult = fa3Journal.exportJournal("json", eventSearch.text) }
            Button { text: "Nyomtatás"; onClicked: root.actionResult = fa3Journal.printJournal(eventSearch.text) }
            Button { text: "E-mail"; onClicked: root.actionResult = fa3Journal.shareJournal("EMAIL", eventSearch.text) }
            Button { text: "Chat"; onClicked: root.actionResult = fa3Journal.shareJournal("CHAT", eventSearch.text) }
        }

        TabBar {
            id: journalTabs
            Layout.fillWidth: true
            TabButton { text: "Áttekintés" }
            TabButton { text: "Rendszer" }
            TabButton { text: "Beszélgetések" }
            TabButton { text: "Projektek" }
            TabButton { text: "Események" }
            TabButton { text: "Archívum" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: journalTabs.currentIndex

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12
                    Label { text: "Működési áttekintés"; font.pixelSize: 17; font.bold: true }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 10
                        MetricCard { label: "Rendszer"; value: fa3Journal.systemCount.toString(); note: "system/runtime events" }
                        MetricCard { label: "Beszélgetés"; value: fa3Journal.conversationCount.toString(); note: "decision/context events" }
                        MetricCard { label: "Utolsó frissítés"; value: fa3Journal.lastRefresh.length > 10 ? fa3Journal.lastRefresh.substring(11, 19) : "—"; note: fa3Journal.lastRefresh }
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        text: "Az aktív napló append-only. A GUI törlése tombstone rekordot készít; az archiváló SEALED csomagot hoz létre SHA-256 payload-integritással. Az archívum visszaállítása csak sikeres integritás-ellenőrzés után engedélyezett."
                    }
                    EventList { Layout.fillWidth: true; Layout.fillHeight: true; eventModel: fa3Journal.filteredEvents("ALL", eventSearch.text) }
                }
            }

            EventList { eventModel: fa3Journal.filteredEvents("SYSTEM", eventSearch.text); emptyText: "Nincs rendszerbejegyzés." }
            EventList { eventModel: fa3Journal.filteredEvents("CONVERSATION", eventSearch.text); emptyText: "Nincs beszélgetési bejegyzés." }

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Projektéletciklus"; font.pixelSize: 16; font.bold: true }
                        Item { Layout.fillWidth: true }
                        ComboBox { id: projectFilter; model: ["Aktív", "Lezárt", "Bevezetendő", "Összes"] }
                    }
                    EventList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        eventModel: projectFilter.currentIndex === 0 ? root.projectEvents("ACTIVE") :
                                    projectFilter.currentIndex === 1 ? root.projectEvents("CLOSED") :
                                    projectFilter.currentIndex === 2 ? root.projectEvents("PLANNED") : root.projectEvents("ALL")
                    }
                }
            }

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    EventList { Layout.fillWidth: true; Layout.fillHeight: true; eventModel: fa3Journal.filteredEvents("ALL", eventSearch.text) }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: root.selectedEventId.length ? "Kijelölt: " + root.selectedEventId : "Nincs kijelölt esemény"; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        Button {
                            text: "Törlés (soft)"
                            enabled: root.selectedEventId.length > 0
                            onClicked: {
                                root.actionResult = fa3Journal.softDeleteEvent(root.selectedEventId)
                                root.selectedEventId = ""
                            }
                        }
                    }
                }
            }

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Naplóarchiváló"; font.pixelSize: 17; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Button { text: "Policy archiválás"; onClicked: root.actionResult = fa3Journal.archiveByPolicy() }
                        Button { text: "Archiválás most"; onClicked: archiveConfirm.open() }
                        Button { text: "Mappa"; onClicked: fa3Journal.openStorageRoot() }
                    }
                    Label {
                        Layout.fillWidth: true
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        text: "Az archiválás lezárja az aktív naplót, SHA-256 manifestet készít, majd új aktív naplót nyit. Visszaállításkor az eredeti rekordazonosító megmarad provenance mezőként, de új esemény-ID készül."
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: fa3Journal.archives
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            height: 62
                            highlighted: root.selectedArchiveFile === modelData.file_name
                            onClicked: {
                                root.selectedArchiveFile = modelData.file_name
                                root.selectedArchiveId = modelData.id
                            }
                            contentItem: RowLayout {
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Label { text: modelData.id; font.bold: true; font.family: "monospace"; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.created_at + " · " + modelData.reason + " · " + modelData.event_count + " esemény"; color: root.textMuted; font.pixelSize: 11 }
                                }
                                Label { text: modelData.status; color: root.accent; font.bold: true; Layout.preferredWidth: 80 }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: root.selectedArchiveId.length ? "Kijelölt: " + root.selectedArchiveId : "Nincs kijelölt archívum"; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        Button { text: "Integritás"; enabled: root.selectedArchiveFile.length > 0; onClicked: root.actionResult = fa3Journal.verifyArchive(root.selectedArchiveFile) }
                        Button { text: "Visszaállítás"; enabled: root.selectedArchiveFile.length > 0; onClicked: restoreConfirm.open() }
                        Button { text: "Archív törlése"; enabled: root.selectedArchiveFile.length > 0; onClicked: retireConfirm.open() }
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: root.actionResult.length ? root.actionResult : "Journal storage: " + fa3Journal.storageRoot
            color: root.actionResult.indexOf("FAIL") >= 0 || root.actionResult.indexOf("FAILED") >= 0 ? "#d35f5f" : root.textMuted
            elide: Text.ElideMiddle
            font.pixelSize: 10
        }
    }

    Dialog {
        id: eventDialog
        title: "Új FA3 naplóbejegyzés"
        modal: true
        anchors.centerIn: parent
        width: 620
        standardButtons: Dialog.Save | Dialog.Cancel
        ColumnLayout {
            width: parent.width
            spacing: 8
            ComboBox { id: eventDomain; Layout.fillWidth: true; model: ["SYSTEM", "CONVERSATION", "PROJECT", "EVIDENCE", "SECURITY", "AUDIT"] }
            TextField { id: eventSource; Layout.fillWidth: true; placeholderText: "Forrás (pl. FA3 Control Center, Ollama, ChatGPT)" }
            TextField { id: eventProject; Layout.fillWidth: true; placeholderText: "Project ID (opcionális)" }
            ComboBox { id: eventLifecycle; Layout.fillWidth: true; model: ["RECORDED", "PROPOSED", "EVALUATING", "APPROVED", "PLANNED", "IMPLEMENTING", "VALIDATING", "ACTIVE", "BLOCKED", "COMPLETED", "ARCHIVED"] }
            TextField { id: eventSummary; Layout.fillWidth: true; placeholderText: "Összefoglaló" }
            TextArea { id: eventDetails; Layout.fillWidth: true; Layout.preferredHeight: 130; placeholderText: "Részletek"; wrapMode: TextEdit.Wrap }
        }
        onAccepted: {
            root.actionResult = fa3Journal.recordEvent(eventDomain.currentText, eventSource.text, eventProject.text, eventLifecycle.currentText, eventSummary.text, eventDetails.text)
            eventSource.clear(); eventProject.clear(); eventSummary.clear(); eventDetails.clear()
        }
    }

    Dialog {
        id: archiveConfirm
        title: "Aktív napló archiválása"
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Yes | Dialog.No
        Label { text: "SEALED archívum készül, majd az aktív napló új rotációt kezd." }
        onAccepted: root.actionResult = fa3Journal.archiveAll("MANUAL_GUI")
    }

    Dialog {
        id: restoreConfirm
        title: "Archívum visszaállítása"
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Yes | Dialog.No
        Label { text: "A visszaállítás előtt kötelező SHA-256 integritás-ellenőrzés fut." }
        onAccepted: root.actionResult = fa3Journal.restoreArchive(root.selectedArchiveFile)
    }

    Dialog {
        id: retireConfirm
        title: "Archívum törlése"
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Yes | Dialog.No
        Label { text: "Az archívum nem kerül fizikailag purge-ra: retention trash-ba lesz áthelyezve." }
        onAccepted: {
            root.actionResult = fa3Journal.retireArchive(root.selectedArchiveFile)
            root.selectedArchiveFile = ""
            root.selectedArchiveId = ""
        }
    }
}
