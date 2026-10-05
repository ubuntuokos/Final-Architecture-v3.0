import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property string handoffText
    property var clipboardService
    property color panelColor: "#0f2035"
    property color borderColor: "#1d3550"
    property color textColor: "#f5f8fc"
    property color mutedColor: "#8397ad"
    property color accentColor: "#25a7ff"

    signal copySucceeded()
    signal copyFailed(string reason)

    visible: handoffText.length > 0
    radius: 8
    color: panelColor
    border.color: borderColor
    border.width: 1
    implicitHeight: contentColumn.implicitHeight + 20

    function copyAll() {
        if (handoffText.length === 0) {
            copyFailed("EMPTY_HANDOFF")
            return
        }
        if (!clipboardService || !clipboardService.copyTextToClipboard) {
            copyFailed("CLIPBOARD_SERVICE_UNAVAILABLE")
            return
        }
        var result = clipboardService.copyTextToClipboard(handoffText)
        if (result && result.ok) copySucceeded()
        else copyFailed(result && result.error ? String(result.error) : "COPY_FAILED")
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        RowLayout {
            Layout.fillWidth: true

            Label {
                Layout.fillWidth: true
                text: "Új beszélgetés átadása"
                color: root.textColor
                font.bold: true
            }

            Button {
                id: copyAllButton
                text: "Másolás"
                enabled: root.handoffText.length > 0
                Accessible.name: "Teljes átadó szöveg másolása"
                onClicked: root.copyAll()
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(260, Math.max(48, handoffLabel.implicitHeight + 12))
            clip: true

            Label {
                id: handoffLabel
                width: Math.max(1, parent.width)
                text: root.handoffText
                color: root.textColor
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                selectByMouse: false
            }
        }

        Label {
            Layout.fillWidth: true
            text: "A teljes átadás egyetlen Másolás művelettel kerül a vágólapra."
            color: root.mutedColor
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}