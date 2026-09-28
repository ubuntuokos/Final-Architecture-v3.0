import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: root
    property color panel: "#182738"
    property color raised: "#213348"
    property color border: "#38516a"
    property color foreground: "#edf3fa"
    property color muted: "#a2b5c9"
    property color accent: "#65b5ec"
    property bool midnight: true
    property bool focusMode: false
    property bool sprintRunning: false
    property int sprintSeconds: 25 * 60
    property string selectedSceneId: ""
    property var scenes: fa3Screenplay.document.scenes || []
    property var breakdownScenes: fa3Screenplay.breakdown.scenes || []

    Timer {
        interval: 1000
        running: root.sprintRunning
        repeat: true
        onTriggered: {
            if (root.sprintSeconds > 0) root.sprintSeconds -= 1
            else root.sprintRunning = false
        }
    }

    FileDialog {
        id: importFileDialog
        title: "Import local screenplay"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Screenplay files (*.fdx *.fountain)", "All files (*)"]
        onAccepted: fa3Screenplay.importFile(selectedFile, formatBox.currentText.toLowerCase(), profileBox.currentText)
    }
    FileDialog {
        id: openProjectDialog
        title: "Open FA3 canonical screenplay JSON"
        fileMode: FileDialog.OpenFile
        nameFilters: ["FA3 screenplay JSON (*.json)"]
        onAccepted: fa3Screenplay.loadCanonical(selectedFile)
    }
    FileDialog {
        id: saveProjectDialog
        title: "Save canonical project (preserves revisions and branches)"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["FA3 screenplay JSON (*.json)"]
        onAccepted: fa3Screenplay.saveCanonical(selectedFile, overwriteBox.checked)
    }
    FileDialog {
        id: exportFileDialog
        title: "Export bounded screenplay subset (FA3 JSON remains canonical)"
        fileMode: FileDialog.SaveFile
        defaultSuffix: formatBox.currentText.toLowerCase()
        nameFilters: formatBox.currentText === "FDX" ? ["Final Draft XML (*.fdx)"] : ["Fountain screenplay (*.fountain)"]
        onAccepted: fa3Screenplay.exportSource(selectedFile, formatBox.currentText.toLowerCase(), overwriteBox.checked)
    }

    Rectangle {
        anchors.fill: parent
        color: root.midnight ? "#0c1520" : "#e7edf4"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Label { text: "Story / Screenplay"; color: root.midnight ? root.foreground : "#182738"; font.pixelSize: 24; font.bold: true }
                Label {
                    text: "FA3 native editor & deterministic production breakdown · reference-stage, no independent model or schedule authority"
                    color: root.accent; font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
            Item { Layout.fillWidth: true }
            Switch { text: "Midnight"; checked: root.midnight; onToggled: root.midnight = checked }
            Switch { text: "Typewriter / focus"; checked: root.focusMode; onToggled: root.focusMode = checked }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Production"; color: root.muted }
            ComboBox { id: profileBox; model: ["FEATURE", "TV_MOVIE", "EPISODIC", "COMMERCIAL", "LIVE_BROADCAST", "OTHER"] }
            Label { text: "Interchange"; color: root.muted }
            ComboBox { id: formatBox; model: ["FOUNTAIN", "FDX"] }
            Button { text: "Open file"; onClicked: importFileDialog.open() }
            Button { text: "Open FA3 project"; onClicked: openProjectDialog.open() }
            Button { text: "Import text"; onClicked: fa3Screenplay.importText(scriptText.text, formatBox.currentText.toLowerCase(), profileBox.currentText) }
            Item { Layout.fillWidth: true }
            Button { text: "Save FA3"; enabled: root.scenes.length > 0; onClicked: saveProjectDialog.open() }
            Button { text: "Export"; enabled: root.scenes.length > 0; onClicked: exportFileDialog.open() }
            CheckBox { id: overwriteBox; text: "Explicit replace"; checked: false }
        }
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            Rectangle {
                SplitView.fillWidth: root.focusMode
                SplitView.preferredWidth: root.focusMode ? 1000 : 650
                color: root.midnight ? "#122132" : "#f9fbfd"
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Script source"; font.bold: true; color: root.midnight ? root.foreground : "#1b2d40" }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: scriptText.text.trim().length === 0 ? "0 words" : scriptText.text.trim().split(/\s+/).length + " words"
                            color: root.accent
                        }
                        Label { text: "Goal"; color: root.muted }
                        SpinBox { id: goal; from: 100; to: 250000; value: 1500; stepSize: 100; editable: true }
                    }
                    TextArea {
                        id: scriptText
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: root.midnight ? root.foreground : "#102334"
                        font.family: "monospace"
                        font.pixelSize: 14
                        background: Rectangle { color: root.midnight ? "#0d1926" : "white"; border.color: root.border; radius: 5 }
                        text: ""
                        wrapMode: TextEdit.Wrap
                        placeholderText: "Title: ...\nAuthor: ...\n\nINT. ROOM - DAY\n\nAction...\n\n@CHARACTER\nDialogue..."
                        placeholderTextColor: root.muted
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Writing sprint"; color: root.muted }
                        Label { text: Math.floor(root.sprintSeconds / 60) + ":" + ("0" + root.sprintSeconds % 60).slice(-2); color: root.foreground }
                        Button { text: root.sprintRunning ? "Pause" : "Start"; onClicked: root.sprintRunning = !root.sprintRunning }
                        Button { text: "Reset 25m"; onClicked: { root.sprintRunning = false; root.sprintSeconds = 25 * 60 } }
                        Item { Layout.fillWidth: true }
                        Label { text: root.scenes.length + " scenes"; color: root.accent }
                    }
                }
            }
            Rectangle {
                visible: !root.focusMode
                SplitView.preferredWidth: 650
                SplitView.fillWidth: true
                color: root.panel
                border.color: root.border
                radius: 8
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Source-linked breakdown"; font.bold: true; color: root.foreground; font.pixelSize: 16 }
                        Item { Layout.fillWidth: true }
                        Button { text: "Derive"; enabled: root.scenes.length > 0; onClicked: fa3Screenplay.derive(false) }
                        Button { text: "Explicit refresh"; enabled: root.scenes.length > 0 && root.breakdownScenes.length > 0; onClicked: fa3Screenplay.derive(true) }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Local reviewer"; color: root.muted }
                        TextField { id: reviewer; Layout.fillWidth: true; placeholderText: "Name (not an authenticated approval)" }
                        Button { text: "Handoff preview"; enabled: root.breakdownScenes.length > 0; onClicked: fa3Screenplay.buildHandoffPreview() }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Branch"; color: root.muted }
                        TextField { id: branchField; Layout.fillWidth: true; placeholderText: "alternative-ending" }
                        Button { text: "Fork"; enabled: root.scenes.length > 0; onClicked: fa3Screenplay.fork(branchField.text) }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Edit scene"; color: root.muted }
                        TextField { id: headingEdit; Layout.fillWidth: true; placeholderText: root.selectedSceneId ? "New heading for " + root.selectedSceneId : "Select a scene below" }
                        Button { text: "Save revision"; enabled: root.selectedSceneId.length > 0; onClicked: fa3Screenplay.editHeading(root.selectedSceneId, headingEdit.text) }
                    }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ColumnLayout {
                            width: parent.width
                            spacing: 6
                            Repeater {
                                model: root.breakdownScenes.length ? root.breakdownScenes : root.scenes
                                delegate: Rectangle {
                                    required property var modelData
                                    property var item: modelData
                                    Layout.fillWidth: true
                                    implicitHeight: sceneDetail.implicitHeight + 18
                                    color: root.raised
                                    border.color: item.status === "STALE" ? "#ff9c60" : root.border
                                    radius: 5
                                    ColumnLayout {
                                        id: sceneDetail
                                        anchors.left: parent.left; anchors.right: parent.right
                                        anchors.top: parent.top; anchors.margins: 9
                                        spacing: 4
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Button {
                                                text: item.scene_id
                                                onClicked: { root.selectedSceneId = item.scene_id; headingEdit.text = item.heading }
                                            }
                                            Label { Layout.fillWidth: true; text: item.heading; color: root.foreground; wrapMode: Text.WordWrap }
                                            Label { text: item.status || "CANONICAL"; color: item.status === "STALE" ? "#ffb379" : root.accent }
                                        }
                                        Label {
                                            text: "Location: " + (item.location || "—") + " · Speaking cast: " + ((item.speaking_cast || []).join(", ") || "—") + " · Silent cast unverified"
                                            color: root.muted; wrapMode: Text.WordWrap
                                        }
                                        Repeater {
                                            model: item.proposals || []
                                            delegate: RowLayout {
                                                required property var modelData
                                                property var tag: modelData
                                                Layout.fillWidth: true
                                                Label { text: tag.kind + ": " + tag.value; color: root.foreground; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                                Label { text: tag.approval; color: tag.approval === "PENDING" ? "#ffb379" : "#88d4ad" }
                                                Button { text: "Accept"; enabled: tag.approval === "PENDING" && item.status !== "STALE"; onClicked: fa3Screenplay.review(tag.id, "APPROVED", reviewer.text) }
                                                Button { text: "Reject"; enabled: tag.approval === "PENDING" && item.status !== "STALE"; onClicked: fa3Screenplay.review(tag.id, "REJECTED", reviewer.text) }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            color: root.panel
            border.color: root.border
            radius: 5
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 8
                Label { text: "Handoff: " + (fa3Screenplay.handoff.status || "NOT GENERATED") + " · Local review only · No schedule or provider authority"; color: root.accent; font.bold: true }
                Label {
                    Layout.fillWidth: true
                    text: fa3Screenplay.error.length ? fa3Screenplay.error : (fa3Screenplay.handoff.blockers || []).join("; ") || fa3Screenplay.receipt
                    color: fa3Screenplay.error.length ? "#ff9c90" : root.muted
                    elide: Text.ElideRight
                }
            }
        }
    }
}
