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
    property bool compactNavigation: false
    property bool statusStripVisible: true

    signal compactNavigationRequested(bool enabled)
    signal statusStripRequested(bool enabled)
    signal navigateRequested(int pageIndex)

    property int selectedIndex: 0
    property string draftResult: ""
    property var sections: [
        {title: "Megjelenés", badge: "GUI", tone: root.accent, detail: "A Control Center közvetlen felületi beállításai."},
        {title: "Erőforrás-policy", badge: "GATED", tone: root.orange, detail: "CPU/GPU/NPU/NUMA preferenciák ChangeSet-intentként."},
        {title: "Hálózat", badge: "POLICY", tone: root.cyan, detail: "Lokális és jóváhagyott távoli provider-hozzáférés."},
        {title: "Biztonság", badge: "FAIL-CLOSED", tone: root.magenta, detail: "Approval, secret-metadata és security policy."},
        {title: "Frissítések", badge: "CONTROLLED", tone: root.green, detail: "Komponens- és provider-frissítési preferenciák."},
        {title: "Naplózás", badge: "JOURNAL", tone: root.accent, detail: "Retention, export és archive-kezelési preferenciák."}
    ]

    function createDraft(scope, action, target, rationale) {
        draftResult = fa3Repository.createDraftChangeSet(scope, action, target, rationale)
    }

    component SettingLine: ColumnLayout {
        property string labelText: ""
        property string helpText: ""
        Layout.fillWidth: true
        spacing: 2
        Label {
            text: parent.labelText
            color: root.textPrimary
            font.pixelSize: 11
            font.bold: true
            Layout.fillWidth: true
        }
        Label {
            text: parent.helpText
            color: root.textMuted
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label {
                text: "Rendszerbeállítások"
                color: root.textPrimary
                font.pixelSize: 22
                font.bold: true
            }
            Label {
                text: "Válassz kategóriát a bal oldalon; a jobb oldali munkaterület a rendelkezésre álló helyet használja, és szükség esetén görgethető."
                color: root.textMuted
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                id: categoryPane
                Layout.preferredWidth: Math.max(220, Math.min(270, root.width * 0.24))
                Layout.minimumWidth: 220
                Layout.maximumWidth: 270
                Layout.fillHeight: true
                radius: 9
                color: root.panel
                border.color: root.border
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Label {
                        text: "Kategóriák"
                        color: root.textMuted
                        font.pixelSize: 9
                        font.bold: true
                    }

                    ListView {
                        id: settingsCategoryList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 6
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.sections
                        currentIndex: root.selectedIndex
                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AlwaysOn
                            active: true
                        }

                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: ListView.view.width - 10
                            height: 54
                            radius: 7
                            color: index === root.selectedIndex ? root.panelRaised : (settingsMouse.containsMouse ? "#10233a" : "transparent")
                            border.color: index === root.selectedIndex ? modelData.tone : "transparent"
                            border.width: index === root.selectedIndex ? 1 : 0

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8
                                Rectangle {
                                    width: 7
                                    height: 7
                                    radius: 4
                                    color: modelData.tone
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label {
                                            text: modelData.title
                                            color: root.textPrimary
                                            font.pixelSize: 11
                                            font.bold: true
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            text: modelData.badge
                                            color: modelData.tone
                                            font.pixelSize: 7
                                            font.bold: true
                                        }
                                    }
                                    Label {
                                        text: modelData.detail
                                        color: root.textMuted
                                        font.pixelSize: 8
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            MouseArea {
                                id: settingsMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedIndex = index
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: settingsWorkspace
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 520
                radius: 9
                color: root.panel
                border.color: root.sections[root.selectedIndex].tone
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: root.sections[root.selectedIndex].title
                            color: root.textPrimary
                            font.pixelSize: 18
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Label {
                            text: root.sections[root.selectedIndex].badge
                            color: root.sections[root.selectedIndex].tone
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                    Label {
                        text: root.sections[root.selectedIndex].detail
                        color: root.textMuted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: root.border
                    }

                    ScrollView {
                        id: settingsDetailScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AlwaysOn
                            active: true
                        }

                        ColumnLayout {
                            width: settingsDetailScroll.availableWidth
                            spacing: 12

                            StackLayout {
                                id: settingsStack
                                Layout.fillWidth: true
                                Layout.minimumHeight: Math.max(300, settingsDetailScroll.availableHeight - 12)
                                currentIndex: root.selectedIndex

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine {
                                        labelText: "Kompakt navigáció"
                                        helpText: "Keskenyebb oldalsávot és sűrűbb menüt használ."
                                    }
                                    Switch {
                                        text: checked ? "Bekapcsolva" : "Kikapcsolva"
                                        checked: root.compactNavigation
                                        onToggled: root.compactNavigationRequested(checked)
                                    }
                                    SettingLine {
                                        labelText: "Alsó állapotsáv"
                                        helpText: "CPU / GPU / NPU / RAM / Pressure státuszsáv megjelenítése."
                                    }
                                    Switch {
                                        text: checked ? "Látható" : "Rejtett"
                                        checked: root.statusStripVisible
                                        onToggled: root.statusStripRequested(checked)
                                    }
                                    Label {
                                        text: "A két megjelenítési beállítás azonnal érvényesül az aktuális Control Center munkamenetben."
                                        color: root.green
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine {
                                        labelText: "Erőforrás-profil"
                                        helpText: "A host módosítása nem közvetlen: a választás ChangeSet-tervezetet készít."
                                    }
                                    ComboBox {
                                        id: resourcePolicy
                                        Layout.preferredWidth: 260
                                        model: ["Balanced", "Interactive", "Throughput"]
                                    }
                                    Button {
                                        text: "ChangeSet-tervezet készítése"
                                        onClicked: root.createDraft("resources", "set-resource-policy", "host", "Requested resource policy: " + resourcePolicy.currentText)
                                    }
                                    Label {
                                        text: "Közvetlen CPU/GPU/NPU/NUMA módosítás tiltott; a broker/approval lánc marad az authority."
                                        color: root.orange
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine {
                                        labelText: "Provider-hozzáférés"
                                        helpText: "Lokális-only vagy jóváhagyott távoli provider egress-intent."
                                    }
                                    ComboBox {
                                        id: networkPolicy
                                        Layout.preferredWidth: 310
                                        model: ["Local only", "Approved remote providers"]
                                    }
                                    Button {
                                        text: "Hálózati policy-tervezet"
                                        onClicked: root.createDraft("network", "set-provider-egress-policy", "provider-egress", "Requested network policy: " + networkPolicy.currentText)
                                    }
                                    Label {
                                        text: "A beépített Web Workspace nem nyit külső böngészőt; a provider-egress ettől külön policy."
                                        color: root.textMuted
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine {
                                        labelText: "Fail-closed védelem"
                                        helpText: "Privilegizált művelet, secret vagy approval megkerülése nem állítható át ebből a GUI-ból."
                                    }
                                    CheckBox {
                                        text: "Approval required"
                                        checked: true
                                        enabled: false
                                    }
                                    CheckBox {
                                        text: "Secret values hidden"
                                        checked: true
                                        enabled: false
                                    }
                                    Button {
                                        text: "Security & Approvals megnyitása"
                                        onClicked: root.navigateRequested(10)
                                    }
                                    Label {
                                        text: "A biztonsági authority szándékosan nem duplikálható a Rendszerbeállításokban."
                                        color: root.magenta
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine {
                                        labelText: "Frissítési csatorna"
                                        helpText: "A választás kontrollált update-intentként kerül továbbításra."
                                    }
                                    ComboBox {
                                        id: updateChannel
                                        Layout.preferredWidth: 240
                                        model: ["Stable", "Preview"]
                                    }
                                    Button {
                                        text: "Frissítési tervezet"
                                        onClicked: root.createDraft("updates", "set-update-channel", "fa3-components", "Requested update channel: " + updateChannel.currentText)
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine {
                                        labelText: "Napló-retention"
                                        helpText: "A retention módosítása Journal policy-tervezet; meglévő archívumot nem töröl közvetlenül."
                                    }
                                    RowLayout {
                                        Label {
                                            text: "Napok:"
                                            color: root.textMuted
                                        }
                                        SpinBox {
                                            id: retentionDays
                                            from: 7
                                            to: 3650
                                            value: 90
                                            editable: true
                                        }
                                    }
                                    Button {
                                        text: "Retention-tervezet"
                                        onClicked: root.createDraft("journal", "set-retention-days", "journal-retention", "Requested retention days: " + retentionDays.value)
                                    }
                                    Item { Layout.fillHeight: true }
                                }
                            }

                            Rectangle {
                                visible: root.draftResult.length > 0
                                Layout.fillWidth: true
                                implicitHeight: draftLabel.implicitHeight + 20
                                radius: 6
                                color: "#091624"
                                border.color: root.accent
                                Label {
                                    id: draftLabel
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: root.draftResult
                                    color: root.accent
                                    font.pixelSize: 9
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
