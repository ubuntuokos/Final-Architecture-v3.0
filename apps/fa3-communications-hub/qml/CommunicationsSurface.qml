import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Frame {
    id: root

    // Embedded contract: CONTEXT_LIMITED. Effective scope is the intersection
    // of user, role, application, context and data permissions.
    property string surfaceMode: "CONTEXT_LIMITED"
    property string contextId: ""
    property string contextLabel: "Aktuális munkakörnyezet"
    property bool canReadMail: false
    property bool canCompose: false
    property bool canReadContacts: false

    signal composeRequested(string contextId)
    signal contactRequested(string contextId)
    signal openFullHub(string contextId)

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Kommunikáció"; font.bold: true; Layout.fillWidth: true }
            Label { text: root.surfaceMode; color: "#8bd5ca"; font.bold: true }
        }

        Label {
            Layout.fillWidth: true
            text: root.contextId.length > 0
                  ? root.contextLabel + " · " + root.contextId
                  : "Nincs engedélyezett kommunikációs kontextus."
            wrapMode: Text.Wrap
        }

        Label {
            Layout.fillWidth: true
            text: "Embedded scope is the intersection of user, role, application, context and data permissions."
            wrapMode: Text.Wrap
            opacity: 0.7
        }

        RowLayout {
            Button {
                text: "Kapcsolódó levelek"
                enabled: root.contextId.length > 0 && root.canReadMail
            }
            Button {
                text: "Email írása"
                enabled: root.contextId.length > 0 && root.canCompose
                onClicked: root.composeRequested(root.contextId)
            }
            Button {
                text: "Kontaktok"
                enabled: root.contextId.length > 0 && root.canReadContacts
                onClicked: root.contactRequested(root.contextId)
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Megnyitás a Communications Hubban"
                enabled: root.contextId.length > 0
                onClicked: root.openFullHub(root.contextId)
            }
        }
    }
}
