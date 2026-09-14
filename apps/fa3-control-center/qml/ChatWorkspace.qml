import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property string role: "Mentor"
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    property string viewMode: String(fa3Preferences.value("chat/viewMode", "Standard"))
    property int chatFontSize: Number(fa3Preferences.value("chat/fontSize", 14))
    property string chatFontWeight: String(fa3Preferences.value("chat/fontWeight", "Normal"))
    property bool showGenInfo: Boolean(fa3Preferences.value("chat/showGenInfo", false))
    property bool scrollMessageToTopOnSend: Boolean(fa3Preferences.value("chat/scrollMessageToTopOnSend", true))
    property bool autoLatchGenerating: Boolean(fa3Preferences.value("chat/autoLatchGenerating", true))
    property string messageStyle: String(fa3Preferences.value("chat/messageStyle", "Cards"))
    property bool expandToWindowWidth: Boolean(fa3Preferences.value("chat/expandToWindowWidth", false))
    property string adapterState: "ADAPTER-GATED"

    signal closeRequested()
    signal navigateRequested(int pageIndex)

    function roleDescription(name) {
        if (name === "Mentor") return "Tanulási, szakmai és megvalósítási iránymutatás."
        if (name === "Coach") return "Célok, fókusz, következő lépések és visszacsatolás."
        if (name === "Manager") return "Feladat-, prioritás-, erőforrás- és projektkoordináció."
        if (name === "Ellenőr") return "Ellenőrzés, bizonyíték, eltérés, kockázat és megfelelőség."
        if (name === "Ötletelő") return "Alternatívák, új ötletek és kreatív irányok generálása."
        if (name === "Tanácsadó") return "Opciók, trade-offok és döntéstámogató elemzés."
        return "FA3 szerepalapú beszélgetési munkatér."
    }

    function resetSession() {
        chatModel.clear()
        chatModel.append({
            kind: "SYSTEM",
            author: "FA3",
            body: role + " chat munkatér megnyitva. " + roleDescription(role),
            state: "READY"
        })
        chatModel.append({
            kind: "SYSTEM",
            author: "Runtime",
            body: "Nincs hitelesített role-chat provider adapter hozzárendelve. A felület ezért nem állít elő mesterséges választ és nem jelöl hamisan ONLINE állapotot.",
            state: "ADAPTER-GATED"
        })
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

    function draftPrompt() {
        var text = composer.text.trim()
        if (text.length === 0) return
        chatModel.append({kind: "USER", author: "Te", body: text, state: "LOCAL-DRAFT"})
        composer.clear()
        chatModel.append({
            kind: "SYSTEM",
            author: "Runtime",
            body: "Az üzenet helyi vázlatként látható, de nincs elküldve: előbb aktív provider/runtime adapter szükséges.",
            state: "NOT-SENT"
        })
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

    onRoleChanged: resetSession()
    Component.onCompleted: resetSession()

    Connections {
        target: fa3Preferences
        function onPreferenceChanged(key, value) {
            if (key === "chat/viewMode") root.viewMode = String(value)
            else if (key === "chat/fontSize") root.chatFontSize = Number(value)
            else if (key === "chat/fontWeight") root.chatFontWeight = String(value)
            else if (key === "chat/showGenInfo") root.showGenInfo = Boolean(value)
            else if (key === "chat/scrollMessageToTopOnSend") root.scrollMessageToTopOnSend = Boolean(value)
            else if (key === "chat/autoLatchGenerating") root.autoLatchGenerating = Boolean(value)
            else if (key === "chat/messageStyle") root.messageStyle = String(value)
            else if (key === "chat/expandToWindowWidth") root.expandToWindowWidth = Boolean(value)
        }
    }

    ListModel { id: chatModel }

    component Surface: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Surface {
            Layout.fillWidth: true
            Layout.preferredHeight: 76
            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label { text: "Kérdezd: " + root.role; color: root.textPrimary; font.pixelSize: 20; font.bold: true }
                    Label { text: root.roleDescription(root.role); color: root.textMuted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                Rectangle {
                    radius: 12
                    implicitWidth: adapterLabel.implicitWidth + 20
                    implicitHeight: 24
                    color: "#2a2113"
                    border.color: root.orange
                    Label { id: adapterLabel; anchors.centerIn: parent; text: root.adapterState; color: root.orange; font.pixelSize: 8; font.bold: true }
                }
                Button { text: "Models & Providers"; onClicked: root.navigateRequested(5) }
                Button { text: "Integrations"; onClicked: root.navigateRequested(14) }
                ToolButton { text: "✕"; onClicked: root.closeRequested() }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                anchors.fill: parent
                spacing: 12

                Item { Layout.fillWidth: !root.expandToWindowWidth; Layout.preferredWidth: root.expandToWindowWidth ? 0 : 80 }

                Surface {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.maximumWidth: root.expandToWindowWidth ? 100000 : 1120

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: root.viewMode === "Compact" ? 10 : 14
                        spacing: root.viewMode === "Compact" ? 7 : 10

                        ListView {
                            id: messageList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: root.viewMode === "Compact" ? 6 : 10
                            boundsBehavior: Flickable.StopAtBounds
                            model: chatModel
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                            delegate: Item {
                                required property string kind
                                required property string author
                                required property string body
                                required property string state
                                width: ListView.view.width
                                height: messageCard.implicitHeight

                                Rectangle {
                                    id: messageCard
                                    width: root.messageStyle === "Bubbles" ? Math.min(parent.width * 0.82, messageColumn.implicitWidth + 28) : parent.width - 10
                                    anchors.right: kind === "USER" && root.messageStyle === "Bubbles" ? parent.right : undefined
                                    anchors.left: kind !== "USER" || root.messageStyle !== "Bubbles" ? parent.left : undefined
                                    implicitHeight: messageColumn.implicitHeight + (root.messageStyle === "Plain" ? 8 : 20)
                                    radius: root.messageStyle === "Plain" ? 0 : 8
                                    color: root.messageStyle === "Plain" ? "transparent" : (kind === "USER" ? "#102a43" : root.panelRaised)
                                    border.color: root.messageStyle === "Plain" ? "transparent" : (state === "ADAPTER-GATED" || state === "NOT-SENT" ? root.orange : root.border)

                                    ColumnLayout {
                                        id: messageColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: root.messageStyle === "Plain" ? 4 : 10
                                        spacing: 4
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Label {
                                                text: author
                                                color: kind === "USER" ? root.accent : root.textPrimary
                                                font.pixelSize: Math.max(9, root.chatFontSize - 3)
                                                font.bold: true
                                            }
                                            Item { Layout.fillWidth: true }
                                            Label {
                                                visible: root.showGenInfo
                                                text: state
                                                color: state === "ADAPTER-GATED" || state === "NOT-SENT" ? root.orange : root.textMuted
                                                font.pixelSize: 8
                                            }
                                        }
                                        Label {
                                            Layout.fillWidth: true
                                            text: body
                                            color: root.textPrimary
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: root.chatFontSize
                                            font.weight: root.chatFontWeight === "Semibold" ? Font.DemiBold : (root.chatFontWeight === "Medium" ? Font.Medium : Font.Normal)
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.border }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextArea {
                                id: composer
                                Layout.fillWidth: true
                                Layout.preferredHeight: root.viewMode === "Compact" ? 58 : 78
                                placeholderText: "Írj a(z) " + root.role + " szerepnek…"
                                wrapMode: TextEdit.Wrap
                                color: root.textPrimary
                                font.pixelSize: root.chatFontSize
                                background: Rectangle { radius: 7; color: "#091624"; border.color: root.border }
                            }
                            ColumnLayout {
                                spacing: 6
                                Button {
                                    text: "Vázlat"
                                    enabled: composer.text.trim().length > 0
                                    onClicked: root.draftPrompt()
                                }
                                Button {
                                    text: "Küldés"
                                    enabled: false
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Aktív és hitelesített role-chat provider adapter szükséges."
                                }
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            text: "A chatablak most ténylegesen megnyílik a kiválasztott szereppel. Üzenetküldés csak provider/runtime admission után engedélyezhető; addig a GUI fail-closed marad."
                            color: root.orange
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Item { Layout.fillWidth: !root.expandToWindowWidth; Layout.preferredWidth: root.expandToWindowWidth ? 0 : 80 }
            }
        }
    }
}
