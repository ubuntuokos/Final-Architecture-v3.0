import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property color canvas: "#07111f"
    property color panel: "#0b1728"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8295aa"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color magenta: "#b778ff"
    color: canvas

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 560)
        implicitHeight: col.implicitHeight + 40
        radius: 12
        color: root.panel
        border.color: root.border
        ColumnLayout {
            id: col
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            Label { text: "FA3 belépés"; color: root.textPrimary; font.pixelSize: 26; font.bold: true }
            Label {
                Layout.fillWidth: true
                text: "A titkosított Session Vault feloldása szükséges. Ez nem az operációs rendszer jelszava és nem új identity authority."
                color: root.textMuted; wrapMode: Text.WordWrap
            }
            TextField {
                id: password
                Layout.fillWidth: true
                placeholderText: "Vault jelszó"
                echoMode: TextInput.Password
                focus: true
                onAccepted: { fa3SessionVault.unlockWithPassphrase(text); text = "" }
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: "Belépés"
                    Layout.fillWidth: true
                    onClicked: { fa3SessionVault.unlockWithPassphrase(password.text); password.text = "" }
                }
                Button {
                    text: "Jelszókezelő"
                    Layout.fillWidth: true
                    onClicked: fa3SessionVault.unlockWithSecretService()
                }
            }
            Label {
                visible: fa3SessionVault.errorMessage.length > 0
                Layout.fillWidth: true
                text: fa3SessionVault.errorMessage
                color: root.magenta
                wrapMode: Text.WordWrap
            }
        }
    }
}
