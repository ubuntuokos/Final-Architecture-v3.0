import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    // GUI profile identity. This surface never becomes runtime/canonical authority.
    readonly property string profileId: "FA3-GUI-LANGUAGE-CONTROL-001"

    required property var settings
    required property color surface1
    required property color surface2
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    // Runtime projection contract. The backend may bind these values.
    property string userLanguage: settings.value("languageControl/userLanguage", "auto")
    property string outputLanguage: settings.value("languageControl/outputLanguage", "same-as-input")
    property var nativeLanguages: []
    property var mediatedLanguages: []
    property string executionLanguage: "UNKNOWN"
    property bool mediationRequired: false
    property string mediationPath: "PENDING_BACKEND"
    property string translatorProvider: "PENDING_BACKEND"
    property string dataClassification: "INTERNAL"
    property bool cloudRequested: settings.value("languageControl/cloudRequested", false)
    property bool cloudEffective: false
    property string validationStatus: "PENDING_BACKEND"
    property real confidence: -1
    property string evidenceId: "PENDING_BACKEND"
    property string protectedTokenStatus: "PENDING_BACKEND"
    property string speechRoute: "PENDING_BACKEND"

    // User preferences. Runtime policy remains authoritative.
    property bool preferNative: settings.value("languageControl/preferNative", true)
    property bool allowMediated: settings.value("languageControl/allowMediated", true)
    property bool localFirst: settings.value("languageControl/localFirst", true)
    property string validationMode: settings.value("languageControl/validationMode", "critical")
    property string viewMode: settings.value("languageControl/viewMode", "user")

    function t(hu, en) {
        return language === "en" ? en : hu
    }

    function px(value) {
        return Math.max(9, Math.round(value * fontScale))
    }

    function languageList(values) {
        return values && values.length > 0 ? values.join(", ") : "UNKNOWN"
    }

    function confidenceText() {
        if (confidence < 0)
            return "UNKNOWN"
        return Math.round(confidence * 100) + "%"
    }

    function statusColor(status) {
        const normalized = String(status).toUpperCase()
        if (normalized === "PASS" || normalized === "ALLOWED")
            return "#55a868"
        if (normalized === "FAIL" || normalized === "DENIED")
            return "#c85c5c"
        return "#d99b32"
    }

    component Card: Rectangle {
        radius: Math.round(12 * root.uiScale)
        color: root.surface1
        border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
    }

    component FieldRow: RowLayout {
        property string fieldLabel: ""
        property string fieldValue: "UNKNOWN"
        property color valueColor: root.textPrimary
        Layout.fillWidth: true
        spacing: 12

        Label {
            text: parent.fieldLabel
            color: root.textMuted
            font.pixelSize: root.px(11)
            Layout.preferredWidth: Math.round(190 * root.uiScale)
        }
        Label {
            text: parent.fieldValue
            color: parent.valueColor
            font.pixelSize: root.px(12)
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 16

            Item { Layout.preferredHeight: 20 }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Label {
                        text: root.t("Nyelvi vezérlés", "Language Control")
                        font.pixelSize: root.px(24)
                        font.bold: true
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.t(
                            "Natív és FA3-közvetített modellnyelvek, routing, policy és evidence megfigyelése. A GUI nem policy-authority.",
                            "Observe native and FA3-mediated model languages, routing, policy and evidence. The GUI is not a policy authority."
                        )
                        color: root.textMuted
                        font.pixelSize: root.px(12)
                        wrapMode: Text.WordWrap
                    }
                }

                Label {
                    text: root.profileId + " · P0/MUST"
                    color: root.accent
                    font.pixelSize: root.px(10)
                    font.bold: true
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.preferredHeight: Math.round(74 * root.uiScale)

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 12

                    Label { text: root.t("Nézet", "View"); color: root.textMuted }
                    ComboBox {
                        model: ["user", "expert", "admin"]
                        currentIndex: root.viewMode === "expert" ? 1 : root.viewMode === "admin" ? 2 : 0
                        onActivated: {
                            root.viewMode = currentText
                            root.settings.setValue("languageControl/viewMode", currentText)
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        text: root.t("Static GUI i18n ≠ runtime Language Bridge", "Static GUI i18n ≠ runtime Language Bridge")
                        color: root.textMuted
                        font.pixelSize: root.px(10)
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.preferredHeight: Math.round(230 * root.uiScale)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    Label {
                        text: root.t("Felhasználói nyelv", "User language")
                        font.pixelSize: root.px(16)
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: root.t("Bemenet", "Input"); Layout.preferredWidth: Math.round(160 * root.uiScale) }
                        ComboBox {
                            Layout.preferredWidth: Math.round(220 * root.uiScale)
                            editable: true
                            model: ["auto", "hu", "en", "de", "fr", "es", "it", "pl", "ja", "zh"]
                            currentIndex: Math.max(0, model.indexOf(root.userLanguage))
                            onActivated: {
                                root.userLanguage = currentText
                                root.settings.setValue("languageControl/userLanguage", currentText)
                            }
                            onAccepted: {
                                root.userLanguage = editText
                                root.settings.setValue("languageControl/userLanguage", editText)
                            }
                        }
                        Label { text: root.t("Kimenet", "Output"); Layout.preferredWidth: Math.round(100 * root.uiScale) }
                        ComboBox {
                            Layout.preferredWidth: Math.round(220 * root.uiScale)
                            editable: true
                            model: ["same-as-input", "hu", "en", "de", "fr", "es", "it", "pl", "ja", "zh"]
                            currentIndex: Math.max(0, model.indexOf(root.outputLanguage))
                            onActivated: {
                                root.outputLanguage = currentText
                                root.settings.setValue("languageControl/outputLanguage", currentText)
                            }
                            onAccepted: {
                                root.outputLanguage = editText
                                root.settings.setValue("languageControl/outputLanguage", editText)
                            }
                        }
                    }

                    CheckBox {
                        text: root.t("Natív modellnyelv előnyben", "Prefer native model language")
                        checked: root.preferNative
                        onToggled: {
                            root.preferNative = checked
                            root.settings.setValue("languageControl/preferNative", checked)
                        }
                    }
                    CheckBox {
                        text: root.t("Közvetített modell engedélyezése", "Allow mediated model language")
                        checked: root.allowMediated
                        onToggled: {
                            root.allowMediated = checked
                            root.settings.setValue("languageControl/allowMediated", checked)
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.preferredHeight: Math.round(270 * root.uiScale)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9

                    Label {
                        text: root.t("Modellnyelvi capability", "Model language capability")
                        font.pixelSize: root.px(16)
                        font.bold: true
                    }
                    FieldRow { fieldLabel: root.t("Natív nyelvek", "Native languages"); fieldValue: root.languageList(root.nativeLanguages) }
                    FieldRow { fieldLabel: root.t("Közvetített nyelvek", "Mediated languages"); fieldValue: root.languageList(root.mediatedLanguages) }
                    FieldRow { fieldLabel: root.t("Végrehajtási nyelv", "Execution language"); fieldValue: root.executionLanguage }
                    FieldRow { fieldLabel: root.t("Közvetítés szükséges", "Mediation required"); fieldValue: root.mediationRequired ? "YES" : "NO" }
                    FieldRow { fieldLabel: root.t("Útvonal", "Route"); fieldValue: root.mediationPath }
                    FieldRow { fieldLabel: root.t("Fordító provider", "Translation provider"); fieldValue: root.translatorProvider }
                }
            }

            Card {
                visible: root.viewMode !== "user"
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.preferredHeight: Math.round(300 * root.uiScale)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9

                    Label {
                        text: root.t("Policy & validáció", "Policy & validation")
                        font.pixelSize: root.px(16)
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: root.t("Adatbesorolás", "Data classification"); Layout.preferredWidth: Math.round(190 * root.uiScale) }
                        ComboBox {
                            model: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
                            currentIndex: Math.max(0, model.indexOf(root.dataClassification))
                            // Selection is an operator intent only. Backend policy remains authoritative.
                            onActivated: root.dataClassification = currentText
                        }
                    }

                    CheckBox {
                        text: "Local-first"
                        checked: root.localFirst
                        onToggled: {
                            root.localFirst = checked
                            root.settings.setValue("languageControl/localFirst", checked)
                        }
                    }
                    CheckBox {
                        text: root.t("Cloud fordítás kérése", "Request cloud translation")
                        checked: root.cloudRequested
                        onToggled: {
                            root.cloudRequested = checked
                            root.settings.setValue("languageControl/cloudRequested", checked)
                        }
                    }

                    FieldRow {
                        fieldLabel: root.t("Cloud effektív", "Cloud effective")
                        fieldValue: root.dataClassification === "SECRET"
                                    ? "DENIED_BY_CONTRACT"
                                    : (root.cloudEffective ? "ALLOWED" : "PENDING_BACKEND")
                        valueColor: root.statusColor(fieldValue)
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: root.t("Szemantikai validáció", "Semantic validation"); Layout.preferredWidth: Math.round(190 * root.uiScale) }
                        ComboBox {
                            model: ["critical", "always"]
                            currentIndex: root.validationMode === "always" ? 1 : 0
                            onActivated: {
                                root.validationMode = currentText
                                root.settings.setValue("languageControl/validationMode", currentText)
                            }
                        }
                    }

                    FieldRow {
                        fieldLabel: root.t("Validációs státusz", "Validation status")
                        fieldValue: root.validationStatus
                        valueColor: root.statusColor(root.validationStatus)
                    }
                    FieldRow { fieldLabel: root.t("Megbízhatóság", "Confidence"); fieldValue: root.confidenceText() }
                }
            }

            Card {
                visible: root.viewMode === "admin"
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                Layout.preferredHeight: Math.round(270 * root.uiScale)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 9

                    Label {
                        text: root.t("Provenance & evidence", "Provenance & evidence")
                        font.pixelSize: root.px(16)
                        font.bold: true
                    }
                    FieldRow { fieldLabel: "Evidence ID"; fieldValue: root.evidenceId }
                    FieldRow {
                        fieldLabel: root.t("Védett tokenek", "Protected tokens")
                        fieldValue: root.protectedTokenStatus
                        valueColor: root.statusColor(root.protectedTokenStatus)
                    }
                    FieldRow { fieldLabel: root.t("Beszéd útvonal", "Speech route"); fieldValue: root.speechRoute }
                    Label {
                        Layout.fillWidth: true
                        text: root.t(
                            "Az eredeti input authoritative. A fordítás derived projection. A GUI UNKNOWN/PENDING_BACKEND értéket soha nem jelenít meg PASS-ként.",
                            "Original input remains authoritative. Translation is a derived projection. The GUI never renders UNKNOWN/PENDING_BACKEND as PASS."
                        )
                        color: "#d99b32"
                        wrapMode: Text.WordWrap
                        font.pixelSize: root.px(11)
                    }
                }
            }

            Label {
                visible: root.dataClassification === "SECRET" && root.cloudRequested
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                text: root.t(
                    "SECRET adatnál a külső fordítás canonical szerződés szerint tiltott. A GUI-kérés nem írhatja felül ezt a szabályt.",
                    "External translation is forbidden for SECRET data by canonical contract. A GUI request cannot override this rule."
                )
                color: "#c85c5c"
                wrapMode: Text.WordWrap
                font.pixelSize: root.px(12)
                font.bold: true
            }

            Item { Layout.preferredHeight: 24 }
        }
    }
}
