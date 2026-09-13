import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

LanguageAwareAppShell {
    id: shell

    Shortcut {
        sequence: "Ctrl+Alt+P"
        context: Qt.ApplicationShortcut
        onActivated: plannerDrawer.open()
    }

    RoundButton {
        parent: shell.contentItem
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: Math.round(82 * shell.uiScale)
        anchors.bottomMargin: Math.round(22 * shell.uiScale)
        z: 1001
        width: Math.round(48 * shell.uiScale)
        height: width
        text: "P"
        visible: fa3Settings.value("planner/showLauncher", true)
        ToolTip.visible: hovered
        ToolTip.text: shell.t("Tervező · Ctrl+Alt+P", "Planner · Ctrl+Alt+P")
        onClicked: plannerDrawer.open()
    }

    Drawer {
        id: plannerDrawer
        parent: shell.contentItem
        edge: Qt.RightEdge
        modal: true
        width: Math.min(shell.width * 0.52, Math.round(760 * shell.uiScale))
        height: shell.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        PlannerControlPage {
            anchors.fill: parent
            settings: fa3Settings
            textMuted: shell.textMuted
            accent: shell.accent
            fontScale: shell.fontScale
            language: fa3Settings.language
        }
    }
}
