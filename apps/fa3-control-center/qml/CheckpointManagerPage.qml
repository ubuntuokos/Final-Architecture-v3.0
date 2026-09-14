import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property string draftResult: ""

    function checkpointRecords() {
        var rows = fa3Repository.searchRecords(checkpointSearch.text)
        return rows.filter(function(v) {
            var h = (v.id + " " + v.title + " " + v.path + " " + v.category).toLowerCase()
            return h.indexOf("checkpoint") >= 0 || h.indexOf("model") >= 0 || h.indexOf("lora") >= 0 || h.indexOf("vae") >= 0 || h.indexOf("adapter") >= 0 || h.indexOf("weight") >= 0
        })
    }

    function draft(action, target, rationale) {
        draftResult = fa3Repository.createDraftChangeSet("MODEL_CHECKPOINT_GOVERNANCE", action, target, rationale)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: "Checkpoint Manager"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
            Label {
                text: "Checkpoint, LoRA, VAE és adapter artifactok inventory-, admission- és lineage-felülete. Nem végez közvetlen fájlmozgatást vagy promotiont."
                color: root.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: [
                    {title: "Discovery", value: "REGISTRY", tone: root.accent},
                    {title: "Integrity", value: "SHA-256", tone: root.green},
                    {title: "Security", value: "FAIL-CLOSED", tone: root.magenta},
                    {title: "Promotion", value: "EVIDENCE-GATED", tone: root.orange}
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 82
                    radius: 8
                    color: root.panel
                    border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12; spacing: 4
                        Label { text: modelData.title; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: modelData.value; color: modelData.tone; font.pixelSize: 12; font.bold: true }
                    }
                }
            }
        }

        TextField {
            id: checkpointSearch
            Layout.fillWidth: true
            placeholderText: "Checkpoint / model / LoRA / VAE / adapter keresése…"
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 280
            radius: 9
            color: root.panel
            border.color: root.border

            ListView {
                id: checkpointList
                anchors.fill: parent
                anchors.margins: 8
                anchors.rightMargin: 12
                clip: true
                model: root.checkpointRecords()
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                delegate: ItemDelegate {
                    width: ListView.view.width - 12
                    height: 58
                    background: Rectangle { color: hovered ? root.panelRaised : "transparent"; radius: 5 }
                    onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                    contentItem: RowLayout {
                        Rectangle { width: 7; height: 7; radius: 4; color: (modelData.status || "").indexOf("PENDING") >= 0 ? root.orange : root.green }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 1
                            Label { text: modelData.id; color: root.textPrimary; font.family: "monospace"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: modelData.title || modelData.path; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        }
                        Label { text: modelData.status || "INDEXED"; color: root.textMuted; font.pixelSize: 9; Layout.preferredWidth: 150; elide: Text.ElideRight }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Button { text: "Inventory reconcile tervezet"; onClicked: root.draft("propose.checkpoint.inventory-reconcile", "model-artifacts", "Discover and reconcile checkpoint inventory without direct mutation") }
            Button { text: "Admission tervezet"; onClicked: root.draft("propose.checkpoint.admission", checkpointSearch.text.length ? checkpointSearch.text : "selected-checkpoint", "Require immutable source, SHA-256, license, serialization/security, lineage and runtime compatibility evidence") }
            Button { text: "Quarantine tervezet"; onClicked: root.draft("propose.checkpoint.quarantine", checkpointSearch.text.length ? checkpointSearch.text : "selected-checkpoint", "Quarantine requested; no direct file operation from GUI") }
            Item { Layout.fillWidth: true }
        }

        Label {
            text: "Admission chain: discovery → immutable source → SHA-256 → license → serialization/security → lineage → runtime compatibility → evidence → promotion. A checkpoint csak trusted source + ellenőrzött artifactként léphet tovább."
            color: root.orange; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        Label { visible: root.draftResult.length > 0; text: root.draftResult; color: root.accent; font.pixelSize: 9; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
    }
}
