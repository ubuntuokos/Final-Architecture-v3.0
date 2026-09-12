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
    component Card: Rectangle { radius: 12 * root.uiScale; color: root.surface1; border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10) }

    ColumnLayout {
        width: parent.width; spacing: 18; anchors.margins: 24
        Column {
            spacing: 4
            Label { text: "AI Coach"; font.pixelSize: root.px(24); font.bold: true }
            Label { text: root.t("Célok, fókusz, blockerek, következő legjobb lépés és végrehajtási fejlődés.", "Goals, focus, blockers, next-best actions and execution progress."); color: root.textMuted; font.pixelSize: root.px(13) }
        }
        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 250 * root.uiScale
            GridLayout {
                anchors.fill: parent; anchors.margins: 18; columns: 2; columnSpacing: 24; rowSpacing: 12
                Label { text: root.t("Coach engedélyezve", "Coach enabled") }
                Switch { checked: root.settings.value("coach/enabled", true); onToggled: root.settings.setValue("coach/enabled", checked) }
                Label { text: root.t("Coaching profil", "Coaching profile") }
                ComboBox { model: ["Supportive", "Structured", "Performance", "Critical Reviewer", "Executive", "Custom"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("coach/profile", "Executive"))); onActivated: root.settings.setValue("coach/profile", currentText) }
                Label { text: root.t("Proaktivitás", "Proactivity") }
                ComboBox { model: ["Silent", "Advisory", "Balanced", "Proactive", "Strict"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("coach/proactivity", "Balanced"))); onActivated: root.settings.setValue("coach/proactivity", currentText) }
                Label { text: root.t("Intervenció", "Intervention") }
                ComboBox { model: ["Silent", "Advisory", "Balanced", "Proactive", "Strict"]; Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.settings.value("coach/intervention", "Balanced"))); onActivated: root.settings.setValue("coach/intervention", currentText) }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 250 * root.uiScale
                ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 7
                    Label { text: "Progress & Intervention"; font.bold: true; font.pixelSize: root.px(16) }
                    CheckBox { text: root.t("Rendszeres check-in", "Regular check-ins"); checked: root.settings.value("coach/checkIns", true); onToggled: root.settings.setValue("coach/checkIns", checked) }
                    CheckBox { text: root.t("Projekt-awareness", "Project awareness"); checked: root.settings.value("coach/projectAwareness", true); onToggled: root.settings.setValue("coach/projectAwareness", checked) }
                    CheckBox { text: root.t("Heti review", "Weekly review"); checked: root.settings.value("coach/weeklyReview", true); onToggled: root.settings.setValue("coach/weeklyReview", checked) }
                    TextField { Layout.fillWidth: true; placeholderText: "Quiet hours"; text: root.settings.value("coach/quietHours", "20:00-08:00"); onEditingFinished: root.settings.setValue("coach/quietHours", text) }
                }
            }
            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 250 * root.uiScale
                ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                    Label { text: "Mentor ↔ Coach"; font.bold: true; font.pixelSize: root.px(16) }
                    CheckBox { text: root.t("Mentor referral engedélyezve", "Allow Mentor referrals"); checked: root.settings.value("coach/mentorReferrals", true); onToggled: root.settings.setValue("coach/mentorReferrals", checked) }
                    Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("Coach: cél- vagy végrehajtási akadályt észlel → learning gap esetén Mentor referral → Mentor tanít/gyakoroltat → mastery evidence → Coach folytatja a célt.", "Coach detects a goal/execution blocker → learning gap triggers Mentor referral → Mentor teaches/practices → mastery evidence → Coach resumes the objective.") }
                }
            }
        }
        Card {
            Layout.fillWidth: true; Layout.preferredHeight: 175 * root.uiScale
            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 8
                Label { text: "Authority boundary"; font.bold: true; font.pixelSize: root.px(16) }
                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("A Coach javasolhat célt, prioritást, milestone-t és következő lépést, de nem írhat canonical roadmapet, task state-et vagy runtime policy-t közvetlenül. Minden mutáció proposal/ChangeSet + existing authority útvonalon megy.", "The Coach may recommend goals, priorities, milestones and next actions, but cannot directly mutate canonical roadmaps, task state or runtime policy. Mutations require proposal/ChangeSet routing through existing authorities.") }
                Label { text: "FA3-COACH-001 — GUI/reference projection; runtime provider admission remains pending."; color: root.accent }
            }
        }
    }
}
