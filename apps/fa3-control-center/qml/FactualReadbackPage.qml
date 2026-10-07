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
    property color magenta: "#b778ff"

    // Supplied by the Control Center binding when the reconciled GUI head is available.
    property var readbackRecord: ({
        taskScope: "UNBOUND",
        sourceSet: [],
        sourcePriority: "LIVE STATE → CANONICAL REPOSITORY → OWNER DIRECTIVE → RETRIEVED PRIOR SOURCE",
        readbackStatus: "UNKNOWN",
        reanalysisStatus: "UNKNOWN",
        currentStateVerification: "UNKNOWN",
        contradictions: [],
        unknownFacts: [],
        scopeGuardResult: "UNKNOWN",
        continuationDecision: "BLOCKER_STOP"
    })

    readonly property bool continuationAllowed: readbackRecord.continuationDecision === "ALLOW_CONTINUATION"

    component Card: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    component StateBadge: Label {
        property string stateText: "UNKNOWN"
        text: stateText
        color: stateText === "PASS" || stateText === "VERIFIED" || stateText === "ALLOW_CONTINUATION"
               ? root.green
               : stateText === "BLOCKER_STOP" || stateText === "FAIL"
                 ? root.magenta
                 : root.orange
        font.pixelSize: 9
        font.bold: true
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 14

            Item { Layout.preferredHeight: 8 }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18

                Label {
                    text: "Fact Readback"
                    color: root.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                }
                Label {
                    text: "CFA3-FACTUAL-READBACK-CONTINUITY-POLICY-001"
                    color: root.cyan
                    font.pixelSize: 10
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    text: "Korábbi feladat, terv vagy állapot csak tényszerű visszaolvasás, újraelemzés és aktuális állapot-ellenőrzés után folytatható. Az emlékezet keresési támpont, nem bizonyíték."
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                columns: root.width > 1150 ? 4 : 2
                columnSpacing: 10
                rowSpacing: 10

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 116
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: "Readback"; color: root.textPrimary; font.bold: true }
                        StateBadge { stateText: readbackRecord.readbackStatus || "UNKNOWN" }
                        Label {
                            Layout.fillWidth: true
                            text: "Primary/retrieved sources ténylegesen visszaolvasva."
                            color: root.textMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 116
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: "Re-analysis"; color: root.textPrimary; font.bold: true }
                        StateBadge { stateText: readbackRecord.reanalysisStatus || "UNKNOWN" }
                        Label {
                            Layout.fillWidth: true
                            text: "A visszaolvasott állapot újraértékelve; terv ≠ végrehajtott tény."
                            color: root.textMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 116
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: "Current state"; color: root.textPrimary; font.bold: true }
                        StateBadge { stateText: readbackRecord.currentStateVerification || "UNKNOWN" }
                        Label {
                            Layout.fillWidth: true
                            text: "Aktuális authoritative/determinisztikus állapot ellenőrizve."
                            color: root.textMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 116
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        Label { text: "Decision"; color: root.textPrimary; font.bold: true }
                        StateBadge { stateText: readbackRecord.continuationDecision || "BLOCKER_STOP" }
                        Label {
                            Layout.fillWidth: true
                            text: root.continuationAllowed
                                  ? "A readback governance preflight PASS. Ez nem effect authority."
                                  : "A folytatás fail-closed módon blokkolt."
                            color: root.textMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 140
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    Label { text: "Task scope"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: readbackRecord.taskScope || "UNBOUND"
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        font.pixelSize: 10
                    }
                    Label { text: "Scope Guard"; color: root.textPrimary; font.bold: true }
                    StateBadge { stateText: readbackRecord.scopeGuardResult || "UNKNOWN" }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 190
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    Label { text: "Source set"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: readbackRecord.sourcePriority || ""
                        color: root.cyan
                        wrapMode: Text.WordWrap
                        font.pixelSize: 9
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: readbackRecord.sourceSet || []
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            height: 34
                            contentItem: Label {
                                text: modelData
                                color: root.textMuted
                                font.family: "monospace"
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                spacing: 10

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 170
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        Label { text: "Contradictions"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label {
                            text: (readbackRecord.contradictions || []).length === 0
                                  ? "Nincs unresolved contradiction."
                                  : (readbackRecord.contradictions || []).length + " contradiction"
                            color: (readbackRecord.contradictions || []).length === 0 ? root.green : root.magenta
                            font.pixelSize: 9
                            font.bold: true
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "Unresolved contradiction esetén a döntés kötelezően BLOCKER_STOP."
                            color: root.textMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                        }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 170
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        Label { text: "Unknown facts"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label {
                            text: (readbackRecord.unknownFacts || []).length === 0
                                  ? "Nincs ismeretlen tény."
                                  : (readbackRecord.unknownFacts || []).length + " unknown fact"
                            color: (readbackRecord.unknownFacts || []).length === 0 ? root.green : root.orange
                            font.pixelSize: 9
                            font.bold: true
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "UNKNOWN nem tölthető ki emlékezetből vagy korábbi AI-állításból."
                            color: root.textMuted
                            wrapMode: Text.WordWrap
                            font.pixelSize: 9
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                text: "Readback PASS ≠ security/effect/workflow/model/resource/merge/release authorization."
                color: root.orange
                font.pixelSize: 9
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Item { Layout.preferredHeight: 18 }
        }
    }
}
