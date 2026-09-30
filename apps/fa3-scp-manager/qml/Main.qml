import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1440
    height: 900
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    color: "#07111f"
    title: "FA3 — Secure Communication & Proxy Manager"

    SecureCommunicationSettings {
        anchors.fill: parent
        adminMode: true
        contextLabel: "FA3 GLOBAL / SCP MANAGER"
    }
}
