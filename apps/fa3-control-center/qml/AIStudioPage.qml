import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property var repository
    required property color surface1
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
        { key: "marketing", title: "Marketing AI Studio", subtitle: "FA3-MARKETING-001 · Mautic / Twenty / listmonk", badge: "P0" },
        { key: "website", title: t("Weboldalkészítés AI Studio", "Website AI Studio"), subtitle: t("Weboldal-struktúra, tartalom, design és publikálási workflow", "Website structure, content, design and publishing workflow"), badge: "STUDIO" },
        { key: "presentation", title: t("Prezentáció AI Studio", "Presentation AI Studio"), subtitle: "FA3-PROVIDER-PRESENTON-001 · presentation generation/edit/export", badge: "PROVIDER" },
        { key: "image", title: "Image", subtitle: "ComfyUI / InvokeAI / GIMP / Krita", badge: "MEDIA" },
        { key: "video", title: "Video", subtitle: "Generation / Kdenlive / OpenShot / editorial", badge: "MEDIA" },
        { key: "animation", title: "Animation", subtitle: "OpenToonz / Krita / Synfig Studio / motion / character", badge: "MEDIA" },
        { key: "3d", title: "3D / VFX", subtitle: "Geometry / Blender / Bforartist / Natron / Gaffer", badge: "MEDIA" },
        { key: "audio", title: "Audio", subtitle: "Ardour / Audacity / STT / TTS / restoration", badge: "MEDIA" },
        { key: "music", title: "Music", subtitle: "Generation / stems / DAW / mastering", badge: "MEDIA" },
        { key: "story", title: "Story / Screenplay", subtitle: "FA3 Story production context", badge: "STORY" }
    ]

    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 16
        Item { Layout.preferredHeight: 10 }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            text: "AI Studio"
            font.pixelSize: root.px(24)
            font.bold: true
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            text: root.t("Kreatív, marketing-, web- és prezentációs munkaterületek egyetlen FA3 Studio felületen.", "Creative, marketing, web and presentation workspaces on one FA3 Studio surface.")
            color: root.textMuted
            wrapMode: Text.WordWrap
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
                    width: Math.max(250, Math.min(330, (root.availableWidth - 80) / 3))
                    height: 142
                    radius: Math.round(11 * root.uiScale)
                    color: root.selectedStudio === modelData.key ? Qt.lighter(root.surface1, 1.08) : root.surface1
                    border.color: root.selectedStudio === modelData.key ? root.accent : Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

                    MouseArea { anchors.fill: parent; onClicked: root.selectedStudio = modelData.key }
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Label { Layout.fillWidth: true; text: modelData.title; font.pixelSize: root.px(16); font.bold: true; wrapMode: Text.WordWrap }
                            Label { text: modelData.badge; color: root.accent; font.bold: true; font.pixelSize: root.px(10) }
                        }
                        Label { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData.subtitle; color: root.textMuted; wrapMode: Text.WordWrap }
                        Label { text: root.t("Részletek", "Details") + " →"; color: root.accent }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            Layout.preferredHeight: detailColumn.implicitHeight + 30
            radius: Math.round(11 * root.uiScale)
            color: root.surface1

            ColumnLayout {
                id: detailColumn
                anchors.fill: parent
                anchors.margins: 15
                spacing: 8
                Label {
                    Layout.fillWidth: true
                    font.pixelSize: root.px(18)
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
                    text: root.selectedStudio === "marketing" ? root.t("Hungarian-first marketing workflow: kutatás → stratégia → natív HU tartalom → quality/policy gate → HITL → Mautic/Twenty/listmonk végrehajtás → attribution/evidence. A marketing provider nem válik új authority-vé.", "Hungarian-first marketing workflow: research → strategy → native HU content → quality/policy gate → HITL → Mautic/Twenty/listmonk execution → attribution/evidence. Marketing providers do not become new authorities.") :
                          root.selectedStudio === "website" ? root.t("Önálló Studio-terület weboldalak tervezéséhez és előállításához. Nem olvad össze a Marketing AI Studio-val; a publikálás és külső műveletek meglévő FA3 approval/publishing authority-kon keresztül mennek.", "Dedicated Studio area for website planning and creation. It remains distinct from Marketing AI Studio; publishing and external actions route through existing FA3 approval/publishing authorities.") :
                          root.selectedStudio === "presentation" ? root.t("Prezentáció-készítési felület. A Presenton opcionális, self-hosted worker/provider; nem identity, workflow, model-routing vagy evidence authority. LibreOffice/Impress és más exportutak a meglévő dokumentum/media rétegen keresztül használhatók.", "Presentation creation surface. Presenton is an optional self-hosted worker/provider; it is not an identity, workflow, model-routing or evidence authority. LibreOffice/Impress and other export paths remain under existing document/media layers.") :
                          root.t("Az adott kreatív terület a meglévő FA3 capability-ket és provider-adaptereket vetíti ki; nem hoz létre új authorityt.", "This creative area projects existing FA3 capabilities and provider adapters; it creates no new authority.")
                }
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
        Item { Layout.preferredHeight: 22 }
    }
}
