// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property var controller
    property string selectionScope: scopeBox.currentText
    property var selectedEngine: ({})
    property var compareIds: []
    property var lastOutput: ({})

    function refresh() {
        if (!controller) {
            engineList.model = []
            return
        }
        engineList.model = controller.filterEngines(
            search.text,
            classBox.currentText === "ALL" ? "" : classBox.currentText,
            localOnly.checked,
            lanAllowed.checked,
            cloudAllowed.checked,
            showUnavailable.checked)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Engine & Provider Selector"; font.bold: true; font.pixelSize: 18 }
            Item { Layout.fillWidth: true }
            Label { text: "Fallback requires explicit policy"; font.bold: true }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Search engine, capability or provider…"
                onTextChanged: root.refresh()
            }
            ComboBox {
                id: classBox
                model: ["ALL","EDITORIAL","MEDIA_COMPOSITION","TRANSCODE","VIDEO_GENERATION","VIDEO_REFINEMENT","DIGITAL_HUMAN","LIP_SYNC","PORTRAIT_ANIMATION","BODY_ANIMATION","VOICE","AUDIO_PROCESSING","DUBBING","TRANSLATION","COMPOSITING","DCC_3D","RENDER","NEURAL_RENDER","STREAMING","CUSTOM"]
                onCurrentTextChanged: root.refresh()
            }
            ComboBox {
                id: scopeBox
                model: ["GLOBAL","APPLICATION","WORKSPACE","PROJECT","SEQUENCE","SCENE","TRACK","CLIP","NODE","TASK"]
            }
        }

        RowLayout {
            CheckBox { id: localOnly; text: "Local"; checked: true; onToggled: root.refresh() }
            CheckBox { id: lanAllowed; text: "LAN"; checked: true; onToggled: root.refresh() }
            CheckBox { id: cloudAllowed; text: "Cloud"; checked: false; onToggled: root.refresh() }
            CheckBox { id: showUnavailable; text: "Show unavailable/planned"; checked: true; onToggled: root.refresh() }
            Item { Layout.fillWidth: true }
            Label { text: "Scope: " + root.selectionScope }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Frame {
                SplitView.preferredWidth: 560
                ColumnLayout {
                    anchors.fill: parent
                    ListView {
                        id: engineList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            highlighted: root.selectedEngine.engine_id === modelData.engine_id
                            onClicked: root.selectedEngine = modelData
                            contentItem: RowLayout {
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.name + "\n" + modelData.engine_classes.join(", ")
                                    wrapMode: Text.WordWrap
                                }
                                Label { text: modelData.health_state || modelData.status }
                                CheckBox {
                                    text: "Compare"
                                    onToggled: {
                                        if (controller) controller.toggleCompare(modelData.engine_id, checked)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Frame {
                SplitView.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Label {
                        text: root.selectedEngine.name || "Select an engine"
                        font.bold: true
                        font.pixelSize: 17
                    }
                    Label { text: root.selectedEngine.engine_id || "" }
                    Label { text: "Status: " + (root.selectedEngine.health_state || "") }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: root.selectedEngine.capability_projection
                              ? "Capabilities: " + root.selectedEngine.capability_projection.join(", ")
                              : ""
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: root.selectedEngine.execution_modes
                              ? "Execution: " + root.selectedEngine.execution_modes.join(", ")
                              : ""
                    }
                    ComboBox {
                        id: fallbackBox
                        Layout.fillWidth: true
                        model: ["OFF","ASK","APPROVED_ONLY"]
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "The selector records user intent only. Model/provider routing remains with Model Router; CPU/GPU/NPU placement remains with HRB."
                    }
                    RowLayout {
                        Button {
                            text: "Set preference"
                            enabled: !!controller && !!root.selectedEngine.engine_id
                            onClicked: root.lastOutput = controller.prepareSelection(
                                root.selectedEngine.engine_id,
                                root.selectionScope,
                                fallbackBox.currentText)
                        }
                        Button {
                            text: "Compare selected"
                            enabled: !!controller
                            onClicked: root.lastOutput = controller.prepareComparison()
                        }
                    }
                    Frame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        ScrollView {
                            anchors.fill: parent
                            TextArea {
                                readOnly: true
                                wrapMode: TextEdit.Wrap
                                text: JSON.stringify(root.lastOutput, null, 2)
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: controller
        function onCatalogChanged() { root.refresh() }
    }

    Component.onCompleted: {
        if (controller) controller.refresh()
        refresh()
    }
}
