import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ScrollView {
    id: root
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8295aa"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    clip: true

    FileDialog {
        id: secretFileDialog
        title: "Opcionális vault secret fájl"
        onAccepted: fa3SessionVault.unlockWithSecretFile(selectedFile)
    }

    ColumnLayout {
        width: root.availableWidth
        spacing: 14
        anchors.margins: 18

        Label { text: "Session Vault / Kulcsvault"; color: root.textPrimary; font.pixelSize: 24; font.bold: true }
        Label {
            Layout.fillWidth: true
            text: "Az OS-be bejelentkezett felhasználó az FA3 felhasználó. A LUKS2 vault csak a kulcsokat és érzékeny adatokat védi; külön FA3-login nincs az alap egyszemélyes módban."
            color: root.textMuted; wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: statusCol.implicitHeight + 28
            radius: 8; color: root.panel; border.color: root.border
            ColumnLayout {
                id: statusCol
                anchors.fill: parent; anchors.margins: 14
                Label { text: "Állapot: " + fa3SessionVault.statusText; color: fa3SessionVault.unlocked ? root.green : root.orange; font.bold: true }
                Label { text: "Tárolófájl: " + fa3SessionVault.imagePath; color: root.textMuted; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                Label { visible: fa3SessionVault.unlocked; text: "Mount: " + fa3SessionVault.mountPath; color: root.textMuted; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                Label { visible: fa3SessionVault.errorMessage.length > 0; text: fa3SessionVault.errorMessage; color: root.magenta; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: unlockCol.implicitHeight + 28
            radius: 8; color: root.panelRaised; border.color: root.border
            ColumnLayout {
                id: unlockCol
                anchors.fill: parent; anchors.margins: 14
                spacing: 10
                Label { text: "Feloldás"; color: root.textPrimary; font.bold: true }
                TextField {
                    id: passphrase
                    Layout.fillWidth: true
                    placeholderText: "FA3 vault jelszó"
                    echoMode: TextInput.Password
                    enabled: fa3SessionVault.configured && !fa3SessionVault.unlocked
                    onAccepted: {
                        fa3SessionVault.unlockWithPassphrase(text)
                        text = ""
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Vault feloldása jelszóval"
                        enabled: fa3SessionVault.configured && !fa3SessionVault.unlocked
                        onClicked: { fa3SessionVault.unlockWithPassphrase(passphrase.text); passphrase.text = "" }
                    }
                    Button {
                        text: "Feloldás jelszókezelőből"
                        enabled: fa3SessionVault.configured && !fa3SessionVault.unlocked
                        onClicked: fa3SessionVault.unlockWithSecretService()
                    }
                    Button {
                        text: "Opcionális secret fájl"
                        enabled: fa3SessionVault.configured && !fa3SessionVault.unlocked
                        onClicked: secretFileDialog.open()
                    }
                }
                RowLayout {
                    Button {
                        text: "Jelszó mentése a jelszókezelőbe"
                        enabled: passphrase.text.length > 0
                        onClicked: { fa3SessionVault.storePassphraseInSecretService(passphrase.text); passphrase.text = "" }
                    }
                    Button {
                        text: "Vault zárolása"
                        enabled: fa3SessionVault.unlocked
                        onClicked: fa3SessionVault.lock()
                    }
                    Button { text: "Állapot frissítése"; onClicked: fa3SessionVault.refresh() }
                }
            }
        }

        Rectangle {
            visible: !fa3SessionVault.configured
            Layout.fillWidth: true
            implicitHeight: setupCol.implicitHeight + 28
            radius: 8; color: root.panel; border.color: root.orange
            ColumnLayout {
                id: setupCol
                anchors.fill: parent; anchors.margins: 14
                Label { text: "Első inicializálás szükséges"; color: root.orange; font.bold: true }
                Label {
                    Layout.fillWidth: true
                    text: "Futtasd egyszer:  bin/fa3-session-vault-init\nEz létrehozza a helyi, generikus nevű LUKS2 tároló image-et. USB, HSM és air-gap nem kötelező."
                    color: root.textMuted; wrapMode: Text.WordWrap
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: policyCol.implicitHeight + 28
            radius: 8; color: root.panel; border.color: root.border
            ColumnLayout {
                id: policyCol
                anchors.fill: parent; anchors.margins: 14
                Label { text: "Kulcskezelési szabály"; color: root.textPrimary; font.bold: true }
                Label {
                    Layout.fillWidth: true
                    text: "A Root CA kulcs és user-session custody tárolható ebben a titkosított image-ben. A fa3-step-ca service account nem olvashatja. FA3 tokenek, külső provider belépési titkok és egyéb FA3-jelszavak nem ebbe kerülnek: azokat a külön FA3-SECRET-BROKER-001 kezeli egy generikus nevű LUKS2 image-ben. A Session Vault feloldásához a Secret Service csak opcionális adapter; sem KDE, sem GNOME, sem konkrét desktop vagy display server nem canonical függőség."
                    color: root.textMuted; wrapMode: Text.WordWrap
                }
            }
        }
    }
}
