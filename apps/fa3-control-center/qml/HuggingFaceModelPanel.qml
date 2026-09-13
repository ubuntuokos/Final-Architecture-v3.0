import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property var repository
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language

    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }
    function hfRecords() {
        const rows = repository.searchRecords("FA3-PROVIDER-HF-MODEL-STORE-001")
        return rows
    }

    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 14
        Item { Layout.preferredHeight: 8 }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: "Hugging Face"
            font.pixelSize: root.px(22)
            font.bold: true
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: "FA3-PROVIDER-HF-MODEL-STORE-001 · Model Manager source/cache projection"
            color: root.textMuted
            wrapMode: Text.WordWrap
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.preferredHeight: 126
            radius: 10
            color: root.surface1
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 6
                Label { text: root.t("Elsődleges upstream modellforrás", "Primary upstream model source"); font.bold: true }
                Label {
                    Layout.fillWidth: true
                    text: root.t("A fejléc Hugging Face gombja a weboldalt nyitja meg. Ez az aloldal a Model Manager provider/cache szerepét mutatja. Production admissionnél immutable revision + content hash kötelező; floating main/latest nem elfogadható.", "The header Hugging Face button opens the website. This subpage represents the Model Manager provider/cache role. Production admission requires immutable revision + content hash; floating main/latest is not accepted.")
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                }
            }
        }
        Repeater {
            model: root.hfRecords()
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.preferredHeight: 96
                radius: 10
                color: root.surface1
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 5
                    Label { Layout.fillWidth: true; text: modelData.id; font.bold: true; elide: Text.ElideRight }
                    Label { Layout.fillWidth: true; text: modelData.title; color: root.textMuted; wrapMode: Text.WordWrap }
                    Label { text: modelData.status || "UNKNOWN"; color: root.accent; font.bold: true }
                }
            }
        }
        Item { Layout.preferredHeight: 20 }
    }
}
