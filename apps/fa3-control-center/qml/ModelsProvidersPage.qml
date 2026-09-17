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
    property var selectedFit: ({})

    Component.onCompleted: fa3Llmfit.refresh()

    component SummaryCard: Rectangle {
        property string titleText: ""
        property string detailText: ""
        property string badgeText: ""
        property color tone: root.accent
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
        implicitHeight: 108

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Rectangle { width: 7; height: 7; radius: 4; color: parent.parent.parent.tone }
                Label { text: parent.parent.parent.titleText; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                Rectangle {
                    implicitWidth: badgeLabel.implicitWidth + 14
                    implicitHeight: 21
                    radius: 5
                    color: Qt.rgba(parent.parent.parent.tone.r, parent.parent.parent.tone.g, parent.parent.parent.tone.b, 0.10)
                    border.color: Qt.rgba(parent.parent.parent.tone.r, parent.parent.parent.tone.g, parent.parent.parent.tone.b, 0.35)
                    Label { id: badgeLabel; anchors.centerIn: parent; text: parent.parent.parent.parent.badgeText; color: parent.parent.parent.parent.tone; font.pixelSize: 8; font.bold: true }
                }
            }
            Label { text: parent.parent.detailText; color: root.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.fillHeight: true }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 13

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: "Model Manager · Models & Providers"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
            Label { text: "Canonical model/provider projection + llmfit hardware-fit advisory; admission and placement remain HRB-governed"; color: root.textMuted; font.pixelSize: 11 }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            SummaryCard {
                Layout.fillWidth: true
                titleText: "Provider Registry"
                detailText: fa3Repository.providerCount + " canonical provider records"
                badgeText: "CANONICAL"
                tone: root.accent
            }
            SummaryCard {
                Layout.fillWidth: true
                titleText: "llmfit"
                detailText: fa3Llmfit.available ? "Headless provider · " + fa3Llmfit.socketPath : (fa3Llmfit.lastError || "Provider not connected")
                badgeText: fa3Llmfit.statusText
                tone: fa3Llmfit.available ? root.green : root.orange
            }
            SummaryCard {
                Layout.fillWidth: true
                titleText: "Hardware observation"
                detailText: (fa3Llmfit.system.gpu_name || "Local fit input") + (fa3Llmfit.system.gpu_count !== undefined ? " · " + fa3Llmfit.system.gpu_count + " accelerator(s)" : "")
                badgeText: "OBSERVED"
                tone: root.cyan
            }
            SummaryCard {
                Layout.fillWidth: true
                titleText: "Evidence boundary"
                detailText: "llmfit estimate ≠ runtime evidence; measured execution is required for promotion"
                badgeText: "FAIL-CLOSED"
                tone: root.orange
            }
        }

        TabBar {
            id: modelTabs
            Layout.fillWidth: true
            TabButton { text: "Model Manager / Hardware Fit" }
            TabButton { text: "Providers" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: modelTabs.currentIndex

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 104
                        radius: 9
                        color: root.panel
                        border.color: root.border
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label { text: "Use case"; color: root.textMuted; font.pixelSize: 10 }
                                ComboBox {
                                    id: fitUseCase
                                    Layout.preferredWidth: 130
                                    model: ["general", "coding", "reasoning", "chat", "multimodal", "embedding"]
                                }
                                Label { text: "Runtime"; color: root.textMuted; font.pixelSize: 10 }
                                ComboBox {
                                    id: fitRuntime
                                    Layout.preferredWidth: 125
                                    model: ["any", "llamacpp", "mlx"]
                                }
                                Label { text: "Context"; color: root.textMuted; font.pixelSize: 10 }
                                SpinBox {
                                    id: fitContext
                                    Layout.preferredWidth: 135
                                    from: 1024
                                    to: 1048576
                                    stepSize: 1024
                                    value: 8192
                                    editable: true
                                }
                                Label { text: "Workload class"; color: root.textMuted; font.pixelSize: 10 }
                                ComboBox {
                                    id: resourceClass
                                    Layout.preferredWidth: 190
                                    textRole: "label"
                                    valueRole: "value"
                                    model: [
                                        {label: "CPU + memory", value: "CPU_MEMORY"},
                                        {label: "Accelerator requested", value: "ACCELERATOR"}
                                    ]
                                }
                                Button {
                                    text: fa3Llmfit.busy ? "Refreshing…" : "Refresh recommendations"
                                    enabled: !fa3Llmfit.busy
                                    onClicked: fa3Llmfit.recommendModels(fitUseCase.currentText, fitRuntime.currentText, fitContext.value)
                                }
                                Item { Layout.fillWidth: true }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: "Hardware values from llmfit are " + fa3Llmfit.observationAuthority + ". They may inform fit estimation but never authorize admission."
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                                Label {
                                    text: resourceClass.currentValue === "ACCELERATOR" ? "HRB lease + Accelerator Guard required" : "No accelerator discovery/lease required"
                                    color: resourceClass.currentValue === "ACCELERATOR" ? root.orange : root.green
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 285
                        radius: 9
                        color: root.panel
                        border.color: root.border
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Hardware-fit recommendations"; color: root.textPrimary; font.pixelSize: 14; font.bold: true; Layout.fillWidth: true }
                                Label { text: fa3Llmfit.models.length + " model"; color: root.textMuted; font.pixelSize: 10 }
                            }
                            ListView {
                                id: fitList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                model: fa3Llmfit.models
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                                delegate: ItemDelegate {
                                    required property var modelData
                                    width: ListView.view.width - 10
                                    height: 72
                                    highlighted: root.selectedFit.name === modelData.name
                                    onClicked: root.selectedFit = modelData
                                    background: Rectangle {
                                        radius: 6
                                        color: parent.highlighted ? "#12324a" : (parent.hovered ? root.panelRaised : "transparent")
                                        border.color: parent.highlighted ? root.cyan : "transparent"
                                    }
                                    contentItem: RowLayout {
                                        spacing: 10
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2
                                            Label { text: modelData.name || "Unnamed model"; color: root.textPrimary; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            Label {
                                                text: (modelData.provider || "") + "  ·  " + (modelData.parameter_count || "") + "  ·  estimate only"
                                                color: root.textMuted
                                                font.pixelSize: 9
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                        Label { text: modelData.fit_label || modelData.fit_level || "—"; color: root.cyan; Layout.preferredWidth: 90 }
                                        Label { text: modelData.best_quant || "native"; color: root.textPrimary; Layout.preferredWidth: 90 }
                                        Label {
                                            text: modelData.memory_required_gb !== undefined && modelData.memory_required_gb !== null ? Number(modelData.memory_required_gb).toFixed(1) + " GiB" : "—"
                                            color: root.textPrimary
                                            Layout.preferredWidth: 90
                                        }
                                        Label {
                                            text: modelData.estimated_tps !== undefined && modelData.estimated_tps !== null ? Number(modelData.estimated_tps).toFixed(1) + " tok/s" : "—"
                                            color: root.textPrimary
                                            Layout.preferredWidth: 100
                                        }
                                        Label { text: modelData.runtime_label || modelData.runtime || "—"; color: root.textMuted; Layout.preferredWidth: 105 }
                                        Label { text: modelData.estimate_confidence_label || modelData.estimate_confidence || "estimated"; color: root.textMuted; Layout.preferredWidth: 105 }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 126
                        radius: 9
                        color: root.panel
                        border.color: root.border
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 13
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                Label {
                                    text: root.selectedFit.name ? root.selectedFit.name : "Select a model to prepare admission"
                                    color: root.textPrimary
                                    font.bold: true
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: "The buttons create DRAFT_NOT_SUBMITTED ChangeSets only. llmfit cannot route, place, lease, execute, benchmark, or promote a model by itself."
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                                Label {
                                    id: draftResult
                                    text: ""
                                    color: root.accent
                                    font.pixelSize: 9
                                    Layout.fillWidth: true
                                    elide: Text.ElideMiddle
                                }
                            }
                            Button {
                                text: "Benchmark ChangeSet"
                                enabled: !!root.selectedFit.name
                                onClicked: draftResult.text = fa3Repository.createDraftChangeSet(
                                    "MODEL_MANAGER_LLMFIT_BENCHMARK",
                                    "benchmark.model_fit",
                                    root.selectedFit.name,
                                    fa3Llmfit.benchmarkDraftRationale(root.selectedFit, resourceClass.currentValue === "ACCELERATOR", fitContext.value))
                            }
                            Button {
                                text: "Placement ChangeSet"
                                enabled: !!root.selectedFit.name
                                onClicked: draftResult.text = fa3Repository.createDraftChangeSet(
                                    "MODEL_MANAGER_LLMFIT_PLACEMENT",
                                    "request.runtime.placement",
                                    root.selectedFit.name,
                                    fa3Llmfit.placementDraftRationale(root.selectedFit, resourceClass.currentValue === "ACCELERATOR", fitContext.value))
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    TextField {
                        id: providerSearch
                        Layout.fillWidth: true
                        placeholderText: "Search provider registry…"
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 280
                        radius: 9
                        color: root.panel
                        border.color: root.border
                        border.width: 1

                        ListView {
                            id: providerList
                            anchors.fill: parent
                            anchors.margins: 8
                            anchors.rightMargin: 12
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds
                            model: fa3Repository.recordsByCategory("provider").filter(function(v) {
                                var needle = providerSearch.text.toLowerCase()
                                return needle.length === 0 || v.id.toLowerCase().indexOf(needle) >= 0 || v.title.toLowerCase().indexOf(needle) >= 0
                            })

                            ScrollBar.vertical: ScrollBar {
                                policy: ScrollBar.AlwaysOn
                                minimumSize: 0.08
                                contentItem: Rectangle {
                                    implicitWidth: 8
                                    radius: 4
                                    color: parent.pressed ? root.accent : "#50667e"
                                }
                                background: Rectangle {
                                    implicitWidth: 10
                                    radius: 5
                                    color: "#091624"
                                }
                            }

                            delegate: ItemDelegate {
                                required property var modelData
                                width: ListView.view.width - 14
                                height: 50
                                background: Rectangle { color: parent.hovered ? root.panelRaised : "transparent"; radius: 5 }
                                onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                                contentItem: RowLayout {
                                    Rectangle { width: 7; height: 7; radius: 4; color: (modelData.status || "").indexOf("PENDING") >= 0 ? root.orange : root.green }
                                    Label { text: modelData.id; color: root.textPrimary; font.family: "monospace"; Layout.preferredWidth: 310; elide: Text.ElideRight }
                                    Label { text: modelData.title; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.status || "REGISTERED"; color: (modelData.status || "").indexOf("PENDING") >= 0 ? root.orange : root.green; font.pixelSize: 9; font.bold: true; Layout.preferredWidth: 170; elide: Text.ElideRight }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
