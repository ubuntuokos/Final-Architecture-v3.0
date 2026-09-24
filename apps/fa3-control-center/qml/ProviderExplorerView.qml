import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    signal admissionDraftRequested(string providerKey, string providerName)

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property string lastDraftResult: ""

    function stateTone(state) {
        if (state === "ENABLED") return green
        if (state === "ADMITTED") return accent
        if (state === "VERIFIED") return "#b778ff"
        return orange
    }

    function filteredRows() {
        var rows = fa3ExternalLlmCatalog.providers || []
        var needle = searchField.text.toLowerCase()
        var state = stateFilter.currentText
        return rows.filter(function(row) {
            var matchesText = needle.length === 0
                || String(row.provider_name).toLowerCase().indexOf(needle) >= 0
                || String(row.external_provider_key).toLowerCase().indexOf(needle) >= 0
                || String(row.base_url).toLowerCase().indexOf(needle) >= 0
            var matchesState = state === "ALL" || String(row.discovery_state) === state
            return matchesText && matchesState
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "Provider Explorer"; color: root.textPrimary; font.pixelSize: 20; font.bold: true }
                Label {
                    text: "External LLM discovery catalog · read-only metadata + DRAFT admission intent"
                    color: root.textMuted
                    font.pixelSize: 10
                }
            }
            Rectangle {
                radius: 5
                color: "#10243a"
                border.color: root.border
                implicitWidth: statusText.implicitWidth + 16
                implicitHeight: 24
                Label {
                    id: statusText
                    anchors.centerIn: parent
                    text: fa3ExternalLlmCatalog.status
                    color: fa3ExternalLlmCatalog.status.indexOf("LOADED") >= 0 ? root.green : root.orange
                    font.pixelSize: 8
                    font.bold: true
                }
            }
            Button {
                text: "Reload local catalog"
                onClicked: fa3ExternalLlmCatalog.reload()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 54
            radius: 7
            color: "#101c2e"
            border.color: root.orange
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 16
                Label { text: "DISCOVERY ≠ ADMISSION"; color: root.orange; font.bold: true; font.pixelSize: 10 }
                Label { text: "NO SILENT LOCAL → CLOUD FALLBACK"; color: root.orange; font.bold: true; font.pixelSize: 10 }
                Label {
                    Layout.fillWidth: true
                    text: "Free tier, base URL és model lista önmagában nem FA3 admission evidence."
                    color: root.textMuted
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: "Search discovered provider, key or base URL…"
            }
            ComboBox {
                id: stateFilter
                model: ["ALL", "DISCOVERED", "OBSERVED", "VERIFIED", "ADMITTED", "ENABLED"]
            }
        }

        Label {
            Layout.fillWidth: true
            text: "Source commit: " + (fa3ExternalLlmCatalog.sourceCommit || "not materialized") + " · " + fa3ExternalLlmCatalog.catalogPath
            color: root.textMuted
            font.pixelSize: 9
            elide: Text.ElideMiddle
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: root.panel
            border.color: root.border

            ListView {
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                spacing: 3
                model: root.filteredRows()

                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: Rectangle {
                    width: ListView.view.width
                    height: 76
                    radius: 6
                    color: index % 2 === 0 ? "#0c1a2b" : "#0a1625"
                    border.color: root.border

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: root.stateTone(String(modelData.discovery_state))
                        }

                        ColumnLayout {
                            Layout.preferredWidth: 210
                            spacing: 2
                            Label { text: modelData.provider_name; color: root.textPrimary; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                            Label { text: modelData.external_provider_key; color: root.textMuted; font.family: "monospace"; font.pixelSize: 8; elide: Text.ElideRight; Layout.fillWidth: true }
                        }

                        ColumnLayout {
                            Layout.preferredWidth: 170
                            spacing: 2
                            Label { text: modelData.discovery_state; color: root.stateTone(String(modelData.discovery_state)); font.bold: true; font.pixelSize: 9 }
                            Label { text: modelData.free_tier_kind + " · models " + (modelData.free_models === null ? "?" : modelData.free_models); color: root.textMuted; font.pixelSize: 9 }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Label { text: modelData.base_url || "base URL not supplied"; color: root.textPrimary; font.family: "monospace"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                            Label { text: (modelData.modalities || []).join(", "); color: root.textMuted; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                            Label { text: modelData.registration_requirement || "registration metadata unknown"; color: root.textMuted; font.pixelSize: 8; elide: Text.ElideRight; Layout.fillWidth: true }
                        }

                        Button {
                            text: "Admission draft"
                            onClicked: root.admissionDraftRequested(String(modelData.external_provider_key), String(modelData.provider_name))
                        }
                    }
                }

                Label {
                    anchors.centerIn: parent
                    visible: parent.count === 0
                    text: fa3ExternalLlmCatalog.status === "CATALOG_NOT_MATERIALIZED"
                        ? "No local runtime catalog. Materialize a pinned source snapshot first."
                        : "No provider matches the current filter."
                    color: root.textMuted
                }
            }
        }

        Label {
            visible: root.lastDraftResult.length > 0
            Layout.fillWidth: true
            text: root.lastDraftResult
            color: root.accent
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
