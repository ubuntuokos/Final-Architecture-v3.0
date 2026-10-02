import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: root
    property var stateProvider
    property color panelColor: "#10243a"
    property color borderColor: "#28425e"
    property color textColor: "#f5f8fc"
    property color mutedColor: "#8ea3b8"
    property color warningColor: "#f0b14a"

    property string effectiveMode: stateProvider ? stateProvider.effectiveMode : "DEGRADED"
    property bool critical: effectiveMode === "SAFE_MODE"
                            || effectiveMode === "DEGRADED"
                            || effectiveMode === "CONFLICT"
                            || effectiveMode === "RESOURCE_PRESSURE"
                            || effectiveMode === "AUTHORITY_LOST"
                            || (stateProvider && stateProvider.degraded)
    text: (critical ? "⚠ " : "WM ") + effectiveMode.replaceAll("+", " + ")
    flat: true
    padding: 8
    Accessible.name: "Workload Mode: " + effectiveMode
    Accessible.description: stateProvider
        ? "Authority " + stateProvider.authority + ", FA3 " + stateProvider.fa3State
        : "Required Workload Mode service unavailable"
    ToolTip.visible: hovered
    ToolTip.text: stateProvider
        ? ("Global mode: " + stateProvider.effectiveMode
           + "\nLocal mode: " + stateProvider.localMode
           + "\nAuthority: " + stateProvider.authority
           + "\nFA3: " + stateProvider.fa3State
           + "\nGameMode: " + stateProvider.gameModeState
           + "\nSafety: " + stateProvider.safetyState)
        : "Workload Mode required service unavailable"
    onClicked: details.open()

    contentItem: Label {
        text: root.text
        color: root.critical ? root.warningColor : root.textColor
        font.pixelSize: 9
        font.bold: true
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 6
        color: root.panelColor
        border.color: root.critical ? root.warningColor : root.borderColor
        border.width: 1
    }

    Popup {
        id: details
        x: Math.max(-260, root.width - width)
        y: root.height + 6
        width: 330
        padding: 14
        modal: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            radius: 8
            color: root.panelColor
            border.color: root.borderColor
        }
        contentItem: ColumnLayout {
            spacing: 7
            Label { text: "Workload Mode"; color: root.textColor; font.pixelSize: 14; font.bold: true }
            Label { text: "Global: " + root.effectiveMode; color: root.textColor }
            Label { text: "Local: " + (root.stateProvider ? root.stateProvider.localMode : "NORMAL"); color: root.mutedColor }
            Label { text: "Authority: " + (root.stateProvider ? root.stateProvider.authority : "UNAVAILABLE"); color: root.mutedColor }
            Label { text: "FA3: " + (root.stateProvider ? root.stateProvider.fa3State : "DISCONNECTED"); color: root.mutedColor }
            Label { text: "GameMode: " + (root.stateProvider ? root.stateProvider.gameModeState : "UNAVAILABLE"); color: root.mutedColor }
            Label { text: "Workloads: " + (root.stateProvider ? root.stateProvider.activeWorkloadCount : 0); color: root.mutedColor }
            Label { text: "Pressure: " + (root.stateProvider ? root.stateProvider.resourcePressure : "UNKNOWN"); color: root.mutedColor }
            Label { text: "Safety: " + (root.stateProvider ? root.stateProvider.safetyState : "UNKNOWN"); color: root.mutedColor }
            Label { text: "Conflict: " + (root.stateProvider ? root.stateProvider.conflictState : "UNKNOWN"); color: root.mutedColor }
            Label {
                text: "Coexistence: " + (root.stateProvider && root.stateProvider.coexistencePeers.length
                      ? root.stateProvider.coexistencePeers.join(", ") : "none")
                color: root.mutedColor
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            Label {
                visible: root.stateProvider ? root.stateProvider.degraded : true
                text: "⚠ " + (root.stateProvider ? root.stateProvider.degradedReason : "WORKLOAD_MODE_REQUIRED_SERVICE_UNAVAILABLE")
                color: root.warningColor
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }
}
