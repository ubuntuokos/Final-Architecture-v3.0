import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property string contextLabel: "FA3 / Humanizer"
    property string preferenceScope: "USER"
    property color bg: "#07111f"
    property color panel: "#0b1728"
    property color raised: "#10243a"
    property color border: "#1d3850"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8aa0b5"
    property color accent: "#25a7ff"
    property color warning: "#f0b14a"

    Rectangle { anchors.fill: parent; color: root.bg }

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            Label {
                text: "Humanizer settings"
                color: root.textPrimary
                font.pixelSize: 22
                font.bold: true
            }
            Label {
                text: root.contextLabel + " · shared settings service · " + fa3Humanizer.fabricState
                color: root.textMuted
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: generalColumn.implicitHeight + 24
                radius: 7
                color: root.panel
                border.color: root.border

                ColumnLayout {
                    id: generalColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Switch {
                        text: "AI functions enabled"
                        checked: fa3Humanizer.aiEnabled
                        onToggled: fa3Humanizer.setPreference(root.preferenceScope, "ai_enabled", checked)
                    }
                    Label {
                        text: fa3Humanizer.aiEnabled
                              ? "AI requests still require UAF → Model Router → HRB admission."
                              : "AI OFF: no model or provider execution is permitted."
                        color: fa3Humanizer.aiEnabled ? root.textMuted : root.warning
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }

                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true

                        Label { text: "Language"; color: root.textMuted }
                        ComboBox {
                            Layout.fillWidth: true
                            model: fa3Humanizer.languages
                            Component.onCompleted: currentIndex = Math.max(0, model.indexOf(fa3Humanizer.language))
                            onActivated: fa3Humanizer.setPreference(root.preferenceScope, "language", currentText)
                        }

                        Label { text: "Register"; color: root.textMuted }
                        ComboBox {
                            Layout.fillWidth: true
                            model: fa3Humanizer.registerProfiles
                            Component.onCompleted: currentIndex = Math.max(0, model.indexOf(fa3Humanizer.registerProfile))
                            onActivated: fa3Humanizer.setPreference(root.preferenceScope, "register_profile", currentText)
                        }

                        Label { text: "Edit budget"; color: root.textMuted }
                        ComboBox {
                            Layout.fillWidth: true
                            model: fa3Humanizer.editBudgets
                            Component.onCompleted: currentIndex = Math.max(0, model.indexOf(fa3Humanizer.editBudget))
                            onActivated: fa3Humanizer.setPreference(root.preferenceScope, "edit_budget", currentText)
                        }

                        Label { text: "Author voice profile"; color: root.textMuted }
                        TextField {
                            Layout.fillWidth: true
                            text: fa3Humanizer.voiceProfile
                            placeholderText: "Optional profile ID"
                            onEditingFinished: fa3Humanizer.setPreference(root.preferenceScope, "voice_profile", text)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: preserveColumn.implicitHeight + 24
                radius: 7
                color: root.panel
                border.color: root.border

                ColumnLayout {
                    id: preserveColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    Label { text: "Protected content"; color: root.textPrimary; font.bold: true }
                    CheckBox {
                        text: "Preserve numbers"
                        checked: fa3Humanizer.protectNumbers
                        onToggled: fa3Humanizer.setPreference(root.preferenceScope, "preserve_numbers", checked)
                    }
                    CheckBox {
                        text: "Preserve URLs"
                        checked: fa3Humanizer.protectUrls
                        onToggled: fa3Humanizer.setPreference(root.preferenceScope, "preserve_urls", checked)
                    }
                    CheckBox {
                        text: "Preserve quotations"
                        checked: fa3Humanizer.protectQuotes
                        onToggled: fa3Humanizer.setPreference(root.preferenceScope, "preserve_quotes", checked)
                    }
                    CheckBox {
                        text: "Preserve citation markers"
                        checked: fa3Humanizer.protectCitations
                        onToggled: fa3Humanizer.setPreference(root.preferenceScope, "preserve_citations", checked)
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: policyColumn.implicitHeight + 24
                radius: 7
                color: root.panel
                border.color: root.border

                ColumnLayout {
                    id: policyColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 7

                    Label { text: "Scope inheritance"; color: root.textPrimary; font.bold: true }
                    Repeater {
                        model: fa3Humanizer.policyLayers
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Label { text: modelData.label; color: root.textPrimary; Layout.fillWidth: true }
                            Label {
                                text: modelData.locked ? "LOCKED / DRAFT ONLY" : "SHARED OVERRIDE"
                                color: modelData.locked ? root.textMuted : root.accent
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }
                    }
                    Label {
                        text: "Global, Host and User/role policy cannot be weakened here. Embedded applications may only use the same shared service with a narrower context."
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: extColumn.implicitHeight + 24
                radius: 7
                color: root.panel
                border.color: root.border

                ColumnLayout {
                    id: extColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6
                    Label { text: "Extension classes"; color: root.textPrimary; font.bold: true }
                    Label {
                        text: "Analyzer · Transformer · Validator · Language · Style · Register · Genre · Author Voice · Metric · Grammar · Terminology · Detector · Document Adapter"
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Label {
                        text: "Discovery never equals admission or activation."
                        color: root.warning
                    }
                }
            }
        }
    }
}
