import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0d1c2f"
    property color panelRaised: "#132a42"
    property color border: "#24384f"
    property color textPrimary: "#eef5ff"
    property color textMuted: "#8096ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    // Backend-owned models. The QML surface never invents PASS or priority.
    property var accelerators: []
    property var activeConflict: null
    property string guardMode: "RECOMMEND"
    property string operationNotice: ""

    signal refreshRequested()
    signal decisionRequested(string conflictId, string action, string targetAcceleratorId, bool remember)

    function value(obj, key, fallback) {
        if (!obj || obj[key] === undefined || obj[key] === null) return fallback
        return obj[key]
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Accelerator Guard"; color: root.textPrimary; font.pixelSize: 20; font.bold: true }
                Label {
                    text: "GPU/NPU contention · FA3-ACCEL-GUARD-001 · user-priority arbitration"
                    color: root.textMuted
                    font.pixelSize: 10
                }
            }
            Rectangle {
                radius: 6
                implicitWidth: 120
                implicitHeight: 28
                color: root.panelRaised
                border.color: root.accent
                Label { anchors.centerIn: parent; text: root.guardMode; color: root.accent; font.bold: true; font.pixelSize: 9 }
            }
            Button { text: "Refresh"; onClicked: root.refreshRequested() }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "A Guard technikai kockázatot értékel és ajánlást ad. Konfliktus esetén alapértelmezetten nem dönt a felhasználó helyett, és nem állít le külső vagy FA3 workloadot hallgatólagosan."
            color: root.textMuted
            font.pixelSize: 10
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
            Layout.preferredHeight: 190
            radius: 8
            color: root.panel
            border.color: root.border

            ListView {
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                model: root.accelerators
                spacing: 4
                delegate: Rectangle {
                    width: ListView.view.width
                    height: 74
                    radius: 6
                    color: root.panelRaised
                    border.color: root.value(modelData, "state", "UNKNOWN") === "USER_DECISION_REQUIRED" ? root.orange : root.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 12
                        ColumnLayout {
                            Layout.preferredWidth: 190
                            Label { text: root.value(modelData, "id", "accelerator"); color: root.textPrimary; font.bold: true }
                            Label { text: root.value(modelData, "kind", "GPU/NPU") + " · " + root.value(modelData, "role", "compute"); color: root.textMuted; font.pixelSize: 9 }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: root.value(modelData, "usageText", "telemetry pending"); color: root.textPrimary }
                            Label { text: root.value(modelData, "clientsText", "no attributed clients"); color: root.textMuted; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        Label {
                            text: root.value(modelData, "state", "UNKNOWN")
                            color: text === "USER_DECISION_REQUIRED" ? root.orange : root.green
                            font.bold: true
                            font.pixelSize: 9
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: root.panel
            border.color: root.activeConflict ? root.orange : root.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Label {
                    text: root.activeConflict ? "Accelerator decision required" : "No unresolved accelerator conflict"
                    color: root.activeConflict ? root.orange : root.green
                    font.pixelSize: 15
                    font.bold: true
                }

                GridLayout {
                    visible: root.activeConflict !== null
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 16
                    rowSpacing: 6
                    Label { text: "Accelerator"; color: root.textMuted }
                    Label { text: root.value(root.activeConflict, "accelerator_id", ""); color: root.textPrimary }
                    Label { text: "Existing workload"; color: root.textMuted }
                    Label { text: root.value(root.activeConflict, "existingText", "external workload"); color: root.textPrimary }
                    Label { text: "FA3 request"; color: root.textMuted }
                    Label { text: root.value(root.activeConflict, "requestText", "FA3 workload"); color: root.textPrimary }
                    Label { text: "Assessment"; color: root.textMuted }
                    Label { text: root.value(root.activeConflict, "assessmentText", "technical assessment pending"); color: root.orange }
                    Label { text: "Recommendation"; color: root.textMuted }
                    Label { text: root.value(root.activeConflict, "recommendationText", "Wait for measured recommendation"); color: root.accent }
                }

                ComboBox {
                    id: actionChoice
                    visible: root.activeConflict !== null
                    Layout.fillWidth: true
                    model: [
                        "KEEP_EXTERNAL",
                        "PREFER_FA3",
                        "MOVE_FA3",
                        "PAUSE_FA3",
                        "WAIT",
                        "ALLOW_SHARED",
                        "CANCEL_FA3",
                        "ALLOW_ONCE"
                    ]
                }

                TextField {
                    id: targetAccelerator
                    visible: root.activeConflict !== null && actionChoice.currentText === "MOVE_FA3"
                    Layout.fillWidth: true
                    placeholderText: "Target accelerator ID"
                }

                CheckBox {
                    id: rememberDecision
                    visible: root.activeConflict !== null
                    text: "Remember this decision as an explicit policy"
                }

                RowLayout {
                    visible: root.activeConflict !== null
                    Layout.fillWidth: true
                    Item { Layout.fillWidth: true }
                    Label { text: "No action has been taken."; color: root.textMuted; font.pixelSize: 9 }
                    Button {
                        text: "Apply decision"
                        onClicked: root.decisionRequested(
                            root.value(root.activeConflict, "id", ""),
                            actionChoice.currentText,
                            targetAccelerator.text,
                            rememberDecision.checked
                        )
                    }
                }
            }
        }
    }
}
