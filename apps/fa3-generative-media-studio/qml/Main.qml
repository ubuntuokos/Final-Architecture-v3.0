import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1280
    height: 800
    visible: true
    title: "FA3 Generative Media Studio"

    readonly property color bg: "#07111f"
    readonly property color panel: "#0b1728"
    readonly property color raised: "#10233a"
    readonly property color border: "#1d3550"
    readonly property color textPrimary: "#f5f8fc"
    readonly property color textMuted: "#8ba0b8"
    readonly property color accent: "#25a7ff"
    readonly property color green: "#35e0a1"
    readonly property color orange: "#f0b14a"
    color: root.bg

    function isVideoCapability(value) {
        return value.indexOf("VIDEO_") === 0 || value === "LIPSYNC" || value === "CHARACTER_ANIMATE"
    }

    header: ToolBar {
        background: Rectangle { color: root.panel; border.color: root.border }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            Label { text: "FA3 Generative Media Studio"; color: root.textPrimary; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true }
            Label { text: "CAP-111 · PROVIDER NEUTRAL"; color: root.green; font.pixelSize: 10; font.bold: true }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 16

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 760
            radius: 10
            color: root.panel
            border.color: root.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label { text: "Generációs kérés"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }

                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 10

                    Label { text: "Capability"; color: root.textMuted }
                    ComboBox { id: capabilityBox; Layout.fillWidth: true; model: studioBackend.capabilities }

                    Label { text: "Provider / model"; color: root.textMuted }
                    Label { Layout.fillWidth: true; text: "Automatikus · FA3 Model Router"; color: root.green; font.bold: true }

                    Label { text: "Képarány"; color: root.textMuted }
                    ComboBox { id: aspectBox; Layout.fillWidth: true; model: ["AUTO", "16:9", "9:16", "1:1", "4:3", "3:2", "21:9"] }

                    Label { visible: root.isVideoCapability(capabilityBox.currentText); text: "Shot-hossz"; color: root.textMuted }
                    RowLayout {
                        visible: root.isVideoCapability(capabilityBox.currentText)
                        Layout.fillWidth: true
                        Slider { id: durationSlider; Layout.fillWidth: true; from: 6; to: 20; stepSize: 1; value: 8 }
                        Label { text: Math.round(durationSlider.value) + " mp"; color: root.textPrimary; Layout.preferredWidth: 60 }
                    }
                }

                Label { text: "Kreatív intent / prompt"; color: root.textMuted }
                TextArea {
                    id: promptArea
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    placeholderText: "Írd le a képet, snittet, karaktermozgást vagy lip-sync feladatot…"
                    wrapMode: TextEdit.Wrap
                    color: root.textPrimary
                    background: Rectangle { color: root.raised; border.color: root.border; radius: 7 }
                }

                Label { text: "Referencia artifactok · egy hivatkozás soronként"; color: root.textMuted }
                TextArea {
                    id: refsArea
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    placeholderText: "asset://…\nproject://…\nfile-ref://…"
                    wrapMode: TextEdit.WrapAnywhere
                    color: root.textPrimary
                    background: Rectangle { color: root.raised; border.color: root.border; radius: 7 }
                }

                Item { Layout.fillHeight: true }

                Button {
                    Layout.fillWidth: true
                    text: "Provider-semleges kérés összeállítása"
                    onClicked: studioBackend.compileRequest(
                        capabilityBox.currentText,
                        promptArea.text,
                        Math.round(durationSlider.value),
                        aspectBox.currentText,
                        refsArea.text)
                }
            }
        }

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 410
            radius: 10
            color: root.panel
            border.color: root.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label { text: "Végrehajtási lánc"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }

                Repeater {
                    model: [
                        "1 · Studio request compiler",
                        "2 · UAF authorization / action handoff",
                        "3 · Model Router provider + model resolution",
                        "4 · HRB resource admission / lease",
                        "5 · Admitted provider execution",
                        "6 · Result validation + Evidence Registry receipt",
                        "7 · Video Editor / asset handoff"
                    ]
                    delegate: Rectangle {
                        required property string modelData
                        Layout.fillWidth: true
                        implicitHeight: chainLabel.implicitHeight + 20
                        radius: 7
                        color: root.raised
                        border.color: root.border
                        Label {
                            id: chainLabel
                            anchors.fill: parent
                            anchors.margins: 10
                            text: modelData
                            color: root.textPrimary
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: statusLabel.implicitHeight + 24
                    radius: 7
                    color: "#091624"
                    border.color: studioBackend.statusText.indexOf("BLOCKED") === 0 ? root.orange : root.border
                    Label {
                        id: statusLabel
                        anchors.fill: parent
                        anchors.margins: 12
                        text: studioBackend.statusText
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                    }
                }

                Label {
                    visible: studioBackend.lastRequestPath.length > 0
                    Layout.fillWidth: true
                    text: "Request:\n" + studioBackend.lastRequestPath
                    color: root.accent
                    font.pixelSize: 9
                    wrapMode: Text.WrapAnywhere
                }

                Item { Layout.fillHeight: true }

                Label {
                    Layout.fillWidth: true
                    text: "A GUI nem hív közvetlenül ComfyUI-t, Wan-t vagy más providert, nem választ fizikai modellt, és nem foglal GPU-t. Ezek meglévő FA3 authorityk feladatai."
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
