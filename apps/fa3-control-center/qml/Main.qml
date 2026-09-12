import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: window
    width: 1540
    height: 960
    minimumWidth: 1180
    minimumHeight: 720
    visible: true
    title: "Final Architecture 3.0 — Control Center"

    property color surface0: palette.window
    property color surface1: palette.base
    property color surface2: palette.alternateBase
    property color accent: palette.highlight
    property color textPrimary: palette.windowText
    property color textMuted: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.62)
    property int selectedIndex: 0

    component Panel: Rectangle {
        radius: 12
        color: window.surface1
        border.color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.10)
    }

    component MetricCard: Panel {
        property string label: ""
        property string value: ""
        property string note: ""
        implicitWidth: 190
        implicitHeight: 112
        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 6
            Label { text: parent.parent.label; color: window.textMuted; font.pixelSize: 12 }
            Label { text: parent.parent.value; font.pixelSize: 28; font.bold: true }
            Label { text: parent.parent.note; color: window.textMuted; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
        }
    }

    component SectionTitle: Column {
        property string title: ""
        property string subtitle: ""
        spacing: 3
        Label { text: parent.title; font.pixelSize: 24; font.bold: true }
        Label { text: parent.subtitle; color: window.textMuted; font.pixelSize: 13 }
    }

    component ModuleCard: Panel {
        property string title: ""
        property string subtitle: ""
        property string badge: "READY"
        implicitWidth: 250
        implicitHeight: 120
        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 7
            RowLayout {
                width: parent.width
                Label { text: parent.parent.parent.title; font.pixelSize: 17; font.bold: true; Layout.fillWidth: true }
                Label {
                    text: parent.parent.parent.badge
                    color: window.accent
                    font.pixelSize: 10
                    font.bold: true
                }
            }
            Label {
                text: parent.parent.subtitle
                color: window.textMuted
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
    }

    ListModel {
        id: navigationModel
        ListElement { label: "Command Center"; iconText: "⌂" }
        ListElement { label: "Projects"; iconText: "▣" }
        ListElement { label: "AI Studio"; iconText: "✦" }
        ListElement { label: "Agents & Workflows"; iconText: "⌘" }
        ListElement { label: "Models & Providers"; iconText: "◫" }
        ListElement { label: "Architecture"; iconText: "◇" }
        ListElement { label: "Resources"; iconText: "▤" }
        ListElement { label: "Security & Approvals"; iconText: "◆" }
        ListElement { label: "Observability"; iconText: "⌁" }
        ListElement { label: "Evidence"; iconText: "✓" }
        ListElement { label: "Integrations"; iconText: "↔" }
        ListElement { label: "System"; iconText: "⚙" }
    }

    header: ToolBar {
        height: 62
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            spacing: 14

            Label {
                text: "FA3"
                font.pixelSize: 21
                font.bold: true
            }
            Rectangle { width: 1; height: 28; color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.16) }
            Label {
                text: "Final Architecture 3.0"
                font.pixelSize: 15
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            Label { text: "CANONICAL"; color: window.accent; font.bold: true; font.pixelSize: 11 }
            Label { text: "143 capabilities"; color: window.textMuted; font.pixelSize: 12 }
            ToolButton {
                text: "↻"
                ToolTip.visible: hovered
                ToolTip.text: "Canonical állapot frissítése"
                onClicked: fa3Repository.refresh()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 238
            Layout.fillHeight: true
            color: window.surface1
            border.color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.08)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                ListView {
                    id: nav
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: navigationModel
                    currentIndex: window.selectedIndex

                    delegate: ItemDelegate {
                        width: ListView.view.width
                        height: 44
                        highlighted: ListView.isCurrentItem
                        onClicked: {
                            nav.currentIndex = index
                            window.selectedIndex = index
                        }
                        contentItem: Row {
                            spacing: 12
                            Label { text: iconText; width: 22; horizontalAlignment: Text.AlignHCenter }
                            Label { text: label; font.pixelSize: 13 }
                        }
                    }
                }

                Panel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 112
                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 5
                        Label { text: "Repository"; font.bold: true; font.pixelSize: 12 }
                        Label {
                            width: parent.width
                            text: fa3Repository.repoRoot
                            color: window.textMuted
                            elide: Text.ElideMiddle
                            font.pixelSize: 10
                        }
                        Label { text: "Frissítve: " + fa3Repository.lastRefresh; color: window.textMuted; font.pixelSize: 10 }
                    }
                }
            }
        }

        StackLayout {
            id: pages
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.selectedIndex

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle {
                        Layout.fillWidth: true
                        title: "Command Center"
                        subtitle: "FA3 rendszerállapot, canonical integritás és operátori fókusz"
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        MetricCard { label: "Canonical rekord"; value: fa3Repository.canonicalRecordCount.toString(); note: "read-only projection" }
                        MetricCard { label: "Profile"; value: fa3Repository.profileCount.toString(); note: "canonical profiles" }
                        MetricCard { label: "Provider"; value: fa3Repository.providerCount.toString(); note: "registered providers" }
                        MetricCard { label: "Decision"; value: fa3Repository.decisionCount.toString(); note: "Decision Registry" }
                        MetricCard { label: "Evidence"; value: fa3Repository.evidenceCount.toString(); note: "JSON evidence records" }
                        MetricCard { label: "Pending"; value: fa3Repository.pendingCount.toString(); note: "runtime/conformance attention" }
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 290
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            Label { text: "Aktuális canonical rekordok"; font.pixelSize: 16; font.bold: true }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: fa3Repository.searchRecords("")
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 46
                                    onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                                    contentItem: RowLayout {
                                        spacing: 12
                                        Label { text: modelData.id; font.family: "monospace"; Layout.preferredWidth: 330; elide: Text.ElideRight }
                                        Label { text: modelData.title; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Label { text: modelData.status; color: modelData.status.indexOf("PENDING") >= 0 ? "#d99b32" : window.textMuted; Layout.preferredWidth: 160 }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Projects & Workspaces"; subtitle: "Projektek, assetek és knowledge-contextus egy közös operátori nézetben" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        ModuleCard { title: "Active Workspace"; subtitle: "FA3 repository és aktuális canonical graph"; badge: "LOCAL" }
                        ModuleCard { title: "Assets"; subtitle: "Kép, videó, 3D, audio és dokumentum projekció"; badge: "INDEX" }
                        ModuleCard { title: "Knowledge"; subtitle: "Canonical RAG/read projection; nincs párhuzamos memória-authority"; badge: "READ" }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "AI Studio"; subtitle: "A teljes lokális kreatív pipeline egységes felülete" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        ModuleCard { title: "Image"; subtitle: "ComfyUI / InvokeAI / editor bridge projekció" }
                        ModuleCard { title: "Video"; subtitle: "Kdenlive, generation, compositing és editorial pipeline" }
                        ModuleCard { title: "Animation"; subtitle: "Motion, character és timeline workflow-k" }
                        ModuleCard { title: "3D / VFX"; subtitle: "Geometry, Blender/Bforartist, Natron/Gaffer kapcsolatok" }
                        ModuleCard { title: "Audio"; subtitle: "STT, TTS, restoration, separation és voice fabric" }
                        ModuleCard { title: "Music"; subtitle: "Music generation, stems, DAW és mastering workflow-k" }
                        ModuleCard { title: "Story / Screenplay"; subtitle: "FA3 Story profile és production context projection" }
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        Column {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Label { text: "Execution boundary"; font.bold: true; font.pixelSize: 15 }
                            Label {
                                width: parent.width
                                wrapMode: Text.WordWrap
                                color: window.textMuted
                                text: "A Studio nem indít közvetlenül privilegizált toolt vagy modellt. A végrehajtás a meglévő FA3 model-router, MCP/capability gateway, workflow és host-resource authority-kon keresztül történik."
                            }
                        }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Agents & Workflows"; subtitle: "Interaktív agentek, durable workflow-k, taskok és execution projection" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        ModuleCard { title: "Interactive Agents"; subtitle: "Goose / desktop agent projection"; badge: "ROUTED" }
                        ModuleCard { title: "Durable Workflows"; subtitle: "Temporal authority állapot és futások"; badge: "READ" }
                        ModuleCard { title: "Tasks"; subtitle: "Current tasks, approvals és blockers"; badge: "QUEUE" }
                        ModuleCard { title: "Tool Execution"; subtitle: "Central MCP mediation és policy outcome"; badge: "GATED" }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 16
                    anchors.margins: 24
                    SectionTitle { title: "Models & Providers"; subtitle: "Model registry, provider projection és inference állapot" }
                    RowLayout {
                        Layout.fillWidth: true
                        MetricCard { label: "Provider rekord"; value: fa3Repository.providerCount.toString(); note: "canonical provider registry" }
                        MetricCard { label: "Capability baseline"; value: "143"; note: "változatlan" }
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 520
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            TextField { id: providerSearch; Layout.fillWidth: true; placeholderText: "Provider keresése…" }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: fa3Repository.recordsByCategory("provider").filter(function(v) {
                                    return providerSearch.text.length === 0 ||
                                           v.id.toLowerCase().indexOf(providerSearch.text.toLowerCase()) >= 0 ||
                                           v.title.toLowerCase().indexOf(providerSearch.text.toLowerCase()) >= 0
                                })
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 50
                                    contentItem: RowLayout {
                                        Label { text: modelData.id; font.family: "monospace"; Layout.preferredWidth: 330; elide: Text.ElideRight }
                                        Label { text: modelData.title; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Label { text: modelData.status; color: window.textMuted; Layout.preferredWidth: 180 }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 16
                    anchors.margins: 24
                    SectionTitle { title: "Architecture Explorer"; subtitle: "Profiles, contracts, providers, decisions, gates és conformance rekordok" }
                    TextField {
                        id: architectureSearch
                        Layout.fillWidth: true
                        placeholderText: "Keresés ID, név, státusz vagy path alapján…"
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 620
                        ListView {
                            anchors.fill: parent
                            anchors.margins: 8
                            clip: true
                            model: fa3Repository.searchRecords(architectureSearch.text)
                            delegate: ItemDelegate {
                                width: ListView.view.width
                                height: 58
                                onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                                contentItem: RowLayout {
                                    spacing: 10
                                    Label { text: modelData.category.toUpperCase(); color: window.accent; font.pixelSize: 10; Layout.preferredWidth: 80 }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Label { text: modelData.id; font.family: "monospace"; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                        Label { text: modelData.title; color: window.textMuted; elide: Text.ElideRight; Layout.fillWidth: true }
                                    }
                                    Label { text: modelData.status; color: window.textMuted; Layout.preferredWidth: 180 }
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Resources"; subtitle: "Read-only host telemetry és ChangeSet-alapú intent" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        MetricCard { label: "Host"; value: fa3Repository.hostName; note: "local host" }
                        MetricCard { label: "Kernel"; value: fa3Repository.kernelVersion; note: "running kernel" }
                        MetricCard { label: "CPU threads"; value: fa3Repository.cpuThreads.toString(); note: "read-only discovery" }
                        MetricCard { label: "Memory"; value: fa3Repository.memoryGiB.toFixed(1) + " GiB"; note: "physical memory" }
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            Label { text: "Host Resource Governance"; font.pixelSize: 17; font.bold: true }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                color: window.textMuted
                                text: "CPU/GPU/NPU/NUMA/memory/placement beavatkozást ez a GUI nem hajt végre. Az operátor typed ChangeSet draftot készít, amelyet a meglévő Host Resource Broker és approval chain kezel."
                            }
                            Button { text: "Új ChangeSet draft"; onClicked: changeSetDialog.open() }
                            Label { id: draftResult; color: window.accent; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Security & Approvals"; subtitle: "Policy, approval és security evidence read projection" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        ModuleCard { title: "Policies"; subtitle: "Effective policy állapot és decision outcome"; badge: "READ" }
                        ModuleCard { title: "Approvals"; subtitle: "Függő ChangeSet és execution approval-k"; badge: "GATED" }
                        ModuleCard { title: "Secrets"; subtitle: "Metadata/projection only; secret értékek nélkül"; badge: "NO VALUES" }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Observability"; subtitle: "Metrics, traces, provenance és rendszerállapot" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        ModuleCard { title: "Metrics"; subtitle: "Resource és service telemetry projection"; badge: "READ" }
                        ModuleCard { title: "Traces"; subtitle: "Workflow/tool/model execution trace projection"; badge: "READ" }
                        ModuleCard { title: "Provenance"; subtitle: "Artifact és execution provenance chain"; badge: "READ" }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Evidence"; subtitle: "Conformance, receipts és promotion bizonyítékok" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        MetricCard { label: "Evidence rekord"; value: fa3Repository.evidenceCount.toString(); note: "repository evidence" }
                        MetricCard { label: "Pending canonical"; value: fa3Repository.pendingCount.toString(); note: "figyelmet igényel" }
                    }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 250
                        Column {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Label { text: "Evidence authority boundary"; font.bold: true; font.pixelSize: 15 }
                            Label {
                                width: parent.width
                                wrapMode: Text.WordWrap
                                color: window.textMuted
                                text: "A GUI evidence rekordokat megjelenít, de nem minősíthet saját magától PASS-nak, nem promotálhat runtime-ot és nem írhatja felül a Unified Observability/Evidence authority döntését."
                            }
                        }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "Integrations"; subtitle: "Desktop, DCC, editor, MCP és provider kapcsolatok" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 12
                        ModuleCard { title: "Creative Apps"; subtitle: "Krita, GIMP, Kdenlive, Bforartist/Blender, Natron/Gaffer" }
                        ModuleCard { title: "Agent Clients"; subtitle: "Goose, Open WebUI, OpenYak és kapcsolódó projectionök" }
                        ModuleCard { title: "MCP"; subtitle: "Central gateway által mediált capability-k"; badge: "GATED" }
                    }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    anchors.margins: 24
                    SectionTitle { title: "System"; subtitle: "GUI runtime, repository és platform információ" }
                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 260
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            columnSpacing: 22
                            rowSpacing: 10
                            Label { text: "Application"; color: window.textMuted }
                            Label { text: "FA3 Control Center 0.1.0" }
                            Label { text: "Toolkit"; color: window.textMuted }
                            Label { text: "Qt 6 / QML" }
                            Label { text: "Repository"; color: window.textMuted }
                            Label { text: fa3Repository.repoRoot; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Label { text: "Mutation policy"; color: window.textMuted }
                            Label { text: "Draft ChangeSet only — no direct privileged execution" }
                            Label { text: "Display target"; color: window.textMuted }
                            Label { text: "KDE Plasma / Wayland" }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: changeSetDialog
        title: "Typed ChangeSet draft"
        modal: true
        anchors.centerIn: parent
        width: 560
        standardButtons: Dialog.Save | Dialog.Cancel

        ColumnLayout {
            width: parent.width
            spacing: 10
            TextField { id: csScope; Layout.fillWidth: true; placeholderText: "Scope (pl. HOST_RESOURCE_GOVERNANCE)" }
            TextField { id: csAction; Layout.fillWidth: true; placeholderText: "Action (pl. propose.memory.hugepages)" }
            TextField { id: csTarget; Layout.fillWidth: true; placeholderText: "Target (canonical ID vagy host resource)" }
            TextArea {
                id: csRationale
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                placeholderText: "Indoklás"
                wrapMode: TextEdit.Wrap
            }
            Label {
                Layout.fillWidth: true
                color: window.textMuted
                wrapMode: Text.WordWrap
                text: "A Save csak helyi DRAFT_NOT_SUBMITTED JSON-t készít. Nem futtat parancsot és nem módosít canonical állapotot."
            }
        }

        onAccepted: {
            draftResult.text = fa3Repository.createDraftChangeSet(csScope.text, csAction.text, csTarget.text, csRationale.text)
            csScope.clear()
            csAction.clear()
            csTarget.clear()
            csRationale.clear()
        }
    }
}
