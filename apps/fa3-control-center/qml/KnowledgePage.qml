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
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    component Card: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 14
            Item { Layout.preferredHeight: 8 }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Label { text: "Knowledge & Retrieval"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "FA3-KNOWLEDGE-001 · Hierarchical + Hybrid Retrieval Fabric"; color: root.cyan; font.pixelSize: 10; font.bold: true }
                Label {
                    Layout.fillWidth: true
                    text: "Provider-neutral RetrievalPlan → provider dispatch → RetrievalTrace → evidence fusion → ContextPassport. A Journal és az eredeti artifactok maradnak a forrás-authority-k."
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                columns: root.width > 1150 ? 4 : 2
                columnSpacing: 10
                rowSpacing: 10
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 136
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12
                        Label { text: "PageIndex Local"; color: root.textPrimary; font.bold: true }
                        Label { text: "PREFERRED LOCAL"; color: root.green; font.pixelSize: 8; font.bold: true }
                        Label { Layout.fillWidth: true; text: "Tree index + reasoning retrieval · FA3 Model Router loopback only"; color: root.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 9 }
                        Label { text: "Evidence-backed state · canonical records"; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 136
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12
                        Label { text: "PageIndex MCP Cloud"; color: root.textPrimary; font.bold: true }
                        Label { text: "OPTIONAL CLOUD"; color: root.cyan; font.pixelSize: 8; font.bold: true }
                        Label { Layout.fillWidth: true; text: "Explicit upload approval + CAP-140 egress + Central MCP Gateway"; color: root.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 9 }
                        Label { text: "PENDING_CURRENT_HOST · NO DIRECT BYPASS"; color: root.magenta; font.pixelSize: 8; font.bold: true }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 136
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12
                        Label { text: "OpenKB"; color: root.textPrimary; font.bold: true }
                        Label { text: "OPTIONAL COMPILER"; color: root.orange; font.pixelSize: 8; font.bold: true }
                        Label { Layout.fillWidth: true; text: "Materialized derived knowledge compiler; nem source authority."; color: root.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 9 }
                        Label { text: "PENDING_CURRENT_HOST"; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 136
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12
                        Label { text: "ConDB"; color: root.textPrimary; font.bold: true }
                        Label { text: "OPTIONAL CACHE"; color: root.orange; font.pixelSize: 8; font.bold: true }
                        Label { Layout.fillWidth: true; text: "Materialized tree-search/cache accelerator; derived és rebuildable."; color: root.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 9 }
                        Label { text: "PENDING_CURRENT_HOST"; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                }
            }

            TabBar {
                id: tabs
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                TabButton { text: "Planner" }
                TabButton { text: "Trace & Evidence" }
                TabButton { text: "Multimodal" }
                TabButton { text: "Authority" }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                currentIndex: tabs.currentIndex
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 205
                    ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 7
                        Label { text: "RetrievalPlan"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                        Label { text: "metadata → hierarchical → lexical → vector(optional) → tree_reasoning → rerank → evidence_fusion"; color: root.cyan; font.pixelSize: 9 }
                        Label { Layout.fillWidth: true; text: "A planner provider-neutral. A vector retrieval opcionális; a hierarchical path kötelező. Provider routing csak a terv után történhet."; color: root.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 10 }
                        Label { text: "No fabricated CONNECTED/PASS"; color: root.orange; font.pixelSize: 9; font.bold: true }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 205
                    ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 7
                        Label { text: "RetrievalTrace + ContextPassport"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                        Label { Layout.fillWidth: true; text: "Minden candidate megőrzi a source locatorokat és evidence linkeket. A ContextPassport csak derived, hash-bound és újraépíthető kontextus-projekció."; color: root.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 10 }
                        Label { text: "Append-only trace · provenance required"; color: root.green; font.pixelSize: 9; font.bold: true }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 205
                    ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 7
                        Label { text: "Multimodal derived projections"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                        Label { text: "Image → SourceRegion / CrossModalRelation"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Video → MediaSegment / TemporalSpan"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Audio → transcript / MediaSegment / TemporalSpan"; color: root.textMuted; font.pixelSize: 9 }
                        Label { Layout.fillWidth: true; text: "A bináris kép-, videó- és hangfájl nem kerül a knowledge indexbe; csak az artifact-ref és a származtatott struktúra."; color: root.orange; wrapMode: Text.WordWrap; font.pixelSize: 10 }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 205
                    ColumnLayout { anchors.fill: parent; anchors.margins: 15; spacing: 7
                        Label { text: "Authority boundaries"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                        Label { text: "Source truth · FA3-JOURNAL-001 + original artifacts"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Model routing · FA3-AUTH-MODEL-ROUTER-001"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "MCP · FA3-AUTH-MCP-GATEWAY-001"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Evidence · FA3-AUTH-OBS-EVIDENCE-001"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Provider authority escalation: DENY"; color: root.magenta; font.pixelSize: 9; font.bold: true }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 180
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14
                    Label { text: "Evidence-backed provider / canonical states"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true
                        model: {
                            var rows = []
                            var terms = ["KNOWLEDGE", "PAGEINDEX", "OPENKB", "CONDB"]
                            for (var i = 0; i < terms.length; ++i) {
                                var part = fa3Repository.searchRecords(terms[i])
                                for (var j = 0; j < part.length; ++j)
                                    rows.push(part[j])
                            }
                            return rows
                        }
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            height: 38
                            contentItem: RowLayout {
                                Label { text: modelData.id; color: root.textPrimary; font.family: "monospace"; Layout.preferredWidth: 360; elide: Text.ElideRight }
                                Label { text: modelData.status; color: (modelData.status || "").indexOf("PENDING") >= 0 ? root.orange : root.green; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }
            Item { Layout.preferredHeight: 18 }
        }
    }
}
