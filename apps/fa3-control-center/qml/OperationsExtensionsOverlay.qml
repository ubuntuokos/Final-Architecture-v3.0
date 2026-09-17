import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    anchors.fill: parent
    z: 990

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

    ToolButton {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 136
        anchors.bottomMargin: 54
        width: 126
        height: 38
        text: "◈  Operations"
        z: 2
        ToolTip.visible: hovered
        ToolTip.text: "Manager · Model Lab · Update Center · Ctrl+Shift+O"
        onClicked: drawer.open()
        contentItem: Label {
            text: parent.text
            color: root.textPrimary
            font.pixelSize: 10
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 8
            color: parent.hovered ? "#16334f" : "#102a43"
            border.color: root.cyan
        }
    }

    Shortcut {
        sequence: "Ctrl+Shift+O"
        context: Qt.ApplicationShortcut
        onActivated: drawer.open()
    }

    Drawer {
        id: drawer
        parent: Overlay.overlay
        edge: Qt.RightEdge
        modal: true
        interactive: true
        width: Math.min(root.width * 0.84, 1320)
        height: root.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#07111f"; border.color: root.border }

        contentItem: ColumnLayout {
            anchors.fill: parent
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                Layout.leftMargin: 14
                Layout.rightMargin: 10
                Label { text: "FA3 Operations Extensions"; color: root.textPrimary; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }
                Label { text: "projection only · authority delta 0"; color: root.textMuted; font.pixelSize: 9 }
                ToolButton { text: "×"; onClicked: drawer.close() }
            }

            TabBar {
                id: modeTabs
                Layout.fillWidth: true
                TabButton { text: "Manager" }
                TabButton { text: "Model Lab" }
                TabButton { text: "Update Center" }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: modeTabs.currentIndex

                ManagerPage {
                    repository: fa3Repository
                    surface1: root.panel
                    textPrimary: root.textPrimary
                    textMuted: root.textMuted
                    accent: root.accent
                    uiScale: 1.0
                    fontScale: 1.0
                    language: "hu"
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0
                        TabBar {
                            id: modelTabs
                            Layout.fillWidth: true
                            TabButton { text: "OpenModelDB" }
                            TabButton { text: "llmfit" }
                        }
                        StackLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: modelTabs.currentIndex
                            OpenModelDbPage {
                                surface0: "#07111f"
                                surface1: root.panel
                                surface2: root.panelRaised
                                accent: root.accent
                                textPrimary: root.textPrimary
                                textMuted: root.textMuted
                            }
                            LlmfitPage {
                                client: llmfitClient
                                textMuted: root.textMuted
                                accent: root.accent
                                surface1: root.panel
                            }
                        }
                    }
                }

                UpdateCenterPage {
                    panel: root.panel
                    panelRaised: root.panelRaised
                    border: root.border
                    textPrimary: root.textPrimary
                    textMuted: root.textMuted
                    accent: root.accent
                    green: root.green
                    orange: root.orange
                    magenta: root.magenta
                    onCheckRequested: fa3Repository.createDraftChangeSet("UPDATE_FABRIC", "CHECK_ALL", "ALL", "DRAFT_NOT_SUBMITTED update discovery intent")
                    onUpdateSelectedRequested: function(componentIds) { fa3Repository.createDraftChangeSet("UPDATE_FABRIC", "UPDATE_SELECTED", componentIds.join(","), "DRAFT_NOT_SUBMITTED selected update intent") }
                    onSecurityUpdateRequested: fa3Repository.createDraftChangeSet("UPDATE_FABRIC", "SECURITY_UPDATE", "RECOMMENDED", "DRAFT_NOT_SUBMITTED security update intent")
                    onRestartChoiceRequested: function(choice, schedule) { fa3Repository.createDraftChangeSet("UPDATE_RESTART", choice, schedule, "DRAFT_NOT_SUBMITTED restart intent; protected workloads remain authoritative blockers") }
                }
            }
        }
    }
}
