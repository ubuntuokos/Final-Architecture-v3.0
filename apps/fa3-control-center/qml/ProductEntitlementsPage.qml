// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property var controller

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: "My FA3"
                    font.pixelSize: 22
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Frissítés"
                    onClicked: root.controller.refresh()
                }
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Read-only termékprojekció. Az Operating Level a működési hatókört jelenti; az alkalmazások külön entitlementek. Ez a felület nem ad runtime-, provider-, hardver-, security- vagy license-jogosultságot."
            }

            Label {
                Layout.fillWidth: true
                color: root.controller.lastError.length > 0 ? "#f0b14a" : "#8da2b8"
                text: "Állapot: " + root.controller.status +
                      (root.controller.lastError.length > 0 ? " · " + root.controller.lastError : "")
            }

            GroupBox {
                title: "Operating Levels"
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Repeater {
                        model: root.controller.operatingLevels
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                text: modelData.level_id
                                font.bold: true
                                Layout.preferredWidth: 150
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: (modelData.scope || []).join(" · ")
                            }
                            Label {
                                text: "rank " + modelData.rank
                                color: "#8da2b8"
                            }
                        }
                    }
                }
            }

            GroupBox {
                title: "Egyenként választható alkalmazások"
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Repeater {
                        model: root.controller.applications
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                text: modelData.name
                                font.bold: true
                                Layout.preferredWidth: 280
                                elide: Text.ElideRight
                            }
                            Label {
                                text: modelData.minimum_operating_level
                                Layout.preferredWidth: 130
                            }
                            Label {
                                text: modelData.portfolio_state
                                color: "#8da2b8"
                                Layout.preferredWidth: 110
                            }
                            Label {
                                Layout.fillWidth: true
                                text: modelData.application_class
                                color: "#8da2b8"
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            GroupBox {
                title: "Opcionális Domain Packok"
                Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent
                    Repeater {
                        model: root.controller.domainPacks
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: modelData.name
                                font.bold: true
                                Layout.preferredWidth: 300
                            }
                            Label {
                                text: (modelData.applications || []).length + " alkalmazás"
                                Layout.preferredWidth: 120
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "Opcionális bundle · egyedi alkalmazásválasztás megmarad"
                                color: "#8da2b8"
                            }
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: "#8da2b8"
                text: "A tényleges futtatást továbbra is a Security, License & Rights, HRB, Model Router, Engine/Provider admission és Evidence rétegek szabályozzák."
            }
        }
    }
}
