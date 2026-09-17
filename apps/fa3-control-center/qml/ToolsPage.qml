import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property color panel
    required property color panelRaised
    required property color border
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property color cyan
    required property color green
    required property color orange
    required property color magenta

    clip: true
    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        spacing: 14

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Label {
                text: "Tools"
                color: root.textPrimary
                font.pixelSize: 28
                font.bold: true
            }
            Label {
                text: "Feladatorientált segédeszközök · canonical admission és provider routing mögött"
                color: root.textMuted
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 74
            radius: 8
            color: root.panelRaised
            border.color: root.border
            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12
                Rectangle { width: 8; height: 8; radius: 4; color: root.green }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label { text: "FA3-TOOLS-FABRIC-001"; color: root.textPrimary; font.bold: true; font.pixelSize: 11 }
                    Label {
                        text: "A Tools nem új execution authority: intent → admission → HRB → provider router → provenance."
                        color: root.textMuted
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
                Label { text: "CANONICAL"; color: root.accent; font.bold: true; font.pixelSize: 9 }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 1100 ? 3 : 2
            rowSpacing: 12
            columnSpacing: 12

            ToolCard {
                title: "Digitalizálás"
                subtitle: "Hang-, kép- és videó-ingest. A digitalizálás külön marad a fájlkonverziótól."
                badge: "INGEST"
                tone: root.cyan
            }
            ToolCard {
                title: "Konvertálás"
                subtitle: "Dokumentum, kép, hang, videó és 3D hosszúfarkú konverzió. Specializált provider az első választás."
                badge: "FA3-FILE-CONVERSION-001"
                tone: root.accent
                providerLine: "ConvertX · P2 · QUARANTINED · XeLaTeX DENY"
                warning: true
            }
            ToolCard {
                title: "Fájl küldés / fogadás"
                subtitle: "Átviteli és szinkron feladatok kontrollált adaptereken keresztül."
                badge: "TRANSFER"
                tone: root.green
            }
            ToolCard {
                title: "Archiválás / Biztonsági mentés"
                subtitle: "Tömörítés, kibontás, mentés, visszaállítás és snapshot feladatok."
                badge: "ARCHIVE"
                tone: root.orange
            }
            ToolCard {
                title: "Letöltések"
                subtitle: "Általános és média letöltési feladatok queue- és egress-policy mögött."
                badge: "DOWNLOAD"
                tone: root.magenta
            }
            ToolCard {
                title: "Fájlműveletek"
                subtitle: "Hash, integritás-ellenőrzés, metadata és duplikátum-kezelés."
                badge: "UTILITY"
                tone: root.cyan
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 118
            radius: 8
            color: root.panel
            border.color: root.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 5
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "ConvertX provider állapot"; color: root.textPrimary; font.bold: true; font.pixelSize: 12 }
                    Item { Layout.fillWidth: true }
                    Label { text: "QUARANTINED"; color: root.orange; font.bold: true; font.pixelSize: 9 }
                }
                Label {
                    text: "A jelenlegi upstream web-flow cookie/job alapú és nem hivatalos stabil API. Agent/n8n/MCP közvetlen hívás tiltott."
                    color: root.textMuted
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    text: "Promotion: static + security regression + digest-pinned runtime + valódi current-host E2E + egress + HRB + provenance PASS."
                    color: root.textMuted
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
        }

        Item { Layout.preferredHeight: 12 }
    }

    component ToolCard: Rectangle {
        required property string title
        required property string subtitle
        required property string badge
        required property color tone
        property string providerLine: ""
        property bool warning: false

        Layout.fillWidth: true
        Layout.preferredHeight: providerLine.length > 0 ? 154 : 128
        radius: 8
        color: root.panel
        border.color: warning ? root.orange : root.border

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                Rectangle { width: 8; height: 8; radius: 4; color: tone }
                Label { text: title; color: root.textPrimary; font.bold: true; font.pixelSize: 12; Layout.fillWidth: true }
                Label { text: badge; color: tone; font.pixelSize: 8; font.bold: true }
            }
            Label {
                text: subtitle
                color: root.textMuted
                font.pixelSize: 9
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                visible: providerLine.length > 0
                text: providerLine
                color: warning ? root.orange : root.textMuted
                font.pixelSize: 9
                font.bold: warning
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Item { Layout.fillHeight: true }
        }
    }
}
