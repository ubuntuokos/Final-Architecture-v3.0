import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: root
    property string mode: modeBox.currentText
    property string targetVoice: targetVoiceField.text
    property string language: languageField.text
    property int latencyBudgetMs: latencySpin.value
    property bool realtime: modeBox.currentText === "REALTIME_VOICE_CONVERSION"

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Voice Transformation"; font.bold: true; font.pixelSize: 16 }
            Item { Layout.fillWidth: true }
            Label { text: "FA3-VOICE-001"; opacity: 0.7 }
        }

        ComboBox {
            id: modeBox
            Layout.fillWidth: true
            model: [
                "VOICE_CONVERSION",
                "REALTIME_VOICE_CONVERSION",
                "SINGING_VOICE_CONVERSION",
                "STYLE_TRANSFER",
                "SPEECH_REPRESENTATION"
            ]
        }

        TextField {
            id: targetVoiceField
            Layout.fillWidth: true
            placeholderText: modeBox.currentText === "SPEECH_REPRESENTATION"
                ? "Target voice not required"
                : "Canonical target voice identity"
            enabled: modeBox.currentText !== "SPEECH_REPRESENTATION"
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: languageField
                Layout.fillWidth: true
                text: "hu-HU"
                placeholderText: "BCP-47 language"
            }
            SpinBox {
                id: latencySpin
                from: 10
                to: 2000
                value: 80
                editable: true
                enabled: root.realtime
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            opacity: 0.75
            text: "This panel only forms provider-neutral intent. Model Router selects eligible AI providers; Host Resource Broker selects devices. Human-target transformation requires explicit valid consent and rights. Reference-only donor engines are never selectable."
        }

        RowLayout {
            Button { text: "Preview"; enabled: false }
            Button { text: "Compare"; enabled: false }
            Button { text: "Apply"; enabled: false }
            Item { Layout.fillWidth: true }
            Label { text: "No runtime provider admitted by this change"; opacity: 0.65 }
        }
    }
}
