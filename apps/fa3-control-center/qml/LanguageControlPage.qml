import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var preferences
    required property color panel
    required property color panelRaised
    required property color border
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property color green
    required property color orange

    readonly property string profileId: "FA3-GUI-LANGUAGE-CONTROL-001"
    readonly property string bridgeId: "FA3-LANGUAGE-BRIDGE-001"

    property string primaryLanguage: String(preferences.value("languageControl/primaryLanguage", ""))
    property string secondaryLanguage: String(preferences.value("languageControl/secondaryLanguage", ""))
    property string additionalLanguages: String(preferences.value("languageControl/additionalLanguages", ""))
    readonly property bool systemLanguageValid: primaryLanguage.length > 0 && secondaryLanguage.length > 0 && primaryLanguage !== secondaryLanguage

    function setPrimaryLanguage(value) {
        const normalized = String(value).trim()
        if (normalized.length === 0 || normalized === secondaryLanguage) return false
        primaryLanguage = normalized
        save("languageControl/primaryLanguage", normalized)
        return true
    }

    function setSecondaryLanguage(value) {
        const normalized = String(value).trim()
        if (normalized.length === 0 || normalized === primaryLanguage) return false
        secondaryLanguage = normalized
        save("languageControl/secondaryLanguage", normalized)
        return true
    }

    property string inputLanguage: String(preferences.value("languageControl/userLanguage", "auto"))
    property string outputLanguage: String(preferences.value("languageControl/outputLanguage", "same-as-input"))
    property bool preferNative: Boolean(preferences.value("languageControl/preferNative", true))
    property bool allowMediated: Boolean(preferences.value("languageControl/allowMediated", true))
    property bool localFirst: Boolean(preferences.value("languageControl/localFirst", true))
    property bool cloudRequested: Boolean(preferences.value("languageControl/cloudRequested", false))
    property string validationMode: String(preferences.value("languageControl/validationMode", "critical"))
    property string dataClassification: String(preferences.value("languageControl/dataClassification", "INTERNAL"))

    function save(key, value) {
        preferences.setValue(key, value)
    }

    component StatusRow: RowLayout {
        property string labelText: ""
        property string valueText: "N/A"
        property color valueTone: root.textPrimary
        Layout.fillWidth: true
        spacing: 12
        Label {
            text: parent.labelText
            color: root.textMuted
            font.pixelSize: 10
            Layout.preferredWidth: 190
        }
        Label {
            text: parent.valueText
            color: parent.valueTone
            font.pixelSize: 10
            font.bold: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }
    }

    component Card: Rectangle {
        Layout.fillWidth: true
        color: root.panel
        border.color: root.border
        radius: 8
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        ColumnLayout {
            width: parent.width
            spacing: 12

            Item { Layout.preferredHeight: 8 }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                spacing: 3
                Label {
                    text: "Tolmács / Nyelvi híd"
                    color: root.textPrimary
                    font.pixelSize: 20
                    font.bold: true
                }
                Label {
                    text: "Human ↔ FA3, FA3 ↔ AI modell, model ↔ model és speech ↔ model nyelvi közvetítés. A natív és közvetített nyelvi képesség külön marad."
                    color: root.textMuted
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    text: root.profileId + " · " + root.bridgeId + " · P0/MUST"
                    color: root.accent
                    font.pixelSize: 9
                    font.bold: true
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 250
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Rendszernyelvek"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                        Label { text: root.systemLanguageValid ? "VALID" : "INCOMPLETE"; color: root.systemLanguageValid ? root.green : root.orange; font.pixelSize: 9; font.bold: true }
                    }
                    Label { text: "Pontosan egy Primary és egy ettől különböző Secondary rendszernyelv kötelező. Nincs globálisan hardcoded felhasználói nyelv."; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Primary"; color: root.textMuted; Layout.preferredWidth: 130 }
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: "pl. hu-HU"
                            text: root.primaryLanguage
                            onEditingFinished: root.setPrimaryLanguage(text)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Secondary"; color: root.textMuted; Layout.preferredWidth: 130 }
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: "pl. en-US"
                            text: root.secondaryLanguage
                            onEditingFinished: root.setSecondaryLanguage(text)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Additional"; color: root.textMuted; Layout.preferredWidth: 130 }
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: "0..N BCP47, vesszővel elválasztva"
                            text: root.additionalLanguages
                            onEditingFinished: {
                                root.additionalLanguages = text.trim()
                                root.save("languageControl/additionalLanguages", root.additionalLanguages)
                            }
                        }
                    }
                    Label {
                        visible: !root.systemLanguageValid
                        text: "PENDING: Primary és Secondary értéket kell megadni, és a kettő nem lehet azonos."
                        color: root.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 196
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "Nyelvi beállítás"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Bemeneti nyelv"; color: root.textMuted; Layout.preferredWidth: 130 }
                        ComboBox {
                            Layout.fillWidth: true
                            editable: true
                            model: ["auto", "hu", "en", "de", "fr", "es", "it", "pl", "ja", "zh"]
                            currentIndex: Math.max(0, model.indexOf(root.inputLanguage))
                            onActivated: {
                                root.inputLanguage = currentText
                                root.save("languageControl/userLanguage", currentText)
                            }
                            onAccepted: {
                                root.inputLanguage = editText
                                root.save("languageControl/userLanguage", editText)
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Kimeneti nyelv"; color: root.textMuted; Layout.preferredWidth: 130 }
                        ComboBox {
                            Layout.fillWidth: true
                            editable: true
                            model: ["same-as-input", "hu", "en", "de", "fr", "es", "it", "pl", "ja", "zh"]
                            currentIndex: Math.max(0, model.indexOf(root.outputLanguage))
                            onActivated: {
                                root.outputLanguage = currentText
                                root.save("languageControl/outputLanguage", currentText)
                            }
                            onAccepted: {
                                root.outputLanguage = editText
                                root.save("languageControl/outputLanguage", editText)
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        CheckBox {
                            text: "Natív modellnyelv előnyben"
                            checked: root.preferNative
                            onToggled: { root.preferNative = checked; root.save("languageControl/preferNative", checked) }
                        }
                        CheckBox {
                            text: "Közvetített nyelv engedélyezése"
                            checked: root.allowMediated
                            onToggled: { root.allowMediated = checked; root.save("languageControl/allowMediated", checked) }
                        }
                    }
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 244
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 7
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Language Bridge állapot"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                        Label { text: "ADAPTER-GATED"; color: root.orange; font.pixelSize: 9; font.bold: true }
                    }
                    StatusRow { labelText: "Natív nyelvek"; valueText: "N/A" }
                    StatusRow { labelText: "Közvetített nyelvek"; valueText: "N/A" }
                    StatusRow { labelText: "Végrehajtási nyelv"; valueText: "N/A" }
                    StatusRow { labelText: "Fordítási útvonal"; valueText: "PENDING_BACKEND"; valueTone: root.orange }
                    StatusRow { labelText: "Fordító provider"; valueText: "NOT CONFIGURED"; valueTone: root.orange }
                    StatusRow { labelText: "Szemantikai validáció"; valueText: "PENDING_BACKEND"; valueTone: root.orange }
                    StatusRow { labelText: "Confidence"; valueText: "N/A" }
                    StatusRow { labelText: "Speech route"; valueText: "PENDING_BACKEND"; valueTone: root.orange }
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 224
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "Policy és adatvédelem"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Adatbesorolás"; color: root.textMuted; Layout.preferredWidth: 130 }
                        ComboBox {
                            Layout.fillWidth: true
                            model: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
                            currentIndex: Math.max(0, model.indexOf(root.dataClassification))
                            onActivated: {
                                root.dataClassification = currentText
                                root.save("languageControl/dataClassification", currentText)
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        CheckBox {
                            text: "Local-first"
                            checked: root.localFirst
                            onToggled: { root.localFirst = checked; root.save("languageControl/localFirst", checked) }
                        }
                        CheckBox {
                            text: "Külső/cloud fordítás kérése"
                            checked: root.cloudRequested
                            enabled: root.dataClassification !== "SECRET"
                            onToggled: { root.cloudRequested = checked; root.save("languageControl/cloudRequested", checked) }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Validáció"; color: root.textMuted; Layout.preferredWidth: 130 }
                        ComboBox {
                            Layout.fillWidth: true
                            model: ["critical", "always"]
                            currentIndex: root.validationMode === "always" ? 1 : 0
                            onActivated: { root.validationMode = currentText; root.save("languageControl/validationMode", currentText) }
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.dataClassification === "SECRET"
                              ? "SECRET adatnál a külső fordítás szerződés szerint tiltott."
                              : "A cloud-kérés csak preferencia; a backend policy és provider-adapter dönt a tényleges útvonalról."
                        color: root.dataClassification === "SECRET" ? root.orange : root.textMuted
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 76
                radius: 8
                color: root.panelRaised
                border.color: root.border
                Label {
                    anchors.fill: parent
                    anchors.margins: 12
                    text: "Az eredeti input authoritative; a fordítás derived projection. UNKNOWN / PENDING_BACKEND állapot soha nem jelent PASS-t. A GUI nem policy-authority."
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Item { Layout.preferredHeight: 16 }
        }
    }
}
