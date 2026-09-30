import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1520
    height: 920
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    color: "#07111f"
    title: "FA3 — Humanizer"

    property var analysis: ({})
    property var comparison: ({})
    property var aiRequest: ({})

    header: ToolBar {
        background: Rectangle { color: "#0b1728" }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            Label { text: "FA3 Humanizer"; color: "#f5f8fc"; font.bold: true; font.pixelSize: 18 }
            Label { text: "CAP-125 · Humanization & Writing Quality"; color: "#8aa0b5"; Layout.fillWidth: true }
            Label { text: fa3Humanizer.fabricState; color: "#f0b14a"; font.pixelSize: 9; font.bold: true }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Item {
            SplitView.fillWidth: true
            SplitView.minimumWidth: 650

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Analyze"
                        onClicked: window.analysis = fa3Humanizer.analyzeText(sourceText.text)
                    }
                    Button {
                        text: "Safe normalize"
                        onClicked: candidateText.text = fa3Humanizer.safeNormalize(sourceText.text)
                    }
                    Button {
                        text: "Compare"
                        onClicked: window.comparison = fa3Humanizer.compareText(sourceText.text, candidateText.text)
                    }
                    Button {
                        text: "Prepare AI request"
                        onClicked: window.aiRequest = fa3Humanizer.buildAiRewriteRequest(sourceText.text)
                    }
                    Item { Layout.fillWidth: true }
                }

                SplitView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    orientation: Qt.Vertical

                    Frame {
                        SplitView.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Original"; font.bold: true }
                            TextArea {
                                id: sourceText
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                wrapMode: TextEdit.Wrap
                                placeholderText: "Paste or write text to analyze."
                                text: "Az FA3 Humanizer a jelentést és a védett adatokat megőrzi. 175 capability marad a kanonikus baseline. https://example.invalid [1]"
                            }
                        }
                    }

                    Frame {
                        SplitView.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Candidate"; font.bold: true }
                            TextArea {
                                id: candidateText
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                wrapMode: TextEdit.Wrap
                                placeholderText: "A deterministic candidate or an approved AI-routed candidate appears here."
                            }
                        }
                    }
                }

                Frame {
                    Layout.fillWidth: true
                    implicitHeight: 130
                    ColumnLayout {
                        anchors.fill: parent
                        Label { text: "Inspector"; font.bold: true }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Analysis: " + JSON.stringify(window.analysis)
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "Comparison: " + JSON.stringify(window.comparison)
                        }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "AI request: " + JSON.stringify(window.aiRequest)
                        }
                    }
                }
            }
        }

        HumanizerSettingsPanel {
            SplitView.preferredWidth: 430
            SplitView.minimumWidth: 360
            contextLabel: "FA3 HUMANIZER / SHARED"
            preferenceScope: "USER"
        }
    }
}
