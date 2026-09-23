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

    property var selectedAction: ({})
    property string operationNotice: ""

    signal stageActionIntentRequested(string actionId)
    signal navigateRequested(string routeId)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Agent Action Center"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    text: "Agent Native / Unified Action Fabric · typed contracts · approval/evidence visible · no direct provider bypass"
                    color: root.textMuted
                    font.pixelSize: 10
                }
            }
            Rectangle {
                radius: 8
                implicitWidth: 150
                implicitHeight: 28
                color: root.panelRaised
                border.color: root.accent
                Label { anchors.centerIn: parent; text: "UAF · DRAFT ONLY"; color: root.accent; font.pixelSize: 9; font.bold: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 58
            radius: 8
            color: root.panel
            border.color: root.border
            Label {
                anchors.fill: parent
                anchors.margins: 12
                text: "Intent → Action Contract → Decision Fabric advisory → authorization/approval → provider compatibility → HRB/Secret Broker when required → execution → evidence"
                color: root.textMuted
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.preferredWidth: Math.min(720, root.width * 0.58)
                Layout.fillHeight: true
                radius: 8
                color: root.panel
                border.color: root.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    TextField {
                        id: actionFilter
                        Layout.fillWidth: true
                        placeholderText: "UAF action keresése…"
                    }

                    Label {
                        text: fa3Repository.searchActions(actionFilter.text).length + " canonical GUI/agent action contract"
                        color: root.textMuted
                        font.pixelSize: 9
                    }

                    ListView {
                        id: actionList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 5
                        model: fa3Repository.searchActions(actionFilter.text)
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 86
                            radius: 7
                            color: root.selectedAction.id === modelData.id ? root.panelRaised : "#091624"
                            border.color: root.selectedAction.id === modelData.id ? root.accent : root.border

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.id; color: root.textPrimary; font.pixelSize: 11; font.bold: true }
                                    Label { Layout.fillWidth: true; text: modelData.description; color: root.textMuted; font.pixelSize: 9; elide: Text.ElideRight }
                                    RowLayout {
                                        spacing: 10
                                        Label { text: modelData.mutating ? "MUTATING" : "READ"; color: modelData.mutating ? root.orange : root.green; font.pixelSize: 8; font.bold: true }
                                        Label { text: "approval: " + modelData.approval; color: root.textMuted; font.pixelSize: 8 }
                                        Label { text: modelData.hrbRequired ? "HRB REQUIRED" : "NO HRB"; color: modelData.hrbRequired ? root.orange : root.textMuted; font.pixelSize: 8 }
                                        Label { visible: modelData.decisionReceiptRequired; text: "DecisionReceipt"; color: root.accent; font.pixelSize: 8; font.bold: true }
                                    }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedAction = modelData
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 330
                radius: 8
                color: root.panel
                border.color: root.selectedAction.id ? root.accent : root.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    Label {
                        text: root.selectedAction.id || "Válassz canonical action contractot"
                        color: root.textPrimary
                        font.pixelSize: 16
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.WrapAnywhere
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.selectedAction.description || "A lista közvetlenül a canonical/actions UAF szerződéseiből épül."
                        color: root.textMuted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    GridLayout {
                        visible: Boolean(root.selectedAction.id)
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 7
                        Label { text: "Approval"; color: root.textMuted }
                        Label { text: root.selectedAction.approval || "—"; color: root.textPrimary }
                        Label { text: "Provider role"; color: root.textMuted }
                        Label { text: root.selectedAction.providerRole || "policy-bounded"; color: root.textPrimary; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: "HRB"; color: root.textMuted }
                        Label { text: root.selectedAction.hrbRequired ? "REQUIRED" : "not required"; color: root.selectedAction.hrbRequired ? root.orange : root.green }
                        Label { text: "Decision receipt"; color: root.textMuted }
                        Label { text: root.selectedAction.decisionReceiptRequired ? "REQUIRED" : "contract-defined"; color: root.selectedAction.decisionReceiptRequired ? root.accent : root.textPrimary }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }

                    Button {
                        Layout.fillWidth: true
                        enabled: Boolean(root.selectedAction.id)
                        text: "Stage DRAFT action intent"
                        onClicked: root.stageActionIntentRequested(root.selectedAction.id || "")
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "Ez nem UAF execution. A draft nem ad authorizationt, approvalt, provider admissiont, resource lease-t vagy PASS evidence-et."
                        color: root.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Button { text: "Decision Inspector"; onClicked: root.navigateRequested("decision.inspector") }
                        Button { text: "Security & Approvals"; onClicked: root.navigateRequested("governance.security") }
                        Button { text: "Evidence"; onClicked: root.navigateRequested("governance.evidence") }
                    }

                    Label {
                        visible: root.operationNotice.length > 0
                        Layout.fillWidth: true
                        text: root.operationNotice
                        color: root.accent
                        font.pixelSize: 9
                        wrapMode: Text.WrapAnywhere
                    }

                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
