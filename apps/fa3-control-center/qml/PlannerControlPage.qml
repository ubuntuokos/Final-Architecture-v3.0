import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var settings
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language

    function t(hu, en) { return language === "en" ? en : hu }
    function px(value) { return Math.max(9, Math.round(value * fontScale)) }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        Label { text: root.t("Tervező / Planner", "Planner"); font.pixelSize: root.px(22); font.bold: true }
        Label { text: "PENDING_CANONICAL_BINDING"; color: "#d99b32"; font.bold: true }
        Label {
            Layout.fillWidth: true
            text: root.t("Célok, korlátok, függőségek, mérföldkövek és elfogadási feltételek tervezési nézete.", "Planning view for goals, constraints, dependencies, milestones and acceptance criteria.")
            wrapMode: Text.WordWrap
            color: root.textMuted
        }

        RowLayout {
            Label { text: root.t("Alap mód", "Default mode") }
            ComboBox {
                model: ["PLAN", "DECOMPOSE", "SEQUENCE", "MILESTONE", "DEPENDENCY_MAP", "CONTINGENCY"]
                currentIndex: Math.max(0, model.indexOf(root.settings.value("planner/defaultMode", "PLAN")))
                onActivated: root.settings.setValue("planner/defaultMode", currentText)
            }
        }

        RowLayout {
            Label { text: root.t("Részletesség", "Granularity") }
            ComboBox {
                model: ["High-level", "Balanced", "Detailed"]
                currentIndex: Math.max(0, model.indexOf(root.settings.value("planner/granularity", "Balanced")))
                onActivated: root.settings.setValue("planner/granularity", currentText)
            }
        }

        CheckBox {
            text: root.t("Függőségek feltérképezése", "Dependency mapping")
            checked: root.settings.value("planner/dependencyMapping", true)
            onToggled: root.settings.setValue("planner/dependencyMapping", checked)
        }
        CheckBox {
            text: root.t("Elfogadási feltételek", "Acceptance criteria")
            checked: root.settings.value("planner/requireAcceptanceCriteria", true)
            onToggled: root.settings.setValue("planner/requireAcceptanceCriteria", checked)
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: root.textMuted
            text: root.t("A repository aktuális snapshotjában a Tervező canonical rekordja még nem látható; a GUI ezért nem ad hozzá kitalált FA3-azonosítót.", "The current repository snapshot does not yet expose the Planner canonical record, so the GUI does not assign an invented FA3 identifier.")
        }
        Item { Layout.fillHeight: true }
    }
}
