import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property color textMuted
    required property color accent
    required property color surface1

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 14
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Remote AI Hub"; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true }
            Label { text: "CORE"; color: root.accent; font.bold: true }
        }
        Label { text: "FA3-REMOTE-AI-EXEC-001 · PR #150"; color: root.textMuted }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 190; radius: 10; color: root.surface1
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 8
                RowLayout { Layout.fillWidth: true; Label { text: "Hugging Face Spaces"; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true }; Label { text: "PRIMARY REFERENCE"; color: root.accent; font.bold: true } }
                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: "Kiemelt Remote AI provider. A Spaces útvonal külön marad a Hugging Face Model Store providertől." }
                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Nincs silent local→remote fallback. Távoli végrehajtás csak explicit admission, privacy/egress policy, quota, artifact validation és provenance mellett történhet." }
                Label { text: "FA3-PROVIDER-HF-SPACES-001"; color: root.accent }
            }
        }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#d99b32"; text: "A canonical materializáció a nyitott PR #150-ben van; ez a GUI projection nem duplikálja a canonical authority-t és nem állít live remote-provider PASS-t." }
        Item { Layout.fillHeight: true }
    }
}
