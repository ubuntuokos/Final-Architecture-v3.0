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

    property int selectedIndex: 7
    property var modules: [
        {title: "Image", badge: "READY", tone: root.magenta, summary: "ComfyUI / InvokeAI / editor bridge projection.", actions: ["Generate és edit pipeline", "Krita / GIMP bridge", "Model- és workflow-választás", "Artifact provenance"]},
        {title: "Video", badge: "READY", tone: root.accent, summary: "Generation, compositing és editorial workflow.", actions: ["Video generation", "Kdenlive editorial", "OpenFX / LUT pipeline", "Render és export handoff"]},
        {title: "Animation", badge: "READY", tone: root.cyan, summary: "Motion, character és timeline workflow-k.", actions: ["Character motion", "Timeline workflow", "Asset handoff", "Preview és render"]},
        {title: "3D / VFX", badge: "READY", tone: root.orange, summary: "Geometry, Bforartist/Blender, Natron/Gaffer kapcsolatok.", actions: ["Geometry / mesh", "DCC bridge", "Compositing", "Scene és artifact provenance"]},
        {title: "Audio", badge: "READY", tone: root.green, summary: "STT, TTS, restoration, separation és voice fabric.", actions: ["Speech-to-text", "Text-to-speech", "Restoration / separation", "Voice workflow"]},
        {title: "Music", badge: "READY", tone: root.magenta, summary: "Music generation, stems, DAW és mastering workflow-k.", actions: ["Generation", "Stem separation", "DAW handoff", "Mastering"]},
        {title: "Story / Screenplay", badge: "READY", tone: root.accent, summary: "FA3 Story profile és production-context projection.", actions: ["Story planning", "Screenplay structure", "Scene breakdown", "Production handoff"]},
        {title: "Office", badge: "UNO", tone: root.cyan, summary: "Writer, Calc és Impress AI-réteg Preview → explicit Apply / Undo folyamattal.", actions: ["Writer · Rewrite · Summarize · Translate · Explain · Continue text · Review", "Calc · Formula · Table analysis · Formula explanation · Data-cleaning plan", "Impress · Slide outline · Slide rewrite · Speaker notes", "Selection/context → proposal → Preview → explicit Apply/UNO mutation → Undo"]},
        {title: "Marketing", badge: "PUBLISH", tone: root.orange, summary: "Kampány-, tartalom- és publikációs workflow-k.", actions: ["Campaign planning", "Content generation", "Mautic / Twenty / listmonk projection", "Approval és publication handoff"]},
        {title: "Weboldal", badge: "PUBLISH", tone: root.cyan, summary: "Webes publikáció, preview és deployment workflow-k.", actions: ["Page/content planning", "Preview", "Asset handoff", "Controlled deployment"]},
        {title: "Prezentáció", badge: "PUBLISH", tone: root.green, summary: "Prezentációk készítése, exportja és publikációs átadása.", actions: ["Deck outline", "Slide generation", "Speaker notes", "Export és handoff"]}
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 13

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: "AI Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
            Label { text: "Kreatív, Office és publikációs rétegek — kattints egy rétegre a részletekhez"; color: root.textMuted; font.pixelSize: 11 }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            ScrollView {
                id: moduleScroll
                Layout.preferredWidth: Math.min(590, root.width * 0.52)
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ScrollBar.vertical.policy: ScrollBar.AlwaysOn

                Flow {
                    width: moduleScroll.availableWidth - 8
                    spacing: 10

                    Repeater {
                        model: root.modules
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: Math.max(220, (moduleScroll.availableWidth - 30) / 2)
                            height: 112
                            radius: 9
                            color: index === root.selectedIndex ? root.panelRaised : (cardMouse.containsMouse ? "#10233a" : root.panel)
                            border.color: index === root.selectedIndex ? modelData.tone : root.border
                            border.width: index === root.selectedIndex ? 2 : 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 13
                                spacing: 7
                                RowLayout {
                                    Layout.fillWidth: true
                                    Rectangle { width: 8; height: 8; radius: 4; color: modelData.tone }
                                    Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                                    Label { text: modelData.badge; color: modelData.tone; font.pixelSize: 8; font.bold: true }
                                }
                                Label { text: modelData.summary; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.fillHeight: true }
                                Label { text: index === root.selectedIndex ? "RÉSZLETEK MEGNYITVA" : "Kattints a részletekhez"; color: index === root.selectedIndex ? modelData.tone : root.textMuted; font.pixelSize: 8; font.bold: true }
                            }

                            MouseArea {
                                id: cardMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedIndex = index
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 390
                radius: 9
                color: root.panel
                border.color: root.modules[root.selectedIndex].tone
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { width: 10; height: 10; radius: 5; color: root.modules[root.selectedIndex].tone }
                        Label { text: root.modules[root.selectedIndex].title; color: root.textPrimary; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true }
                        Label { text: root.modules[root.selectedIndex].badge; color: root.modules[root.selectedIndex].tone; font.pixelSize: 9; font.bold: true }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: root.modules[root.selectedIndex].summary
                        color: root.textMuted
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                    Label { text: "Elérhető felületek / műveletek"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }

                    Repeater {
                        model: root.modules[root.selectedIndex].actions
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: actionText.implicitHeight + 20
                            radius: 6
                            color: root.panelRaised
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                Label { text: "›"; color: root.modules[root.selectedIndex].tone; font.pixelSize: 14; font.bold: true }
                                Label { id: actionText; text: modelData; color: root.textPrimary; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: noteText.implicitHeight + 22
                        radius: 6
                        color: "#091624"
                        border.color: root.border
                        Label {
                            id: noteText
                            anchors.fill: parent
                            anchors.margins: 11
                            text: root.modules[root.selectedIndex].title === "Office"
                                ? "Office authority: a LibreOffice/UNO módosítás csak Preview után, explicit Apply lépéssel történhet; közvetlen dokumentummódosítás nincs."
                                : "Ez a panel az FA3 munkafelületét választja ki; végrehajtás csak a megfelelő provider/adapter és approval-határ szerint történhet."
                            color: root.textMuted
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
