import QtQuick

OperationsAwareAppShell {
    id: studioShell

    Rectangle {
        parent: studioShell.contentItem
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.leftMargin: studioShell.sidebarCollapsed ? Math.round(58 * studioShell.uiScale) : Math.round(260 * studioShell.uiScale)
        color: studioShell.surface0
        z: 850
        visible: studioShell.selectedIndex === studioShell.indexForKey("studio")

        AIStudioPage {
            anchors.fill: parent
            repository: fa3Repository
            surface1: studioShell.surface1
            textPrimary: studioShell.textPrimary
            textMuted: studioShell.textMuted
            accent: studioShell.accent
            uiScale: studioShell.uiScale
            fontScale: studioShell.fontScale
            language: fa3Settings.language
        }
    }
}
