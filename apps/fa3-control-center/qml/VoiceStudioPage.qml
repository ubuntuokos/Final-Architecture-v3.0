import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string runtimeMessage: fa3VoiceWorkspace.state + (fa3VoiceWorkspace.lastError.length ? " · " + fa3VoiceWorkspace.lastError : "")
    Component.onCompleted: fa3VoiceWorkspace.refresh()
    Connections { target: fa3VoiceWorkspace; function onGenerationCompleted(result) { root.runtimeMessage = "COMPLETED · " + result.job_id } }
    property color panel: "#20242a"
    property color panelRaised: "#292f38"
    property color border: "#3a424e"
    property color textPrimary: "#f1f3f7"
    property color textMuted: "#a9b0bc"
    property color accent: "#c594ff"
    property color green: "#76c893"
    property color orange: "#f2b05e"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "Voice Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "Shared Voice I/O · delegates synthesis to FA3-VOICE-001 · no provider or device authority"; color: root.accent; font.pixelSize: 10; font.bold: true }
            }
            Item { Layout.fillWidth: true }
            Label { text: "175 capabilities · +0 authority"; color: root.green; font.bold: true }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            Repeater {
                model: ["Generate","Voices","Capture","Transform","Stories","Dubbing","Effects","History","Models","Providers","Jobs","Settings"]
                TabButton { text: modelData }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Rectangle {
                SplitView.preferredWidth: 560
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    RowLayout {
                        ComboBox { Layout.fillWidth: true; model: ["Project: Demo Story","Project: QuickClip","Project: Narration"] }
                        ComboBox { id: voiceBox; Layout.preferredWidth: 180; model: ["Narrator","Character A","Character B"] }
                        ComboBox { id: languageBox; Layout.preferredWidth: 120; model: ["hu-HU","en-US","de-DE"] }
                    }
                    TextArea {
                        id: scriptEditor
                        Layout.fillWidth: true
                        Layout.preferredHeight: 170
                        text: "Írd ide vagy illeszd be a narráció szövegét. A provider- és hardverválasztást a Model Router + HRB végzi."
                        wrapMode: TextEdit.Wrap
                    }
                    RowLayout {
                        Button { text: "Generate"; enabled: fa3VoiceWorkspace.state === "READY"; onClicked: fa3VoiceWorkspace.generate(scriptEditor.text, voiceBox.currentText, languageBox.currentText, 0, false, true) }
                        Button { text: "Preview"; enabled: false }
                        Button { text: "Add to timeline"; enabled: false }
                        Item { Layout.fillWidth: true }
                        Label { text: root.runtimeMessage; color: fa3VoiceWorkspace.state === "READY" ? root.green : root.orange; font.bold: true }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#111318"
                        radius: 6
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            Label { text: "Multi-track Story Timeline"; color: root.textPrimary; font.bold: true }
                            Repeater {
                                model: ["Narrator","Character A","Character B","Music","Ambience","SFX"]
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 44
                                    color: index % 2 ? root.panelRaised : root.panel
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        Label { text: modelData; color: root.textPrimary; Layout.preferredWidth: 120 }
                                        ProgressBar { Layout.fillWidth: true; value: (index + 2) / 8 }
                                        Label { text: index < 3 ? "VOICE" : "AUDIO"; color: index < 3 ? root.accent : root.textMuted; font.pixelSize: 9 }
                                    }
                                }
                            }
                        }
                    }
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
                    spacing: 10
                    Label { text: "Voice Profile"; color: root.textPrimary; font.bold: true }
                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        Label { text: "Identity"; color: root.textMuted } Label { text: "Narrator / hu-HU"; color: root.textPrimary }
                        Label { text: "Consent"; color: root.textMuted } Label { text: "VERIFIED"; color: root.green; font.bold: true }
                        Label { text: "Provider"; color: root.textMuted } Label { text: "Model Router decision"; color: root.textPrimary }
                        Label { text: "Device"; color: root.textMuted } Label { text: "HRB placement"; color: root.textPrimary }
                        Label { text: "Execution"; color: root.textMuted } Label { text: "LOCAL / policy-bound"; color: root.textPrimary }
                    }
                    GroupBox {
                        title: "Effects & Transform"
                        Layout.fillWidth: true
                        GridLayout {
                            anchors.fill: parent
                            columns: 2
                            CheckBox { text: "Pitch"; checked: true }
                            CheckBox { text: "EQ"; checked: true }
                            CheckBox { text: "Compression" }
                            CheckBox { text: "Reverb" }
                            CheckBox { text: "Delay" }
                            CheckBox { text: "Chorus" }
                        }
                    }
                    GroupBox {
                        title: "Lineage"
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Original → Take → Transform Chain → Derived Asset"; color: root.textPrimary }
                            Label { text: "Original asset is never overwritten."; color: root.green }
                            Label { text: "Voice/reference rights and consent remain bound to derived output."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        font.pixelSize: 10
                        text: "This GUI is a non-authoritative client of the authenticated Shared Voice service. Provider/model/device authority remains with FA3-VOICE-001, Model Router and HRB; candidate execution never implies production promotion."
                    }
                }
            }
        }
    }
}
