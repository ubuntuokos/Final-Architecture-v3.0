import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: root
    property string surfaceMode: "EMBEDDED"
    property string applicationId: ""
    property string projectId: ""
    property string workflowId: ""
    property bool aiEnabled: false
    property bool runtimeAdmitted: false

    signal actionIntent(string actionId, var context)
    signal openFullHubRequested(var context)

    readonly property bool embedded: surfaceMode === "EMBEDDED"

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: root.embedded ? "Kommunikáció" : "Communications Hub"
                font.pixelSize: 22
                font.bold: true
                Layout.fillWidth: true
            }
            Label {
                text: root.runtimeAdmitted ? "RUNTIME ADMITTED" : "PENDING CURRENT HOST"
                opacity: 0.7
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: root.embedded
                ? "Csak az aktuális alkalmazás / projekt / workflow engedélyezett kommunikációja és kontaktjai jelenhetnek meg."
                : "Teljes postaláda-, kontakt-, shared inbox- és kommunikációs nézet a tényleges jogosultsági körön belül."
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Levelek" }
            TabButton { text: "Kontaktok" }
            TabButton { text: "Shared Inbox" }
            TabButton { text: "Előzmények" }
            TabButton { visible: !root.embedded; text: "Fiókok" }
            TabButton { visible: !root.embedded; text: "Biztonság" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Pane {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: root.embedded ? "Kontextushoz kötött threadek" : "Engedélyezett postaládák és threadek"; font.bold: true }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: [
                            {title:"Provider runtime nincs felvéve", detail:"A statikus UI nem hajt végre hálózati műveletet."},
                            {title:"Biztonsági kapulánc aktív", detail:"A művelet UAF/security policy útvonalon hajtható végre."}
                        ]
                        delegate: ItemDelegate {
                            width: ListView.view.width
                            contentItem: Column {
                                Text { text: modelData.title; font.bold: true }
                                Text { text: modelData.detail; opacity: 0.7; wrapMode: Text.WordWrap; width: parent.width }
                            }
                        }
                    }
                    RowLayout {
                        Button {
                            text: "Új levél"
                            onClicked: root.actionIntent("email.compose", root.contextPayload())
                        }
                        Button {
                            text: "Megnyitás a Hubban"
                            visible: root.embedded
                            onClicked: root.openFullHubRequested(root.contextPayload())
                        }
                    }
                }
            }

            Pane {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: root.embedded ? "Kontextushoz engedélyezett kontaktok" : "Kontaktok és szervezetek"; font.bold: true }
                    Label { text: root.embedded ? "Globális címjegyzék-felderítés embedded módban tiltott." : "A teljes nézet is csak az effektív jogosultsági körön belül működik."; wrapMode: Text.WordWrap }
                    Button { text: "Kontakt létrehozási intent"; onClicked: root.actionIntent("contact.create", root.contextPayload()) }
                }
            }

            Pane {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Shared Inbox"; font.bold: true }
                    Label { text: "Kiosztás, belső megjegyzés és csapatstátusz security gate után."; wrapMode: Text.WordWrap }
                    Button { text: "Hozzárendelési intent"; onClicked: root.actionIntent("shared-inbox.assign", root.contextPayload()) }
                }
            }

            Pane {
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Kommunikációs előzmények"; font.bold: true }
                    Label { text: "Projekt-, feladat-, meeting-, kontakt- és szervezetkapcsolatok canonical CommunicationRelation alapján."; wrapMode: Text.WordWrap }
                }
            }

            Pane {
                visible: !root.embedded
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Fiókok és provider bridge-ek"; font.bold: true }
                    Label { text: "SMTP / IMAP / JMAP / CardDAV / CalDAV / OAuth/OIDC csak admission + Current Host evidence után."; wrapMode: Text.WordWrap }
                    Label { text: "Credential authority: FA3 Secret Broker"; font.bold: true }
                }
            }

            Pane {
                visible: !root.embedded
                ColumnLayout {
                    anchors.fill: parent
                    Label { text: "Biztonság és AI"; font.bold: true }
                    CheckBox {
                        text: "AI-funkciók engedélyezése ebben a felületben"
                        checked: root.aiEnabled
                        onToggled: root.aiEnabled = checked
                    }
                    Label { text: "Az AI további global/application/module/capability/operation engedélyekhez kötött. Silent fallback nincs."; wrapMode: Text.WordWrap }
                    Label { text: "Email tartalom: UNTRUSTED INPUT • Attachment: scan/DLP • Credentials: Secret Broker"; wrapMode: Text.WordWrap }
                }
            }
        }
    }

    function contextPayload() {
        return {
            "surface_mode": root.surfaceMode,
            "application_id": root.applicationId,
            "project_id": root.projectId,
            "workflow_id": root.workflowId,
            "ai_enabled": root.aiEnabled
        }
    }
}
