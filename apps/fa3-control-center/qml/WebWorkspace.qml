import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

Item {
    id: root

    property url webUrl: "about:blank"
    property string titleText: "Web Workspace"
    property color surface: "#0b1728"
    property color surfaceRaised: "#0f2035"
    property color borderTone: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property string noticeText: "Isolated FA3 Web Workspace · browser extensions unavailable · popup windows stay inside this surface"

    signal closeRequested()

    WebEngineProfile {
        id: isolatedProfile
        offTheRecord: true
    }

    Rectangle {
        anchors.fill: parent
        color: root.surface
        border.color: root.borderTone

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 46
                color: root.surfaceRaised
                border.color: root.borderTone

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 6

                    ToolButton { text: "←"; enabled: webView.canGoBack; onClicked: webView.goBack() }
                    ToolButton { text: "→"; enabled: webView.canGoForward; onClicked: webView.goForward() }
                    ToolButton { text: "↻"; onClicked: webView.reload() }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Label {
                            text: root.titleText
                            color: root.textPrimary
                            font.pixelSize: 11
                            font.bold: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                        Label {
                            text: webView.url.toString()
                            color: root.textMuted
                            font.pixelSize: 8
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                        }
                    }

                    Rectangle {
                        radius: 5
                        color: "#102a43"
                        border.color: root.borderTone
                        implicitWidth: 104
                        implicitHeight: 26
                        Label {
                            anchors.centerIn: parent
                            text: "ISOLATED WEB"
                            color: root.accent
                            font.pixelSize: 8
                            font.bold: true
                        }
                    }

                    ToolButton { text: "✕"; onClicked: root.closeRequested() }
                }
            }

            WebEngineView {
                id: webView
                Layout.fillWidth: true
                Layout.fillHeight: true
                profile: isolatedProfile
                url: root.webUrl

                onNewWindowRequested: function(request) {
                    if (request.requestedUrl && request.requestedUrl.toString().length > 0) {
                        webView.url = request.requestedUrl
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                color: "#06101c"
                border.color: root.borderTone
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8
                    Rectangle { width: 6; height: 6; radius: 3; color: root.accent }
                    Label {
                        text: root.noticeText
                        color: root.textMuted
                        font.pixelSize: 8
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
