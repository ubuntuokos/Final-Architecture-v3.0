import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: palette.base
    property color panelRaised: palette.alternateBase
    property color border: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.10)
    property color textPrimary: palette.windowText
    property color textMuted: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.62)
    property color accent: palette.highlight
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    signal navigateRequested(int pageIndex)

    function parseOsDetails(event) {
        if (!event || !event.details) return null
        try {
            var parsed = JSON.parse(event.details)
            return parsed && parsed.fa3_os ? parsed.fa3_os : null
        } catch (e) {
            return null
        }
    }

    function osEvents() {
        var all = fa3Journal.filteredEvents("ALL", "")
        var out = []
        for (var i = 0; i < all.length; ++i) {
            var ctx = parseOsDetails(all[i])
            if (ctx) out.push({event: all[i], ctx: ctx})
        }
        return out
    }

    function derivedWorkstreams() {
        var rows = osEvents()
        var byId = ({})
        for (var i = 0; i < rows.length; ++i) {
            var evt = rows[i].event
            var ctx = rows[i].ctx
            var kind = ""
            var id = ""
            if (ctx.workstream_id) { kind = "WORKSTREAM"; id = ctx.workstream_id }
            else if (evt.project_id) { kind = "PROJECT"; id = evt.project_id }
            else if (ctx.workflow_reference) { kind = "WORKFLOW"; id = ctx.workflow_reference }
            else if (ctx.session_id) { kind = "SESSION"; id = ctx.session_id }
            else if (ctx.artifact_id) { kind = "ARTIFACT"; id = ctx.artifact_id }
            if (!id) continue
            var key = kind + ":" + id
            if (!byId[key]) byId[key] = {kind: kind, id: id, count: 0, apps: [], last: evt.timestamp || ""}
            byId[key].count += 1
            byId[key].last = evt.timestamp || byId[key].last
            if (ctx.application_id && byId[key].apps.indexOf(ctx.application_id) < 0) byId[key].apps.push(ctx.application_id)
        }
        var out = []
        for (var key in byId) out.push(byId[key])
        out.sort(function(a, b) { return a.id.localeCompare(b.id) })
        return out
    }

    component Panel: Rectangle {
        radius: 12
        color: root.panel
        border.color: root.border
    }

    component Metric: Panel {
        property string labelText: ""
        property string valueText: ""
        property string noteText: ""
        property color tone: root.accent
        implicitWidth: 185
        implicitHeight: 96
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 13
            spacing: 3
            Label { text: parent.parent.labelText; color: root.textMuted; font.pixelSize: 9 }
            Label { text: parent.parent.valueText; color: parent.parent.tone; font.pixelSize: 16; font.bold: true }
            Label { text: parent.parent.noteText; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "FA3 OS"; color: root.textPrimary; font.pixelSize: 24; font.bold: true }
                Label { text: "Aktivitás, workstream, privacy és provenance kontextus · FA3-JOURNAL-001 fölötti non-authoritative runtime projection"; color: root.textMuted; font.pixelSize: 11 }
            }
            Button { text: "Journal"; onClicked: root.navigateRequested(12) }
            Button { text: "Frissítés"; onClicked: fa3Journal.refresh() }
        }

        Flow {
            Layout.fillWidth: true
            spacing: 10
            Metric { labelText: "Runtime"; valueText: "REFERENCE"; noteText: "FA3-OS-RUNTIME-001"; tone: root.accent }
            Metric { labelText: "Event authority"; valueText: "JOURNAL"; noteText: "FA3-JOURNAL-001"; tone: root.green }
            Metric { labelText: "Privacy"; valueText: "FAIL-CLOSED"; noteText: "gate before persistence"; tone: root.magenta }
            Metric { labelText: "OS events"; valueText: root.osEvents().length.toString(); noteText: "canonical Journal enrichment"; tone: root.accent }
            Metric { labelText: "Host admission"; valueText: "PENDING"; noteText: "CURRENT HOST E2E PENDING"; tone: root.orange }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Timeline" }
            TabButton { text: "Workstreams" }
            TabButton { text: "Privacy" }
            TabButton { text: "Provenance" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "FA3 OS Timeline"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Label { text: "read-only Journal projection"; color: root.textMuted; font.pixelSize: 9 }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.osEvents()
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            height: 68
                            contentItem: RowLayout {
                                spacing: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: modelData.ctx.action || "EVENT"; color: root.accent; font.pixelSize: 10; font.bold: true }
                                        Label { text: modelData.ctx.application_id || modelData.event.source || "FA3 OS"; color: root.textMuted; font.pixelSize: 10 }
                                        Item { Layout.fillWidth: true }
                                        Label { text: modelData.event.timestamp || ""; color: root.textMuted; font.pixelSize: 9 }
                                    }
                                    Label { text: modelData.event.summary || modelData.ctx.subject.reference; color: root.textPrimary; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label {
                                        text: (modelData.event.project_id ? modelData.event.project_id + " · " : "") + (modelData.ctx.workstream_id || modelData.ctx.session_id || modelData.ctx.subject.reference || "")
                                        color: root.textMuted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                        Label { anchors.centerIn: parent; visible: parent.count === 0; text: "Még nincs FA3 OS enrichment esemény a canonical Journalban."; color: root.textMuted }
                    }
                }
            }

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Label { text: "Deterministic Workstreams"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                    Label { text: "Származtatott, újraépíthető nézet. Nem írja át és nem helyettesíti a Journal történeti igazságát."; color: root.textMuted; font.pixelSize: 10 }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.derivedWorkstreams()
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            height: 58
                            contentItem: RowLayout {
                                Label { text: modelData.kind; color: root.accent; font.pixelSize: 9; font.bold: true; Layout.preferredWidth: 90 }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.id; color: root.textPrimary; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.apps.join(", ") || "no application metadata"; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                Label { text: modelData.count + " event"; color: root.textMuted; font.pixelSize: 9 }
                                Label { text: modelData.last; color: root.textMuted; font.pixelSize: 9; Layout.preferredWidth: 190; elide: Text.ElideRight }
                            }
                        }
                    }
                }
            }

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12
                    Label { text: "Privacy Center"; color: root.textPrimary; font.pixelSize: 17; font.bold: true }
                    Label { text: "FA3-OS-POLICY-001 · policy gate BEFORE_DURABLE_PERSISTENCE"; color: root.accent; font.pixelSize: 10; font.bold: true }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 22
                        rowSpacing: 9
                        Label { text: "Keylogging"; color: root.textMuted } ; Label { text: "DENY"; color: root.green; font.bold: true }
                        Label { text: "Generic clipboard"; color: root.textMuted } ; Label { text: "DENY"; color: root.green; font.bold: true }
                        Label { text: "Continuous / generic screen capture"; color: root.textMuted } ; Label { text: "DENY"; color: root.green; font.bold: true }
                        Label { text: "Terminal"; color: root.textMuted } ; Label { text: "METADATA_ONLY"; color: root.green; font.bold: true }
                        Label { text: "Password managers / secret paths"; color: root.textMuted } ; Label { text: "DENY"; color: root.green; font.bold: true }
                        Label { text: "Browser content"; color: root.textMuted } ; Label { text: "SELECTIVE_OPT_IN"; color: root.orange; font.bold: true }
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        text: "A Global Pause, alkalmazás/path/project allow/deny és selective-erasure vezérlők canonical követelmények. Ebben a referencia-GUI-ban szándékosan nem jelennek meg működő kapcsolóként addig, amíg nincs current-host admitted command bridge és auditált authorization path."
                    }
                    Item { Layout.fillHeight: true }
                    Label { text: "CURRENT HOST E2E PENDING"; color: root.orange; font.bold: true }
                }
            }

            Panel {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 11
                    Label { text: "Provenance & Context Passport"; color: root.textPrimary; font.pixelSize: 17; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        text: "A jelenlegi vertical slice a Journalban tárolt provenance, artifact, parent-event és correlation referenciákat mutatja. A teljes FA3ContextPassport / asset-lineage graph következő projection-fázis; az itt látható adat nem kap külön authority-t."
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.osEvents()
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            height: 62
                            contentItem: RowLayout {
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.ctx.artifact_id || modelData.ctx.subject.reference || modelData.event.id; color: root.textPrimary; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: (modelData.ctx.provenance ? modelData.ctx.provenance.source_class : "") + " · " + (modelData.ctx.provenance ? (modelData.ctx.provenance.source_reference || "") : ""); color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                Label { text: "confidence " + Number(modelData.ctx.confidence || 0).toFixed(2); color: root.textMuted; font.pixelSize: 9 }
                            }
                        }
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: "Authority boundary: observe → normalize → correlate → remember → retrieve → compose context → prove provenance. Execution, orchestration, resource allocation and canonical event truth remain outside FA3 OS."
            color: root.textMuted
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
