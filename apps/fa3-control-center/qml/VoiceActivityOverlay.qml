import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string activityState: "IDLE"
    property string applicationName: "QuickClip"
    property string actorName: "Assistant"
    property string voiceName: "Narrator (hu-HU)"
    property string jobId: ""
    property bool localProcessing: true
    property color panel: "#111318"
    property color border: "#3a424e"
    property color textPrimary: "#f1f3f7"
    property color textMuted: "#a9b0bc"
    property color accent: "#25a7ff"
    visible: activityState !== "IDLE"
    width: 360
    height: 118
    radius: 10
    color: panel
    border.color: border
    z: 1000

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        RowLayout {
            Layout.fillWidth: true
            Label { text: "● " + root.activityState; color: root.activityState === "ERROR" ? "#ff7272" : root.accent; font.bold: true }
            Item { Layout.fillWidth: true }
            Label { text: localProcessing ? "LOCAL" : "REMOTE"; color: textMuted; font.pixelSize: 9 }
        }
        Label { text: root.applicationName + " · " + root.actorName + " · " + root.voiceName; color: textPrimary; elide: Text.ElideRight; Layout.fillWidth: true }
        RowLayout {
            Button { text: "Pause"; enabled: false }
            Button {
                text: "Stop"
                enabled: root.jobId.length > 0
                onClicked: fa3VoiceWorkspace.cancelJob(root.jobId, "USER_STOP_FROM_OVERLAY")
            }
            Item { Layout.fillWidth: true }
            Label { text: "visible voice activity required"; color: textMuted; font.pixelSize: 9 }
        }
    }
}
