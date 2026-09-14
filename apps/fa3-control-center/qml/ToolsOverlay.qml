import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    anchors.fill: parent
    z: 1000

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
        id: toolsLauncher
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 18
        anchors.bottomMargin: 18
        width: 104
        height: 38
        text: "▦  Tools"
        z: 2
        ToolTip.visible: hovered
        ToolTip.text: "FA3 Tools · Ctrl+Shift+T"
        Accessible.name: "FA3 Tools"
        onClicked: toolsDrawer.open()
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
            border.color: root.accent
        }
    }

    Shortcut {
        sequence: "Ctrl+Shift+T"
        context: Qt.ApplicationShortcut
        onActivated: toolsDrawer.open()
    }

    Drawer {
        id: toolsDrawer
        parent: Overlay.overlay
        edge: Qt.RightEdge
        modal: true
        interactive: true
        width: Math.min(root.width * 0.76, 1160)
        height: root.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: "#07111f"
            border.color: root.border
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: "#081421"
                border.color: root.border
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 12
                    Label {
                        text: "▦  FA3 Tools"
                        color: root.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Label {
                        text: "FA3-TOOLS-FABRIC-001"
                        color: root.textMuted
                        font.pixelSize: 8
                    }
                    ToolButton { text: "×"; onClicked: toolsDrawer.close() }
                }
            }

            ToolsPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 16
                panel: root.panel
                panelRaised: root.panelRaised
                border: root.border
                textPrimary: root.textPrimary
                textMuted: root.textMuted
                accent: root.accent
                cyan: root.cyan
                green: root.green
                orange: root.orange
                magenta: root.magenta
            }
        }
    }
}
