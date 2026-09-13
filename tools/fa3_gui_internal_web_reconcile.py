from pathlib import Path

root = Path('.')
main = root / 'apps/fa3-control-center/qml/Main.qml'
cmake = root / 'apps/fa3-control-center/CMakeLists.txt'
cpp = root / 'apps/fa3-control-center/src/main.cpp'
installer = root / 'deployment/fa3-gui/install.sh'
gate = root / '.github/workflows/fa3-gui-gate.yml'
web = root / 'apps/fa3-control-center/qml/WebWorkspace.qml'


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'expected marker not found in {path}: {old[:120]!r}')
    path.write_text(text.replace(old, new, 1))


replace_once(main, 'import QtQuick.Window\n', 'import QtQuick.Window\nimport QtWebEngine\n')
replace_once(
    main,
    '    property string askRole: "Mentor"\n',
    '    property string askRole: "Mentor"\n'
    '    property bool webWorkspaceOpen: false\n'
    '    property url webWorkspaceUrl: "about:blank"\n'
    '    property string webWorkspaceTitle: "Web Workspace"\n\n'
    '    function openInternalWeb(targetUrl, titleText) {\n'
    '        webWorkspaceUrl = targetUrl\n'
    '        webWorkspaceTitle = titleText\n'
    '        webWorkspaceOpen = true\n'
    '    }\n'
)
replace_once(
    main,
    '            onClicked: Qt.openUrlExternally(quickLinkRoot.targetUrl)\n',
    '            onClicked: window.openInternalWeb(quickLinkRoot.targetUrl, quickLinkRoot.linkText)\n'
)
replace_once(
    main,
    '                currentIndex: window.selectedIndex\n',
    '                currentIndex: window.webWorkspaceOpen ? 17 : window.selectedIndex\n'
)

tail_old = '''                                Label { text: "Display target"; color: window.textMuted }\n                                Label { text: "KDE Plasma / Wayland"; color: window.textPrimary }\n                            }\n                        }\n                    }\n                }\n            }\n\n            Rectangle {'''
tail_new = '''                                Label { text: "Display target"; color: window.textMuted }\n                                Label { text: "KDE Plasma / Wayland"; color: window.textPrimary }\n                            }\n                        }\n                    }\n                }\n\n                WebWorkspace {\n                    webUrl: window.webWorkspaceUrl\n                    titleText: window.webWorkspaceTitle\n                    surface: window.panel\n                    surfaceRaised: window.panelRaised\n                    borderTone: window.border\n                    textPrimary: window.textPrimary\n                    textMuted: window.textMuted\n                    accent: window.accent\n                    onCloseRequested: window.webWorkspaceOpen = false\n                }\n            }\n\n            Rectangle {'''
replace_once(main, tail_old, tail_new)

web.write_text('''import QtQuick\nimport QtQuick.Controls\nimport QtQuick.Layouts\nimport QtWebEngine\n\nItem {\n    id: root\n\n    property url webUrl: "about:blank"\n    property string titleText: "Web Workspace"\n    property color surface: "#0b1728"\n    property color surfaceRaised: "#0f2035"\n    property color borderTone: "#1d3550"\n    property color textPrimary: "#f5f8fc"\n    property color textMuted: "#8397ad"\n    property color accent: "#25a7ff"\n    property string noticeText: "Isolated FA3 Web Workspace · browser extensions unavailable · popup windows stay inside this surface"\n\n    signal closeRequested()\n\n    WebEngineProfile {\n        id: isolatedProfile\n        offTheRecord: true\n    }\n\n    Rectangle {\n        anchors.fill: parent\n        color: root.surface\n        border.color: root.borderTone\n\n        ColumnLayout {\n            anchors.fill: parent\n            spacing: 0\n\n            Rectangle {\n                Layout.fillWidth: true\n                Layout.preferredHeight: 46\n                color: root.surfaceRaised\n                border.color: root.borderTone\n\n                RowLayout {\n                    anchors.fill: parent\n                    anchors.leftMargin: 10\n                    anchors.rightMargin: 10\n                    spacing: 6\n\n                    ToolButton { text: "←"; enabled: webView.canGoBack; onClicked: webView.goBack() }\n                    ToolButton { text: "→"; enabled: webView.canGoForward; onClicked: webView.goForward() }\n                    ToolButton { text: "↻"; onClicked: webView.reload() }\n\n                    ColumnLayout {\n                        Layout.fillWidth: true\n                        spacing: 0\n                        Label {\n                            text: root.titleText\n                            color: root.textPrimary\n                            font.pixelSize: 11\n                            font.bold: true\n                            Layout.fillWidth: true\n                            elide: Text.ElideRight\n                        }\n                        Label {\n                            text: webView.url.toString()\n                            color: root.textMuted\n                            font.pixelSize: 8\n                            Layout.fillWidth: true\n                            elide: Text.ElideMiddle\n                        }\n                    }\n\n                    Rectangle {\n                        radius: 5\n                        color: "#102a43"\n                        border.color: root.borderTone\n                        implicitWidth: 104\n                        implicitHeight: 26\n                        Label {\n                            anchors.centerIn: parent\n                            text: "ISOLATED WEB"\n                            color: root.accent\n                            font.pixelSize: 8\n                            font.bold: true\n                        }\n                    }\n\n                    ToolButton { text: "✕"; onClicked: root.closeRequested() }\n                }\n            }\n\n            WebEngineView {\n                id: webView\n                Layout.fillWidth: true\n                Layout.fillHeight: true\n                profile: isolatedProfile\n                url: root.webUrl\n\n                onNewWindowRequested: function(request) {\n                    if (request.requestedUrl && request.requestedUrl.toString().length > 0) {\n                        webView.url = request.requestedUrl\n                    }\n                }\n            }\n\n            Rectangle {\n                Layout.fillWidth: true\n                Layout.preferredHeight: 28\n                color: "#06101c"\n                border.color: root.borderTone\n                RowLayout {\n                    anchors.fill: parent\n                    anchors.leftMargin: 10\n                    anchors.rightMargin: 10\n                    spacing: 8\n                    Rectangle { width: 6; height: 6; radius: 3; color: root.accent }\n                    Label {\n                        text: root.noticeText\n                        color: root.textMuted\n                        font.pixelSize: 8\n                        Layout.fillWidth: true\n                        elide: Text.ElideRight\n                    }\n                }\n            }\n        }\n    }\n}\n''')

replace_once(
    cmake,
    'find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2)\n',
    'find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2 WebEngineQuick)\n'
)
replace_once(
    cmake,
    'set_source_files_properties(qml/JournalPage.qml PROPERTIES QT_RESOURCE_ALIAS JournalPage.qml)\n',
    'set_source_files_properties(qml/JournalPage.qml PROPERTIES QT_RESOURCE_ALIAS JournalPage.qml)\n'
    'set_source_files_properties(qml/WebWorkspace.qml PROPERTIES QT_RESOURCE_ALIAS WebWorkspace.qml)\n'
)
replace_once(cmake, '        qml/JournalPage.qml\n', '        qml/JournalPage.qml\n        qml/WebWorkspace.qml\n')
replace_once(cmake, '        Qt6::QuickControls2\n', '        Qt6::QuickControls2\n        Qt6::WebEngineQuick\n')

replace_once(cpp, '#include <QUrl>\n', '#include <QUrl>\n#include <QtWebEngineQuick/qtwebenginequickglobal.h>\n')
replace_once(
    cpp,
    'int main(int argc, char *argv[])\n{\n    QGuiApplication app(argc, argv);\n',
    'int main(int argc, char *argv[])\n{\n    QtWebEngineQuick::initialize();\n    QGuiApplication app(argc, argv);\n'
)

replace_once(
    installer,
    '    qt6-base-dev qt6-declarative-dev \\\n',
    '    qt6-base-dev qt6-declarative-dev qt6-webengine-dev \\\n'
)
replace_once(
    installer,
    '    qml6-module-qtquick qml6-module-qtquick-controls \\\n',
    '    qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtwebengine \\\n'
)
replace_once(
    installer,
    '  \'labelText: "NPU"\'\n)\n',
    '  \'labelText: "NPU"\'\n  \'import QtWebEngine\'\n  \'openInternalWeb\'\n)\n'
)
installer_text = installer.read_text()
marker = 'done\n\nif command -v git'
negative = '''done\n\nif grep -Fq 'Qt.openUrlExternally(quickLinkRoot.targetUrl)' "$MAIN_QML"; then\n  echo "FA3 GUI source-contract check FAILED: QuickLink still escapes to an external browser" >&2\n  exit 3\nfi\n\nif command -v git'''
if marker not in installer_text:
    raise SystemExit('installer negative-gate marker not found')
installer.write_text(installer_text.replace(marker, negative, 1))

replace_once(
    gate,
    '            qt6-base-dev qt6-declarative-dev \\\n',
    '            qt6-base-dev qt6-declarative-dev qt6-webengine-dev \\\n'
)
replace_once(
    gate,
    '            qml6-module-qtquick qml6-module-qtquick-controls \\\n',
    '            qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtwebengine \\\n'
)

# Remove the one-shot materialization machinery from the resulting branch.
for transient in [
    root / '.github/workflows/fa3-internal-web-workspace-reconcile.yml',
    root / '.github/workflows/fa3-internal-web-reconcile-v2.yml',
    root / 'tools/fa3_gui_internal_web_reconcile.py',
]:
    if transient.exists():
        transient.unlink()
