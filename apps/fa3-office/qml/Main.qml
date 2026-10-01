// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1480
    height: 900
    minimumWidth: 1080
    minimumHeight: 680
    visible: true
    title: "FA3 — Office"

    property var sessionPlan: ({})
    property var runtimeState: ({})

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            Label { text: "FA3 Office"; font.bold: true; font.pixelSize: 19 }
            Label { text: "CAP-018 · FA3-DOC-001"; Layout.fillWidth: true }
            Label { text: fa3Office.fabricState; font.pixelSize: 10 }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Frame {
            SplitView.preferredWidth: 310
            ColumnLayout {
                anchors.fill: parent
                Label { text: "Workspace"; font.bold: true; font.pixelSize: 16 }
                ComboBox {
                    id: surface
                    Layout.fillWidth: true
                    model: fa3Office.surfaces()
                    textRole: "label"
                    valueRole: "id"
                }
                Label { text: "Format profile"; font.bold: true }
                ComboBox {
                    id: format
                    Layout.fillWidth: true
                    model: fa3Office.formatProfiles()
                    textRole: "id"
                    valueRole: "id"
                }
                CheckBox {
                    id: aiEnabled
                    text: "AI access enabled for this session"
                    checked: false
                }
                Button {
                    text: "Prepare governed session"
                    Layout.fillWidth: true
                    onClicked: root.sessionPlan = fa3Office.prepareSession(
                                   surface.currentValue, format.currentValue, aiEnabled.checked)
                }
                Button {
                    text: "Read-only LibreOffice probe"
                    Layout.fillWidth: true
                    onClicked: root.runtimeState = fa3Office.runtimeProbe()
                }
                Item { Layout.fillHeight: true }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "No LibreOffice process is started by this materialization. Runtime activation remains License & Rights + Current Host gated."
                }
            }
        }

        Item {
            SplitView.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label { text: "Office Fabric"; font.bold: true; font.pixelSize: 22 }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "LibreOffice Core / LibreOfficeKit / UNO is the approved primary engine candidate. FA3 keeps its own Qt6/QML surface and FA3-DOC-001 canonical document authority."
                }

                RowLayout {
                    Frame {
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Runtime"; font.bold: true }
                            Label { text: root.runtimeState.installed === true ? "LibreOffice discovered" : "Not probed / not discovered" }
                            Label { text: root.runtimeState.runtime_admission || "PENDING" }
                        }
                    }
                    Frame {
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Mutation"; font.bold: true }
                            Label { text: "Preview → explicit Apply → Undo" }
                            Label { text: "No silent fallback" }
                        }
                    }
                    Frame {
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Formats"; font.bold: true }
                            Label { text: "Editable candidates: ODT DOCX ODS XLSX ODP PPTX" }
                            Label { text: "PDF: preview/delivery only by default" }
                        }
                    }
                }

                GroupBox {
                    title: "Governed session plan"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ScrollView {
                        anchors.fill: parent
                        TextArea {
                            readOnly: true
                            wrapMode: TextEdit.Wrap
                            text: JSON.stringify(root.sessionPlan, null, 2)
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "Calligra UI/workflow donor and Collabora collaboration provider/donor remain PENDING_DONOR_INTAKE while #581 owns the exclusive donor-intake slot."
                }
            }
        }
    }
}
