import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color panel: "#0b1728"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: "Skill Fabric Inspector"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    text: "Canonical registry + local static reference gate · read-only · no skill execution"
                    color: root.textMuted
                    font.pixelSize: 10
                }
            }
            Button {
                text: "Frissítés"
                Accessible.name: "Skill Fabric állapot frissítése"
                onClicked: fa3SkillFabric.refresh()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 114
            radius: 8
            color: root.panel
            border.color: root.border

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 6
                Label {
                    Layout.fillWidth: true
                    text: "Registry: " + fa3SkillFabric.registryState
                    color: root.accent
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    text: "Helyi statikus gate: " + fa3SkillFabric.referenceGateState
                    color: fa3SkillFabric.referenceGateState === "STATIC_REFERENCE_PASS" ? root.green : root.orange
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    text: "CURRENT-HOST: NINCS IGAZOLVA. Ez a nézet nem ellenőrzi és nem helyettesíti a fizikai bizonyítékot."
                    color: root.orange
                    font.pixelSize: 10
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: fa3SkillFabric.lastError.length > 0
            text: fa3SkillFabric.lastError
            color: root.orange
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Nyilvántartott skillek"; color: root.textPrimary; font.pixelSize: 15; font.bold: true }
            Item { Layout.fillWidth: true }
            Label {
                text: fa3SkillFabric.skills.length + " bejegyzés"
                color: root.textMuted
                font.pixelSize: 10
            }
        }

        Label {
            Layout.fillWidth: true
            visible: fa3SkillFabric.skills.length === 0
            text: "Nem áll rendelkezésre ellenőrzött helyi skill-regiszter. Nem következtetünk automatikusan aktív skillekre."
            color: root.orange
            wrapMode: Text.WordWrap
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 6
            model: fa3SkillFabric.skills
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 84
                radius: 8
                color: root.panel
                border.color: root.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Label {
                            text: modelData.skill_id
                            color: root.textPrimary
                            font.pixelSize: 13
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Label {
                            text: modelData.admission_status
                            color: modelData.admission_status === "ADMITTED" ? root.green : root.orange
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "v" + modelData.version + " · " + modelData.distribution_class
                              + " · " + (modelData.task_scoped ? "feladathoz kötött" : "scope nem igazolt")
                        color: root.textMuted
                        font.pixelSize: 10
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "Aktiválás/felhasználás: nincs current-host bizonyíték ebben a nézetben."
                        color: root.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: "A registry-beli ADMITTED metadata nem futtatási jogosultság. Minden felhasználás külön kiválasztást, jóváhagyást, hash-ellenőrzést és aktív feladatbérletet igényel."
            color: root.textMuted
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Label {
            Layout.fillWidth: true
            text: fa3SkillFabric.reportSha256.length > 0
                  ? "Helyi referenciajelentés SHA-256: " + fa3SkillFabric.reportSha256
                  : "Nem érhető el helyi referenciajelentés."
            color: root.textMuted
            font.pixelSize: 9
            wrapMode: Text.WrapAnywhere
        }
    }
}
