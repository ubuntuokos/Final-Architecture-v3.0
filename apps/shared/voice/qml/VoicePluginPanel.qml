import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: root
    property string hostApplication: "fa3.quickclip"
    property string projectionMode: "QUICK"
    property string voiceProfile: "voice.narrator.hu"
    property string language: "hu-HU"
    property string styleIntent: "Natural"
    property string durationPolicy: "Fit to Clip"
    property bool generateCaptions: true
    property bool duckBackgroundMusic: true
    property bool preservePreviousTake: true
    property real targetDurationSeconds: 27.8
    property real generatedDurationSeconds: 31.2
    signal stageActionRequested(string actionId, string target, string rationale)

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Shared Voice Plugin"; color: "#f1f3f7"; font.pixelSize: 17; font.bold: true }
            Label { text: root.projectionMode; color: "#c594ff"; font.bold: true }
            Item { Layout.fillWidth: true }
            Label { text: root.hostApplication; color: "#a9b0bc" }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Generate" }
            TabButton { text: "Quick Dub" }
            TabButton { text: "Narration" }
        }

        StackLayout {
            currentIndex: tabs.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    Label { text: "Script"; color: "#a9b0bc" }
                    TextArea {
                        id: scriptText
                        Layout.fillWidth: true
                        Layout.preferredHeight: 96
                        text: "Mutasd be röviden ezt a jelenetet."
                        wrapMode: TextEdit.Wrap
                    }
                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Label { text: "Voice"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["Narrator (hu-HU)", "Character A", "Character B", "Project Voice"] }
                        Label { text: "Language"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["hu-HU", "en-US", "de-DE"]; currentIndex: 0 }
                        Label { text: "Style"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["Natural", "Calm", "Energetic", "Character Intent"] }
                        Label { text: "Speed"; color: "#a9b0bc" }
                        RowLayout {
                            Layout.fillWidth: true
                            Slider { Layout.fillWidth: true; from: 0.75; to: 1.35; value: 1.0 }
                            Label { text: "1.0×"; color: "#f1f3f7" }
                        }
                        Label { text: "Duration"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["Fit to Clip", "Keep Voice Timing", "Extend Video", "Manual Review"] }
                        Label { text: "Effects"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["None", "Natural Voice", "Radio", "Room", "Custom Chain"] }
                    }

                    GroupBox {
                        title: "Fit to Clip"
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label {
                                text: "Target " + root.targetDurationSeconds.toFixed(1) + " s · generated " + root.generatedDurationSeconds.toFixed(1) + " s"
                                color: "#f2b05e"
                            }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["Adjust speech rate", "Suggest shorter script", "Extend video", "Keep original timing"]
                            }
                            Label {
                                text: "Text rewriting is preview-only until explicit Apply."
                                color: "#a9b0bc"
                                font.pixelSize: 10
                            }
                        }
                    }

                    CheckBox { text: "Generate editable captions"; checked: root.generateCaptions }
                    CheckBox { text: "Duck background music"; checked: root.duckBackgroundMusic }
                    CheckBox { text: "Preserve previous take"; checked: root.preservePreviousTake }

                    RowLayout {
                        Button {
                            text: "Dictate"
                            onClicked: root.stageActionRequested("speech.capture", root.hostApplication, "Stage local capture intent")
                        }
                        Button {
                            text: "Preview"
                            onClicked: root.stageActionRequested("voice.preview", root.voiceProfile, "Provider-neutral preview intent")
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: "Generate & Insert"
                            highlighted: true
                            onClicked: root.stageActionRequested("voice.quickvideo.generate-insert", root.hostApplication, "Generate audio, alignment, editable captions and optional ducking through FA3 authorities")
                        }
                    }
                }
            }

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    Label { text: "Quick Dub"; color: "#f1f3f7"; font.pixelSize: 16; font.bold: true }
                    Label { text: "STT → speaker map → optional translation → TTS → alignment → editable mix"; color: "#c594ff"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Label { text: "Source language"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["Auto", "en-US", "hu-HU", "de-DE"] }
                        Label { text: "Target language"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["hu-HU", "en-US", "de-DE"] }
                        Label { text: "Speaker 1"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["Narrator", "Character A", "Project Voice"] }
                        Label { text: "Speaker 2"; color: "#a9b0bc" }
                        ComboBox { Layout.fillWidth: true; model: ["Character B", "Narrator", "Project Voice"] }
                    }
                    CheckBox { text: "Preserve ambience"; checked: true }
                    CheckBox { text: "Generate editable subtitles"; checked: true }
                    CheckBox { text: "Fit translated speech to detected regions"; checked: true }
                    RowLayout {
                        Button { text: "Analyze"; onClicked: root.stageActionRequested("voice.quickdub.analyze", root.hostApplication, "Analyze source audio and speakers") }
                        Button { text: "Preview Dub"; onClicked: root.stageActionRequested("voice.quickdub.preview", root.hostApplication, "Stage preview dub") }
                        Item { Layout.fillWidth: true }
                        Button { text: "Build Editable Dub"; highlighted: true; onClicked: root.stageActionRequested("voice.quickdub.build", root.hostApplication, "Create editable dub projection") }
                    }
                }
            }

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    Label { text: "Quick Narration"; color: "#f1f3f7"; font.pixelSize: 16; font.bold: true }
                    Label { text: "Selected application text/context is converted into a reviewable narration intent without copy-paste."; color: "#a9b0bc"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 110; text: "Selected host context"; readOnly: true }
                    ComboBox { Layout.fillWidth: true; model: ["Narrator (hu-HU)", "Project Voice", "Character Voice"] }
                    RowLayout {
                        Button { text: "Preview" }
                        Item { Layout.fillWidth: true }
                        Button { text: "Stage Narration"; highlighted: true; onClicked: root.stageActionRequested("voice.narration.stage", root.hostApplication, "Stage narration through FA3-VOICE-001") }
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: "Authority boundary: FA3-VOICE-001 → Model Router → HRB → admitted provider. No direct provider/device/network execution."
            color: "#a9b0bc"
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
    }
}
