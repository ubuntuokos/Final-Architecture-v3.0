import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var settings
    required property color surface1
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    function t(hu, en) { return language === "en" ? en : hu }
    function px(value) { return Math.max(9, Math.round(value * fontScale)) }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12

        Label { text: root.t("Animáció", "Animation"); font.pixelSize: root.px(24); font.bold: true }
        Label {
            Layout.fillWidth: true
            text: root.t("2D animációs desktop integrációk.", "2D animation desktop integrations.")
            color: root.textMuted
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: root.t("Alapértelmezett", "Default"); font.bold: true }
            ComboBox {
                id: defaultAnimationApp
                Layout.fillWidth: true
                model: ["OpenToonz", "Krita", "Synfig Studio"]
                Component.onCompleted: {
                    const configured = root.settings.value("integrations/animationEditor", "OpenToonz")
                    const idx = model.indexOf(configured)
                    currentIndex = idx >= 0 ? idx : 0
                }
                onActivated: root.settings.setValue("integrations/animationEditor", currentText)
            }
        }

        CheckBox {
            text: "OpenToonz"
            checked: root.settings.value("integrations/opentoonzEnabled", true)
            onToggled: root.settings.setValue("integrations/opentoonzEnabled", checked)
        }
        CheckBox {
            text: "Krita"
            checked: root.settings.value("integrations/kritaAnimationEnabled", true)
            onToggled: root.settings.setValue("integrations/kritaAnimationEnabled", checked)
        }
        CheckBox {
            text: "Synfig Studio"
            checked: root.settings.value("integrations/synfigStudioEnabled", true)
            onToggled: root.settings.setValue("integrations/synfigStudioEnabled", checked)
        }

        Label { text: "FA3-ANIMATION-PRODUCTION-001"; color: root.accent }
        Label {
            Layout.fillWidth: true
            text: root.t("OpenToonz a tradicionális 2D referencia; Krita és Synfig Studio külön animációs integrációként választható.", "OpenToonz is the traditional 2D reference; Krita and Synfig Studio are selectable animation integrations.")
            color: root.textMuted
            wrapMode: Text.WordWrap
        }
        Item { Layout.fillHeight: true }
    }
}
