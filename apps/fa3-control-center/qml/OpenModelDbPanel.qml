import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language

    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    contentWidth: availableWidth
    Component.onCompleted: if (openModelDbService.catalogStatus === "NOT_LOADED") openModelDbService.refreshCatalog()

    ColumnLayout {
        width: root.availableWidth
        spacing: 12
        Item { Layout.preferredHeight: 8 }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: "OpenModelDB"
            font.pixelSize: root.px(22)
            font.bold: true
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: "FA3-PROVIDER-OPENMODELDB-001 · staged SHA-256 acquisition"
            color: root.textMuted
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Label { Layout.fillWidth: true; text: openModelDbService.catalogStatus; color: root.accent; font.bold: true }
            Button { text: root.t("Frissítés", "Refresh"); enabled: !openModelDbService.catalogBusy; onClicked: openModelDbService.refreshCatalog() }
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            wrapMode: Text.WordWrap
            color: root.textMuted
            text: root.t("A letöltések staging területre érkeznek, SHA-256 ellenőrzéssel. A staging siker nem production admission; provenance/licenc/security gate továbbra is szükséges.", "Downloads land in staging with SHA-256 verification. Successful staging is not production admission; provenance/license/security gates remain required.")
        }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            text: root.t("Modellkatalógus", "Model catalog")
            font.pixelSize: root.px(17)
            font.bold: true
        }

        Repeater {
            model: openModelDbService.models
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.rightMargin: 20
                Layout.preferredHeight: Math.max(170, modelColumn.implicitHeight + 28)
                radius: 10
                color: root.surface1

                ColumnLayout {
                    id: modelColumn
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 7
                    Label { Layout.fillWidth: true; text: modelData.name; font.bold: true; wrapMode: Text.WordWrap }
                    Label { Layout.fillWidth: true; text: modelData.author + " · " + modelData.license; color: root.textMuted; wrapMode: Text.WordWrap }
                    Label {
                        Layout.fillWidth: true
                        text: modelData.resources.length ? (modelData.resources[0].label + " · SHA256 " + (modelData.resources[0].sha256 || "MISSING")) : root.t("Nincs resource", "No resource")
                        color: root.textMuted
                        wrapMode: Text.WrapAnywhere
                    }
                    Button {
                        Layout.alignment: Qt.AlignLeft
                        text: root.t("Staging letöltés", "Stage download")
                        enabled: modelData.resources.length > 0 && modelData.resources[0].sha256 && modelData.resources[0].sha256.length === 64
                        onClicked: openModelDbService.queueDownload(modelData.id, modelData.name, modelData.license, modelData.resources[0])
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.preferredHeight: Math.max(220, queueColumn.implicitHeight + 28)
            radius: 10
            color: root.surface1

            ColumnLayout {
                id: queueColumn
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8
                Label { text: root.t("Letöltési sor", "Download queue"); font.pixelSize: root.px(17); font.bold: true }
                Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WrapAnywhere; text: openModelDbService.stagingRoot }
                ListView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(120, contentHeight)
                    clip: true
                    model: openModelDbService.downloads
                    delegate: ItemDelegate {
                        required property var modelData
                        width: ListView.view.width
                        contentItem: Label {
                            text: (modelData.model_name || modelData.id || "download") + " · " + (modelData.status || "")
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
        Item { Layout.preferredHeight: 20 }
    }
}
