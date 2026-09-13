import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    property string lastDraft: ""
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }
    property var credential: fa3SecretBroker.credentialStatus("civitai")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true
                Label { text: "CivitAI"; font.pixelSize: root.px(22); font.bold: true }
                Label { text: "FA3-PROVIDER-CIVITAI-001 · Model Manager provider projection"; color: root.textMuted }
            }
            Label { text: root.credential.available ? "AUTH READY" : "PUBLIC / NO TOKEN"; color: root.accent; font.bold: true }
        }
        RowLayout { Layout.fillWidth: true
            TextField { id: search; Layout.fillWidth: true; placeholderText: root.t("CivitAI modellek keresése…", "Search CivitAI models…"); onAccepted: civitaiClient.searchModels(text) }
            Button { text: civitaiClient.busy ? root.t("Betöltés…", "Loading…") : root.t("Keresés", "Search"); enabled: !civitaiClient.busy; onClicked: civitaiClient.searchModels(search.text) }
        }
        Label { Layout.fillWidth: true; visible: civitaiClient.errorText.length > 0; color: "#d99b32"; text: civitaiClient.errorText; wrapMode: Text.WordWrap }
        Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WordWrap; text: root.t("A CivitAI pickle/virus scan státusza upstream metadata, nem FA3 security PASS. Letöltési admission előtt SHA-256, licenc/provenance review és Model Artifact Security szükséges.", "CivitAI pickle/virus scan status is upstream metadata, not FA3 security PASS. SHA-256, license/provenance review and Model Artifact Security are required before download admission.") }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth
            ColumnLayout { width: parent.width; spacing: 8
                Repeater { model: civitaiClient.models
                    delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 124; radius: 8; color: root.surface1
                        RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 12
                            ColumnLayout { Layout.fillWidth: true
                                Label { Layout.fillWidth: true; text: modelData.name + (modelData.versionName ? " · " + modelData.versionName : ""); font.bold: true; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: (modelData.type || "") + " · " + (modelData.creator || ""); color: root.textMuted; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: "SHA-256: " + (modelData.sha256 || "MISSING"); color: modelData.sha256 && modelData.sha256.length === 64 ? root.accent : "#d99b32"; font.family: "monospace"; elide: Text.ElideMiddle }
                                Label { Layout.fillWidth: true; text: "Upstream scans: pickle=" + (modelData.pickleScanResult || "unknown") + " · virus=" + (modelData.virusScanResult || "unknown"); color: root.textMuted }
                            }
                            Button { text: root.t("Acquisition draft", "Acquisition draft"); enabled: modelData.sha256 && modelData.sha256.length === 64 && modelData.downloadUrl; onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_CIVITAI_MODEL", "civitai:" + modelData.id + ":" + modelData.versionId + ":" + modelData.fileName, "CivitAI staged acquisition; expected SHA256=" + modelData.sha256 + "; upstream scan metadata is non-authoritative; license/provenance/security admission required.") }
                        }
                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""; color: root.accent; elide: Text.ElideMiddle }
    }
}
