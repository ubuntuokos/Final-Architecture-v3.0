import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var preferences
    required property color panel
    required property color panelRaised
    required property color border
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property color green
    required property color orange

    readonly property string profileId: "FA3-GUI-LANGUAGE-CONTROL-001"
    readonly property string bridgeId: "FA3-LANGUAGE-BRIDGE-001"

    property string inputLanguage: String(preferences.value("languageControl/userLanguage", "auto"))
    property string outputLanguage: String(preferences.value("languageControl/outputLanguage", "same-as-input"))
    property bool preferNative: Boolean(preferences.value("languageControl/preferNative", true))
    property bool allowMediated: Boolean(preferences.value("languageControl/allowMediated", true))
    property bool localFirst: Boolean(preferences.value("languageControl/localFirst", true))
    property bool cloudRequested: Boolean(preferences.value("languageControl/cloudRequested", false))
    property string validationMode: String(preferences.value("languageControl/validationMode", "critical"))
    property string dataClassification: String(preferences.value("languageControl/dataClassification", "INTERNAL"))
    property bool pageWasVisible: false

    function save(key, value) {
        preferences.setValue(key, value)
    }

    function startInterpreter() {
        fa3Interpreter.startLive(root.inputLanguage,
                                 root.outputLanguage,
                                 root.dataClassification,
                                 root.localFirst,
                                 root.cloudRequested)
    }

    function stateTone() {
        if (fa3Interpreter.state === "LISTENING" || fa3Interpreter.state === "READY") return root.green
        if (fa3Interpreter.state === "TRANSCRIBING" || fa3Interpreter.state === "TRANSLATING" || fa3Interpreter.state === "STARTING") return root.accent
        return root.orange
    }

    function statusTone(value) {
        if (value === "PASS" || value === "READY" || value === "PROBE-READY" || value.indexOf("BYPASS") === 0 || value === "LISTENING") return root.green
        if (value === "RUNNING" || value === "STARTING") return root.accent
        return root.orange
    }

    onVisibleChanged: {
        if (visible && !pageWasVisible) {
            pageWasVisible = true
            Qt.callLater(function() {
                if (!fa3Interpreter.active) root.startInterpreter()
            })
        } else if (!visible && pageWasVisible) {
            pageWasVisible = false
            if (fa3Interpreter.active) fa3Interpreter.stop()
        }
    }

    component StatusRow: RowLayout {
        property string labelText: ""
        property string valueText: "N/A"
        property color valueTone: root.textPrimary
        Layout.fillWidth: true
        spacing: 12
        Label {
            text: parent.labelText
            color: root.textMuted
            font.pixelSize: 10
            Layout.preferredWidth: 150
        }
        Label {
            text: parent.valueText
            color: parent.valueTone
            font.pixelSize: 10
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
    }

    component Card: Rectangle {
        Layout.fillWidth: true
        color: root.panel
        border.color: root.border
        radius: 8
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        ColumnLayout {
            width: parent.width
            spacing: 12

            Item { Layout.preferredHeight: 8 }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Label {
                        text: "Élő Tolmács"
                        color: root.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                    }
                    Label {
                        text: "A Tolmács megnyitásakor a tényleges session indul: mikrofon → STT → Language Bridge → opcionális TTS. Nincs külön beállítási indítóképernyő."
                        color: root.textMuted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        text: root.profileId + " · " + root.bridgeId + " · original authoritative / translation derived projection"
                        color: root.accent
                        font.pixelSize: 9
                        font.bold: true
                    }
                }

                Rectangle {
                    implicitWidth: stateLabel.implicitWidth + 20
                    implicitHeight: 28
                    radius: 6
                    color: Qt.rgba(root.stateTone().r, root.stateTone().g, root.stateTone().b, 0.10)
                    border.color: root.stateTone()
                    Label {
                        id: stateLabel
                        anchors.centerIn: parent
                        text: fa3Interpreter.state
                        color: root.stateTone()
                        font.pixelSize: 9
                        font.bold: true
                    }
                }

                ToolButton {
                    text: "⚙ Beállítások"
                    onClicked: settingsDialog.open()
                    ToolTip.visible: hovered
                    ToolTip.text: "Tolmács beállításai"
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 154
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Forrás"; color: root.textMuted; Layout.preferredWidth: 70 }
                        ComboBox {
                            id: sourceLanguageBox
                            Layout.fillWidth: true
                            editable: true
                            model: ["auto", "hu", "en", "de", "fr", "es", "it", "pl", "ja", "zh"]
                            currentIndex: Math.max(0, model.indexOf(root.inputLanguage))
                            onActivated: {
                                root.inputLanguage = currentText
                                root.save("languageControl/userLanguage", currentText)
                            }
                            onAccepted: {
                                root.inputLanguage = editText
                                root.save("languageControl/userLanguage", editText)
                            }
                        }

                        ToolButton {
                            text: "⇄"
                            enabled: root.inputLanguage !== "auto" && root.outputLanguage !== "same-as-input"
                            onClicked: {
                                var oldSource = root.inputLanguage
                                root.inputLanguage = root.outputLanguage
                                root.outputLanguage = oldSource
                                root.save("languageControl/userLanguage", root.inputLanguage)
                                root.save("languageControl/outputLanguage", root.outputLanguage)
                                if (fa3Interpreter.active) root.startInterpreter()
                            }
                            ToolTip.visible: hovered
                            ToolTip.text: "Forrás- és célnyelv felcserélése"
                        }

                        Label { text: "Cél"; color: root.textMuted; Layout.preferredWidth: 45 }
                        ComboBox {
                            id: targetLanguageBox
                            Layout.fillWidth: true
                            editable: true
                            model: ["same-as-input", "hu", "en", "de", "fr", "es", "it", "pl", "ja", "zh"]
                            currentIndex: Math.max(0, model.indexOf(root.outputLanguage))
                            onActivated: {
                                root.outputLanguage = currentText
                                root.save("languageControl/outputLanguage", currentText)
                            }
                            onAccepted: {
                                root.outputLanguage = editText
                                root.save("languageControl/outputLanguage", editText)
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: fa3Interpreter.detail
                        color: fa3Interpreter.paused && fa3Interpreter.active ? root.orange : root.textMuted
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Button {
                            text: fa3Interpreter.active ? "Újraindítás" : "Indítás"
                            onClicked: root.startInterpreter()
                        }
                        Button {
                            text: fa3Interpreter.paused ? "Folytatás" : "Szünet"
                            enabled: fa3Interpreter.active
                            onClicked: fa3Interpreter.paused ? fa3Interpreter.resume() : fa3Interpreter.pause()
                        }
                        Button {
                            text: "Leállítás"
                            enabled: fa3Interpreter.active
                            onClicked: fa3Interpreter.stop()
                        }
                        Button {
                            text: "Transcript törlése"
                            onClicked: fa3Interpreter.clearTranscript()
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: fa3Interpreter.active ? "● SESSION " + fa3Interpreter.sessionId.slice(0, 8) : "○ nincs aktív session"
                            color: fa3Interpreter.active ? root.green : root.textMuted
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                spacing: 12

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 258
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Eredeti beszéd"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                            Label { text: fa3Interpreter.detectedLanguage.length > 0 ? fa3Interpreter.detectedLanguage.toUpperCase() : "AUTO"; color: root.accent; font.pixelSize: 9; font.bold: true }
                        }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            TextArea {
                                readOnly: true
                                text: fa3Interpreter.originalText.length > 0 ? fa3Interpreter.originalText : "Hallgatás után itt jelenik meg a hitelesített STT transcript."
                                color: fa3Interpreter.originalText.length > 0 ? root.textPrimary : root.textMuted
                                wrapMode: TextEdit.Wrap
                                background: Rectangle { color: root.panelRaised; radius: 6; border.color: root.border }
                            }
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 258
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Tolmácsolás"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                            Label { text: root.outputLanguage.toUpperCase(); color: root.accent; font.pixelSize: 9; font.bold: true }
                        }
                        ScrollView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            TextArea {
                                readOnly: true
                                text: fa3Interpreter.translatedText.length > 0 ? fa3Interpreter.translatedText : "A fordítás csak admitted Language Bridge adapter PASS eredménye után jelenik meg."
                                color: fa3Interpreter.translatedText.length > 0 ? root.textPrimary : root.textMuted
                                wrapMode: TextEdit.Wrap
                                background: Rectangle { color: root.panelRaised; radius: 6; border.color: root.border }
                            }
                        }
                    }
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 188
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Élő pipeline"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                        Label { text: "FAIL-CLOSED"; color: root.orange; font.pixelSize: 9; font.bold: true }
                    }
                    StatusRow { labelText: "Mikrofon / capture"; valueText: fa3Interpreter.microphoneStatus; valueTone: root.statusTone(valueText) }
                    StatusRow { labelText: "STT"; valueText: fa3Interpreter.sttStatus + " · FA3-PROVIDER-WHISPER-001"; valueTone: root.statusTone(fa3Interpreter.sttStatus) }
                    StatusRow { labelText: "Fordítás"; valueText: fa3Interpreter.translationStatus; valueTone: root.statusTone(valueText) }
                    StatusRow { labelText: "TTS"; valueText: fa3Interpreter.ttsStatus; valueTone: root.statusTone(valueText) }
                    Label {
                        Layout.fillWidth: true
                        text: "ADAPTER-GATED / PENDING_BACKEND nem PASS. Ha egy kötelező stage nincs admitted állapotban, a session láthatóan megáll; az FA3 nem generál ál-transcriptet vagy ál-fordítást."
                        color: root.textMuted
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 82
                radius: 8
                color: root.panelRaised
                border.color: root.border
                Label {
                    anchors.fill: parent
                    anchors.margins: 12
                    text: root.dataClassification === "SECRET"
                          ? "SECRET: külső fordítás tiltott. Az eredeti input authoritative; a fordítás derived projection; session-audio csak ideiglenes helyi fájlban él és leállításkor törlődik."
                          : "Az eredeti input authoritative; a fordítás derived projection. A session-audio EPHEMERAL-TEMP-ONLY. Külső egress csak explicit policy/admitted adapter mellett lehetséges."
                    color: root.dataClassification === "SECRET" ? root.orange : root.textMuted
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Item { Layout.preferredHeight: 16 }
        }
    }

    Dialog {
        id: settingsDialog
        title: "Tolmács beállításai / Nyelvi híd"
        modal: true
        anchors.centerIn: parent
        width: Math.min(root.width * 0.78, 760)
        height: Math.min(root.height * 0.82, 650)
        standardButtons: Dialog.Close

        ScrollView {
            anchors.fill: parent
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn

            ColumnLayout {
                width: parent.width
                spacing: 12

                Label {
                    text: "Tolmács / Nyelvi híd beállításai"
                    color: root.textPrimary
                    font.pixelSize: 16
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    text: "A beállítások nem indítópult: a felső Tolmács gomb és a Tolmács főmenü az élő munkateret indítja."
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                }

                GroupBox {
                    title: "Nyelvi policy"
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent
                        CheckBox {
                            text: "Natív modellnyelv előnyben"
                            checked: root.preferNative
                            onToggled: { root.preferNative = checked; root.save("languageControl/preferNative", checked) }
                        }
                        CheckBox {
                            text: "Közvetített nyelv engedélyezése"
                            checked: root.allowMediated
                            onToggled: { root.allowMediated = checked; root.save("languageControl/allowMediated", checked) }
                        }
                        CheckBox {
                            text: "Local-first"
                            checked: root.localFirst
                            onToggled: { root.localFirst = checked; root.save("languageControl/localFirst", checked) }
                        }
                    }
                }

                GroupBox {
                    title: "Adatvédelem és egress"
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Adatbesorolás"; color: root.textMuted; Layout.preferredWidth: 130 }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
                                currentIndex: Math.max(0, model.indexOf(root.dataClassification))
                                onActivated: {
                                    root.dataClassification = currentText
                                    root.save("languageControl/dataClassification", currentText)
                                    if (root.dataClassification === "SECRET" && root.cloudRequested) {
                                        root.cloudRequested = false
                                        root.save("languageControl/cloudRequested", false)
                                    }
                                }
                            }
                        }
                        CheckBox {
                            text: "Külső/cloud fordítás kérése"
                            checked: root.cloudRequested
                            enabled: root.dataClassification !== "SECRET"
                            onToggled: { root.cloudRequested = checked; root.save("languageControl/cloudRequested", checked) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Szemantikai validáció"; color: root.textMuted; Layout.preferredWidth: 130 }
                            ComboBox {
                                Layout.fillWidth: true
                                model: ["critical", "always"]
                                currentIndex: root.validationMode === "always" ? 1 : 0
                                onActivated: { root.validationMode = currentText; root.save("languageControl/validationMode", currentText) }
                            }
                        }
                    }
                }

                GroupBox {
                    title: "Runtime állapot"
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent
                        StatusRow { labelText: "Capture"; valueText: String(fa3Interpreter.probe().microphoneCapture); valueTone: root.statusTone(valueText) }
                        StatusRow { labelText: "STT"; valueText: String(fa3Interpreter.probe().stt); valueTone: root.statusTone(valueText) }
                        StatusRow { labelText: "Fordító provider"; valueText: String(fa3Interpreter.probe().translation); valueTone: root.statusTone(valueText) }
                        StatusRow { labelText: "Speech route"; valueText: String(fa3Interpreter.probe().tts); valueTone: root.statusTone(valueText) }
                        StatusRow { labelText: "Audio retention"; valueText: String(fa3Interpreter.probe().audioRetention); valueTone: root.green }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: "UNKNOWN / PENDING_BACKEND állapot soha nem jelent PASS-t. A GUI nem policy-authority; credential vagy raw secret nem kerül a beállításokba."
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                }
            }
        }
    }
}
