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

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "Models & Providers"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "Model Registry, provider projections and local inference surfaces"; color: root.textMuted; font.pixelSize: 11 }
            }
            Button {
                text: "Provider Explorer"
                onClicked: providerExplorerDialog.open()
            }
            Button {
                text: "Provider Execution"
                onClicked: providerExecutionDialog.open()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            SummaryCard { Layout.fillWidth: true; titleText: "Provider Registry"; detailText: fa3Repository.providerCount + " canonical provider records"; badgeText: "CANONICAL"; tone: root.accent }
            SummaryCard { Layout.fillWidth: true; titleText: "Capability Baseline"; detailText: "FA3 baseline remains authority-stable"; badgeText: "143"; tone: root.green }
            SummaryCard { Layout.fillWidth: true; titleText: "Pending"; detailText: "Runtime/conformance attention"; badgeText: fa3Repository.pendingCount.toString(); tone: fa3Repository.pendingCount > 0 ? root.orange : root.green }
        }

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
                    width: ListView.view.width - 14
                    height: 50
                    background: Rectangle { color: hovered ? root.panelRaised : "transparent"; radius: 5 }
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

    Dialog {
        id: providerExecutionDialog
        modal: true
        title: "Provider Execution"
        anchors.centerIn: parent
        width: Math.min(1040, Math.max(760, root.width - 96))
        height: Math.min(720, Math.max(540, root.height - 96))
        standardButtons: Dialog.Close
        contentItem: ProviderExecutionView {
            panel: root.panel
            panelRaised: root.panelRaised
            border: root.border
            textPrimary: root.textPrimary
            textMuted: root.textMuted
            accent: root.accent
            green: root.green
            orange: root.orange
        }
    }

    Dialog {
        id: providerExplorerDialog
        modal: true
        title: "Provider Explorer"
        anchors.centerIn: parent
        width: Math.min(1220, Math.max(900, root.width - 64))
        height: Math.min(760, Math.max(560, root.height - 64))
        standardButtons: Dialog.Close

        contentItem: ProviderExplorerView {
            id: providerExplorerView
            panel: root.panel
            panelRaised: root.panelRaised
            border: root.border
            textPrimary: root.textPrimary
            textMuted: root.textMuted
            accent: root.accent
            green: root.green
            orange: root.orange
            onAdmissionDraftRequested: function(providerKey, providerName) {
                lastDraftResult = fa3Repository.createDraftChangeSet(
                    "MODEL_PROVIDER_ADMISSION",
                    "propose.external-llm-provider-admission",
                    providerKey,
                    "External LLM catalog discovery only for " + providerName
                    + "; security/privacy/egress/credential/provider admission and Model Router policy remain mandatory."
                )
            }
        }
    }
}
