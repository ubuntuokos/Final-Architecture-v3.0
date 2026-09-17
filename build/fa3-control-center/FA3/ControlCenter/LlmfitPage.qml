import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var client
    required property color textMuted
    required property color accent
    required property color surface1

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Model Manager · llmfit"; font.pixelSize: 24; font.bold: true; Layout.fillWidth: true }
            Label { text: root.client.statusText; color: root.client.available ? root.accent : "#d99b32"; font.bold: true }
            Button { text: root.client.busy ? "Frissítés…" : "Frissítés"; enabled: !root.client.busy; onClicked: root.client.refresh() }
        }
        Label { text: "FA3-PROVIDER-LLMFIT-001 · PR #151 · advisory only"; color: root.textMuted }
        RowLayout {
            Layout.fillWidth: true
            ComboBox { id: useCase; model: ["general","coding","reasoning","chat","multimodal","embedding"] }
            ComboBox { id: runtime; model: ["any","llamacpp","mlx"] }
            SpinBox { id: contextSize; from: 1024; to: 1048576; stepSize: 1024; value: 8192; editable: true }
            Button { text: "Ajánlás"; onClicked: root.client.recommendModels(useCase.currentText,runtime.currentText,contextSize.value) }
            Item { Layout.fillWidth: true }
            Label { text: root.client.socketPath; color: root.textMuted; elide: Text.ElideMiddle; Layout.preferredWidth: 300 }
        }
        Label { visible: root.client.lastError.length>0; Layout.fillWidth: true; text: root.client.lastError; color: "#d99b32"; wrapMode: Text.WordWrap }
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; radius: 8; color: root.surface1
            ListView {
                anchors.fill: parent; anchors.margins: 8; clip: true; spacing: 3; model: root.client.models
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width; height: 56
                    contentItem: RowLayout {
                        Label { text: modelData.name || modelData.model || modelData.id || "model"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: modelData.quantization || modelData.quant || "—"; color: root.textMuted; Layout.preferredWidth: 100 }
                        Label { text: modelData.fit || modelData.fit_level || modelData.score || "—"; color: root.accent; Layout.preferredWidth: 110 }
                        Label { text: modelData.estimated_tps !== undefined ? Number(modelData.estimated_tps).toFixed(1)+" tok/s" : "—"; color: root.textMuted; Layout.preferredWidth: 100 }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Button {
                text: "Benchmark ChangeSet"
                onClicked: fa3Repository.createDraftChangeSet("MODEL_MANAGER", "BENCHMARK_MODEL", "llmfit", "DRAFT_NOT_SUBMITTED benchmark intent from advisory fit data")
            }
            Button {
                text: "Placement ChangeSet"
                onClicked: fa3Repository.createDraftChangeSet("MODEL_MANAGER", "PROPOSE_PLACEMENT", "llmfit", "DRAFT_NOT_SUBMITTED placement intent; HRB remains authority")
            }
            Item { Layout.fillWidth: true }
            Label { text: "DRAFT_NOT_SUBMITTED"; color: root.textMuted; font.pixelSize: 10 }
        }
        Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WordWrap; text: "A llmfit becslése nem production evidence, nem Model Router és nem Host Resource Broker döntés." }
    }
}
