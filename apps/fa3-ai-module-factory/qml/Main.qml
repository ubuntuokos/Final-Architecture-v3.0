// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1500
    height: 900
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    title: "FA3 — AI Module Factory"

    property var plan: ({})
    ListModel { id: artifactModel }

    function artifactsAsArray() {
        var rows = []
        for (var i = 0; i < artifactModel.count; ++i)
            rows.push(artifactModel.get(i))
        return rows
    }

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            Label { text: "FA3 AI Module Factory"; font.bold: true; font.pixelSize: 18 }
            Label { text: "CAP-095 · work-derived module planning"; Layout.fillWidth: true }
            Label { text: fa3ModuleFactory.fabricState; font.pixelSize: 10 }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Frame {
            SplitView.preferredWidth: 420
            SplitView.minimumWidth: 360
            ColumnLayout {
                anchors.fill: parent
                spacing: 10

                Label { text: "Source work"; font.bold: true; font.pixelSize: 16 }
                ComboBox {
                    id: sourceApp
                    Layout.fillWidth: true
                    model: fa3ModuleFactory.sourceApplications
                    textRole: "label"
                    valueRole: "id"
                }
                TextField {
                    id: artifactId
                    Layout.fillWidth: true
                    placeholderText: "Approved artifact ID"
                }
                CheckBox { id: approved; text: "Human-approved final" }
                CheckBox { id: provenance; text: "Provenance VERIFIED" }
                CheckBox { id: useRights; text: "Use rights ALLOWED" }
                CheckBox { id: trainingRights; text: "Training rights ALLOWED" }
                CheckBox { id: derivativeRights; text: "Derivative-model rights ALLOWED" }
                ComboBox {
                    id: consent
                    Layout.fillWidth: true
                    model: ["PRIVATE", "PROJECT", "SHARED"]
                }
                Button {
                    text: "Add qualified-source candidate"
                    Layout.fillWidth: true
                    onClicked: {
                        artifactModel.append({
                            artifact_id: artifactId.text,
                            source_application: sourceApp.currentValue,
                            approved_final: approved.checked,
                            provenance_status: provenance.checked ? "VERIFIED" : "UNKNOWN",
                            use_rights: useRights.checked ? "ALLOWED" : "UNKNOWN",
                            training_rights: trainingRights.checked ? "ALLOWED" : "UNKNOWN",
                            derivative_model_rights: derivativeRights.checked ? "ALLOWED" : "UNKNOWN",
                            consent_scope: consent.currentText
                        })
                        artifactId.clear()
                    }
                }

                Label { text: "Dataset candidates: " + artifactModel.count; font.bold: true }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: artifactModel
                    clip: true
                    delegate: ItemDelegate {
                        width: ListView.view.width
                        text: artifact_id + " · " + source_application
                    }
                }
                Button {
                    text: "Clear"
                    onClicked: artifactModel.clear()
                }
            }
        }

        Item {
            SplitView.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Label { text: "Module"; font.bold: true; font.pixelSize: 18 }
                TextField {
                    id: moduleName
                    Layout.fillWidth: true
                    placeholderText: "Module name"
                }
                ComboBox {
                    id: moduleType
                    Layout.fillWidth: true
                    model: fa3ModuleFactory.moduleTypes
                    textRole: "label"
                    valueRole: "id"
                }
                CheckBox {
                    id: aiEnabled
                    text: "AI access enabled for this function"
                    checked: false
                }

                RowLayout {
                    Button {
                        text: "Prepare governed plan"
                        onClicked: window.plan = fa3ModuleFactory.preparePlan(
                            moduleName.text, moduleType.currentValue,
                            window.artifactsAsArray(), aiEnabled.checked)
                    }
                    Button {
                        text: "Save draft"
                        enabled: window.plan.state === "DRAFT_REQUIRES_HUMAN_APPROVAL"
                        onClicked: fa3ModuleFactory.saveLastPlanDraft()
                    }
                    Item { Layout.fillWidth: true }
                }

                Frame {
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent
                        Label { text: "Guard state"; font.bold: true }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: window.plan.state || "No plan prepared"
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "No direct provider execution · no direct hardware selection · human approval required"
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: fa3ModuleFactory.lastDraftPath.length
                                  ? "Draft: " + fa3ModuleFactory.lastDraftPath : ""
                        }
                    }
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        text: JSON.stringify(window.plan, null, 2)
                    }
                }
            }
        }
    }
}
