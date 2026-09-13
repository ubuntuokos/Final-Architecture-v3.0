import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

AppShell {
    id: shell

    Shortcut {
        sequence: "Ctrl+Shift+L"
        context: Qt.ApplicationShortcut
        onActivated: languageDrawer.open()
    }

    RoundButton {
        id: languageLauncher
        parent: shell.contentItem
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: Math.round(22 * shell.uiScale)
        anchors.bottomMargin: Math.round(22 * shell.uiScale)
        z: 1000
        width: Math.round(48 * shell.uiScale)
        height: width
        text: "文/A"
        font.pixelSize: shell.px(11)
        ToolTip.visible: hovered
        ToolTip.text: shell.t("Nyelvi vezérlés · Ctrl+Shift+L", "Language Control · Ctrl+Shift+L")
        onClicked: languageDrawer.open()
    }

    Drawer {
        id: languageDrawer
        parent: shell.contentItem
        edge: Qt.RightEdge
        modal: true
        interactive: true
        width: Math.min(shell.width * 0.72, Math.round(1080 * shell.uiScale))
        height: shell.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: shell.surface0
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            spacing: 0

            ToolBar {
                Layout.fillWidth: true
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    Label {
                        text: shell.t("Nyelvi vezérlés", "Language Control")
                        font.pixelSize: shell.px(18)
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Label {
                        text: "FA3-GUI-LANGUAGE-CONTROL-001"
                        color: shell.textMuted
                        font.pixelSize: shell.px(9)
                    }
                    ToolButton {
                        text: "×"
                        onClicked: languageDrawer.close()
                    }
                }
            }

            LanguageControlPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
                settings: fa3Settings
                surface1: shell.surface1
                surface2: shell.surface2
                textPrimary: shell.textPrimary
                textMuted: shell.textMuted
                accent: shell.accent
                uiScale: shell.uiScale
                fontScale: shell.fontScale
                language: fa3Settings.language
            }
        }
    }
}
