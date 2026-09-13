import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtWebEngine

AnimationAwareAppShell {
    id: shell

    property real monitorScale: {
        const sx = Math.max(0.5, Screen.desktopAvailableWidth / 1920.0)
        const sy = Math.max(0.5, Screen.desktopAvailableHeight / 1080.0)
        return Math.max(0.85, Math.min(1.45, Math.sqrt(Math.min(sx, sy))))
    }

    // Starter Models is a mandatory Model Manager subpage, never a global main-menu area.
    function areaVisible(key) {
        if (key === "starterModels")
            return false
        if (key === "command" || key === "settings")
            return true
        return fa3Settings.value("areas/" + key + "Visible", true)
    }

    // Window geometry follows monitor available geometry, not the live UI-scale slider.
    minimumWidth: Math.min(1120, Math.round(Screen.desktopAvailableWidth * 0.82))
    minimumHeight: Math.min(700, Math.round(Screen.desktopAvailableHeight * 0.78))
    width: Math.max(minimumWidth, Math.min(1720, Math.round(Screen.desktopAvailableWidth * 0.92)))
    height: Math.max(minimumHeight, Math.min(1040, Math.round(Screen.desktopAvailableHeight * 0.90)))
    uiScale: Math.max(0.82, Math.min(1.75, monitorScale * fa3Settings.uiScale))

    Component.onCompleted: fa3ResourceTelemetry.refreshNow()

    component AskDialog: Dialog {
        id: askDialog
        property string roleTitle: ""
        property string roleKey: ""
        property string transcript: ""
        title: shell.t("Párbeszéd — ", "Conversation — ") + roleTitle
        modal: true
        anchors.centerIn: parent
        width: Math.min(shell.width * 0.66, 900)
        height: Math.min(shell.height * 0.74, 700)
        closePolicy: Popup.CloseOnEscape

        contentItem: ColumnLayout {
            spacing: 10
            Label {
                Layout.fillWidth: true
                text: shell.t("A szerep canonical határai megmaradnak; a GUI nem válik tool- vagy döntési authority-vé.", "Canonical role boundaries remain intact; the GUI does not become a tool or decision authority.")
                color: shell.textMuted
                wrapMode: Text.WordWrap
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: shell.surface1
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 8
                    TextArea {
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        text: askDialog.transcript.length ? askDialog.transcript : shell.t("Nincs még üzenet.", "No messages yet.")
                    }
                }
            }
            TextArea {
                id: prompt
                Layout.fillWidth: true
                Layout.preferredHeight: 100
                wrapMode: TextEdit.Wrap
                placeholderText: shell.t("Írd be a kérdésed…", "Type your question…")
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: shell.t("Küldés", "Send")
                    enabled: prompt.text.trim().length > 0
                    onClicked: {
                        const q = prompt.text.trim()
                        const prefix = askDialog.transcript.length ? "\n\n" : ""
                        askDialog.transcript += prefix + shell.t("Te: ", "You: ") + q + "\n\n" + askDialog.roleTitle + ": " + shell.t("A kérdés rögzítve; production válasz csak a megfelelő runtime adapteren keresztül jelenhet meg.", "Question recorded; a production response may appear only through the appropriate runtime adapter.")
                        prompt.clear()
                    }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: shell.t("Beállítások", "Settings")
                    onClicked: {
                        askDialog.close()
                        shell.navigateKey("settings")
                    }
                }
                Button { text: shell.t("Bezárás", "Close"); onClicked: askDialog.close() }
            }
        }
    }

    component WebHubDrawer: Drawer {
        id: webDrawer
        required property string hubTitle
        required property url homeUrl
        parent: shell.contentItem
        edge: Qt.RightEdge
        modal: true
        width: Math.min(shell.width * 0.92, 1500)
        height: shell.height

        contentItem: ColumnLayout {
            spacing: 0
            ToolBar {
                Layout.fillWidth: true
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    ToolButton { text: "←"; enabled: hubWebView.canGoBack; onClicked: hubWebView.goBack() }
                    ToolButton { text: "→"; enabled: hubWebView.canGoForward; onClicked: hubWebView.goForward() }
                    ToolButton { text: "↻"; onClicked: hubWebView.reload() }
                    Label { text: webDrawer.hubTitle; font.bold: true }
                    TextField {
                        Layout.fillWidth: true
                        readOnly: true
                        text: hubWebView.url.toString()
                        selectByMouse: true
                    }
                    ToolButton { text: "⌂"; onClicked: hubWebView.url = webDrawer.homeUrl }
                    ToolButton { text: "×"; onClicked: webDrawer.close() }
                }
            }
            WebEngineView {
                id: hubWebView
                Layout.fillWidth: true
                Layout.fillHeight: true
                url: webDrawer.homeUrl
                onNewWindowRequested: function(request) { request.openIn(hubWebView) }
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

    AskDialog { id: mentorAsk; roleKey: "mentor"; roleTitle: shell.t("Mentor", "Mentor") }
    AskDialog { id: coachAsk; roleKey: "coach"; roleTitle: shell.t("Coach", "Coach") }
    AskDialog { id: managerAsk; roleKey: "manager"; roleTitle: shell.t("Manager", "Manager") }
    AskDialog { id: inspectorAsk; roleKey: "inspector"; roleTitle: shell.t("Ellenőr", "Inspector") }
    AskDialog { id: ideatorAsk; roleKey: "ideator"; roleTitle: shell.t("Ötletelő", "Ideator") }
    AskDialog { id: advisorAsk; roleKey: "advisor"; roleTitle: shell.t("Tanácsadó", "Advisor") }

    header: ToolBar {
        height: Math.round(62 * shell.uiScale)
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 6
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
                ToolTip.visible: hovered
                ToolTip.text: shell.t("Vissza", "Back")
            }
            Label { text: "FA3"; font.pixelSize: shell.px(21); font.bold: true }
            Label { visible: shell.width >= 1280; text: "Final Architecture 3.0"; font.pixelSize: shell.px(14); font.bold: true }
            Button {
                text: "Hugging Face"
                highlighted: true
                onClicked: huggingFaceDrawer.open()
                ToolTip.visible: hovered
                ToolTip.text: shell.t("Hugging Face weboldal", "Hugging Face website")
            }
            Button {
                text: "CivitAI"
                onClicked: civitaiWebDrawer.open()
                ToolTip.visible: hovered
                ToolTip.text: shell.t("CivitAI weboldal", "CivitAI website")
            }
            Button {
                text: "OpenModelDB"
                onClicked: openModelDbWebDrawer.open()
                ToolTip.visible: hovered
                ToolTip.text: shell.t("OpenModelDB weboldal", "OpenModelDB website")
            }
            Item { Layout.fillWidth: true }
            Label { text: shell.t("Kérdezd", "Ask"); font.bold: true }
            ToolButton {
                id: askButton
                text: "▾"
                onClicked: askMenu.open()
                Menu {
                    id: askMenu
                    MenuItem { visible: fa3Settings.value("roleButtons/mentorVisible", true); text: shell.t("Mentor", "Mentor"); onTriggered: mentorAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/coachVisible", true); text: shell.t("Coach", "Coach"); onTriggered: coachAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/managerVisible", true); text: shell.t("Manager", "Manager"); onTriggered: managerAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/inspectorVisible", true); text: shell.t("Ellenőr", "Inspector"); onTriggered: inspectorAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/ideatorVisible", true); text: shell.t("Ötletelő", "Ideator"); onTriggered: ideatorAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/advisorVisible", true); text: shell.t("Tanácsadó", "Advisor"); onTriggered: advisorAsk.open() }
                }
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

    footer: ResourceStatusStrip {
        telemetry: fa3ResourceTelemetry
        textPrimary: shell.textPrimary
        textMuted: shell.textMuted
        accent: shell.accent
    }

    // Logs are a Settings submenu. Model Manager providers now live inside Model Manager itself.
    Frame {
        id: contextualSubmenu
        parent: shell.contentItem
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: Math.round(10 * shell.uiScale)
        anchors.rightMargin: Math.round(16 * shell.uiScale)
        z: 1000
        visible: shell.selectedIndex === shell.indexForKey("settings")
        padding: Math.round(5 * shell.uiScale)

        RowLayout {
            spacing: 6
            Label { text: shell.t("Beállítások", "Settings"); color: shell.textMuted; font.bold: true }
            Button {
                text: shell.t("Naplók", "Logs")
                onClicked: {
                    fa3Journal.refresh(400)
                    logsDrawer.open()
                }
            }
        }
    }

    WebHubDrawer { id: huggingFaceDrawer; hubTitle: "Hugging Face"; homeUrl: "https://huggingface.co/" }
    WebHubDrawer { id: civitaiWebDrawer; hubTitle: "CivitAI"; homeUrl: "https://civitai.com/" }
    WebHubDrawer { id: openModelDbWebDrawer; hubTitle: "OpenModelDB"; homeUrl: "https://openmodeldb.info/" }

    Drawer {
        id: logsDrawer
        parent: shell.contentItem
        edge: Qt.RightEdge
        modal: true
        width: Math.min(shell.width * 0.86, 1320)
        height: shell.height
        contentItem: ColumnLayout {
            spacing: 0
            ToolBar {
                Layout.fillWidth: true
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    Label { text: shell.t("Beállítások · Naplók", "Settings · Logs"); font.bold: true; Layout.fillWidth: true }
                    ToolButton { text: "×"; onClicked: logsDrawer.close() }
                }
            }
            LogsPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                journal: fa3Journal
                textPrimary: shell.textPrimary
                textMuted: shell.textMuted
                surface1: shell.surface1
                accent: shell.accent
            }
        }
    }
}
