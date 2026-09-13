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

    property string lastDraft: ""
    property var credential: fa3SecretBroker.credentialStatus("civitai")

    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 12
        Item { Layout.preferredHeight: 8 }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: "CivitAI"
            font.pixelSize: root.px(22)
            font.bold: true
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: "FA3-PROVIDER-CIVITAI-001 · Model Manager provider projection"
            color: root.textMuted
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: root.credential.available ? "AUTH READY" : "PUBLIC / NO TOKEN"
            color: root.accent
            font.bold: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            spacing: 8
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: root.t("CivitAI modellek keresése…", "Search CivitAI models…")
                onAccepted: civitaiClient.searchModels(text)
            }
            Button {
                text: civitaiClient.busy ? root.t("Betöltés…", "Loading…") : root.t("Keresés", "Search")
                enabled: !civitaiClient.busy
                onClicked: civitaiClient.searchModels(search.text)
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            visible: civitaiClient.errorText.length > 0
            color: "#d99b32"
            text: civitaiClient.errorText
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            color: root.textMuted
            wrapMode: Text.WordWrap
            text: root.t("A CivitAI pickle/virus scan státusza upstream metadata, nem FA3 security PASS. Letöltési admission előtt SHA-256, licenc/provenance review és Model Artifact Security szükséges.", "CivitAI pickle/virus scan status is upstream metadata, not FA3 security PASS. SHA-256, license/provenance review and Model Artifact Security are required before download admission.")
        }

        Repeater {
            model: civitaiClient.models
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.preferredHeight: Math.max(190, detailColumn.implicitHeight + 28)
                radius: 10
                color: root.surface1

                ColumnLayout {
                    id: detailColumn
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 7

                    Label {
                        Layout.fillWidth: true
                        text: modelData.name + (modelData.versionName ? " · " + modelData.versionName : "")
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    Label {
                        Layout.fillWidth: true
                        text: (modelData.type || "") + " · " + (modelData.creator || "")
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "SHA-256: " + (modelData.sha256 || "MISSING")
                        color: modelData.sha256 && modelData.sha256.length === 64 ? root.accent : "#d99b32"
                        font.family: "monospace"
                        wrapMode: Text.WrapAnywhere
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "Upstream scans: pickle=" + (modelData.pickleScanResult || "unknown") + " · virus=" + (modelData.virusScanResult || "unknown")
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        Layout.alignment: Qt.AlignLeft
                        text: root.t("Acquisition draft", "Acquisition draft")
                        enabled: modelData.sha256 && modelData.sha256.length === 64 && modelData.downloadUrl
                        onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_CIVITAI_MODEL", "civitai:" + modelData.id + ":" + modelData.versionId + ":" + modelData.fileName, "CivitAI staged acquisition; expected SHA256=" + modelData.sha256 + "; upstream scan metadata is non-authoritative; license/provenance/security admission required.")
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""
            color: root.accent
            wrapMode: Text.WrapAnywhere
        }
        Item { Layout.preferredHeight: 20 }
    }
}
