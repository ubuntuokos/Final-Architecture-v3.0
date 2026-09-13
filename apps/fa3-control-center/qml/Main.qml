import QtQuick
import QtQuick.Controls

LegacyMain {
    id: rootWindow

    ModelsProvidersPage {
        parent: rootWindow.contentItem
        x: 238
        y: 0
        width: Math.max(0, parent.width - 238)
        height: parent.height
        z: 1000
        visible: rootWindow.selectedIndex === 4
        surface0: rootWindow.surface0
        surface1: rootWindow.surface1
        surface2: rootWindow.surface2
        accent: rootWindow.accent
        textPrimary: rootWindow.textPrimary
        textMuted: rootWindow.textMuted
    }
}
