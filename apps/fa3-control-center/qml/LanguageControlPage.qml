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
    readonly property string policyId: "FA3-LANGUAGE-POLICY-001"
    readonly property string fabricId: "FA3-LANGUAGE-FABRIC-001"

    // System-language policy. Empty values represent an installation/migration state
    // that MUST be completed before language admission can be considered satisfied.
    property string primaryLanguage: String(preferences.value("languagePolicy/primaryLanguage", ""))
    property string secondaryLanguage: String(preferences.value("languagePolicy/secondaryLanguage", ""))
    property string additionalLanguages: String(preferences.value("languagePolicy/additionalLanguages", ""))
    readonly property bool systemLanguageValid: primaryLanguage.length > 0
                                                && secondaryLanguage.length > 0
                                                && primaryLanguage !== secondaryLanguage

    // Request-level language controls remain separate from the mandatory system pair.
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

    function setPrimaryLanguage(value) {
        if (value.length === 0 || value === secondaryLanguage)
            return
        primaryLanguage = value
        save("languagePolicy/primaryLanguage", value)
    }

    function setSecondaryLanguage(value) {
        if (value.length === 0 || value === primaryLanguage)
            return
        secondaryLanguage = value
        save("languagePolicy/secondaryLanguage", value)
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
                    text: root.profileId + " · " + root.bridgeId + " · " + root.policyId + " · P0/MUST"
                    color: root.accent
                    font.pixelSize: 9
                    font.bold: true
                }
            }

            Card {
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Layout.preferredHeight: 294
                border.color: root.systemLanguageValid ? root.border : root.orange
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Rendszernyelvek"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                        Label {
                            text: root.systemLanguageValid ? "CONFIGURED" : "REQUIRED"
                            color: root.systemLanguageValid ? root.green : root.orange
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: "Az FA3 minden telepítésén pontosan egy elsődleges és egy ettől eltérő másodlagos nyelv kötelező. A további nyelvek opcionálisak."
                        color: root.textMuted
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Elsődleges"; color: root.textMuted; Layout.preferredWidth: 130 }
                        ComboBox {
                            Layout.fillWidth: true
                            editable: true
                            model: ["", "hu-HU", "en-US", "de-DE", "fr-FR", "es-ES", "it-IT", "pl-PL", "ja-JP", "zh-CN"]
                            currentIndex: Math.max(0, model.indexOf(root.primaryLanguage))
                            onActivated: root.setPrimaryLanguage(currentText)
                            onAccepted: root.setPrimaryLanguage(editText)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Másodlagos"; color: root.textMuted; Layout.preferredWidth: 130 }
                        ComboBox {
                            Layout.fillWidth: true
                            editable: true
                            model: ["", "hu-HU", "en-US", "de-DE", "fr-FR", "es-ES", "it-IT", "pl-PL", "ja-JP", "zh-CN"]
                            currentIndex: Math.max(0, model.indexOf(root.secondaryLanguage))
                            onActivated: root.setSecondaryLanguage(currentText)
                            onAccepted: root.setSecondaryLanguage(editText)
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "További (0..N)"; color: root.textMuted; Layout.preferredWidth: 130 }
                        TextField {
                            Layout.fillWidth: true
                            text: root.additionalLanguages
                            placeholderText: "pl. de-DE, fr-FR"
                            onEditingFinished: {
                                root.additionalLanguages = text
                                root.save("languagePolicy/additionalLanguages", text)
                            }
                        }
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.primaryLanguage === root.secondaryLanguage && root.primaryLanguage.length > 0
                              ? "Az elsődleges és másodlagos nyelv nem lehet azonos."
                              : (root.systemLanguageValid
                                 ? "A két kötelező rendszernyelv érvényes. A backend admission igazolja a natív vagy Language Fabric által közvetített működőképességet."
                                 : "A nyelvi konfiguráció befejezetlen; admission és production állapot nem lehet PASS.")
                        color: root.systemLanguageValid ? root.textMuted : root.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
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
                    Label { text: "Kérés-szintű nyelv"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
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
                        Label { text: "Language Fabric / Bridge állapot"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
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
                Layout.preferredHeight: 86
                radius: 8
                color: root.panelRaised
                border.color: root.border
                Label {
                    anchors.fill: parent
                    anchors.margins: 12
                    text: "Az eredeti input authoritative; a fordítás derived projection. UNKNOWN / PENDING_BACKEND állapot soha nem jelent PASS-t. A GUI nem policy-authority. A LiteLLM nyelvsemleges gateway; a nyelvi döntést a Language Fabric végzi."
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
