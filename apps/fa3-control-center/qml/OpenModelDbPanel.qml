import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    Component.onCompleted: if (openModelDbService.catalogStatus === "NOT_LOADED") openModelDbService.refreshCatalog()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true
                Label { text: "OpenModelDB"; font.pixelSize: root.px(22); font.bold: true }
                Label { text: "FA3-PROVIDER-OPENMODELDB-001 · staged SHA-256 acquisition"; color: root.textMuted }
            }
            Label { text: openModelDbService.catalogStatus; color: root.accent }
            Button { text: root.t("Frissítés", "Refresh"); enabled: !openModelDbService.catalogBusy; onClicked: openModelDbService.refreshCatalog() }
        }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("A letöltések staging területre érkeznek, SHA-256 ellenőrzéssel. A staging siker nem production admission; provenance/licenc/security gate továbbra is szükséges.", "Downloads land in staging with SHA-256 verification. Successful staging is not production admission; provenance/license/security gates remain required.") }
        SplitView { Layout.fillWidth: true; Layout.fillHeight: true
            ScrollView { SplitView.fillWidth: true; SplitView.preferredWidth: 760; contentWidth: availableWidth
                ColumnLayout { width: parent.width; spacing: 8
                    Repeater { model: openModelDbService.models
                        delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 130; radius: 8; color: root.surface1
                            RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 12
                                ColumnLayout { Layout.fillWidth: true
                                    Label { Layout.fillWidth: true; text: modelData.name; font.bold: true; elide: Text.ElideRight }
                                    Label { text: modelData.author + " · " + modelData.license; color: root.textMuted }
                                    Label { Layout.fillWidth: true; text: modelData.resources.length ? (modelData.resources[0].label + " · SHA256 " + (modelData.resources[0].sha256 || "MISSING")) : root.t("Nincs resource", "No resource"); color: root.textMuted; elide: Text.ElideMiddle }
                                }
                                Button { text: root.t("Staging letöltés", "Stage download"); enabled: modelData.resources.length > 0 && modelData.resources[0].sha256 && modelData.resources[0].sha256.length === 64; onClicked: openModelDbService.queueDownload(modelData.id, modelData.name, modelData.license, modelData.resources[0]) }
                            }
                        }
                    }
                }
            }
            Rectangle { SplitView.preferredWidth: 360; SplitView.minimumWidth: 280; color: root.surface1; radius: 8
                ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 8
                    Label { text: root.t("Letöltési sor", "Download queue"); font.bold: true }
                    Label { Layout.fillWidth: true; color: root.textMuted; elide: Text.ElideMiddle; text: openModelDbService.stagingRoot }
                    ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: openModelDbService.downloads
                        delegate: ItemDelegate { required property var modelData; width: ListView.view.width; text: (modelData.model_name || modelData.id || "download") + " · " + (modelData.status || "") }
                    }
                }
            }
        }
    }
}
