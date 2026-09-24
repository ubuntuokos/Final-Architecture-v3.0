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
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    property string operationNotice: ""

    signal stageActionIntentRequested(string actionId, string target, string rationale)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true
                Label {
                    text: "FA3 Tools"
                    color: root.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                }
                Label {
                    text: "Feladatorientált utility surface · UAF DRAFT ONLY · provider-választás és végrehajtás nem GUI authority"
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }

            Rectangle {
                radius: 7
                implicitWidth: 170
                implicitHeight: 28
                color: root.panelRaised
                border.color: root.accent
                Label {
                    anchors.centerIn: parent
                    text: "TOOLS · DRAFT ONLY"
                    color: root.accent
                    font.pixelSize: 9
                    font.bold: true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            TextField {
                id: inputRef
                Layout.fillWidth: true
                placeholderText: "Helyi input referencia"
            }
            TextField {
                id: inputMime
                Layout.preferredWidth: 220
                placeholderText: "Forrás MIME, pl. image/png"
            }
            TextField {
                id: outputMime
                Layout.preferredWidth: 220
                placeholderText: "Cél MIME, pl. image/jpeg"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: "Konverziós terv készítése"
                enabled: inputRef.text.length > 0 && inputMime.text.length > 0 && outputMime.text.length > 0
                onClicked: root.stageActionIntentRequested(
                    "file.convert.plan",
                    inputRef.text + "|" + inputMime.text + "->" + outputMime.text,
                    "DRAFT_NOT_SUBMITTED: provider-neutral conversion plan; specialized-provider-first routing remains authoritative."
                )
            }

            Button {
                text: "Végrehajtási tervezet"
                enabled: inputRef.text.length > 0 && inputMime.text.length > 0 && outputMime.text.length > 0
                onClicked: root.stageActionIntentRequested(
                    "file.convert.execute",
                    inputRef.text + "|" + inputMime.text + "->" + outputMime.text,
                    "DRAFT_NOT_SUBMITTED: no execution occurs here; UAF authorization, HRB admission, provider admission and evidence remain mandatory."
                )
            }

            Item { Layout.fillWidth: true }

            Label {
                text: "Nincs közvetlen provider indítás"
                color: root.orange
                font.pixelSize: 9
                font.bold: true
            }
        }

        Label {
            visible: root.operationNotice.length > 0
            Layout.fillWidth: true
            text: root.operationNotice
            color: root.accent
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 12
            rowSpacing: 10

            ToolCard {
                title: "Konvertálás"
                subtitle: "Dokumentum, kép, hang, videó és 3D hosszúfarkú konverzió. A specializált FA3 provider mindig elsőbbséget élvez."
                badge: "FA3-FILE-CONVERSION-001"
                tone: root.accent
                detail: "ConvertX · P2 · QUARANTINED · USER_LOCAL_EXTERNAL · XeLaTeX DENY"
                warning: true
            }
            ToolCard {
                title: "Digitalizálás"
                subtitle: "Capture és ingest külön canonical útvonalon marad; a Tools csak feladatszintű projekció."
                badge: "DIGITALIZATION"
                tone: root.green
            }
            ToolCard {
                title: "Archiválás és mentés"
                subtitle: "Tömörítés, kibontás, backup és snapshot műveletek a saját canonical profiljaikon keresztül."
                badge: "ARCHIVE"
                tone: root.orange
            }
            ToolCard {
                title: "Fájlműveletek"
                subtitle: "Hash, integritás, metadata és duplikátum-kezelés provider-semleges intentként."
                badge: "UTILITY"
                tone: root.magenta
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 108
            radius: 8
            color: root.panel
            border.color: root.orange

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 5

                Label {
                    text: "ConvertX runtime: QUARANTINED / PENDING_CURRENT_HOST"
                    color: root.orange
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    text: "A jelenlegi HRB current-host bootstrap még nem materializál non-accelerator CPU/memória authorizationt. A ConvertX ezért nem production-routable; candidate validation sem jelent promotiont."
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                }
                Label {
                    Layout.fillWidth: true
                    text: "Upstream runtime: USER_LOCAL_EXTERNAL, FA3 release bundle: EXCLUDED."
                    color: root.textMuted
                    font.pixelSize: 9
                }
            }
        }

        Item { Layout.fillHeight: true }
    }

    component ToolCard: Rectangle {
        required property string title
        required property string subtitle
        required property string badge
        required property color tone
        property string detail: ""
        property bool warning: false

        Layout.fillWidth: true
        Layout.preferredHeight: detail.length > 0 ? 138 : 118
        radius: 8
        color: root.panel
        border.color: warning ? root.orange : root.border

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 5

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: title
                    color: root.textPrimary
                    font.bold: true
                    Layout.fillWidth: true
                }
                Label {
                    text: badge
                    color: tone
                    font.pixelSize: 8
                    font.bold: true
                }
            }
            Label {
                Layout.fillWidth: true
                text: subtitle
                color: root.textMuted
                wrapMode: Text.WordWrap
                font.pixelSize: 9
            }
            Label {
                visible: detail.length > 0
                Layout.fillWidth: true
                text: detail
                color: warning ? root.orange : root.textMuted
                wrapMode: Text.WordWrap
                font.pixelSize: 9
            }
            Item { Layout.fillHeight: true }
        }
    }
}
