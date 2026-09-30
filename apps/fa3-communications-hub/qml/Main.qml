import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1280
    height: 800
    visible: true
    title: "FA3 Communications Hub"

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            Label { text: "FA3 Communications Hub"; font.bold: true; Layout.fillWidth: true }
            Label { text: "Static UI • provider runtime pending"; opacity: 0.7 }
        }
    }

    CommunicationsSharedSurface {
        anchors.fill: parent
        anchors.margins: 12
        surfaceMode: "FULL"
        applicationId: "FA3-COMMUNICATIONS-HUB-001"
        runtimeAdmitted: false

        onActionIntent: function(actionId, context) {
            console.log("FA3 action intent only:", actionId, JSON.stringify(context))
        }
    }
}
