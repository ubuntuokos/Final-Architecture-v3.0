import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine
OperationsAwareAppShell {
    id: shell
    component AskDialog: Dialog {
        id: dialog
        property string roleTitle: ""
        title: shell.t("Párbeszéd — ", "Conversation — ") + roleTitle
        modal: true
        anchors.centerIn: parent
        width: Math.min(shell.width * 0.64, 900)
        height: Math.min(shell.height * 0.70, 680)
        contentItem: ColumnLayout {
            spacing: 10
            Label {
                Layout.fillWidth: true
                text: shell.t("A GUI párbeszéd-projekció; a szerep canonical authority-határai változatlanok.", "GUI conversation projection; canonical role authority boundaries remain unchanged.")
                color: shell.textMuted
                wrapMode: Text.WordWrap
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: shell.surface1
                border.color: Qt.rgba(shell.accent.r, shell.accent.g, shell.accent.b, 0.22)
                TextArea {
                    anchors.fill: parent
                    anchors.margins: 10
                    readOnly: true
                    wrapMode: TextEdit.Wrap
                    text: shell.t("A production runtime válaszadapter külön evidence-t igényel.", "The production runtime response adapter requires separate evidence.")
                }
            }
            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                placeholderText: shell.t("Írd be a kérdésed…", "Type your question…")
                wrapMode: TextEdit.Wrap
            }
            RowLayout {
                Layout.fillWidth: true
                Item {
                    Layout.fillWidth: true
                }
                Button {
                    text: shell.t("Bezárás", "Close")
                    onClicked: dialog.close()
                }
            }
        }
    }
    component PortalDrawer: Drawer {
        id: portal
        required property string portalTitle
        required property url homeUrl
        edge: Qt.RightEdge
        modal: true
        width: Math.min(shell.width * 0.92, 1540)
        height: shell.height
        contentItem: ColumnLayout {
            spacing: 0
            ToolBar {
                Layout.fillWidth: true
                background: Rectangle {
                    color: shell.surface1
                    border.color: Qt.rgba(shell.accent.r, shell.accent.g, shell.accent.b, 0.28)
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    ToolButton {
                        text: "←"
                        enabled: portalWeb.canGoBack
                        onClicked: portalWeb.goBack()
                    }
                    ToolButton {
                        text: "→"
                        enabled: portalWeb.canGoForward
                        onClicked: portalWeb.goForward()
                    }
                    ToolButton {
                        text: "↻"
                        onClicked: portalWeb.reload()
                    }
                    Label {
                        text: portal.portalTitle
                        font.bold: true
                    }
                    TextField {
                        Layout.fillWidth: true
                        readOnly: true
                        text: portalWeb.url.toString()
                        selectByMouse: true
                    }
                    ToolButton {
                        text: "⌂"
                        onClicked: portalWeb.url = portal.homeUrl
                    }
                    ToolButton {
                        text: "×"
                        onClicked: portal.close()
                    }
                }
            }
            WebEngineView {
                id: portalWeb
                Layout.fillWidth: true
                Layout.fillHeight: true
                url: portal.homeUrl
                onNewWindowRequested: function(request) {
                    request.openIn(portalWeb)
                }
                onNavigationRequested: function(request) {
                    const scheme = request.url.scheme
                    if (scheme === "http" || scheme === "https" || scheme === "file" || scheme === "data" || scheme === "blob" || scheme === "about")
                    request.accept()
                    else
                    request.reject()
                }
            }
        }
    }
    AskDialog {
        id: mentorAsk
        roleTitle: "Mentor"
    }
    AskDialog {
        id: coachAsk
        roleTitle: "Coach"
    }
    AskDialog {
        id: managerAsk
        roleTitle: "Manager"
    }
    AskDialog {
        id: inspectorAsk
        roleTitle: shell.t("Ellenőr", "Inspector")
    }
    AskDialog {
        id: ideatorAsk
        roleTitle: shell.t("Ötletelő", "Ideator")
    }
    AskDialog {
        id: advisorAsk
        roleTitle: shell.t("Tanácsadó", "Advisor")
    }
    PortalDrawer {
        id: hfPortal
        portalTitle: "Hugging Face"
        homeUrl: "https://huggingface.co/"
    }
    PortalDrawer {
        id: civitaiPortal
        portalTitle: "CivitAI"
        homeUrl: "https://civitai.com/"
    }
    PortalDrawer {
        id: openModelDbPortal
        portalTitle: "OpenModelDB"
        homeUrl: "https://openmodeldb.info/"
    }
    header: ToolBar {
        height: Math.round(68 * shell.uiScale)
        background: Rectangle {
            color: shell.surface1
            border.color: Qt.rgba(shell.accent.r, shell.accent.g, shell.accent.b, 0.28)
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 2
                color: Qt.rgba(shell.accent.r, shell.accent.g, shell.accent.b, 0.46)
            }
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 7
            ToolButton {
                text: "☰"
                onClicked: shell.toggleSidebar()
                ToolTip.visible: hovered
                ToolTip.text: shell.t("Főmenü", "Main menu")
            }
            ToolButton {
                text: "←"
                enabled: shell.navigationHistory.length > 0
                onClicked: shell.goBack()
            }
            ColumnLayout {
                spacing: 0
                Label {
                    text: "FA3"
                    font.pixelSize: shell.px(20)
                    font.bold: true
                    color: shell.accent
                }
                Label {
                    text: "VISUAL MISSION CONTROL"
                    font.pixelSize: shell.px(8)
                    color: shell.textMuted
                    font.letterSpacing: 1.1
                }
            }
            Rectangle {
                width: 1
                Layout.fillHeight: true
                Layout.topMargin: 13
                Layout.bottomMargin: 13
                color: Qt.rgba(shell.textPrimary.r, shell.textPrimary.g, shell.textPrimary.b, 0.14)
            }
            Label {
                text: "MODEL SOURCES"
                color: shell.textMuted
                font.pixelSize: shell.px(9)
                font.bold: true
            }
            Button {
                text: "Hugging Face"
                onClicked: hfPortal.open()
                highlighted: true
            }
            Button {
                text: "CivitAI"
                onClicked: civitaiPortal.open()
            }
            Button {
                text: "OpenModelDB"
                onClicked: openModelDbPortal.open()
            }
            Item {
                Layout.fillWidth: true
            }
            Label {
                text: shell.t("Kérdezd", "Ask")
                color: shell.textMuted
                font.bold: true
            }
            ToolButton {
                text: "▾"
                onClicked: askMenu.open()
                Menu {
                    id: askMenu
                    MenuItem {
                        visible: fa3Settings.value("roleButtons/mentorVisible", true)
                        text: "Mentor"
                        onTriggered: mentorAsk.open()
                    }
                    MenuItem {
                        visible: fa3Settings.value("roleButtons/coachVisible", true)
                        text: "Coach"
                        onTriggered: coachAsk.open()
                    }
                    MenuItem {
                        visible: fa3Settings.value("roleButtons/managerVisible", true)
                        text: "Manager"
                        onTriggered: managerAsk.open()
                    }
                    MenuItem {
                        visible: fa3Settings.value("roleButtons/inspectorVisible", true)
                        text: shell.t("Ellenőr", "Inspector")
                        onTriggered: inspectorAsk.open()
                    }
                    MenuItem {
                        visible: fa3Settings.value("roleButtons/ideatorVisible", true)
                        text: shell.t("Ötletelő", "Ideator")
                        onTriggered: ideatorAsk.open()
                    }
                    MenuItem {
                        visible: fa3Settings.value("roleButtons/advisorVisible", true)
                        text: shell.t("Tanácsadó", "Advisor")
                        onTriggered: advisorAsk.open()
                    }
                }
            }
            Label {
                text: "143"
                color: shell.accent
                font.bold: true
                ToolTip.visible: hovered
                ToolTip.text: "canonical capabilities"
            }
            ToolButton {
                text: "↻"
                onClicked: {
                    fa3Repository.refresh()
                    fa3ResourceTelemetry.refreshNow()
                }
            }
        }
    }
}
