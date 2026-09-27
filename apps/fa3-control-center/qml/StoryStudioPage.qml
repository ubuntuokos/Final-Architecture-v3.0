import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0b1728"
    property color panelRaised: "#10243a"
    property color border: "#18324f"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#91a6ba"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    signal stageActionIntentRequested(string actionId, string target, string rationale)

    property string productionProfile: "Feature Film"
    property string releasePolicy: "Single designated"
    property int workspaceIndex: 0

    property var productionProfiles: [
        "Feature Film", "TV Movie", "TV Series", "Commercial", "Live Broadcast",
        "Documentary", "News / Magazine", "Animation", "Audio Drama", "Stage Play",
        "Music Video", "Short-form", "Interactive", "Custom"
    ]

    property var workspaceTabs: [
        "Script", "Outline", "Story Branches", "Timeline", "Collaboration",
        "Rejected / Stash", "Writer Goals", "Interchange", "Production"
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "FA3 Story Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    text: "Egyetlen production-type-aware Story / Screenplay / Rundown alkalmazás"
                    color: root.textMuted
                    font.pixelSize: 10
                }
            }
            Label {
                text: "CAP-170 · 175 CAPABILITIES"
                color: root.green
                font.pixelSize: 8
                font.bold: true
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 64
            radius: 8
            color: root.panel
            border.color: root.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 14

                ColumnLayout {
                    spacing: 3
                    Label { text: "Production Profile"; color: root.textMuted; font.pixelSize: 8; font.bold: true }
                    ComboBox {
                        id: profileBox
                        Layout.preferredWidth: 220
                        model: root.productionProfiles
                        currentIndex: 0
                        onActivated: root.productionProfile = currentText
                    }
                }

                Rectangle { width: 1; Layout.fillHeight: true; color: root.border }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label { text: root.productionProfile; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                    Label {
                        text: root.productionProfile === "Commercial"
                              ? "Shot / Visual / Copy / Audio / Duration · 60/30/15/6s variánsok"
                              : root.productionProfile === "Live Broadcast"
                                ? "Rundown / Segment / Cue / Camera / Audio / Graphics / Planned vs Actual timing"
                                : root.productionProfile === "TV Series"
                                  ? "Series Bible / Season / Episode / A-B-C story / continuity"
                                  : "Canonical Story IR / Scene / Beat / Revision / Production handoff"
                        color: root.textMuted
                        font.pixelSize: 9
                    }
                }

                Button {
                    text: "Profile conversion"
                    onClicked: root.stageActionIntentRequested(
                        "story.profile.convert", root.productionProfile,
                        "Semantic profile conversion only; silent loss forbidden.")
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            contentWidth: tabRow.implicitWidth
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AsNeeded

            RowLayout {
                id: tabRow
                spacing: 6
                Repeater {
                    model: root.workspaceTabs
                    delegate: Button {
                        required property string modelData
                        required property int index
                        text: modelData
                        checkable: true
                        checked: root.workspaceIndex === index
                        onClicked: root.workspaceIndex = index
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.workspaceIndex

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Script"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: "Screenplay semantics · scene headings · dialogue · action · production revisions · locked pages · AI notes elkülönítve."
                        color: root.textMuted; wrapMode: Text.WordWrap
                    }
                    TextArea {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        placeholderText: "INT. LOCATION — DAY\n\nAction...\n\nCHARACTER\nDialogue..."
                        color: root.textPrimary
                        wrapMode: TextEdit.Wrap
                        background: Rectangle { color: root.panelRaised; radius: 7; border.color: root.border }
                    }
                    RowLayout {
                        CheckBox { text: "Midnight"; checked: true }
                        CheckBox { text: "Typewriter"; checked: false }
                        CheckBox { text: "Focus"; checked: false }
                        Item { Layout.fillWidth: true }
                        Button { text: "Revision diff" }
                    }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Outline / Beat Board"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label { text: "Act · Sequence · Scene · Beat · Storyline · Series/Season Bible"; color: root.textMuted }
                    Repeater {
                        model: ["ACT I — Setup", "SEQUENCE 2 — Escalation", "SCENE 14 — Turning point", "BEAT — Decision"]
                        delegate: Rectangle {
                            required property string modelData
                            Layout.fillWidth: true; implicitHeight: 52; radius: 6; color: root.panelRaised; border.color: root.border
                            Label { anchors.centerIn: parent; text: modelData; color: root.textPrimary }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Story Branches"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label {
                        text: "Main → A → A1 / A2 · tetszőleges mélység · compare / selective merge / promote-to-main"
                        color: root.textMuted
                    }
                    RowLayout {
                        Repeater {
                            model: ["MAIN", "ALT A", "ALT A1", "ALT B"]
                            delegate: Rectangle {
                                required property string modelData
                                width: 130; height: 64; radius: 8; color: root.panelRaised; border.color: root.accent
                                Label { anchors.centerIn: parent; text: modelData; color: root.textPrimary; font.bold: true }
                            }
                        }
                    }
                    Button {
                        text: "+ Új branch"
                        onClicked: root.stageActionIntentRequested(
                            "story.branch.create", "current-story-node",
                            "Create a new narrative branch without deleting the source branch.")
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Timeline / Pacing"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label { text: "Story timing, screenplay length, commercial duration, live planned/actual timing."; color: root.textMuted }
                    ProgressBar { Layout.fillWidth: true; value: 0.62 }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Collaboration"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label {
                        text: "Több szerző szerkesztheti ugyanazt a forgatókönyvet. Minden módosítás szerzőhöz és revízióhoz kötött."
                        color: root.textMuted; wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: [
                            {name:"Writer A", role:"OWNER · AUTHOR · FINAL_PUBLISHER"},
                            {name:"Writer B", role:"AUTHOR"},
                            {name:"Script Editor", role:"EDITOR · COMMENTER"}
                        ]
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: 52; radius: 6; color: root.panelRaised; border.color: root.border
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 10
                                Label { text: modelData.name; color: root.textPrimary; font.bold: true; Layout.fillWidth: true }
                                Label { text: modelData.role; color: root.accent; font.pixelSize: 9 }
                            }
                        }
                    }
                    RowLayout {
                        Label { text: "Final Publisher"; color: root.textPrimary; font.bold: true }
                        ComboBox { model: ["Writer A"]; Layout.preferredWidth: 180 }
                        ComboBox {
                            model: ["Single designated", "Any designated", "All designated"]
                            Layout.preferredWidth: 180
                            onActivated: root.releasePolicy = currentText
                        }
                        Button {
                            text: "Final kiadás"
                            onClicked: root.stageActionIntentRequested(
                                "story.release.final", "current-revision",
                                "Final release requires a designated Final Publisher and immutable release receipt.")
                        }
                    }
                    Label {
                        text: "A nem kijelölt szerző szerkeszthet, de FINAL változatot nem adhat ki."
                        color: root.orange; font.pixelSize: 9
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Rejected / Stash"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label {
                        text: "Az elvetett jelenet, beat, dialógus vagy teljes branch alapértelmezetten nem törlődik."
                        color: root.textMuted; wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: ["Elvetett befejezés · Scene 42", "Korábbi dialógusváltozat · Scene 18"]
                        delegate: Rectangle {
                            required property string modelData
                            Layout.fillWidth: true; implicitHeight: 56; radius: 6; color: root.panelRaised; border.color: root.border
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 10
                                Label { text: modelData; color: root.textPrimary; Layout.fillWidth: true }
                                Button {
                                    text: "Mentés jegyzetbe"
                                    onClicked: root.stageActionIntentRequested(
                                        "story.stash.save-note", modelData,
                                        "Materialize rejected content as a separate note with source and revision lineage.")
                                }
                            }
                        }
                    }
                    Label {
                        text: "A jegyzet külön dokumentumként is exportálható; source document/range/revision/author lineage megmarad."
                        color: root.green; font.pixelSize: 9; wrapMode: Text.WordWrap
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Writer Goals"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    RowLayout {
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: 86; radius: 6; color: root.panelRaised
                            ColumnLayout {
                                anchors.centerIn: parent
                                Label { text: "1 087 / 1 500 szó"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                                Label { text: "72.5% napi cél"; color: root.green }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: 86; radius: 6; color: root.panelRaised
                            ColumnLayout {
                                anchors.centerIn: parent
                                Label { text: "25:00"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                                Label { text: "Sprint timer"; color: root.accent }
                            }
                        }
                    }
                    Label { text: "Statistics · words · pages · scenes · dialogue · locations · branch metrics · active writing time"; color: root.textMuted; wrapMode: Text.WordWrap }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Interchange"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label {
                        text: "Import ⇄ Export symmetry: FDX · Fountain · PDF · TXT · RTF · HTML · Microsoft Office · LibreOffice · OpenOffice · WPS · ONLYOFFICE"
                        color: root.textMuted; wrapMode: Text.WordWrap
                    }
                    Label {
                        text: "Minden admitted import codec ugyanabba a fájltípusba exportál is. Round-trip gate és loss report kötelező."
                        color: root.green; wrapMode: Text.WordWrap
                    }
                    RowLayout {
                        Button { text: "Import…" }
                        Button { text: "Export…" }
                        Button { text: "Round-trip report" }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Rectangle {
                color: root.panel; radius: 8; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { text: "Production"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                    Label {
                        text: "Breakdown · Sides · Shot planning · Storyboard · Scheduling · Budget handoff · Table Read · Audio read export"
                        color: root.textMuted; wrapMode: Text.WordWrap
                    }
                    Label {
                        text: "AI/provider munka csak Model Router → HRB útvonalon; ez a felület nem execution authority."
                        color: root.orange; wrapMode: Text.WordWrap
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
