import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property var categories: []
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
    property int selectedCategory: 0
    property string draftPath: ""

    function filteredCategories(query) {
        var needle = query.trim().toLowerCase()
        if (needle.length === 0) return categories
        return categories.filter(function(v) {
            return (v.code + " " + v.title + " " + v.description + " " + v.protocols).toLowerCase().indexOf(needle) >= 0
        })
    }
    function currentCategory() {
        var rows = filteredCategories(rtdSearch.text)
        if (rows.length === 0) return null
        return rows[Math.max(0, Math.min(selectedCategory, rows.length - 1))]
    }
    component Panel: Rectangle {
        radius: 9; color: root.panel; border.color: root.border; border.width: 1
    }
    component Metric: Panel {
        property string titleText: ""; property string valueText: "—"; property string noteText: ""; property color tone: root.accent
        implicitHeight: 94
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 3
            Label { text: parent.parent.titleText; color: root.textMuted; font.pixelSize: 9; font.bold: true }
            Label { text: parent.parent.valueText; color: parent.parent.tone; font.pixelSize: 17; font.bold: true }
            Label { text: parent.parent.noteText; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
        }
    }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        padding: 18
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        ColumnLayout {
            width: pageScroll.availableWidth
            spacing: 14
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                Label { text: "RTD Providers"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "Real-Time Data provider-ek központi operátori nézete · adatforrás, frissesség, auth, policy és provenance"; color: root.textMuted; font.pixelSize: 10 }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Metric { Layout.fillWidth: true; titleText: "KATEGÓRIAFELÜLET"; valueText: root.categories.length.toString(); noteText: "RTD provider osztály"; tone: root.cyan }
                Metric { Layout.fillWidth: true; titleText: "LIVE ADAPTER"; valueText: "—"; noteText: "runtime evidence szükséges"; tone: root.orange }
                Metric { Layout.fillWidth: true; titleText: "FRESHNESS"; valueText: "GATED"; noteText: "provider / adapter SLA"; tone: root.orange }
                Metric { Layout.fillWidth: true; titleText: "POLICY"; valueText: "FAIL-CLOSED"; noteText: "explicit egress + auth"; tone: root.magenta }
            }
            Panel {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(500, pageScroll.availableHeight - 190)
                RowLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 12
                    ColumnLayout {
                        Layout.preferredWidth: 350; Layout.fillHeight: true; spacing: 8
                        TextField { id: rtdSearch; Layout.fillWidth: true; placeholderText: "RTD kategória keresése…"; onTextChanged: root.selectedCategory = 0 }
                        Label { text: root.filteredCategories(rtdSearch.text).length + " kategória"; color: root.textMuted; font.pixelSize: 9 }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; boundsBehavior: Flickable.StopAtBounds
                            model: root.filteredCategories(rtdSearch.text); currentIndex: root.selectedCategory
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                            delegate: ItemDelegate {
                                width: ListView.view.width; height: 60; highlighted: index === root.selectedCategory; onClicked: root.selectedCategory = index
                                background: Rectangle { radius: 6; color: index === root.selectedCategory ? root.panelRaised : hovered ? "#0d1f31" : "transparent"; border.color: index === root.selectedCategory ? root.accent : "transparent" }
                                contentItem: ColumnLayout {
                                    spacing: 1
                                    Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.code; color: root.textMuted; font.pixelSize: 8; font.family: "monospace" }
                                }
                            }
                        }
                    }
                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.border }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                        Label { text: root.currentCategory() ? root.currentCategory().title : "Nincs találat"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.currentCategory() ? root.currentCategory().description : "A szűréshez nincs RTD kategória."; color: root.textMuted; font.pixelSize: 10 }
                        GridLayout {
                            Layout.fillWidth: true; columns: 2; columnSpacing: 18; rowSpacing: 10
                            Label { text: "Provider state"; color: root.textMuted }
                            Label { text: "ADAPTER-GATED"; color: root.orange; font.bold: true }
                            Label { text: "Last update"; color: root.textMuted }
                            Label { text: "N/A — nincs runtime evidence"; color: root.textPrimary }
                            Label { text: "Freshness SLA"; color: root.textMuted }
                            Label { text: root.currentCategory() ? root.currentCategory().freshness : "—"; color: root.textPrimary }
                            Label { text: "Protocols"; color: root.textMuted }
                            Label { text: root.currentCategory() ? root.currentCategory().protocols : "—"; color: root.textPrimary }
                            Label { text: "Authentication"; color: root.textMuted }
                            Label { text: "NOT CONFIGURED"; color: root.orange; font.bold: true }
                            Label { text: "Policy"; color: root.textMuted }
                            Label { text: "FAIL-CLOSED"; color: root.magenta; font.bold: true }
                            Label { text: "Provenance"; color: root.textMuted }
                            Label { text: "REQUIRED"; color: root.cyan; font.bold: true }
                        }
                        Panel {
                            Layout.fillWidth: true; Layout.preferredHeight: 145; color: root.panelRaised
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 7
                                Label { text: "Authority boundary"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Az RTD Providers a live-data capability operátori projekciója. Az Integrations csak a technikai adaptert mutatja; az Agents & Workflows csak a felhasználást. A GUI nem állít ONLINE állapotot, nem talál ki frissességet és nem kerülheti meg az auth/egress policy-t."; color: root.textMuted; font.pixelSize: 9 }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Button {
                                text: "Adapter ChangeSet-tervezet"; enabled: root.currentCategory() !== null
                                onClicked: {
                                    var c = root.currentCategory()
                                    root.draftPath = fa3Repository.createDraftChangeSet("RTD_PROVIDER", "propose.rtd.adapter", c.code, "RTD adapter konfigurációs javaslat: " + c.title + ". Freshness/auth/policy/provenance evidence kötelező.")
                                }
                            }
                            Label { text: root.draftPath; color: root.accent; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        }
                    }
                }
            }
            Panel {
                Layout.fillWidth: true; Layout.preferredHeight: 170
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Canonical RTD projection"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Label { text: fa3Repository.searchRecords("RTD").length + " RTD-találat a canonical indexben"; color: root.textMuted; font.pixelSize: 9 }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: fa3Repository.searchRecords("RTD")
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                        delegate: ItemDelegate {
                            width: ListView.view.width; height: 40
                            contentItem: RowLayout {
                                Label { text: modelData.id; color: root.textPrimary; font.family: "monospace"; Layout.preferredWidth: 330; elide: Text.ElideRight }
                                Label { text: modelData.title; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: modelData.status; color: root.orange; Layout.preferredWidth: 150; elide: Text.ElideRight }
                            }
                        }
                    }
                }
            }
        }
    }
}
