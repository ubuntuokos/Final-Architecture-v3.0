import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property alias targetWidth: widthField.value
    property alias targetHeight: heightField.value
    property real overlapFraction: overlapField.value / 100.0
    property alias sampler: samplerField.text
    property bool advanced: false
    signal planningChanged()

    GroupBox {
        title: qsTr("Resolution & Memory")
        Layout.fillWidth: true
        GridLayout {
            columns: 2
            anchors.fill: parent
            Label { text: qsTr("Target width") }
            SpinBox { id: widthField; from: 32; to: 32768; value: 3840; stepSize: 32; onValueModified: root.planningChanged() }
            Label { text: qsTr("Target height") }
            SpinBox { id: heightField; from: 32; to: 32768; value: 2160; stepSize: 32; onValueModified: root.planningChanged() }
            Label { text: qsTr("Resource authority") }
            Label { text: "HRB"; font.bold: true }
            CheckBox { text: qsTr("Advanced"); checked: root.advanced; onToggled: root.advanced = checked }
        }
    }

    GroupBox {
        visible: root.advanced
        title: qsTr("Advanced tiled inference")
        Layout.fillWidth: true
        GridLayout {
            columns: 2
            anchors.fill: parent
            Label { text: qsTr("Overlap") }
            SpinBox { id: overlapField; from: 0; to: 95; value: 50; suffix: "%"; onValueModified: root.planningChanged() }
            Label { text: qsTr("Sampler") }
            TextField { id: samplerField; text: "euler"; onTextEdited: root.planningChanged() }
            Label { text: qsTr("Device") }
            Label { text: qsTr("Managed by HRB; no local device pinning") }
        }
    }
}
