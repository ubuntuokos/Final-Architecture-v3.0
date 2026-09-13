import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property var repository
    required property color surface0
    required property color surface1
    required property color surface2
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    property string selectedStudio: "marketing"
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    property var studios: [
        { key: "marketing", glyph: "MKT", title: "Marketing AI Studio", subtitle: "FA3-MARKETING-001 · Mautic / Twenty / listmonk", badge: "P0" },
        { key: "website", glyph: "WEB", title: t("Weboldalkészítés AI Studio", "Website AI Studio"), subtitle: t("Struktúra · tartalom · design · publikálás", "Structure · content · design · publishing"), badge: "STUDIO" },
        { key: "presentation", glyph: "DECK", title: t("Prezentáció AI Studio", "Presentation AI Studio"), subtitle: "Presenton · LibreOffice/Impress · export", badge: "PROVIDER" },
        { key: "image", glyph: "IMG", title: "Image", subtitle: "ComfyUI · InvokeAI · GIMP · Krita", badge: "MEDIA" },
        { key: "video", glyph: "VID", title: "Video", subtitle: "Generation · Kdenlive · OpenShot · editorial", badge: "MEDIA" },
        { key: "animation", glyph: "ANI", title: "Animation", subtitle: "OpenToonz · Krita · Synfig Studio", badge: "MEDIA" },
        { key: "3d", glyph: "3D", title: "3D / VFX", subtitle: "Blender · Bforartist · Natron · Gaffer", badge: "MEDIA" },
        { key: "audio", glyph: "AUD", title: "Audio", subtitle: "Ardour · Audacity · STT · TTS · restoration", badge: "MEDIA" },
        { key: "music", glyph: "MUS", title: "Music", subtitle: "Generation · stems · DAW · mastering", badge: "MEDIA" },
        { key: "story", glyph: "TXT", title: "Story / Screenplay", subtitle: "FA3 Story production context", badge: "STORY" }
    ]

    contentWidth: availableWidth
    background: Rectangle { color: "transparent" }

    ColumnLayout {
        width: root.availableWidth
        spacing: Math.round(16 * root.uiScale)

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            Layout.topMargin: 18
            Layout.preferredHeight: Math.max(118, hero.implicitHeight + 34)
            radius: Math.round(16 * root.uiScale)
            color: root.surface1
            border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.26)

            Rectangle {
                width: 4
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                radius: 2
                color: root.accent
            }

            RowLayout {
                id: hero
                anchors.fill: parent
                anchors.margins: 20
                spacing: 18
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Label { text: "FA3 / AI STUDIO"; color: root.accent; font.pixelSize: root.px(10); font.bold: true; font.letterSpacing: 1.4 }
                    Label { text: root.t("Kreatív vezérlőközpont", "Creative Mission Control"); font.pixelSize: root.px(26); font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: root.t("Kreatív, marketing-, web- és prezentációs munkaterületek közös operátori felülete.", "Unified operator surface for creative, marketing, web and presentation workspaces.")
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                    }
                }
                Rectangle {
                    Layout.preferredWidth: 138
                    Layout.preferredHeight: 62
                    radius: 10
                    color: root.surface2
                    border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.08)
                    Column {
                        anchors.centerIn: parent
                        spacing: 2
                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: root.studios.length + " STUDIO"; color: root.accent; font.bold: true }
                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: "143 CAPABILITIES"; color: root.textMuted; font.pixelSize: root.px(9) }
                    }
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            spacing: 12

            Repeater {
                model: root.studios
                delegate: Rectangle {
                    required property var modelData
                    width: root.availableWidth < 900 ? Math.max(260, root.availableWidth - 48) :
                           root.availableWidth < 1320 ? Math.max(280, (root.availableWidth - 68) / 2) :
                           Math.max(280, (root.availableWidth - 92) / 3)
                    height: 156
                    radius: Math.round(14 * root.uiScale)
                    color: root.selectedStudio === modelData.key ? Qt.lighter(root.surface1, 1.10) : root.surface1
                    border.color: root.selectedStudio === modelData.key ? root.accent : Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
                    border.width: root.selectedStudio === modelData.key ? 2 : 1

                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: 3
                        radius: 2
                        color: root.selectedStudio === modelData.key ? root.accent : Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.26)
                    }

                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.selectedStudio = modelData.key }
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle {
                                Layout.preferredWidth: 48
                                Layout.preferredHeight: 32
                                radius: 7
                                color: root.surface2
                                Label { anchors.centerIn: parent; text: modelData.glyph; color: root.accent; font.bold: true; font.pixelSize: root.px(9) }
                            }
                            Item { Layout.fillWidth: true }
                            Label { text: modelData.badge; color: root.accent; font.bold: true; font.pixelSize: root.px(9); font.letterSpacing: 0.7 }
                        }
                        Label { Layout.fillWidth: true; text: modelData.title; font.pixelSize: root.px(16); font.bold: true; wrapMode: Text.WordWrap }
                        Label { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData.subtitle; color: root.textMuted; wrapMode: Text.WordWrap }
                        Label { text: root.t("Munkaterület megnyitása", "Open workspace") + "  →"; color: root.accent; font.bold: root.selectedStudio === modelData.key }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            Layout.preferredHeight: detailColumn.implicitHeight + 38
            radius: Math.round(14 * root.uiScale)
            color: root.surface1
            border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

            ColumnLayout {
                id: detailColumn
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "ACTIVE WORKSPACE"; color: root.accent; font.pixelSize: root.px(9); font.bold: true; font.letterSpacing: 1.2 }
                    Item { Layout.fillWidth: true }
                    Label { text: "READ / PROPOSE / GATED EXECUTION"; color: root.textMuted; font.pixelSize: root.px(9) }
                }
                Label {
                    Layout.fillWidth: true
                    font.pixelSize: root.px(20)
                    font.bold: true
                    text: root.selectedStudio === "marketing" ? "Marketing AI Studio" :
                          root.selectedStudio === "website" ? root.t("Weboldalkészítés AI Studio", "Website AI Studio") :
                          root.selectedStudio === "presentation" ? root.t("Prezentáció AI Studio", "Presentation AI Studio") :
                          root.studios.find(function(x) { return x.key === root.selectedStudio }).title
                }
                Label {
                    Layout.fillWidth: true
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                    text: root.selectedStudio === "marketing" ? root.t("Hungarian-first marketing workflow: kutatás → stratégia → natív HU tartalom → quality/policy gate → HITL → Mautic/Twenty/listmonk végrehajtás → attribution/evidence.", "Hungarian-first marketing workflow: research → strategy → native HU content → quality/policy gate → HITL → Mautic/Twenty/listmonk execution → attribution/evidence.") :
                          root.selectedStudio === "website" ? root.t("Önálló weboldal-tervezési és -előállítási munkaterület. A publikálás és külső műveletek a meglévő FA3 approval/publishing authority-kon keresztül mennek.", "Dedicated website planning and creation workspace. Publishing and external actions route through existing FA3 approval/publishing authorities.") :
                          root.selectedStudio === "presentation" ? root.t("Prezentáció-készítési munkaterület Presenton és dokumentum/media provider projectionnel; nincs új identity, workflow, model-routing vagy evidence authority.", "Presentation workspace with Presenton and document/media provider projection; no new identity, workflow, model-routing or evidence authority.") :
                          root.t("A kiválasztott kreatív terület a meglévő FA3 capability-ket és provider-adaptereket vetíti ki.", "The selected creative area projects existing FA3 capabilities and provider adapters.")
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Rectangle { Layout.preferredWidth: 130; Layout.preferredHeight: 30; radius: 7; color: root.surface2; Label { anchors.centerIn: parent; text: "CANONICAL BOUND"; color: root.textMuted; font.pixelSize: root.px(9); font.bold: true } }
                    Rectangle { Layout.preferredWidth: 130; Layout.preferredHeight: 30; radius: 7; color: root.surface2; Label { anchors.centerIn: parent; text: "EVIDENCE AWARE"; color: root.textMuted; font.pixelSize: root.px(9); font.bold: true } }
                    Item { Layout.fillWidth: true }
                    Label {
                        visible: root.selectedStudio === "marketing"
                        text: root.repository.searchRecords("FA3-MARKETING-001").length > 0 ? "FA3-MARKETING-001 · CANONICAL" : "FA3-MARKETING-001 · MISSING"
                        color: root.accent
                        font.bold: true
                    }
                    Label {
                        visible: root.selectedStudio === "presentation"
                        text: root.repository.searchRecords("FA3-PROVIDER-PRESENTON-001").length > 0 ? "FA3-PROVIDER-PRESENTON-001 · AVAILABLE" : "FA3-PROVIDER-PRESENTON-001 · MISSING"
                        color: root.accent
                        font.bold: true
                    }
                }
            }
        }
        Item { Layout.preferredHeight: 24 }
    }
}
