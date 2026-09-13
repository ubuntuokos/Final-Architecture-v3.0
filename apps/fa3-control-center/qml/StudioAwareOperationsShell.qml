import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

OperationsAwareAppShell {
    id: studioShell

    // FA3 mission-control visual language. Explicit light mode remains available,
    // but Studio/System themes use the darker control-plane palette from the
    // original FA3 view concepts rather than a generic settings-dashboard look.
    surface0: forcedLight ? "#eef3f8" : "#080c12"
    surface1: forcedLight ? "#ffffff" : "#101722"
    surface2: forcedLight ? "#e4ebf3" : "#182332"
    textPrimary: forcedLight ? "#17202c" : "#edf5ff"
    textMuted: forcedLight ? "#617084" : "#8ea3ba"
    accent: forcedLight ? "#1277b8" : "#42c8f5"
    color: surface0

    function areaVisible(key) {
        if (key === "starterModels")
            return false
        if (key === "command" || key === "settings")
            return true
        return fa3Settings.value("areas/" + key + "Visible", true)
    }

    Rectangle {
        parent: studioShell.contentItem
        anchors.fill: parent
        z: -20
        gradient: Gradient {
            GradientStop { position: 0.0; color: studioShell.forcedLight ? "#eef3f8" : "#080c12" }
            GradientStop { position: 0.58; color: studioShell.forcedLight ? "#f7f9fb" : "#0b1119" }
            GradientStop { position: 1.0; color: studioShell.forcedLight ? "#eaf0f6" : "#0d1520" }
        }
    }

    Rectangle {
        parent: studioShell.contentItem
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.leftMargin: studioShell.sidebarCollapsed ? Math.round(58 * studioShell.uiScale) : Math.round(260 * studioShell.uiScale)
        color: "transparent"
        z: 850
        visible: studioShell.selectedIndex === studioShell.indexForKey("studio")

        AIStudioPage {
            anchors.fill: parent
            repository: fa3Repository
            surface0: studioShell.surface0
            surface1: studioShell.surface1
            surface2: studioShell.surface2
            textPrimary: studioShell.textPrimary
            textMuted: studioShell.textMuted
            accent: studioShell.accent
            uiScale: studioShell.uiScale
            fontScale: studioShell.fontScale
            language: fa3Settings.language
        }
    }
}
