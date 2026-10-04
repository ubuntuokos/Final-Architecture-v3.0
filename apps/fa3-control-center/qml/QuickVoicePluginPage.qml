import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string runtimeMessage: fa3VoiceWorkspace.state + (fa3VoiceWorkspace.lastError.length ? " · " + fa3VoiceWorkspace.lastError : "")
    Component.onCompleted: fa3VoiceWorkspace.refresh()
    Connections { target: fa3VoiceWorkspace; function onGenerationCompleted(result) { root.runtimeMessage = "INSERT READY · " + result.job_id } function onFitCompleted(result) { root.runtimeMessage = "FIT · " + result.decision } function onQuickDubCompleted(result) { root.runtimeMessage = "DUB PLAN READY · " + result.schema } }
    property color panel: "#20242a"
    property color panelRaised: "#292f38"
    property color border: "#3a424e"
    property color textPrimary: "#f1f3f7"
    property color textMuted: "#a9b0bc"
    property color accent: "#25a7ff"
    property color green: "#76c893"
    property color orange: "#f2b05e"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "QuickClip · Shared Voice Plugin"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "QUICK projection · same FA3 Shared Voice core · no application-owned TTS authority"; color: root.accent; font.pixelSize: 10; font.bold: true }
            }
            Item { Layout.fillWidth: true }
            ComboBox { model: ["QUICK","STANDARD","ADVANCED"] }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                SplitView.preferredWidth: 470
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    TabBar {
                        id: quickTabs
                        Layout.fillWidth: true
                        TabButton { text: "Generate" }
                        TabButton { text: "Quick Dub" }
                        TabButton { text: "Narration" }
                        TabButton { text: "From Text" }
                    }
                    Label { text: "Script"; color: root.textMuted }
                    TextArea { id: quickScript; Layout.fillWidth: true; Layout.preferredHeight: 110; text: "Mutasd be 30 másodpercben ezt a terméket."; wrapMode: TextEdit.Wrap }
                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Label { text: "Voice"; color: root.textMuted } ComboBox { id: quickVoice; Layout.fillWidth: true; model: ["Narrator (hu-HU)","Character A","Character B"] }
                        Label { text: "Language"; color: root.textMuted } ComboBox { id: quickLanguage; Layout.fillWidth: true; model: ["hu-HU","en-US"] }
                        Label { text: "Style"; color: root.textMuted } ComboBox { Layout.fillWidth: true; model: ["Natural","Energetic","Calm"] }
                        Label { text: "Duration"; color: root.textMuted } ComboBox { Layout.fillWidth: true; model: ["Fit to Clip (27.8 s)","Keep original timing"] }
                        Label { text: "Effects"; color: root.textMuted } ComboBox { Layout.fillWidth: true; model: ["None","Studio","Radio","Warm"] }
                    }
                    CheckBox { text: "Generate editable captions"; checked: true }
                    CheckBox { id: duckMusic; text: "Duck background music"; checked: true }
                    CheckBox { text: "Preserve previous take"; checked: true }
                    RowLayout {
                        Button { text: "Dictate"; enabled: false }
                        Button { text: "Preview"; enabled: false }
                        Item { Layout.fillWidth: true }
                    }
                    Button { Layout.fillWidth: true; text: "Generate & Insert"; enabled: fa3VoiceWorkspace.state === "READY"; onClicked: fa3VoiceWorkspace.generate(quickScript.text, quickVoice.currentText, quickLanguage.currentText, 27800, duckMusic.checked, true) }
                    Label { text: root.runtimeMessage + " · UAF → FA3-VOICE-001 → Model Router → HRB"; color: fa3VoiceWorkspace.state === "READY" ? root.green : root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 10 }
                }
            }

            Rectangle {
                SplitView.fillWidth: true
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    Label { text: "Fit to Clip"; color: root.textPrimary; font.bold: true }
                    GridLayout {
                        columns: 2
                        Label { text: "Target"; color: root.textMuted } Label { text: "27.8 s"; color: root.textPrimary }
                        Label { text: "Generated"; color: root.textMuted } Label { text: "31.2 s"; color: root.orange }
                    }
                    RadioButton { text: "Adjust speech rate · bounded"; checked: true }
                    RadioButton { text: "Suggest shorter script · Preview → explicit Apply" }
                    RadioButton { text: "Extend video" }
                    RadioButton { text: "Keep original timing" }
                    RowLayout { Button { text: "Preview Fit"; enabled: fa3VoiceWorkspace.state === "READY"; onClicked: fa3VoiceWorkspace.fitToClip(27800,31200) } Button { text: "Apply"; enabled: false } }

                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                    Label { text: "Takes"; color: root.textPrimary; font.bold: true }
                    Repeater {
                        model: ["Take 1 · Natural · 00:28","Take 2 · Energetic · 00:27","Take 3 · Calm · 00:29"]
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 38; color: root.panelRaised; radius: 5
                            RowLayout { anchors.fill: parent; anchors.margins: 7; Label { text: modelData; color: root.textPrimary } Item { Layout.fillWidth: true } Button { text: "Select"; enabled: false } }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                    Label { text: "Quick Dub"; color: root.textPrimary; font.bold: true }
                    RowLayout {
                        ComboBox { Layout.fillWidth: true; model: ["Source: English","Source: Hungarian"] }
                        ComboBox { Layout.fillWidth: true; model: ["Target: Hungarian","Target: English"] }
                    }
                    Label { text: "Speaker 1 → Voice Profile A"; color: root.textMuted }
                    Label { text: "Speaker 2 → Voice Profile B"; color: root.textMuted }
                    Label { text: "STT → speaker segmentation → optional translation → voice mapping → TTS → alignment → editable mix"; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Button { text: "Build Quick Dub Plan"; enabled: fa3VoiceWorkspace.state === "READY"; onClicked: fa3VoiceWorkspace.quickDub("CURRENT_QUICKCLIP_MEDIA", "en", "hu-HU") }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
