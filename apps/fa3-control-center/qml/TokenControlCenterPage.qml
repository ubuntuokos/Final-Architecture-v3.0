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
    property int selectedSection: 0
    property string draftResult: ""
    property var sections: [
        "Áttekintés", "Credentialek", "AI tokenhasználat", "Budgetek", "Provider-ek", "Projektek", "Alkalmazások", "Agentek", "Költségek", "Audit", "Riasztások", "Házirendek"
    ]

    function draft(action, target, rationale) {
        draftResult = fa3Repository.createDraftChangeSet("TOKEN_GOVERNANCE", action, target, rationale)
    }

    component InfoLine: ColumnLayout {
        property string titleText: ""
        property string detailText: ""
        property color tone: root.textMuted
        Layout.fillWidth: true
        spacing: 2
        Label { text: parent.titleText; color: root.textPrimary; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true }
        Label { text: parent.detailText; color: parent.tone; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: "Token Control Center"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
            Label {
                text: "FA3-TOKEN-GOVERNANCE-001 · Credential-titkok és AI-fogyasztási tokenek közös, provider-semleges governance felülete. API tokenek, külső provider belépési titkok és FA3-jelszavak: FA3-SECRET-BROKER-001; raw secret value nem jelenik meg a GUI-ban."
                color: root.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Repeater {
                model: [
                    {title: "Credential values", value: "LUKS2 ENCRYPTED", tone: root.green},
                    {title: "Secret delivery", value: "VAULT / BROKER", tone: root.green},
                    {title: "AI usage", value: "ADAPTER-GATED", tone: root.orange},
                    {title: "Policy", value: "FAIL-CLOSED", tone: root.accent}
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: 76
                    radius: 8
                    color: root.panel
                    border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 3
                        Label { text: modelData.title; color: root.textMuted; font.pixelSize: 8 }
                        Label { text: modelData.value; color: modelData.tone; font.pixelSize: 10; font.bold: true }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                Layout.preferredWidth: 210
                Layout.minimumWidth: 190
                Layout.maximumWidth: 240
                Layout.fillHeight: true
                radius: 9
                color: root.panel
                border.color: root.border

                ListView {
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    spacing: 3
                    model: root.sections
                    currentIndex: root.selectedSection
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                    delegate: ItemDelegate {
                        required property string modelData
                        required property int index
                        width: ListView.view.width - 10
                        height: 38
                        highlighted: index === root.selectedSection
                        onClicked: root.selectedSection = index
                        background: Rectangle { radius: 5; color: highlighted ? root.panelRaised : (hovered ? "#10233a" : "transparent"); border.color: highlighted ? root.accent : "transparent" }
                        contentItem: Label { text: modelData; color: index === root.selectedSection ? root.textPrimary : root.textMuted; font.pixelSize: 10; font.bold: index === root.selectedSection; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 520
                radius: 9
                color: root.panel
                border.color: root.border

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 14
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                    StackLayout {
                        width: parent.availableWidth
                        currentIndex: root.selectedSection

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Két külön tokenréteg"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "1. Credential / access token"; detailText: "API key, OAuth, JWT, session, MCP/service token. Az alkalmazás csak SecretRef/capability handle-t kaphat; tartós plaintext secret tiltott."; tone: root.orange }
                            InfoLine { titleText: "2. AI fogyasztási token"; detailText: "Input, output, context, cache és reasoning tokenhasználat, kvóták, budgetek és költségek. Valós számláló csak runtime/provider telemetry adapterből jelenhet meg."; tone: root.accent }
                            InfoLine { titleText: "Secret runtime"; detailText: "FA3-SECRET-BROKER-001 materialized · generikus nevű külön LUKS2 image · desktop/display-server agnostic core · production promotion requires real current-host E2E."; tone: root.green }
                            InfoLine { titleText: "Usage telemetry"; detailText: "Valós tokenhasználat/költség továbbra is N/A, amíg admitted telemetry adapter nincs."; tone: root.textMuted }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Credentialek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Security boundary"; detailText: "Raw FA3 credential-secret a külön, generikus nevű titkosított image-ben marad; token, külső provider belépési titok és jelszó nem kerülhet QSettings-be, Session Vault raw credential könyvtárba, repository configba, logba, telemetry-be vagy Evidence-be."; tone: root.magenta }
                            TextField { id: credentialProvider; Layout.fillWidth: true; placeholderText: "Provider ID (metadata only)" }
                            TextField { id: credentialRef; Layout.fillWidth: true; placeholderText: "SecretRef / credential handle (nem secret value)" }
                            ComboBox { id: credentialKind; Layout.preferredWidth: 260; model: ["API key handle", "OAuth handle", "JWT handle", "Session handle", "MCP/service token handle"] }
                            Button {
                                text: "Credential binding ChangeSet-tervezet"
                                onClicked: root.draft("propose.credential.binding", credentialProvider.text.length ? credentialProvider.text : "provider", "Bind " + credentialKind.currentText + " via SecretRef=" + credentialRef.text + "; no raw secret storage")
                            }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "AI tokenhasználat"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Input tokens"; detailText: "N/A — telemetry adapter not admitted"; tone: root.orange }
                            InfoLine { titleText: "Output tokens"; detailText: "N/A — telemetry adapter not admitted"; tone: root.orange }
                            InfoLine { titleText: "Context / cache / reasoning"; detailText: "N/A — runtime/provider telemetry required"; tone: root.orange }
                            InfoLine { titleText: "No synthetic counters"; detailText: "A GUI nem becsül és nem gyárt tokenhasználati adatot bizonyíték nélkül."; tone: root.green }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Budgetek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            RowLayout {
                                Label { text: "Napi token budget:"; color: root.textMuted }
                                SpinBox { id: dailyTokens; from: 0; to: 1000000000; value: 0; editable: true }
                            }
                            RowLayout {
                                Label { text: "Havi token budget:"; color: root.textMuted }
                                SpinBox { id: monthlyTokens; from: 0; to: 2000000000; value: 0; editable: true }
                            }
                            RowLayout {
                                Label { text: "Max context / request:"; color: root.textMuted }
                                SpinBox { id: contextBudget; from: 0; to: 10000000; value: 0; editable: true }
                            }
                            Button { text: "Budget policy ChangeSet-tervezet"; onClicked: root.draft("propose.token.budget", "global-token-budget", "daily=" + dailyTokens.value + "; monthly=" + monthlyTokens.value + "; max_context=" + contextBudget.value) }
                            Label { text: "0 = nincs külön GUI-ból kért keret; ez nem jelent korlátlan külső költési engedélyt."; color: root.orange; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Provider-ek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Provider projection"; detailText: "Providerenként credential-handle, kvóta, tokenhasználat és költség csak engedélyezett adapterből jelenhet meg."; tone: root.accent }
                            Button { text: "Provider-token reconciliation tervezet"; onClicked: root.draft("propose.token.provider-reconciliation", "external-providers", "Reconcile provider token/credential governance with External Providers Setup") }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Projektek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Project budget"; detailText: "Projekt-szintű tokenkeret és attribution a Journal/Evidence azonosítókkal kapcsolható össze; jelenleg adapter-gated."; tone: root.textMuted }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Alkalmazások"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Application attribution"; detailText: "FA3 kliensenkénti credential capability és tokenhasználat csak broker + telemetry evidence alapján."; tone: root.textMuted }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Agentek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Agent budget"; detailText: "Agentenkénti input/output/context budget, tool-call attribution és provider scope; közvetlen secret-hozzáférés nélkül."; tone: root.textMuted }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Költségek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Current cost"; detailText: "N/A — billing/usage adapter not admitted"; tone: root.orange }
                            InfoLine { titleText: "Paid provider rule"; detailText: "Külső/fizetős provider alapértelmezetten OFF; explicit provider enablement és budget policy szükséges."; tone: root.magenta }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Audit"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Audited access"; detailText: "Credential handle kérések, rotation/revocation és budget döntések naplózhatók; secret value soha nem kerül audit payloadba."; tone: root.green }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Riasztások"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            InfoLine { titleText: "Expiry / quota / budget"; detailText: "Riasztás csak bizonyított expiry, quota vagy usage állapotból. Synthetic alert nincs."; tone: root.orange }
                            Button { text: "Riasztási policy tervezet"; onClicked: root.draft("propose.token.alert-policy", "token-alerts", "Alert on credential expiry, quota threshold and token/cost budget evidence") }
                            Item { Layout.fillHeight: true }
                        }

                        ColumnLayout {
                            spacing: 12
                            Label { text: "Házirendek"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            CheckBox { text: "Least scope"; checked: true; enabled: false }
                            CheckBox { text: "Expiry + rotation + revocation required"; checked: true; enabled: false }
                            CheckBox { text: "Plaintext secret storage forbidden"; checked: true; enabled: false }
                            CheckBox { text: "Full vault mount to application forbidden"; checked: true; enabled: false }
                            CheckBox { text: "Podman secret: type=mount default; env forbidden"; checked: true; enabled: false }
                            CheckBox { text: "Audited broker access"; checked: true; enabled: false }
                            CheckBox { text: "Fail-closed on missing credential/usage evidence"; checked: true; enabled: false }
                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }

        Label { visible: root.draftResult.length > 0; text: root.draftResult; color: root.accent; font.pixelSize: 9; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
    }
}
