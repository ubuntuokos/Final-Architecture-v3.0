import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

LanguageAwareAppShell {
    id: shell

    RoundButton {
        id: animationLauncher
        parent: shell.contentItem
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: Math.round(82 * shell.uiScale)
        anchors.bottomMargin: Math.round(22 * shell.uiScale)
        z: 1000
        width: Math.round(68 * shell.uiScale)
        height: Math.round(44 * shell.uiScale)
        visible: shell.selectedIndex === shell.indexForKey("integrations")
        text: shell.t("Anim", "Anim")
        font.pixelSize: shell.px(10)
        ToolTip.visible: hovered
        ToolTip.text: shell.t("Animáció integrációk: OpenToonz / Krita / Synfig Studio", "Animation integrations: OpenToonz / Krita / Synfig Studio")
        onClicked: animationDrawer.open()
    }

    Drawer {
        id: animationDrawer
        parent: shell.contentItem
        edge: Qt.RightEdge
        modal: true
        interactive: true
        width: Math.min(shell.width * 0.42, Math.round(680 * shell.uiScale))
        height: shell.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle { color: shell.surface0 }

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
                        text: shell.t("Animáció integrációk", "Animation Integrations")
                        font.pixelSize: shell.px(18)
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Label {
                        text: "FA3-ANIMATION-PRODUCTION-001"
                        color: shell.textMuted
                        font.pixelSize: shell.px(9)
                    }
                    ToolButton { text: "×"; onClicked: animationDrawer.close() }
                }
            }

            AnimationIntegrationPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                settings: fa3Settings
                surface1: shell.surface1
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
