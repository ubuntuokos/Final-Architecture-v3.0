import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color panel: "#0b1624"
    property color panelRaised: "#10233a"
    property color border: "#23374d"
    property color textPrimary: "#eef7ff"
    property color textMuted: "#8ca0b6"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"

    property var status: fa3Repository.governanceStatus
    property var repository: status && status.repository ? status.repository : ({})
    property var gates: status && status.gates ? status.gates : ({})
    property var evidence: status && status.evidence ? status.evidence : ({})
    property var acceptance: status && status.acceptance ? status.acceptance : ({})
    property var promotion: status && status.promotion ? status.promotion : ({})

    function shown(value) {
        if (value === undefined || value === null || String(value).length === 0)
            return "UNKNOWN_OR_PENDING"
        return String(value)
    }

    function stateTone(value) {
        var s = shown(value).toUpperCase()
        if (s.indexOf("PASS") >= 0 || s === "PROMOTED") return green
        if (s.indexOf("PENDING") >= 0 || s.indexOf("UNKNOWN") >= 0 || s.indexOf("EXPIRED") >= 0) return orange
        return textPrimary
    }

    component StatusRow: RowLayout {
        property string labelText: ""
        property string valueText: "UNKNOWN_OR_PENDING"
        property color valueColor: root.textPrimary
        Layout.fillWidth: true
        spacing: 14
        Label { text: labelText; color: root.textMuted; Layout.preferredWidth: 170 }
        Label {
            text: valueText
            color: valueColor
            font.family: "monospace"
            wrapMode: Text.WrapAnywhere
            Layout.fillWidth: true
        }
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: 18
        clip: true

        ColumnLayout {
            width: Math.max(760, root.width - 48)
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Governance Status"; color: root.textPrimary; font.pixelSize: 26; font.bold: true }
                    Label { text: "READ-ONLY MACHINE PROJECTION · reports/governance-status-projection.json"; color: root.textMuted }
                }
                Button {
                    text: "Refresh"
                    onClicked: fa3Repository.refresh()
                    ToolTip.visible: hovered
                    ToolTip.text: "Read-only reread; no Acceptance, Promotion, evidence, or canonical mutation"
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: lifecycle.implicitHeight + 28
                radius: 10
                color: root.panel
                border.color: root.border
                ColumnLayout {
                    id: lifecycle
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "Lifecycle"; color: root.accent; font.bold: true }
                    StatusRow { labelText: "Projection"; valueText: root.shown(root.status._projection_state); valueColor: root.stateTone(valueText) }
                    StatusRow { labelText: "Assurance"; valueText: root.shown(root.status.assurance_state); valueColor: root.stateTone(valueText) }
                    StatusRow { labelText: "Canonical"; valueText: root.shown(root.status.canonical_state); valueColor: root.stateTone(valueText) }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: repoBox.implicitHeight + 28
                radius: 10
                color: root.panel
                border.color: root.border
                ColumnLayout {
                    id: repoBox
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "Repository"; color: root.accent; font.bold: true }
                    StatusRow { labelText: "Commit"; valueText: root.shown(root.repository.head_commit) }
                    StatusRow { labelText: "Release"; valueText: root.shown(root.repository.release) }
                    StatusRow { labelText: "Capabilities"; valueText: root.shown(root.repository.capability_count) }
                    StatusRow { labelText: "Mandatory gates"; valueText: root.shown(root.gates.mandatory_reference_gate_count) }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: evidenceBox.implicitHeight + 28
                radius: 10
                color: root.panel
                border.color: root.border
                ColumnLayout {
                    id: evidenceBox
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "Current Host / Evidence"; color: root.accent; font.bold: true }
                    StatusRow { labelText: "Registry"; valueText: root.shown(root.evidence.registry_status); valueColor: root.stateTone(valueText) }
                    StatusRow { labelText: "Explicit PASS/admitted"; valueText: root.shown(root.evidence.current_host_explicit_pass_or_admitted_count) }
                    StatusRow { labelText: "Pending"; valueText: root.shown(root.evidence.pending_current_host_count); valueColor: Number(root.evidence.pending_current_host_count || 0) > 0 ? root.orange : root.green }
                    StatusRow { labelText: "Expired subjects"; valueText: root.evidence.expired_subjects ? root.evidence.expired_subjects.length : "UNKNOWN_OR_PENDING"; valueColor: Number(valueText) > 0 ? root.orange : root.green }
                    Label { text: "Evidence bindings"; color: root.textPrimary; font.bold: true; Layout.topMargin: 5 }
                    Repeater {
                        model: root.evidence.artifact_bindings || []
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: bindingCol.implicitHeight + 18
                            radius: 8
                            color: root.panelRaised
                            border.color: root.border
                            ColumnLayout {
                                id: bindingCol
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 3
                                Label { text: root.shown(modelData.path); color: root.textPrimary; font.family: "monospace"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                                Label { text: "Host " + root.shown(modelData.host_id) + " · Run " + root.shown(modelData.run_id); color: root.textMuted; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                                Label { text: "Collected " + root.shown(modelData.collected_at) + " · Expires " + root.shown(modelData.expires_at); color: root.textMuted; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                                Label { text: "Commit " + root.shown(modelData.source_commit); color: root.textMuted; font.family: "monospace"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: authorityBox.implicitHeight + 28
                radius: 10
                color: root.panel
                border.color: root.border
                ColumnLayout {
                    id: authorityBox
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "Authoritative generated outputs"; color: root.accent; font.bold: true }
                    StatusRow { labelText: "Acceptance"; valueText: root.shown(root.acceptance.state); valueColor: root.stateTone(valueText) }
                    StatusRow { labelText: "Acceptance source"; valueText: root.shown(root.acceptance.path) }
                    StatusRow { labelText: "Production"; valueText: root.shown(root.promotion.state); valueColor: root.stateTone(valueText) }
                    StatusRow { labelText: "Promotion ID"; valueText: root.shown(root.promotion.promotion_id) }
                    StatusRow { labelText: "Promotion source"; valueText: root.shown(root.promotion.path) }
                }
            }

            Label {
                Layout.fillWidth: true
                text: "UNKNOWN_OR_PENDING is intentionally visible. This surface never turns missing documentation, CI/reference evidence, or a canonical closure into current-host PASS or production promotion."
                color: root.textMuted
                wrapMode: Text.WordWrap
            }
        }
    }
}
