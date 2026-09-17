import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var repository
    required property color surface1
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    function t(hu, en) {
        return language === "en" ? en : hu
    }

    function px(value) {
        return Math.max(9, Math.round(value * fontScale))
    }

    function managerRecords() {
        return repository.searchRecords("FA3-MANAGER-001")
    }

    component Card: Rectangle {
        radius: Math.round(12 * root.uiScale)
        color: root.surface1
        border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
    }

    component WorkCard: Card {
        property string state: ""
        property string title: ""
        property string description: ""
        property string badge: ""
        implicitWidth: Math.round(270 * root.uiScale)
        implicitHeight: Math.round(150 * root.uiScale)
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Label { text: parent.parent.parent.state; color: root.accent; font.bold: true; Layout.fillWidth: true }
                Label { text: parent.parent.parent.badge; color: root.textMuted; font.pixelSize: root.px(10) }
            }
            Label { text: parent.parent.title; font.bold: true; font.pixelSize: root.px(15); Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Label { text: parent.parent.description; color: root.textMuted; Layout.fillWidth: true; Layout.fillHeight: true; wrapMode: Text.WordWrap }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16
            Item { Layout.preferredHeight: 20 }

            Column {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                spacing: 4
                Label { text: "Manager"; font.pixelSize: root.px(24); font.bold: true }
                Label {
                    width: parent.width
                    text: root.t("Munka, delegálás, függőségek és evidence-closure operátori projection. Nem azonos a Model Managerrel.", "Operator projection for work, delegation, dependencies and evidence closure. It is not the Model Manager.")
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                }
            }

            Flow {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                spacing: 12
                WorkCard { state: "DRAFT"; title: root.t("Megfogalmazott munka", "Drafted work"); description: root.t("Cél, acceptance criteria és scope még szerkeszthető.", "Goal, acceptance criteria and scope are still editable."); badge: "LOCAL" }
                WorkCard { state: "READY"; title: root.t("Delegálható", "Ready for delegation"); description: root.t("Dependency és authorization preflight után delegálható.", "May be delegated after dependency and authorization preflight."); badge: "GATED" }
                WorkCard { state: "RUNNING"; title: root.t("Folyamatban", "Running"); description: root.t("A Manager csak projection; a tényleges végrehajtás Agent Execution / MCP authority alatt fut.", "Manager is projection only; execution runs under Agent Execution / MCP authority."); badge: "DELEGATED" }
                WorkCard { state: "BLOCKED"; title: root.t("Blokkolt", "Blocked"); description: root.t("Blokker provenance és következő feloldási lépés szükséges.", "Blocker provenance and next resolution step are required."); badge: "ATTENTION" }
                WorkCard { state: "EVIDENCE_PENDING"; title: "Evidence pending"; description: root.t("A munka elkészültnek tűnhet, de még nincs igazolt closure.", "Work may look complete but closure is not yet evidenced."); badge: "NO DONE" }
                WorkCard { state: "VERIFIED"; title: root.t("Igazolt lezárás", "Verified closure"); description: root.t("Acceptance criteria teljesült és evidence referenciák rendelkezésre állnak.", "Acceptance criteria are met and evidence references are present."); badge: "EVIDENCED" }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.preferredHeight: 150
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8
                    Label { text: root.t("Canonical állapot", "Canonical status"); font.bold: true; font.pixelSize: root.px(16) }
                    Label {
                        Layout.fillWidth: true
                        text: root.managerRecords().length > 0
                              ? "FA3-MANAGER-001: " + root.managerRecords()[0].status
                              : root.t("FA3-MANAGER-001 még nincs ezen a GUI ágon; a külön Manager materialization PR #145 alatt áll.", "FA3-MANAGER-001 is not yet present on this GUI branch; the separate Manager materialization is in PR #145.")
                        wrapMode: Text.WordWrap
                        color: root.managerRecords().length > 0 ? root.accent : root.textMuted
                    }
                    Label { text: "Mentor → knowledge gap · Coach → goals/accountability · Manager → work/delegation/evidence closure"; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }

            Item { Layout.preferredHeight: 20 }
        }
    }
}
