import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: root
    property string selectedProfileId: "voice.narrator.hu"
    signal stageProfileActionRequested(string actionId, string profileId)

    ListModel {
        id: profiles
        ListElement { profileId: "voice.narrator.hu"; title: "Narrator"; language: "hu-HU"; rights: "VALID"; kind: "REAL/PERSONAL" }
        ListElement { profileId: "voice.character.a"; title: "Character A"; language: "hu-HU"; rights: "REVIEW"; kind: "REAL/PERSONAL" }
        ListElement { profileId: "voice.synthetic.demo"; title: "Synthetic Demo"; language: "multi"; rights: "SYNTHETIC"; kind: "SYNTHETIC" }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.preferredWidth: 220
            Layout.fillHeight: true
            color: "#181d23"
            radius: 6
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                Label { text: "Voice Profiles"; color: "#f1f3f7"; font.bold: true }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: profiles
                    clip: true
                    delegate: ItemDelegate {
                        width: ListView.view.width
                        text: title + " · " + language
                        onClicked: root.selectedProfileId = profileId
                    }
                }
                Button {
                    text: "New Profile Draft"
                    Layout.fillWidth: true
                    onClicked: root.stageProfileActionRequested("voice.profile.create", root.selectedProfileId)
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8
            Label { text: "Voice Profile Manager"; color: "#f1f3f7"; font.pixelSize: 18; font.bold: true }
            Label { text: "FA3 canonical identity / consent / rights / lineage"; color: "#c594ff" }
            GridLayout {
                columns: 2
                Layout.fillWidth: true
                Label { text: "Profile"; color: "#a9b0bc" }
                TextField { Layout.fillWidth: true; text: root.selectedProfileId; readOnly: true }
                Label { text: "Language"; color: "#a9b0bc" }
                ComboBox { Layout.fillWidth: true; model: ["hu-HU", "en-US", "de-DE", "multi"] }
                Label { text: "Type"; color: "#a9b0bc" }
                ComboBox { Layout.fillWidth: true; model: ["REAL/PERSONAL", "SYNTHETIC"] }
                Label { text: "Consent"; color: "#a9b0bc" }
                Label { text: "VALID / purpose-scoped"; color: "#76c893"; font.bold: true }
                Label { text: "Rights"; color: "#a9b0bc" }
                Label { text: "SEPARATE CODE / MODEL / VOICE / OUTPUT"; color: "#f2b05e"; font.bold: true }
                Label { text: "Usage scope"; color: "#a9b0bc" }
                ComboBox { Layout.fillWidth: true; model: ["All Applications", "Project Scoped", "Application Scoped"] }
            }
            GroupBox {
                title: "Reference samples"
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Audio + transcript hashes · provenance · retention · revocation"; color: "#a9b0bc"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: ["sample-01.wav · VERIFIED", "sample-02.wav · VERIFIED"]
                        delegate: Label { text: modelData; color: "#f1f3f7" }
                    }
                }
            }
            RowLayout {
                Button { text: "Preview"; onClicked: root.stageProfileActionRequested("voice.profile.preview", root.selectedProfileId) }
                Button { text: "Edit Draft"; onClicked: root.stageProfileActionRequested("voice.profile.edit", root.selectedProfileId) }
                Item { Layout.fillWidth: true }
                Label { text: "No provider/device authority"; color: "#a9b0bc"; font.pixelSize: 10 }
            }
        }
    }
}
