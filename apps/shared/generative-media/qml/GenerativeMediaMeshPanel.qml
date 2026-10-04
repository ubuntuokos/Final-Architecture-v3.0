import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    objectName: "generativeMediaMeshPanel"
    property color panel: "#091624"
    property color borderColor: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    Layout.fillWidth: true
    implicitHeight: content.implicitHeight + 24
    radius: 8
    color: panel
    border.color: borderColor

    property var lanes: [
        {title: "IMAGE / STORYBOARD", detail: "Generate · AI Edit · Storyboard · physical-consistency intent"},
        {title: "MOTION / VIDEO", detail: "Trajectory · camera motion · regional edit · provider-neutral generation"},
        {title: "REFINEMENT", detail: "Upscale · detail refine · denoise/reconstruct · generator→refiner"},
        {title: "CHARACTER", detail: "Motion transfer · reference conditioning · appearance is rights-gated"},
        {title: "RESEARCH", detail: "Generative Media experiments route to AI Module Factory"},
        {title: "SKILL ROUTING", detail: "Advisory scoring only; Model Router remains authority"}
    ]

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Label { id: titleLabel; text: "Generative Media Capability Mesh"; color: root.textPrimary; font.bold: true; font.pixelSize: 13; Layout.fillWidth: true }
            Label { id: runtimeGateLabel; text: "RUNTIME GATED"; color: root.accent; font.bold: true; font.pixelSize: 9 }
        }
        Label {
            id: authorityLabel
            Layout.fillWidth: true
            text: "FA3-native shared projection · capability baseline 175 · Model Router → HRB · Temporal workflow authority"
            color: root.textMuted
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        Label {
            id: executionPolicyLabel
            Layout.fillWidth: true
            text: "CPU reference/manual path · provider may remain ineligible · no silent fallback · display GPU is not auto-enrolled"
            color: root.textMuted
            font.pixelSize: 8
            wrapMode: Text.WordWrap
        }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: 6
            columnSpacing: 8
            Repeater {
                model: root.lanes
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 46
                    radius: 6
                    color: "#0f2035"
                    border.color: root.borderColor
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 7
                        spacing: 2
                        Label { text: modelData.title; color: root.accent; font.pixelSize: 8; font.bold: true }
                        Label { text: modelData.detail; color: root.textPrimary; font.pixelSize: 8; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                }
            }
        }
        Label {
            id: childAdmissionLabel
            Layout.fillWidth: true
            text: "HiDream child providers: not admitted · explicit child donor marker + rights/security/coexistence/runtime gates required"
            color: root.textMuted
            font.pixelSize: 8
            wrapMode: Text.WordWrap
        }
    }

    function currentHostProbeReport() {
        return {
            "panelObjectName": objectName,
            "panelVisible": visible && width > 0 && height > 0,
            "panelWidth": width,
            "panelHeight": height,
            "titleVisible": titleLabel.visible && titleLabel.width > 0 && titleLabel.height > 0,
            "runtimeGateVisible": runtimeGateLabel.visible && runtimeGateLabel.width > 0 && runtimeGateLabel.height > 0,
            "authorityVisible": authorityLabel.visible && authorityLabel.width > 0 && authorityLabel.height > 0,
            "childAdmissionVisible": childAdmissionLabel.visible && childAdmissionLabel.width > 0 && childAdmissionLabel.height > 0,
            "executionPolicyVisible": executionPolicyLabel.visible && executionPolicyLabel.width > 0 && executionPolicyLabel.height > 0,
            "runtimeGateText": runtimeGateLabel.text,
            "executionPolicyText": executionPolicyLabel.text,
            "authorityText": authorityLabel.text,
            "childAdmissionText": childAdmissionLabel.text
        }
    }
}