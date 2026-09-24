import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0d1c2f"
    property color panelRaised: "#132a42"
    property color border: "#24384f"
    property color textPrimary: "#eef5ff"
    property color textMuted: "#8096ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    property var workItems: []
    property var activityRows: []
    property var agentWorkloads: []
    property string projectionState: "ADAPTER-GATED"
    property string operationNotice: ""

    signal refreshRequested()
    signal createWorkItemRequested()
    signal transitionRequested(string canonicalWorkItemId, string requestedState)
    signal providerConfigureRequested(string providerId)

    property var providers: [
        {id: "FA3-PROVIDER-KANEO-001", name: "Kaneo", role: "PRIMARY INTERACTIVE", state: "OPTIONAL"},
        {id: "FA3-PROVIDER-KANBOARD-001", name: "Kanboard", role: "SECONDARY / AUTOMATION", state: "OPTIONAL"},
        {id: "GITHUB_ISSUES", name: "GitHub Issues", role: "EXTERNAL ISSUE ADAPTER", state: "ADAPTER-GATED"}
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Work Management"; color: root.textPrimary; font.pixelSize: 21; font.bold: true }
                Label {
                    text: "Kaneo + Kanboard · provider-neutral projects, boards, tasks and automation projection"
                    color: root.textMuted
                    font.pixelSize: 10
                }
            }
            Rectangle {
                radius: 6
                implicitWidth: 140
                implicitHeight: 28
                color: root.panelRaised
                border.color: root.accent
                Label { anchors.centerIn: parent; text: root.projectionState; color: root.accent; font.bold: true; font.pixelSize: 9 }
            }
            Button { text: "Refresh"; onClicked: root.refreshRequested() }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 66
            radius: 8
            color: root.panel
            border.color: root.border
            Label {
                anchors.fill: parent
                anchors.margins: 12
                wrapMode: Text.WordWrap
                verticalAlignment: Text.AlignVCenter
                color: root.textMuted
                font.pixelSize: 10
                text: "Ez provider-neutral operátori projekció, nem authority. A state transition és automation műveletek külön FA3 authorization döntést igényelnek. A GUI hardver-megfigyelése nem admission authority; az alap Work Management workload CPU-lightweight. GPU/NPU csak explicit workload-igény esetén, HRB admission + friss lease után használható."
            }
        }

        Label {
            visible: root.operationNotice.length > 0
            Layout.fillWidth: true
            text: root.operationNotice
            color: root.accent
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Overview" }
            TabButton { text: "Projects / Boards / Tasks" }
            TabButton { text: "Automations" }
            TabButton { text: "Agent Workloads" }
            TabButton { text: "Activity" }
            TabButton { text: "Providers" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Item {
                RowLayout {
                    anchors.fill: parent
                    spacing: 12
                    Repeater {
                        model: [
                            {title: "Canonical work items", detail: "FA3 registry-governed IDs · provider identity is metadata", badge: "PROVIDER-NEUTRAL"},
                            {title: "Authorization", detail: "Scoped transition/action ALLOW required", badge: "FAIL-CLOSED"},
                            {title: "Resources", detail: "CPU-lightweight by default · HRB is admission authority", badge: "WORKLOAD-DRIVEN"}
                        ]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 8
                            color: root.panel
                            border.color: root.border
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8
                                Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: modelData.detail; color: root.textMuted }
                                Item { Layout.fillHeight: true }
                                Label { text: modelData.badge; color: root.accent; font.pixelSize: 9; font.bold: true }
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Unified work-item projection"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Button { text: "New work item"; onClicked: root.createWorkItemRequested() }
                    }
                    Label {
                        visible: root.workItems.length === 0
                        text: "Nincs betöltött provider-adat. Kaneo/Kanboard/GitHub Issues adapter csatlakoztatásakor ugyanebben a nézetben jelennek meg a work itemek."
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.workItems
                        spacing: 4
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 64
                            radius: 6
                            color: root.panel
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.title || modelData.canonical_work_item_id || "Work item"; color: root.textPrimary; font.bold: true }
                                    Label { text: (modelData.project_workspace_scope || "") + " · " + (modelData.provider_id || "provider-neutral"); color: root.textMuted; font.pixelSize: 9 }
                                }
                                Label { text: modelData.current_state || "UNKNOWN"; color: root.accent; font.bold: true }
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    Label { text: "Automations"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        text: "Event ≠ authorization. Kaneo/Kanboard automation és webhook esemény csak typed/validated input; a kiváltott action külön scoped authorization döntést igényel."
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 90
                        radius: 8
                        color: root.panel
                        border.color: root.border
                        Label { anchors.fill: parent; anchors.margins: 14; wrapMode: Text.WordWrap; color: root.textMuted; text: "Provider automation state: ADAPTER-GATED · integration-wide credential nem kerülheti meg a project/workspace/capability scope-ot." }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Label { text: "Agent Workloads"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        text: "Read-only provider-neutral execution projection. A Work Item és az Agent Workload Task külön identity; a kapcsolat csak opcionális work_item_ref. Lifecycle művelet innen nem fut közvetlenül: csak typed UAF draft intent engedélyezhető az Agent Action Centeren keresztül."
                    }
                    Label {
                        visible: root.agentWorkloads.length === 0
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: root.textMuted
                        text: "Nincs betöltött Agent Workload runtime evidence. PENDING vagy ismeretlen állapotból a GUI nem gyárt RUNNING / PASS / CONNECTED státuszt."
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: root.agentWorkloads
                        spacing: 4
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 72
                            radius: 6
                            color: root.panel
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.task_id || "Agent workload"; color: root.textPrimary; font.bold: true }
                                    Label { text: (modelData.work_item_ref || "no work-item link") + " · " + (modelData.runner_provider || "runner pending"); color: root.textMuted; font.pixelSize: 9 }
                                    Label { text: "HRB: " + (modelData.hrb_state || "UNKNOWN") + " · evidence: " + (modelData.evidence_state || "PENDING"); color: root.textMuted; font.pixelSize: 9 }
                                }
                                Label { text: modelData.phase || "UNKNOWN"; color: root.accent; font.bold: true }
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Label { text: "Activity / reconciliation"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                    Label { text: "Provider revision + observed canonical revision + reconciliation state kötelező."; color: root.textMuted }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: root.activityRows
                        delegate: Label { width: ListView.view.width; text: modelData.summary || "activity"; color: root.textMuted }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Label { text: "Providers"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
                    Repeater {
                        model: root.providers
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 74
                            radius: 7
                            color: root.panel
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.name; color: root.textPrimary; font.bold: true }
                                    Label { text: modelData.id + " · " + modelData.role; color: root.textMuted; font.pixelSize: 9 }
                                }
                                Label { text: modelData.state; color: modelData.state === "OPTIONAL" ? root.green : root.orange; font.bold: true; font.pixelSize: 9 }
                                Button { text: "Configure"; onClicked: root.providerConfigureRequested(modelData.id) }
                            }
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "Kaneo és Kanboard nem kap külön top-level GUI-menüt; ugyanazon Work Management felületen osztoznak. Provider kieséskor a canonical identity és reconciliation state megmarad."
                        color: root.textMuted
                        font.pixelSize: 10
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
