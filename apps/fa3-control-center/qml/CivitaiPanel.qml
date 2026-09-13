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
    property var credential: fa3SecretBroker.credentialStatus("civitai")
    function t(hu, en) {
        return language === "en" ? en : hu
    }
    function px(v) {
        return Math.max(9, Math.round(v * fontScale))
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label {
                    text: "CIVITAI · MODEL SOURCE"
                    color: root.accent
                    font.pixelSize: root.px(10)
                    font.bold: true
                }
                Label {
                    text: "CivitAI"
                    font.pixelSize: root.px(23)
                    font.bold: true
                }
                Label {
                    text: "FA3-PROVIDER-CIVITAI-001"
                    color: root.textMuted
                }
            }
            Label {
                text: root.credential.available ? "AUTH READY" : "PUBLIC / NO TOKEN"
                color: root.accent
                font.bold: true
            }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: root.width < 760 ? 1 : 2
            columnSpacing: 8
            rowSpacing: 8
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: root.t("CivitAI modellek keresése…", "Search CivitAI models…")
                onAccepted: civitaiClient.searchModels(text)
            }
            Button {
                Layout.fillWidth: root.width < 760
                text: civitaiClient.busy ? root.t("Betöltés…", "Loading…") : root.t("Keresés", "Search")
                enabled: !civitaiClient.busy
                onClicked: civitaiClient.searchModels(search.text)
            }
        }
        Label {
            Layout.fillWidth: true
            visible: civitaiClient.errorText.length > 0
            color: "#d99b32"
            text: civitaiClient.errorText
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            color: root.textMuted
            wrapMode: Text.WordWrap
            text: root.t("Az upstream scan státusz nem FA3 security PASS. SHA-256 + licence/provenance + Model Artifact Security admission kötelező.", "Upstream scan state is not an FA3 security PASS. SHA-256 + license/provenance + Model Artifact Security admission are mandatory.")
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 8
                Repeater {
                    model: civitaiClient.models
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.width < 760 ? 190 : 156
                        radius: 8
                        color: root.surface1
                        border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 5
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.name + (modelData.versionName ? " · " + modelData.versionName : "")
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: modelData.type || "MODEL"
                                    color: root.accent
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: modelData.creator || "—"
                                color: root.textMuted
                                elide: Text.ElideRight
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "SHA-256: " + (modelData.sha256 || "MISSING")
                                color: modelData.sha256 && modelData.sha256.length === 64 ? root.accent : "#d99b32"
                                font.family: "monospace"
                                elide: Text.ElideMiddle
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "pickle=" + (modelData.pickleScanResult || "unknown") + " · virus=" + (modelData.virusScanResult || "unknown")
                                color: root.textMuted
                                wrapMode: Text.WordWrap
                            }
                            Item {
                                Layout.fillHeight: true
                            }
                            Button {
                                Layout.fillWidth: root.width < 760
                                text: root.t("Acquisition draft", "Acquisition draft")
                                enabled: modelData.sha256 && modelData.sha256.length === 64 && modelData.downloadUrl
                                onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_CIVITAI_MODEL", "civitai:" + modelData.id + ":" + modelData.versionId + ":" + modelData.fileName, "CivitAI staged acquisition; expected SHA256=" + modelData.sha256 + "; upstream scan metadata is non-authoritative; license/provenance/security admission required.")
                            }
                        }
                    }
                }
            }
        }
        Label {
            Layout.fillWidth: true
            text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""
            color: root.accent
            elide: Text.ElideMiddle
        }
    }
}
