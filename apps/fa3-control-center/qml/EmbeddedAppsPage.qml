import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

Item {
    id: root

    required property var settings
    required property color surface1
    required property color surface2
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    property int selectedAppIndex: 0
    property string statusText: ""
    property var apps: [
        { key: "openwebui", name: "Open WebUI", defaultUrl: "" },
        { key: "comfyui", name: "ComfyUI", defaultUrl: "http://127.0.0.1:8188" },
        { key: "invokeai", name: "InvokeAI", defaultUrl: "http://127.0.0.1:9090" },
        { key: "n8n", name: "n8n", defaultUrl: "" },
        { key: "aitoolkit", name: "AI Toolkit", defaultUrl: "http://127.0.0.1:8675" },
        { key: "openclaw", name: "OpenClaw", defaultUrl: "http://127.0.0.1:18789" },
        { key: "ragflow", name: "RAGFlow", defaultUrl: "" },
        { key: "mautic", name: "Mautic", defaultUrl: "" },
        { key: "twenty", name: "Twenty", defaultUrl: "" },
        { key: "listmonk", name: "listmonk", defaultUrl: "" },
        { key: "custom", name: t("Egyéni AI app", "Custom AI app"), defaultUrl: "" }
    ]

    function t(hu, en) {
        return language === "en" ? en : hu
    }

    function px(value) {
        return Math.max(9, Math.round(value * fontScale))
    }

    function currentApp() {
        return apps[Math.max(0, Math.min(selectedAppIndex, apps.length - 1))]
    }

    function settingKey(app) {
        return "webapps/" + app.key + "/url"
    }

    function configuredUrl(app) {
        return settings.value(settingKey(app), app.defaultUrl).toString()
    }

    function normalizeUrl(value) {
        const trimmed = value.trim()
        if (trimmed.length === 0)
            return ""
        if (trimmed.indexOf("://") < 0)
            return "http://" + trimmed
        return trimmed
    }

    function selectApp(index) {
        selectedAppIndex = index
        const app = currentApp()
        endpoint.text = configuredUrl(app)
        const target = normalizeUrl(endpoint.text)
        if (target.length > 0) {
            webView.url = target
            statusText = t("Betöltés: ", "Loading: ") + app.name
        } else {
            webView.url = "about:blank"
            statusText = t("Ehhez az alkalmazáshoz előbb add meg a helyi URL-t.", "Set the local URL for this application first.")
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.surface2
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: Math.round(230 * root.uiScale)
            Layout.fillHeight: true
            color: root.surface1
            border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Label {
                    text: root.t("AI alkalmazások", "AI Applications")
                    font.pixelSize: root.px(17)
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: root.t("Web UI-k az FA3 ablakán belül", "Web UIs inside the FA3 window")
                    color: root.textMuted
                    wrapMode: Text.WordWrap
                    font.pixelSize: root.px(10)
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.apps

                    delegate: ItemDelegate {
                        required property int index
                        required property var modelData
                        width: ListView.view.width
                        height: Math.round(42 * root.uiScale)
                        highlighted: index === root.selectedAppIndex
                        text: modelData.name
                        onClicked: root.selectApp(index)
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: root.t("Külső böngésző nincs használva.", "No external browser is used.")
                    color: root.accent
                    wrapMode: Text.WordWrap
                    font.pixelSize: root.px(10)
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(54 * root.uiScale)
                color: root.surface1
                border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 6

                    ToolButton {
                        text: "←"
                        enabled: webView.canGoBack
                        onClicked: webView.goBack()
                        ToolTip.visible: hovered
                        ToolTip.text: root.t("Web nézet vissza", "Web view back")
                    }
                    ToolButton {
                        text: "→"
                        enabled: webView.canGoForward
                        onClicked: webView.goForward()
                        ToolTip.visible: hovered
                        ToolTip.text: root.t("Web nézet előre", "Web view forward")
                    }
                    ToolButton {
                        text: "↻"
                        onClicked: webView.reload()
                        ToolTip.visible: hovered
                        ToolTip.text: root.t("Újratöltés", "Reload")
                    }
                    ToolButton {
                        text: "⌂"
                        onClicked: root.selectApp(root.selectedAppIndex)
                        ToolTip.visible: hovered
                        ToolTip.text: root.t("Alkalmazás kezdőcíme", "Application home URL")
                    }

                    TextField {
                        id: endpoint
                        Layout.fillWidth: true
                        placeholderText: "http://127.0.0.1:PORT"
                        selectByMouse: true
                        onAccepted: {
                            const target = root.normalizeUrl(text)
                            if (target.length > 0)
                                webView.url = target
                        }
                    }

                    Button {
                        text: root.t("Mentés", "Save")
                        onClicked: {
                            const app = root.currentApp()
                            const target = root.normalizeUrl(endpoint.text)
                            root.settings.setValue(root.settingKey(app), target)
                            endpoint.text = target
                            if (target.length > 0)
                                webView.url = target
                            root.statusText = root.t("Helyi endpoint elmentve: ", "Local endpoint saved: ") + app.name
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(28 * root.uiScale)
                color: root.surface2

                Label {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    verticalAlignment: Text.AlignVCenter
                    text: root.statusText
                    color: root.textMuted
                    font.pixelSize: root.px(10)
                    elide: Text.ElideRight
                }
            }

            WebEngineView {
                id: webView
                Layout.fillWidth: true
                Layout.fillHeight: true
                url: "about:blank"

                onLoadingChanged: function(info) {
                    if (info.status === WebEngineLoadingInfo.LoadSucceededStatus)
                        root.statusText = root.currentApp().name + " · " + webView.url
                    else if (info.status === WebEngineLoadingInfo.LoadFailedStatus)
                        root.statusText = root.t("Betöltési hiba: ", "Load failed: ") + info.errorString
                }

                onNavigationRequested: function(request) {
                    const scheme = request.url.toString().split(":")[0].toLowerCase()
                    if (["http", "https", "file", "data", "blob", "about"].indexOf(scheme) >= 0)
                        request.accept()
                    else {
                        request.reject()
                        root.statusText = root.t("Külső protokoll blokkolva az FA3-ban: ", "External protocol blocked inside FA3: ") + scheme
                    }
                }

                onNewWindowRequested: function(request) {
                    request.openIn(webView)
                }
            }
        }
    }

    Component.onCompleted: selectApp(0)
}
