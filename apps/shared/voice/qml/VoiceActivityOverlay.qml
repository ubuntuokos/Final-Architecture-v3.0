import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property bool active: false
    property string activityState: "IDLE"
    property string applicationName: ""
    property string agentName: ""
    property string voiceName: ""
    property string privacyState: "LOCAL"
    property int elapsedSeconds: 0
    signal stopRequested()
    signal muteRequested()

    visible: active
    width: 420
    height: 118
    radius: 12
    color: "#111820"
    border.color: activityState === "ERROR" || activityState === "BLOCKED" ? "#f2b05e" : "#25a7ff"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 58
            Layout.preferredHeight: 58
            radius: 29
            color: root.activityState === "RECORDING" ? "#a52a2a" : "#12334a"
            Label {
                anchors.centerIn: parent
                text: root.activityState === "RECORDING" ? "●" : "◉"
                color: "#f1f3f7"
                font.pixelSize: 24
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: root.activityState; color: "#f1f3f7"; font.bold: true; font.pixelSize: 16 }
            Label { text: root.applicationName.length ? root.applicationName : "FA3 Voice"; color: "#a9b0bc" }
            Label {
                text: (root.agentName.length ? root.agentName + " · " : "") +
                      (root.voiceName.length ? root.voiceName + " · " : "") + root.privacyState
                color: "#76c893"
                font.pixelSize: 10
            }
        }

        ColumnLayout {
            Label {
                text: Math.floor(root.elapsedSeconds / 60).toString().padStart(2, "0") + ":" +
                      (root.elapsedSeconds % 60).toString().padStart(2, "0")
                color: "#f1f3f7"
                font.bold: true
            }
            RowLayout {
                Button { text: "Mute"; onClicked: root.muteRequested() }
                Button { text: "Stop"; onClicked: root.stopRequested() }
            }
        }
    }
}
