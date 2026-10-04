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
    property string lastJobId: ""
    property string selectedClipId: "quickclip-current"
    property var lastFitPlan: ({})
    property var lastDubPlan: ({})

    function noticeText() {
        if (fa3VoiceWorkspace.lastError && fa3VoiceWorkspace.lastError.length > 0)
            return "ERROR · " + fa3VoiceWorkspace.lastError
        if (fa3VoiceWorkspace.lastOperation && fa3VoiceWorkspace.lastOperation.length > 0)
            return fa3VoiceWorkspace.lastOperation
        return "Workspace ready · local state only until UAF/provider execution is admitted."
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "Voice Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    text: "Shared Voice I/O · persistent workspace · FA3-VOICE-001 → Model Router → HRB"
                    color: root.accent; font.pixelSize: 10; font.bold: true
                }
            }
            Item { Layout.fillWidth: true }
            Label { text: "175 capabilities · +0 authority"; color: root.green; font.bold: true }
            Button { text: "Refresh"; onClicked: fa3VoiceWorkspace.refresh() }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: fa3VoiceWorkspace.lastError.length > 0 ? "#3a2020" : "#172331"
            border.color: root.border
            radius: 5
            Label {
                anchors.fill: parent
                anchors.margins: 8
                text: root.noticeText()
                color: fa3VoiceWorkspace.lastError.length > 0 ? "#ff9090" : root.textMuted
                elide: Text.ElideRight
            }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            Repeater {
                model: ["Generate","Voices","Capture","Transform","Stories","Dubbing","Effects","History","Models","Providers","Jobs","Settings"]
                TabButton { text: modelData }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // Generate
            Item {
                RowLayout {
                    anchors.fill: parent
                    spacing: 10
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: root.panel
                        border.color: root.border
                        radius: 8
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 9
                            RowLayout {
                                Layout.fillWidth: true
                                ComboBox {
                                    id: generateVoice
                                    Layout.fillWidth: true
                                    model: fa3VoiceWorkspace.voiceProfiles
                                    textRole: "name"
                                    valueRole: "voice_profile_id"
                                    displayText: currentIndex >= 0 ? currentText : "Create a Voice Profile first"
                                }
                                ComboBox { id: generateLanguage; Layout.preferredWidth: 130; model: ["hu-HU","en-US","de-DE"] }
                                ComboBox { id: generateStyle; Layout.preferredWidth: 130; model: ["Natural","Energetic","Calm","Narration"] }
                            }
                            TextArea {
                                id: generateScript
                                Layout.fillWidth: true
                                Layout.preferredHeight: 170
                                placeholderText: "Narration / dialogue text"
                                text: "Írd ide a narráció szövegét."
                                wrapMode: TextEdit.Wrap
                            }
                            RowLayout {
                                CheckBox { id: generateCaptions; text: "Editable captions"; checked: true }
                                CheckBox { id: generateDucking; text: "Music ducking"; checked: true }
                                Item { Layout.fillWidth: true }
                                SpinBox { id: targetDuration; from: 1000; to: 600000; value: 30000; stepSize: 1000; editable: true }
                                Label { text: "ms target"; color: root.textMuted }
                            }
                            RowLayout {
                                Button {
                                    text: "Generate / Stage"
                                    enabled: generateVoice.currentIndex >= 0 && generateScript.text.trim().length > 0
                                    onClicked: {
                                        var row = fa3VoiceWorkspace.stageGeneration(
                                            generateScript.text,
                                            generateVoice.currentValue,
                                            generateLanguage.currentText,
                                            generateStyle.currentText,
                                            "FIT_TO_CLIP",
                                            targetDuration.value,
                                            generateCaptions.checked,
                                            generateDucking.checked)
                                        if (row && row.job_id) root.lastJobId = row.job_id
                                    }
                                }
                                Button {
                                    text: "Fit to Clip"
                                    enabled: root.lastJobId.length > 0
                                    onClicked: root.lastFitPlan = fa3VoiceWorkspace.fitToClip(targetDuration.value, Math.round(targetDuration.value * 1.12))
                                }
                                Button {
                                    text: "Add to Timeline"
                                    enabled: root.lastJobId.length > 0
                                    onClicked: fa3VoiceWorkspace.stageTimelineHandoff(root.lastJobId, root.selectedClipId, "", generateDucking.checked)
                                }
                                Item { Layout.fillWidth: true }
                                Label {
                                    text: root.lastJobId.length > 0 ? root.lastJobId : "No staged job"
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    elide: Text.ElideMiddle
                                    Layout.preferredWidth: 220
                                }
                            }
                            GroupBox {
                                title: "Fit-to-Clip decision"
                                Layout.fillWidth: true
                                visible: Object.keys(root.lastFitPlan).length > 0
                                ColumnLayout {
                                    anchors.fill: parent
                                    Label {
                                        text: root.lastFitPlan.measured_rate_ratio
                                              ? "Measured rate ratio: " + Number(root.lastFitPlan.measured_rate_ratio).toFixed(3)
                                              : ""
                                        color: root.textPrimary
                                    }
                                    Label {
                                        text: "No silent text rewrite. Script shortening always requires Preview → explicit Apply."
                                        color: root.orange
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                    Rectangle {
                        Layout.preferredWidth: 330
                        Layout.fillHeight: true
                        color: root.panel
                        border.color: root.border
                        radius: 8
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Label { text: "Route & authority"; color: root.textPrimary; font.bold: true }
                            Label { text: "Voice: FA3-VOICE-001"; color: root.textMuted }
                            Label { text: "Provider/model: Model Router"; color: root.textMuted }
                            Label { text: "Device: HRB"; color: root.textMuted }
                            Label { text: "Workflow: Temporal"; color: root.textMuted }
                            Label { text: "Action mediation: UAF"; color: root.textMuted }
                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                            Label { text: "Current jobs"; color: root.textPrimary; font.bold: true }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: fa3VoiceWorkspace.jobs
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 54
                                    color: index % 2 ? root.panelRaised : root.panel
                                    Column {
                                        anchors.fill: parent; anchors.margins: 7
                                        Label { text: modelData.job_id || ""; color: root.textPrimary; font.pixelSize: 9; elide: Text.ElideMiddle; width: parent.width }
                                        Label {
                                            text: modelData.status || "UNKNOWN"
                                            color: modelData.status === "BLOCKED_NOT_ADMITTED" ? root.orange : root.green
                                            font.bold: true; font.pixelSize: 9
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Voices
            Item {
                RowLayout {
                    anchors.fill: parent; spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 420; Layout.fillHeight: true
                        color: root.panel; border.color: root.border; radius: 8
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 8
                            Label { text: "Voice Profile Editor"; color: root.textPrimary; font.bold: true }
                            TextField { id: profileId; Layout.fillWidth: true; placeholderText: "voice_profile_id"; text: "voice-narrator-hu" }
                            TextField { id: profileName; Layout.fillWidth: true; placeholderText: "Name"; text: "Narrator HU" }
                            ComboBox { id: profileLanguage; Layout.fillWidth: true; model: ["hu-HU","en-US","de-DE"] }
                            ComboBox { id: identityKind; Layout.fillWidth: true; model: ["SYNTHETIC","PRESET","HUMAN_AUTHORIZED"] }
                            ComboBox { id: consentStatus; Layout.fillWidth: true; model: ["NOT_REQUIRED","GRANTED","REVOKED","EXPIRED"] }
                            TextField { id: consentRef; Layout.fillWidth: true; placeholderText: "Consent proof ref (required for HUMAN_AUTHORIZED)" }
                            Button {
                                text: "Save Voice Profile"
                                Layout.fillWidth: true
                                onClicked: fa3VoiceWorkspace.upsertVoiceProfile(
                                    profileId.text, profileName.text, profileLanguage.currentText,
                                    identityKind.currentText, consentStatus.currentText, consentRef.text)
                            }
                            Label {
                                Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted
                                text: "Profiles may store identity, languages, consent and presets. They cannot pin provider, model, endpoint or device."
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        color: root.panel; border.color: root.border; radius: 8
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12
                            Label { text: "Voice Profiles"; color: root.textPrimary; font.bold: true }
                            ListView {
                                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                model: fa3VoiceWorkspace.voiceProfiles
                                delegate: Rectangle {
                                    width: ListView.view.width; height: 72
                                    color: index % 2 ? root.panelRaised : root.panel
                                    RowLayout {
                                        anchors.fill: parent; anchors.margins: 8
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Label { text: modelData.name || ""; color: root.textPrimary; font.bold: true }
                                            Label { text: (modelData.voice_profile_id || "") + " · " + (modelData.identity_kind || ""); color: root.textMuted }
                                        }
                                        Label {
                                            text: modelData.consent_status || ""
                                            color: modelData.consent_status === "REVOKED" || modelData.consent_status === "EXPIRED" ? root.orange : root.green
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Capture
            Item {
                RowLayout {
                    anchors.fill: parent; spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 430; Layout.fillHeight: true
                        color: root.panel; border.color: root.border; radius: 8
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12; spacing: 8
                            Label { text: "Capture & Dictation Intake"; color: root.textPrimary; font.bold: true }
                            ComboBox { id: captureLanguage; Layout.fillWidth: true; model: ["hu-HU","en-US","de-DE"] }
                            TextField { id: captureSource; Layout.fillWidth: true; placeholderText: "Authorized local audio/microphone artifact ref" }
                            TextArea { id: captureTranscript; Layout.fillWidth: true; Layout.preferredHeight: 130; placeholderText: "Optional raw transcript"; wrapMode: TextEdit.Wrap }
                            RowLayout {
                                Layout.fillWidth: true
                                Button {
                                    text: fa3VoiceWorkspace.recording ? "Recording…" : "Start Microphone"
                                    enabled: !fa3VoiceWorkspace.recording
                                    onClicked: fa3VoiceWorkspace.startMicrophoneCapture(captureLanguage.currentText)
                                }
                                Button {
                                    text: "Stop & Add"
                                    enabled: fa3VoiceWorkspace.recording
                                    onClicked: fa3VoiceWorkspace.stopMicrophoneCapture(captureTranscript.text)
                                }
                            }
                            Label {
                                text: fa3VoiceWorkspace.recording
                                      ? "Recording to: " + fa3VoiceWorkspace.recordingPath
                                      : "Microphone idle"
                                color: fa3VoiceWorkspace.recording ? root.orange : root.textMuted
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                            Button {
                                text: "Add Existing Audio to Capture Inbox"
                                Layout.fillWidth: true
                                onClicked: fa3VoiceWorkspace.createCapture(captureLanguage.currentText, captureSource.text, captureTranscript.text)
                            }
                            Label {
                                text: "Original source + raw transcript lineage is preserved. Network egress stays OFF unless separately authorized."
                                color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        color: root.panel; border.color: root.border; radius: 8
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12
                            Label { text: "Local Inbox"; color: root.textPrimary; font.bold: true }
                            ListView {
                                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                                model: fa3VoiceWorkspace.captures
                                delegate: Rectangle {
                                    width: ListView.view.width; height: 62
                                    color: index % 2 ? root.panelRaised : root.panel
                                    Column {
                                        anchors.fill: parent; anchors.margins: 8
                                        Label { text: (modelData.capture_id || "") + " · " + (modelData.language || ""); color: root.textPrimary; font.pixelSize: 9 }
                                        Label { text: modelData.status || ""; color: root.green; font.bold: true }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Transform
            Item {
                VoiceTransformationPanel {
                    anchors.fill: parent
                }
            }

            // Stories
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "Stories · Multi-track voice handoff"; color: root.textPrimary; font.bold: true }
                        Label {
                            text: "Narrator / Characters / Music / Ambience / SFX share project identity; Voice Studio does not become project authority."
                            color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        Repeater {
                            model: ["Narrator","Character A","Character B","Music","Ambience","SFX"]
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 48
                                color: index % 2 ? root.panelRaised : root.panel
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 8
                                    Label { text: modelData; color: root.textPrimary; Layout.preferredWidth: 130 }
                                    ProgressBar { Layout.fillWidth: true; value: (index + 1) / 8 }
                                    Label { text: index < 3 ? "VOICE" : "AUDIO"; color: index < 3 ? root.accent : root.textMuted }
                                }
                            }
                        }
                        RowLayout {
                            TextField { id: storyClipId; Layout.fillWidth: true; text: "scene-001-dialogue-001"; placeholderText: "Host clip/dialogue id" }
                            Button {
                                text: "Stage last job handoff"
                                enabled: root.lastJobId.length > 0
                                onClicked: fa3VoiceWorkspace.stageTimelineHandoff(root.lastJobId, storyClipId.text, "", true)
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // Dubbing
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12; spacing: 9
                        Label { text: "Quick Dub"; color: root.textPrimary; font.bold: true }
                        RowLayout {
                            ComboBox { id: dubSource; Layout.fillWidth: true; model: ["en-US","hu-HU","de-DE"] }
                            ComboBox { id: dubTarget; Layout.fillWidth: true; model: ["hu-HU","en-US","de-DE"] }
                            CheckBox { id: dubTranslate; text: "Translate"; checked: true }
                        }
                        RowLayout {
                            TextField { id: dubSpeaker1; Layout.preferredWidth: 140; text: "Speaker 1" }
                            ComboBox { id: dubVoice1; Layout.fillWidth: true; model: fa3VoiceWorkspace.voiceProfiles; textRole: "name"; valueRole: "voice_profile_id" }
                        }
                        RowLayout {
                            TextField { id: dubSpeaker2; Layout.preferredWidth: 140; text: "Speaker 2" }
                            ComboBox { id: dubVoice2; Layout.fillWidth: true; model: fa3VoiceWorkspace.voiceProfiles; textRole: "name"; valueRole: "voice_profile_id" }
                        }
                        Button {
                            text: "Build Quick Dub Plan"
                            enabled: dubVoice1.currentIndex >= 0
                            onClicked: {
                                var mappings = [{speaker:dubSpeaker1.text, voice_profile_id:dubVoice1.currentValue}]
                                if (dubVoice2.currentIndex >= 0)
                                    mappings.push({speaker:dubSpeaker2.text, voice_profile_id:dubVoice2.currentValue})
                                root.lastDubPlan = fa3VoiceWorkspace.stageQuickDub(
                                    dubSource.currentText, dubTarget.currentText, mappings, dubTranslate.checked)
                            }
                        }
                        Label {
                            text: "Pipeline: STT → speaker segmentation → optional translation → explicit Voice Profile mapping → TTS → alignment → editable mix"
                            color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        Label {
                            text: root.lastDubPlan.plan_id ? "Plan: " + root.lastDubPlan.plan_id : "No Quick Dub plan staged."
                            color: root.lastDubPlan.plan_id ? root.green : root.textMuted
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // Effects
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "Effects & Non-destructive Transformation"; color: root.textPrimary; font.bold: true }
                        GridLayout {
                            columns: 3; Layout.fillWidth: true
                            CheckBox { text: "Pitch"; checked: true }
                            CheckBox { text: "EQ"; checked: true }
                            CheckBox { text: "Compression" }
                            CheckBox { text: "Reverb" }
                            CheckBox { text: "Delay" }
                            CheckBox { text: "Chorus" }
                        }
                        Label { text: "Original → Take → Transform Chain → Derived Asset"; color: root.green }
                        Label {
                            text: "Runtime audio transformation remains under FA3-VOICE-001 consent/rights/provider/HRB gates. This application never overwrites the original asset."
                            color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        VoiceTransformationPanel { Layout.fillWidth: true; Layout.fillHeight: true }
                    }
                }
            }

            // History
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "History · Jobs & Handoffs"; color: root.textPrimary; font.bold: true }
                        SplitView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            ListView {
                                SplitView.fillWidth: true
                                model: fa3VoiceWorkspace.jobs
                                delegate: Rectangle {
                                    width: ListView.view.width; height: 54; color: index % 2 ? root.panelRaised : root.panel
                                    Column { anchors.fill: parent; anchors.margins: 7
                                        Label { text: modelData.job_id || ""; color: root.textPrimary; font.pixelSize: 9 }
                                        Label { text: modelData.status || ""; color: root.textMuted }
                                    }
                                }
                            }
                            ListView {
                                SplitView.fillWidth: true
                                model: fa3VoiceWorkspace.handoffs
                                delegate: Rectangle {
                                    width: ListView.view.width; height: 54; color: index % 2 ? root.panelRaised : root.panel
                                    Column { anchors.fill: parent; anchors.margins: 7
                                        Label { text: modelData.handoff_id || ""; color: root.textPrimary; font.pixelSize: 9 }
                                        Label { text: modelData.clip_id || ""; color: root.textMuted }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Models
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "Models"; color: root.textPrimary; font.bold: true }
                        Label {
                            text: "Physical model selection is not owned by Voice Studio. Inspect the shared Engine/Provider Manager; only Model Router decisions may execute."
                            color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            model: fa3EngineSelector.engines
                            delegate: Rectangle {
                                width: ListView.view.width; height: 54; color: index % 2 ? root.panelRaised : root.panel
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 7
                                    Label { text: modelData.name || modelData.engine_id || ""; color: root.textPrimary; Layout.fillWidth: true }
                                    Label { text: modelData.health_state || modelData.status || ""; color: root.textMuted }
                                }
                            }
                        }
                    }
                }
            }

            // Providers
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "Voice Provider Admission"; color: root.textPrimary; font.bold: true }
                        Label {
                            text: "Provider execution is ALLOWLIST + capability/evidence only. Current hu-HU candidates remain fail-closed until production admission and quality evidence."
                            color: root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        Repeater {
                            model: ["XTTS · hu-HU cloning candidate","Piper · lightweight CPU TTS candidate","Qwen3-TTS · hu-HU unsupported","VoxCPM · hu-HU unsupported","MMS-TTS-HUN · non-commercial / denied","CosyVoice · hu-HU experimental"]
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 46; color: index % 2 ? root.panelRaised : root.panel
                                Label { anchors.fill: parent; anchors.margins: 9; text: modelData; color: root.textPrimary }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            // Jobs
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        RowLayout {
                            Label { text: "Voice Jobs"; color: root.textPrimary; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Button { text: "Refresh"; onClicked: fa3VoiceWorkspace.refresh() }
                        }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            model: fa3VoiceWorkspace.jobs
                            delegate: Rectangle {
                                width: ListView.view.width; height: 62; color: index % 2 ? root.panelRaised : root.panel
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 8
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Label { text: modelData.job_id || ""; color: root.textPrimary; font.pixelSize: 9 }
                                        Label {
                                            text: modelData.status || ""
                                            color: modelData.status === "BLOCKED_NOT_ADMITTED" ? root.orange : root.green
                                        }
                                    }
                                    Button {
                                        text: "Cancel"
                                        enabled: modelData.status !== "COMPLETED" && modelData.status !== "FAILED" && modelData.status !== "CANCELLED"
                                        onClicked: fa3VoiceWorkspace.cancelJob(modelData.job_id, "USER_CANCELLED")
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Settings
            Item {
                Rectangle {
                    anchors.fill: parent; color: root.panel; border.color: root.border; radius: 8
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12; spacing: 8
                        Label { text: "Voice Studio Settings"; color: root.textPrimary; font.bold: true }
                        CheckBox {
                            id: aiTts
                            text: "AI TTS enabled for this application"
                            checked: Boolean(fa3Preferences.value("voice/ttsEnabled", true))
                            onToggled: fa3Preferences.setValue("voice/ttsEnabled", checked)
                        }
                        CheckBox {
                            id: aiStt
                            text: "AI STT enabled"
                            checked: Boolean(fa3Preferences.value("voice/sttEnabled", true))
                            onToggled: fa3Preferences.setValue("voice/sttEnabled", checked)
                        }
                        CheckBox {
                            id: aiRewrite
                            text: "AI script shortening suggestions enabled"
                            checked: Boolean(fa3Preferences.value("voice/scriptShorteningEnabled", false))
                            onToggled: fa3Preferences.setValue("voice/scriptShorteningEnabled", checked)
                        }
                        CheckBox {
                            id: aiTransform
                            text: "AI voice transformation enabled"
                            checked: Boolean(fa3Preferences.value("voice/transformationEnabled", false))
                            onToggled: fa3Preferences.setValue("voice/transformationEnabled", checked)
                        }
                        Label {
                            text: "These toggles control application features only; they cannot admit providers, override rights/consent, select devices, or authorize network egress."
                            color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }
}
