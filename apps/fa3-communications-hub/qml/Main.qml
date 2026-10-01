import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    width: 1440
    height: 900
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    title: "FA3 Communications Hub"
    color: "#10151d"

    property int sectionIndex: 0
    property bool aiEnabled: false

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            Label { text: "FA3 Communications Hub"; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true }
            Label { text: "FULL"; color: "#8bd5ca"; font.bold: true }
            Label { text: "Current Host: PENDING"; color: "#f5a97f" }
            Switch {
                id: aiSwitch
                text: "AI"
                checked: root.aiEnabled
                onToggled: root.aiEnabled = checked
                ToolTip.visible: hovered
                ToolTip.text: "Az AI csak policy- és capability-szintű engedély után használható."
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 235
            Layout.fillHeight: true
            color: "#171e29"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8
                Label { text: "Kommunikáció"; font.bold: true; color: "#c6d0f5" }
                Repeater {
                    model: ["Levelezés", "Kontaktok", "Közös postaládák", "Csapat", "Előzmények", "Biztonság"]
                    delegate: Button {
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        text: modelData
                        checkable: true
                        checked: root.sectionIndex === index
                        onClicked: root.sectionIndex = index
                    }
                }
                Item { Layout.fillHeight: true }
                Label { text: "SMTP · IMAP · JMAP"; color: "#838ba7"; wrapMode: Text.Wrap }
                Label { text: "CardDAV · CalDAV · OAuth2/OIDC"; color: "#838ba7"; wrapMode: Text.Wrap }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.sectionIndex

            Frame {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 16
                    Label { text: "Levelezés"; font.pixelSize: 28; font.bold: true }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 78
                        radius: 8
                        color: "#252b3a"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            Label { text: "Nincs konfigurált, Current Host által igazolt email-fiók."; Layout.fillWidth: true; color: "#cad3f5" }
                            Button { text: "Fiók / provider beállítása"; enabled: false }
                        }
                    }
                    Label { text: "A küldés csak Secret Broker + provider admission + DLP + approval + audit gate PASS után engedélyezett."; color: "#a5adcb"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                }
            }

            Frame {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Kontaktok"; font.pixelSize: 28; font.bold: true }
                    Label { text: "Közös Contact Fabric — személyek, szervezetek, csoportok és projektkapcsolatok."; color: "#a5adcb" }
                    TextField { Layout.fillWidth: true; placeholderText: "Kontakt keresése"; enabled: false }
                    Label { text: "Nincs betöltött kontakt-adatforrás."; color: "#838ba7" }
                    Item { Layout.fillHeight: true }
                }
            }

            Frame {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Közös postaládák"; font.pixelSize: 28; font.bold: true }
                    Label { text: "Assignment · belső megjegyzés · prioritás · shared draft · collision policy"; color: "#a5adcb" }
                    Label { text: "Current Host provider admission szükséges."; color: "#f5a97f" }
                    Item { Layout.fillHeight: true }
                }
            }

            Frame {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Csapatmunka"; font.pixelSize: 28; font.bold: true }
                    Label { text: "A jogosultság felhasználó ∩ szerepkör ∩ alkalmazás ∩ kontextus ∩ adatbesorolás metszete."; color: "#a5adcb"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                }
            }

            Frame {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Kommunikációs előzmények"; font.pixelSize: 28; font.bold: true }
                    Label { text: "Projekt-, feladat-, meeting-, ügyfél- és produkciókapcsolatok egy canonical relation rétegen."; color: "#a5adcb"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                }
            }

            Frame {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Biztonság"; font.pixelSize: 28; font.bold: true }
                    Label { text: "FAIL-CLOSED"; color: "#ed8796"; font.bold: true }
                    Label { text: "Identity · AuthN/AuthZ · Context/Scope · Layer Guard · Privacy · Secret Broker · Attachment · Anti-Phishing · DLP · Audit/Evidence · Current Host"; color: "#a5adcb"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Label { text: root.aiEnabled ? "AI kapcsoló: ON — a további AI gate-ek ettől még kötelezőek." : "AI kapcsoló: OFF — modell/provider hívás tiltott."; color: root.aiEnabled ? "#eed49f" : "#8bd5ca"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Label { text: "Külső email tartalom UNTRUSTED INPUT; nem válhat rendszerutasítássá vagy tool-authorityvá."; color: "#c6d0f5"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
