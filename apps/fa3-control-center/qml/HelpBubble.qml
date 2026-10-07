import QtQuick
import QtQuick.Controls

ToolButton {
    id: root

    property string helpText: ""
    property color bubbleBackground: "#10243a"
    property color bubbleBorder: "#36516d"
    property color bubbleText: "#f5f8fc"

    text: "?"
    implicitWidth: 28
    implicitHeight: 28
    hoverEnabled: true

    ToolTip.visible: hovered || pressed
    ToolTip.delay: 250
    ToolTip.timeout: 12000
    ToolTip.text: helpText

    background: Rectangle {
        radius: width / 2
        color: root.down ? "#183551" : (root.hovered ? "#15304a" : "#10243a")
        border.color: root.hovered ? root.bubbleBorder : "#27425d"
    }

    contentItem: Label {
        text: root.text
        color: root.bubbleText
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
