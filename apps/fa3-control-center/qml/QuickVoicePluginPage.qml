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
    property color accent: "#25a7ff"
    property color green: "#76c893"
    property color orange: "#f2b05e"
    property string lastJobId: ""
    property var fitPlan: ({})
    property var dubPlan: ({})

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "QuickClip · Shared Voice Plugin"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "QUICK projection · persistent Voice workspace · host mutation remains UAF-authorized"; color: root.accent; font.pixelSize: 10; font.bold: true }
            }
            Item { Layout.fillWidth: true }
            ComboBox { id: projectionBox; model: ["QUICK","STANDARD","ADVANCED"] }
            Button { text: "Refresh"; onClicked: fa3VoiceWorkspace.refresh() }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 34
            color: fa3VoiceWorkspace.lastError.length > 0 ? "#3a2020" : "#172331"
            border.color: root.border; radius: 5
            Label {
                anchors.fill: parent; anchors.margins: 8
                text: fa3VoiceWorkspace.lastError.length > 0
                      ? "ERROR · " + fa3VoiceWorkspace.lastError
                      : (fa3VoiceWorkspace.lastOperation.length > 0
                         ? fa3VoiceWorkspace.lastOperation
                         : "Quick Voice ready.")
                color: fa3VoiceWorkspace.lastError.length > 0 ? "#ff9090" : root.textMuted
                elide: Text.ElideRight
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                SplitView.preferredWidth: 500
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
                    TextArea {
                        id: quickScript
                        Layout.fillWidth: true
                        Layout.preferredHeight: 110
                        text: "Mutasd be 30 másodpercben ezt a terméket."
                        wrapMode: TextEdit.Wrap
                    }

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Label { text: "Voice"; color: root.textMuted }
                        ComboBox {
                            id: quickVoice
                            Layout.fillWidth: true
                            model: fa3VoiceWorkspace.voiceProfiles
                            textRole: "name"
                            valueRole: "voice_profile_id"
                            displayText: currentIndex >= 0 ? currentText : "Create Voice Profile in Voice Studio"
                        }
                        Label { text: "Language"; color: root.textMuted }
                        ComboBox { id: quickLanguage; Layout.fillWidth: true; model: ["hu-HU","en-US","de-DE"] }
                        Label { text: "Style"; color: root.textMuted }
                        ComboBox { id: quickStyle; Layout.fillWidth: true; model: ["Natural","Energetic","Calm","Narration"] }
                        Label { text: "Duration"; color: root.textMuted }
                        SpinBox { id: quickTarget; Layout.fillWidth: true; from: 1000; to: 600000; value: 27800; stepSize: 100; editable: true }
                    }

                    CheckBox { id: quickCaptions; text: "Generate editable captions"; checked: true }
                    CheckBox { id: quickDucking; text: "Duck background music"; checked: true }
                    CheckBox { id: quickPreserve; text: "Preserve previous take"; checked: true }

                    RowLayout {
                        Button {
                            text: "Dictate / Capture"
                            onClicked: quickCaptureDialog.open()
                        }
                        Button {
                            text: "Fit Plan"
                            enabled: root.lastJobId.length > 0
                            onClicked: root.fitPlan = fa3VoiceWorkspace.fitToClip(quickTarget.value, Math.round(quickTarget.value * 1.12))
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Generate & Insert"
                        enabled: quickVoice.currentIndex >= 0 && quickScript.text.trim().length > 0
                        onClicked: {
                            var row = fa3VoiceWorkspace.stageGeneration(
                                quickScript.text,
                                quickVoice.currentValue,
                                quickLanguage.currentText,
                                quickStyle.currentText,
                                "FIT_TO_CLIP",
                                quickTarget.value,
                                quickCaptions.checked,
                                quickDucking.checked)
                            if (row && row.job_id) {
                                root.lastJobId = row.job_id
                                if (row.status === "COMPLETED")
                                    fa3VoiceWorkspace.stageTimelineHandoff(row.job_id, "quickclip-current", "", quickDucking.checked)
                            }
                        }
                    }

                    Label {
                        text: "Execution path: Plugin → UAF → FA3-VOICE-001 → Model Router → HRB → admitted provider. BLOCKED_NOT_ADMITTED is a valid fail-closed state."
                        color: root.orange
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.pixelSize: 10
                    }

                    Item { Layout.fillHeight: true }
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
                        Label { text: "Target"; color: root.textMuted }
                        Label { text: (quickTarget.value / 1000).toFixed(1) + " s"; color: root.textPrimary }
                        Label { text: "Example generated"; color: root.textMuted }
                        Label { text: (quickTarget.value * 1.12 / 1000).toFixed(1) + " s"; color: root.orange }
                    }
                    Label {
                        text: root.fitPlan.measured_rate_ratio
                              ? "Rate option: " + Number(root.fitPlan.measured_rate_ratio).toFixed(3) + "×"
                              : "Stage a job, then request a Fit plan."
                        color: root.textPrimary
                    }
                    Label {
                        text: "Shorter-script proposals never apply silently. Preview + explicit Apply remains mandatory."
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                    Label { text: "Takes / Jobs"; color: root.textPrimary; font.bold: true }

                    ListView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        clip: true
                        model: fa3VoiceWorkspace.jobs
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 50
                            color: index % 2 ? root.panelRaised : root.panel
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 7
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.job_id || ""; color: root.textPrimary; font.pixelSize: 9; elide: Text.ElideMiddle }
                                    Label {
                                        text: modelData.status || ""
                                        color: modelData.status === "BLOCKED_NOT_ADMITTED" ? root.orange : root.green
                                        font.pixelSize: 9
                                    }
                                }
                                Button {
                                    text: "Use"
                                    onClicked: root.lastJobId = modelData.job_id
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                    Label { text: "Quick Dub"; color: root.textPrimary; font.bold: true }
                    RowLayout {
                        ComboBox { id: quickDubSource; Layout.fillWidth: true; model: ["en-US","hu-HU","de-DE"] }
                        ComboBox { id: quickDubTarget; Layout.fillWidth: true; model: ["hu-HU","en-US","de-DE"] }
                    }
                    RowLayout {
                        TextField { id: quickSpeaker; Layout.preferredWidth: 130; text: "Speaker 1" }
                        ComboBox {
                            id: quickDubVoice
                            Layout.fillWidth: true
                            model: fa3VoiceWorkspace.voiceProfiles
                            textRole: "name"
                            valueRole: "voice_profile_id"
                        }
                    }
                    CheckBox { id: quickTranslate; text: "Translation enabled"; checked: true }
                    Button {
                        text: "Build Quick Dub Plan"
                        enabled: quickDubVoice.currentIndex >= 0
                        onClicked: root.dubPlan = fa3VoiceWorkspace.stageQuickDub(
                            quickDubSource.currentText,
                            quickDubTarget.currentText,
                            [{speaker: quickSpeaker.text, voice_profile_id: quickDubVoice.currentValue}],
                            quickTranslate.checked)
                    }
                    Label {
                        text: root.dubPlan.plan_id ? "Plan: " + root.dubPlan.plan_id : "No dub plan staged."
                        color: root.dubPlan.plan_id ? root.green : root.textMuted
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    Dialog {
        id: quickCaptureDialog
        title: "Quick Capture"
        modal: true
        anchors.centerIn: parent
        width: 520
        standardButtons: Dialog.Save | Dialog.Cancel
        ColumnLayout {
            width: parent.width
            ComboBox { id: quickCaptureLanguage; Layout.fillWidth: true; model: ["hu-HU","en-US","de-DE"] }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: "Start Microphone"
                    enabled: !fa3VoiceWorkspace.recording
                    onClicked: fa3VoiceWorkspace.startMicrophoneCapture(quickCaptureLanguage.currentText)
                }
                Button {
                    text: "Stop & Add"
                    enabled: fa3VoiceWorkspace.recording
                    onClicked: fa3VoiceWorkspace.stopMicrophoneCapture(quickCaptureTranscript.text)
                }
            }
            Label {
                text: fa3VoiceWorkspace.recording ? fa3VoiceWorkspace.recordingPath : "Or add an existing local audio artifact:"
                color: fa3VoiceWorkspace.recording ? root.orange : root.textMuted
                elide: Text.ElideMiddle
                Layout.fillWidth: true
            }
            TextField { id: quickCaptureSource; Layout.fillWidth: true; placeholderText: "Authorized local audio artifact ref" }
            TextArea { id: quickCaptureTranscript; Layout.fillWidth: true; Layout.preferredHeight: 100; placeholderText: "Optional transcript"; wrapMode: TextEdit.Wrap }
        }
        onAccepted: fa3VoiceWorkspace.createCapture(
            quickCaptureLanguage.currentText,
            quickCaptureSource.text,
            quickCaptureTranscript.text)
    }
}
