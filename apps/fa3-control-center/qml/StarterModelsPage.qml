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
    property var starterRoles: [
        { id: "GENERAL_CHAT_LLM", title: "General / Chat LLM", note: "general assistant and chat baseline" },
        { id: "CODING_REASONING_LLM", title: "Coding / Reasoning LLM", note: "coding and structured reasoning" },
        { id: "EMBEDDING_MODEL", title: "Embedding", note: "RAG / semantic index baseline" },
        { id: "VISION_MULTIMODAL", title: "Vision / Multimodal", note: "image-language understanding" },
        { id: "IMAGE_GENERATION_BASE", title: "Image generation base", note: "local image generation baseline" },
        { id: "SPEECH_TO_TEXT", title: "Speech-to-text", note: "local transcription baseline" },
        { id: "TEXT_TO_SPEECH", title: "Text-to-speech", note: "local speech synthesis baseline" }
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14
        Label { text: root.t("Starter modellek", "Starter Models"); font.pixelSize: root.px(24); font.bold: true }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("Minimális logikai modell-szerepek. A gomb nem tölt le közvetlenül: Model Manager acquisition draftot hoz létre; llmfit finomíthatja a hardware-fit választást, és production admission előtt kötelező a Model Artifact Security lánc.", "Minimal logical model roles. Buttons do not bypass acquisition: they create Model Manager acquisition drafts; llmfit may refine hardware fit and Model Artifact Security remains mandatory before production admission.") }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth
            Flow { width: parent.width; spacing: 12
                Repeater { model: root.starterRoles
                    delegate: Rectangle { required property var modelData; width: 300; height: 150; radius: 10; color: root.surface1
                        ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 7
                            Label { Layout.fillWidth: true; text: modelData.title; font.bold: true; font.pixelSize: root.px(16) }
                            Label { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData.note; color: root.textMuted; wrapMode: Text.WordWrap }
                            Button { text: root.t("Letöltési kérelem", "Request download"); onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_STARTER_MODEL", modelData.id, "Starter model acquisition; provider/model revision chosen through Model Manager + llmfit fit + security admission.") }
                        }
                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""; color: root.accent; elide: Text.ElideMiddle }
    }
}
