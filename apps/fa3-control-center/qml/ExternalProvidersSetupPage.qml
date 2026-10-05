import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property string draftResult: ""

    function boolPref(key, fallback) {
        var v = fa3Preferences.value(key, fallback)
        return v === true || String(v).toLowerCase() === "true" || String(v) === "1"
    }

    function providerRequested(id) {
        return boolPref("externalProviders/provider/" + id, false)
    }

    function filteredProviders() {
        var needle = providerSearch.text.trim().toLowerCase()
        return fa3Repository.recordsByCategory("provider").filter(function(v) {
            var h = (v.id + " " + v.title + " " + v.status).toLowerCase()
            return needle.length === 0 || h.indexOf(needle) >= 0
        })
    }

    function createPolicyDraft() {
        draftResult = fa3Repository.createDraftChangeSet(
                    "EXTERNAL_PROVIDER_GOVERNANCE",
                    "propose.external-provider-policy",
                    "external-providers",
                    "Requested global external/paid provider availability=" + globalEnable.checked + "; monthly budget=" + monthlyBudget.value + ". Effective egress and credential access remain approval-gated.")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: "External Providers Setup"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
            Label {
                text: "Külső és fizetős provider-ek engedélyezési, credential-state és költségkeret felülete. Alapértelmezés: kikapcsolva."
                color: root.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 120
            radius: 9
            color: root.panel
            border.color: globalEnable.checked ? root.orange : root.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Label { text: "Külső / fizetős provider-ek"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                        Label { text: "A kapcsoló csak operátori engedélyezési szándékot tárol; önmagában nem nyit egress-t és nem ad credential hozzáférést."; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    Switch {
                        id: globalEnable
                        checked: root.boolPref("externalProviders/enabled", false)
                        text: checked ? "ENGEDÉLYEZVE (REQUESTED)" : "TILTVA"
                        onToggled: fa3Preferences.setValue("externalProviders/enabled", checked)
                    }
                }
                RowLayout {
                    Label { text: "Havi költségkeret:"; color: root.textMuted; font.pixelSize: 9 }
                    SpinBox {
                        id: monthlyBudget
                        from: 0; to: 1000000
                        value: Number(fa3Preferences.value("externalProviders/monthlyBudget", 0))
                        editable: true
                        onValueModified: fa3Preferences.setValue("externalProviders/monthlyBudget", value)
                    }
                    Label { text: "0 = nincs fizetős provider költség engedélyezve"; color: root.orange; font.pixelSize: 8 }
                    Item { Layout.fillWidth: true }
                    Button { text: "Policy ChangeSet-tervezet"; onClicked: root.createPolicyDraft() }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Rectangle {
                Layout.fillWidth: true; implicitHeight: 72; radius: 8; color: root.panel; border.color: root.border
                ColumnLayout { anchors.fill: parent; anchors.margins: 10; spacing: 3
                    Label { text: "Credential storage"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "BROKER / SECRETREF ONLY"; color: root.green; font.pixelSize: 10; font.bold: true }
                }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: 72; radius: 8; color: root.panel; border.color: root.border
                ColumnLayout { anchors.fill: parent; anchors.margins: 10; spacing: 3
                    Label { text: "Raw token/API key"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "FORBIDDEN IN GUI STORAGE"; color: root.magenta; font.pixelSize: 10; font.bold: true }
                }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: 72; radius: 8; color: root.panel; border.color: root.border
                ColumnLayout { anchors.fill: parent; anchors.margins: 10; spacing: 3
                    Label { text: "Effective egress"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "FAIL-CLOSED / APPROVAL-GATED"; color: root.orange; font.pixelSize: 10; font.bold: true }
                }
            }
        }

        TextField {
            id: providerSearch
            Layout.fillWidth: true
            placeholderText: "Canonical provider keresése…"
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 270
            radius: 9
            color: root.panel
            border.color: root.border

            ListView {
                anchors.fill: parent
                anchors.margins: 8
                anchors.rightMargin: 12
                clip: true
                model: root.filteredProviders()
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                delegate: ItemDelegate {
                    width: ListView.view.width - 12
                    height: 60
                    background: Rectangle { color: hovered ? root.panelRaised : "transparent"; radius: 5 }
                    contentItem: RowLayout {
                        CheckBox {
                            checked: root.providerRequested(modelData.id)
                            enabled: globalEnable.checked
                            onToggled: fa3Preferences.setValue("externalProviders/provider/" + modelData.id, checked)
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 1
                            Label { text: modelData.id; color: root.textPrimary; font.family: "monospace"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: modelData.title; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                        Label { text: modelData.status || "REGISTERED"; color: root.textMuted; font.pixelSize: 8; Layout.preferredWidth: 145; elide: Text.ElideRight }
                        Label { text: root.providerRequested(modelData.id) ? "REQUESTED" : "OFF"; color: root.providerRequested(modelData.id) ? root.orange : root.textMuted; font.pixelSize: 8; font.bold: true; Layout.preferredWidth: 80 }
                    }
                }
            }
        }

        Label {
            text: "A provider-kapcsoló nem jelent runtime admissiont. Credential csak provider-semleges SecretRef/vault/broker útvonalon használható; plaintext API key, OAuth/JWT/session token nem kerülhet QSettings-be, repository configba, logba vagy Evidence-be."
            color: root.orange; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        Label { visible: root.draftResult.length > 0; text: root.draftResult; color: root.accent; font.pixelSize: 9; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
    }
}
