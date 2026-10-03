import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color panel: "#20242a"
    property color panelRaised: "#292f38"
    property color border: "#3a424e"
    property color textPrimary: "#f1f3f7"
    property color textMuted: "#a9b0bc"
    property color accent: "#c594ff"
    property color green: "#76c893"
    property color orange: "#f2b05e"
    signal stageActionIntentRequested(string actionId, string target, string rationale)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "FA3 Voice Studio"; color: root.textPrimary; font.pixelSize: 24; font.bold: true }
                Label { text: "Shared Voice I/O · profiles · capture · transform · stories · dubbing · FA3-VOICE-001"; color: root.accent; font.pixelSize: 10; font.bold: true }
            }
            Item { Layout.fillWidth: true }
            Label { text: "PROVIDER-NEUTRAL"; color: root.green; font.bold: true }
            Label { text: "175 / +0 authority"; color: root.textMuted }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Generate" }
            TabButton { text: "Voices" }
            TabButton { text: "Capture" }
            TabButton { text: "Transform" }
            TabButton { text: "Stories" }
            TabButton { text: "Dubbing" }
            TabButton { text: "Effects" }
            TabButton { text: "History" }
            TabButton { text: "Models" }
            TabButton { text: "Providers" }
            TabButton { text: "Jobs" }
            TabButton { text: "Settings" }
        }

        StackLayout {
            currentIndex: tabs.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            VoicePluginPanel {
                hostApplication: "fa3.voice-studio"
                projectionMode: "ADVANCED"
                onStageActionRequested: function(actionId, target, rationale) {
                    root.stageActionIntentRequested(actionId, target, rationale)
                }
            }

            VoiceProfileManagerPanel {
                onStageProfileActionRequested: function(actionId, profileId) {
                    root.stageActionIntentRequested(actionId, profileId, "Voice Profile Manager draft intent")
                }
            }

            Rectangle {
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14
                    Label { text: "Voice Capture / Dictation"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label { text: "Capture Core → local Inbox → STT → optional refinement → Preview → typed insertion"; color: root.accent; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                    Label { text: "Microphone: LOCAL · Network: OFF · AI refinement: user-toggleable"; color: root.green }
                    RowLayout {
                        Button { text: "Start Capture"; onClicked: root.stageActionIntentRequested("speech.capture", "local-microphone", "Stage local capture") }
                        Button { text: "Transcribe"; onClicked: root.stageActionIntentRequested("speech.transcribe", "latest-capture", "Stage STT") }
                        Button { text: "Preview Insert"; onClicked: root.stageActionIntentRequested("speech.insert.preview", "active-context", "Preview typed insertion") }
                    }
                }
            }

            VoiceTransformationPanel { }

            Rectangle {
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12
                    Label { text: "Stories · Multi-voice timeline"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label { text: "Story/Screenplay scene + dialogue IDs remain authoritative; audio is a derived editable projection."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Repeater {
                        model: ["Narrator", "Character A", "Character B", "Music", "Ambience", "SFX"]
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 48
                            color: index % 2 ? root.panelRaised : "#181d23"
                            radius: 4
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 8
                                Label { text: modelData; color: root.textPrimary; Layout.preferredWidth: 120 }
                                ProgressBar { Layout.fillWidth: true; value: (index + 2) / 8.0 }
                                Button { text: "Review" }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            VoicePluginPanel {
                hostApplication: "fa3.voice-studio"
                projectionMode: "STANDARD"
                onStageActionRequested: function(actionId, target, rationale) {
                    root.stageActionIntentRequested(actionId, target, rationale)
                }
            }

            Rectangle {
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14
                    Label { text: "Effects · non-destructive chain"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Repeater {
                        model: ["Pitch", "EQ", "Compression", "Reverb", "Delay", "Chorus", "AI Style Transform"]
                        CheckBox { text: modelData; checked: index < 3 }
                    }
                    Label { text: "Original → Take → Transform Chain → Derived Asset · original bytes are preserved."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }

            Rectangle { color: root.panel; border.color: root.border; radius: 8; Label { anchors.centerIn: parent; text: "History · takes · lineage · approvals"; color: root.textPrimary; font.pixelSize: 18 } }
            Rectangle { color: root.panel; border.color: root.border; radius: 8; Label { anchors.centerIn: parent; text: "Models · read-only admitted model status via Model Manager"; color: root.textPrimary; font.pixelSize: 18 } }
            Rectangle { color: root.panel; border.color: root.border; radius: 8; Label { anchors.centerIn: parent; text: "Providers · Model Router eligibility / language / rights status"; color: root.textPrimary; font.pixelSize: 18 } }
            Rectangle { color: root.panel; border.color: root.border; radius: 8; Label { anchors.centerIn: parent; text: "Jobs · Temporal / queue status · cancel / retry / evidence"; color: root.textPrimary; font.pixelSize: 18 } }
            Rectangle {
                color: root.panel; border.color: root.border; radius: 8
                ColumnLayout {
                    anchors.centerIn: parent
                    CheckBox { text: "TTS enabled"; checked: true }
                    CheckBox { text: "STT enabled"; checked: true }
                    CheckBox { text: "AI refinement enabled"; checked: false }
                    CheckBox { text: "AI voice transformation enabled"; checked: false }
                    Label { text: "AI features are switchable; deterministic/non-AI surfaces remain usable."; color: root.textMuted }
                }
            }
        }
    }
}
