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

    property var updates: []
    property string channel: "STABLE"
    property bool checking: false
    property string restartState: "NONE"
    property string restartKind: ""
    property var updatedComponents: []
    property var activeProtectedWorkloads: []
    property string recommendedRestartChoice: "WHEN_IDLE_SAFE"
    property string scheduledRestart: ""
    property string operationNotice: ""

    signal stageActionIntentRequested(string actionId, string target, string rationale)

    function selectedIds() {
        var ids = []
        for (var i = 0; i < updateList.count; ++i) {
            var item = updateList.itemAtIndex(i)
            if (item && item.selectedForUpdate)
                ids.push(item.componentId)
        }
        return ids
    }

    function selectedTarget() {
        return selectedIds().join(",")
    }

    function restartRequired() {
        return restartState === "RESTART_REQUIRED_SERVICE"
            || restartState === "REBOOT_REQUIRED_HOST"
            || restartState === "DEFERRED"
            || restartState === "SCHEDULED"
            || restartState === "WAITING_FOR_IDLE"
            || restartState === "READY_TO_RESTART"
    }

    function stageRestart(choice, schedule) {
        var target = choice + (schedule && schedule.length > 0 ? ("@" + schedule) : "")
        root.stageActionIntentRequested(
            "update.restart-choice",
            target,
            "DRAFT_NOT_SUBMITTED: user restart timing choice; UAF authorization, protected-workload checks and evidence remain mandatory."
        )
    }

    function impactColor(impact) {
        if (impact === "HOST_CRITICAL")
            return magenta
        if (impact === "HEAVY")
            return orange
        if (impact === "QUICK")
            return green
        return accent
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true

                Label {
                    text: "FA3 Update Center"
                    color: root.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                }

                Label {
                    text: "UAF DRAFT ONLY · Check All discovery · selective/security maintenance · workload-aware restart"
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                radius: 6
                implicitWidth: 156
                implicitHeight: 28
                color: root.panelRaised
                border.color: root.accent

                Label {
                    anchors.centerIn: parent
                    text: root.channel + " · DRAFT ONLY"
                    color: root.accent
                    font.bold: true
                    font.pixelSize: 9
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: root.checking ? "Ellenőrzés…" : "Frissítések keresése"
                enabled: !root.checking
                onClicked: root.stageActionIntentRequested(
                    "update.check",
                    "",
                    "DRAFT_NOT_SUBMITTED: discovery only; no update activation."
                )
            }

            Button {
                text: "Kijelöltek frissítése"
                enabled: root.selectedIds().length > 0
                onClicked: root.stageActionIntentRequested(
                    "update.apply-selected",
                    root.selectedTarget(),
                    "DRAFT_NOT_SUBMITTED: selected update transaction; authorization, compatibility, HRB/health and rollback gates remain mandatory."
                )
            }

            Button {
                text: "Biztonsági frissítések"
                onClicked: root.stageActionIntentRequested(
                    "update.security",
                    "",
                    "DRAFT_NOT_SUBMITTED: policy-eligible security maintenance; protected workloads and restart rules remain authoritative."
                )
            }

            Item {
                Layout.fillWidth: true
            }

            Label {
                text: "Nincs vak Update All"
                color: root.textMuted
                font.pixelSize: 9
            }
        }

        Rectangle {
            visible: root.restartRequired()
            Layout.fillWidth: true
            implicitHeight: restartBox.implicitHeight + 28
            radius: 8
            color: root.panelRaised
            border.color: root.restartKind === "host" ? root.magenta : root.orange

            ColumnLayout {
                id: restartBox
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 14
                spacing: 8

                Label {
                    text: root.restartKind === "host"
                        ? "A frissítéshez gépújraindítás szükséges"
                        : "A frissítéshez szolgáltatás-újraindítás szükséges"
                    color: root.restartKind === "host" ? root.magenta : root.orange
                    font.pixelSize: 14
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    text: root.updatedComponents.length > 0
                        ? ("Frissített komponensek: " + root.updatedComponents.join(", "))
                        : "A frissítés befejeződött."
                    color: root.textPrimary
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    visible: root.activeProtectedWorkloads.length > 0
                    text: "Aktív védett workloadok: "
                        + root.activeProtectedWorkloads.join(", ")
                        + ". Az FA3 nem szakítja meg őket automatikusan."
                    color: root.orange
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Button {
                        text: "Újraindítás most"
                        onClicked: root.stageRestart("RESTART_NOW", "")
                    }

                    Button {
                        text: "Amikor az FA3 tétlen"
                        highlighted: root.recommendedRestartChoice === "WHEN_IDLE_SAFE"
                        onClicked: root.stageRestart("WHEN_IDLE_SAFE", "")
                    }

                    Button {
                        text: "Időpont kiválasztása"
                        onClicked: scheduleDialog.open()
                    }

                    Button {
                        text: "Később"
                        onClicked: root.stageRestart("LATER", "")
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }

        Label {
            visible: root.operationNotice.length > 0
            Layout.fillWidth: true
            text: root.operationNotice
            color: root.accent
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: root.panel
            border.color: root.border

            ListView {
                id: updateList
                anchors.fill: parent
                anchors.margins: 10
                clip: true
                spacing: 6
                model: root.updates

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                delegate: Rectangle {
                    id: updateRow
                    required property var modelData
                    property bool selectedForUpdate: false
                    property string componentId: String(modelData.id || "")

                    width: ListView.view.width
                    height: 78
                    radius: 7
                    color: root.panelRaised
                    border.color: selectedForUpdate ? root.accent : root.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10

                        CheckBox {
                            checked: updateRow.selectedForUpdate
                            enabled: modelData.status !== "BLOCKED"
                            onToggled: updateRow.selectedForUpdate = checked
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Label {
                                text: modelData.name || modelData.id || "component"
                                color: root.textPrimary
                                font.bold: true
                            }

                            Label {
                                text: (modelData.currentVersion || "?")
                                    + " → "
                                    + (modelData.availableVersion || "?")
                                    + " · "
                                    + (modelData.source || "provider")
                                color: root.textMuted
                                font.pixelSize: 9
                            }
                        }

                        Label {
                            text: modelData.impact || "NORMAL"
                            color: root.impactColor(text)
                            font.pixelSize: 9
                            font.bold: true
                        }

                        Label {
                            text: modelData.status || "REVIEW"
                            color: text === "READY"
                                ? root.green
                                : (text === "BLOCKED" ? root.magenta : root.orange)
                            font.pixelSize: 9
                            font.bold: true
                            Layout.preferredWidth: 92
                            horizontalAlignment: Text.AlignRight
                        }
                    }
                }
            }
        }

        Label {
            text: "A GUI csak DRAFT_NOT_SUBMITTED UAF intentet készít. Nem telepít csomagot, nem indít újra szolgáltatást/gépet és nem ír canonical állapotot."
            color: root.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    Dialog {
        id: scheduleDialog
        title: "Újraindítás időzítése"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent

        contentItem: ColumnLayout {
            spacing: 8

            Label {
                text: "ISO helyi időpont"
                color: root.textMuted
            }

            TextField {
                id: scheduleField
                Layout.preferredWidth: 360
                placeholderText: "YYYY-MM-DDTHH:MM:SS+02:00"
                text: root.scheduledRestart
            }

            Label {
                text: "Aktív védett workload esetén az FA3 elhalasztja és jelzi az újraindítást."
                color: root.orange
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        onAccepted: root.stageRestart("SCHEDULE", scheduleField.text.trim())
    }
}
