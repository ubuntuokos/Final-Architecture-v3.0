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

    function requiredCapabilities() {
        return requiredCaps.text.split(",").map(function(v) { return v.trim() }).filter(function(v) { return v.length > 0 })
    }

    function setCompared(engineId, enabled) {
        var next = compareIds.slice()
        var index = next.indexOf(engineId)
        if (enabled && index < 0) next.push(engineId)
        if (!enabled && index >= 0) next.splice(index, 1)
        compareIds = next
        if (controller) controller.toggleCompare(engineId, enabled)
    }

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
                model: ["GLOBAL","PRODUCT_FAMILY","APPLICATION","WORKSPACE","PROJECT","SEQUENCE","SCENE","TRACK","CLIP","NODE","TASK"]
            }
        }

        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: scopeTarget
                Layout.fillWidth: true
                visible: scopeBox.currentText !== "GLOBAL"
                placeholderText: "Scope target ID, e.g. project:alpha or clip:42"
            }
            TextField {
                id: requiredCaps
                Layout.fillWidth: true
                placeholderText: "Required capabilities, comma-separated (e.g. CAP-121,CAP-126)"
            }
        }

        RowLayout {
            CheckBox { id: localOnly; text: "Local"; checked: true; onToggled: root.refresh() }
            CheckBox { id: lanAllowed; text: "LAN"; checked: true; onToggled: root.refresh() }
            CheckBox { id: cloudAllowed; text: "Cloud/Remote"; checked: false; onToggled: root.refresh() }
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
                                    id: compareCheck
                                    text: "Compare"
                                    Binding {
                                        target: compareCheck
                                        property: "checked"
                                        value: root.compareIds.indexOf(modelData.engine_id) >= 0
                                    }
                                    onClicked: root.setCompared(
                                        modelData.engine_id,
                                        root.compareIds.indexOf(modelData.engine_id) < 0)
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
                            text: "Compatibility"
                            enabled: !!controller && !!root.selectedEngine.engine_id
                            onClicked: root.lastOutput = controller.compatibilityReport(
                                root.selectedEngine.engine_id,
                                root.requiredCapabilities())
                        }
                        Button {
                            text: "Set preference"
                            enabled: !!controller
                                     && !!root.selectedEngine.engine_id
                                     && (scopeBox.currentText === "GLOBAL" || scopeTarget.text.trim().length > 0)
                            onClicked: root.lastOutput = controller.prepareSelection(
                                root.selectedEngine.engine_id,
                                root.selectionScope,
                                scopeTarget.text,
                                root.requiredCapabilities(),
                                fallbackBox.currentText)
                        }
                        Button {
                            text: "Compare selected"
                            enabled: !!controller && root.compareIds.length > 0
                            onClicked: root.lastOutput = controller.prepareComparison(root.requiredCapabilities())
                        }
                        Button {
                            text: "Clear compare"
                            enabled: root.compareIds.length > 0
                            onClicked: {
                                var old = root.compareIds.slice()
                                root.compareIds = []
                                if (controller) {
                                    for (var i = 0; i < old.length; ++i) controller.toggleCompare(old[i], false)
                                }
                            }
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        visible: root.lastOutput && root.lastOutput.compatibility_grade
                        text: visible ? "Compatibility: " + root.lastOutput.compatibility_grade : ""
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
