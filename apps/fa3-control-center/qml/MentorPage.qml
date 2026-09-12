import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    required property var settings
    required property var repository
    required property color surface1
    required property color surface2
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language
    contentWidth: availableWidth

    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    component Card: Rectangle {
        radius: 12 * root.uiScale
        color: root.surface1
        border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
    }

    ColumnLayout {
        width: parent.width
        spacing: 18
        anchors.margins: 24
        Column {
            spacing: 4
            Label { text: "AI Mentor"; font.pixelSize: root.px(24); font.bold: true }
            Label { text: root.t("Tanítás, magyarázat, mastery, tudásrés-felismerés és sandboxolt Practice Lab.", "Teaching, explanation, mastery, knowledge-gap detection and sandboxed Practice Lab."); color: root.textMuted; font.pixelSize: root.px(13) }
        }
        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 220 * root.uiScale
            GridLayout {
                anchors.fill: parent; anchors.margins: 18; columns: 2; columnSpacing: 24; rowSpacing: 12
                Label { text: root.t("Mentor engedélyezve", "Mentor enabled") }
                Switch { checked: root.settings.value("mentor/enabled", true); onToggled: root.settings.setValue("mentor/enabled", checked) }
                Label { text: root.t("Oktatási profil", "Teaching profile") }
                ComboBox { model: ["Teacher", "Coach-style Tutor", "Expert Assistant", "Study", "Custom"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("mentor/profile", "Expert Assistant"))); onActivated: root.settings.setValue("mentor/profile", currentText) }
                Label { text: root.t("Kezdeményezés", "Initiative") }
                ComboBox { model: ["Silent", "Conservative", "Balanced", "Proactive"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("mentor/initiative", "Balanced"))); onActivated: root.settings.setValue("mentor/initiative", currentText) }
                Label { text: root.t("Részletesség", "Detail") }
                ComboBox { model: ["Short", "Normal", "Detailed", "Teaching"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("mentor/detail", "Normal"))); onActivated: root.settings.setValue("mentor/detail", currentText) }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 235 * root.uiScale
                ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                    Label { text: "Memory & Personalization"; font.bold: true; font.pixelSize: root.px(16) }
                    ComboBox { Layout.fillWidth: true; model: ["Ask every time", "Ask for new categories", "Allow approved categories", "Never write memory"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("mentor/memoryPolicy", "Ask for new categories"))); onActivated: root.settings.setValue("mentor/memoryPolicy", currentText) }
                    CheckBox { text: "Mastery tracking"; checked: root.settings.value("mentor/masteryTracking", true); onToggled: root.settings.setValue("mentor/masteryTracking", checked) }
                    CheckBox { text: root.t("Forrásidézetek megkövetelése", "Require citations"); checked: root.settings.value("mentor/citationsRequired", true); onToggled: root.settings.setValue("mentor/citationsRequired", checked) }
                    Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("Canonical memóriaírás továbbra is explicit consent + meglévő Memory authority escalation útvonalon történik.", "Canonical memory writes still require explicit consent and escalation to the existing Memory authority.") }
                }
            }
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 235 * root.uiScale
                ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                    Label { text: "Practice Lab"; font.bold: true; font.pixelSize: root.px(16) }
                    CheckBox { text: root.t("Practice Lab engedélyezése", "Enable Practice Lab"); checked: root.settings.value("mentor/practiceLab", true); onToggled: root.settings.setValue("mentor/practiceLab", checked) }
                    CheckBox { text: root.t("Voice használata", "Use voice"); checked: root.settings.value("mentor/voice", false); onToggled: root.settings.setValue("mentor/voice", checked) }
                    Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("A Mentor nem futtat közvetlenül toolt. A Practice Lab csak authenticated delegated Agent Execution + fail-closed sandbox útvonalon indulhat.", "The Mentor never executes tools directly. Practice Lab execution requires authenticated delegated Agent Execution and a fail-closed sandbox.") }
                }
            }
        }
        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 160 * root.uiScale
            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                Label { text: "Canonical boundary"; font.bold: true; font.pixelSize: root.px(16) }
                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: "FA3-MENTOR-001 — advisory-only. Knowledge/RAG read projection, consent-gated memory write escalation, evidence-bound mastery and delegated sandbox execution. No new authority." }
            }
        }
    }
}
