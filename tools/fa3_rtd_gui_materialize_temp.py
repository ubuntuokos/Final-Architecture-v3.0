from pathlib import Path

main = Path('apps/fa3-control-center/qml/Main.qml')
text = main.read_text(encoding='utf-8')

marker = '    function searchUiEntries(query, category) {\n'
insert = '''    property var rtdProviderCategories: [
        {code: "SEARCH_WEB", title: "Search & Web", description: "Web search, crawling and changing public web data.", protocols: "REST / Plugin / MCP", freshness: "provider-defined"},
        {code: "NEWS_SOCIAL", title: "News & Social", description: "News wires, RSS and social/event streams.", protocols: "REST / RSS / WebSocket", freshness: "minutes / stream"},
        {code: "WEATHER_GEO", title: "Weather & Geo", description: "Weather, alerts, geocoding, POI and map context.", protocols: "REST / stream", freshness: "minutes"},
        {code: "MARKETS", title: "Markets", description: "FX, equities, crypto and commodity market data.", protocols: "REST / WebSocket", freshness: "seconds / provider SLA"},
        {code: "SPORTS_TRAFFIC", title: "Sports & Traffic", description: "Scores, schedules, transport and traffic state.", protocols: "REST / stream", freshness: "seconds / minutes"},
        {code: "REPOSITORIES", title: "Repositories", description: "GitHub/GitLab releases, PRs, issues and repository events.", protocols: "API / webhook", freshness: "event / minutes"},
        {code: "SYSTEM_SENSORS", title: "System & Sensors", description: "Host telemetry, device sensors and IoT observations.", protocols: "local adapter / MQTT", freshness: "seconds"},
        {code: "ENTERPRISE", title: "Enterprise", description: "CRM, ERP, helpdesk and organization data feeds.", protocols: "API / connector", freshness: "provider-defined"},
        {code: "SECURITY", title: "Security", description: "CVE, threat intelligence and security advisory feeds.", protocols: "REST / feed", freshness: "minutes / hours"},
        {code: "MODELS", title: "Models", description: "Changing model metadata, releases, availability and catalog state.", protocols: "API / registry", freshness: "minutes / hours"},
        {code: "COMMUNICATION", title: "Communication", description: "Mail, calendar and chat events exposed through authorized adapters.", protocols: "connector / webhook", freshness: "event"},
        {code: "CUSTOM_API", title: "Custom / API", description: "User- or organization-defined real-time data adapters.", protocols: "REST / WebSocket / MCP", freshness: "declared by adapter"}
    ]

    function searchRtdEntries(query) {
        var needle = query.trim().toLowerCase()
        var out = []
        for (var i = 0; i < rtdProviderCategories.length; ++i) {
            var entry = rtdProviderCategories[i]
            var haystack = (entry.code + " " + entry.title + " " + entry.description).toLowerCase()
            if (needle.length === 0 || haystack.indexOf(needle) >= 0)
                out.push({id: entry.code, title: entry.title, subtitle: entry.description, status: "ADAPTER-GATED", category: "RTD", sourceType: "RTD", pageIndex: 17, path: ""})
        }
        return out
    }

'''
if 'property var rtdProviderCategories' not in text:
    text = text.replace(marker, insert + marker, 1)

old = '        {title: "Remote AI Hub", detail: "Távoli AI-kapacitás és hosted execution", category: "FUNCTION", pageIndex: 1},\n'
new = old + '        {title: "RTD Providers", detail: "Real-Time Data provider-ek, frissesség, policy és provenance", category: "FUNCTION", pageIndex: 17},\n'
if 'title: "RTD Providers"' not in text:
    text = text.replace(old, new, 1)

marker = '        if (scope === "ALL" || scope === "CANONICAL") {\n'
insert = '''        if (scope === "ALL" || scope === "RTD") {
            var rtdRows = searchRtdEntries(needle)
            for (i = 0; i < rtdRows.length; ++i) out.push(rtdRows[i])
        }
'''
if 'scope === "ALL" || scope === "RTD"' not in text:
    text = text.replace(marker, insert + marker, 1)

old = '                        NavButton { iconText: "☁"; label: "Remote AI Hub"; pageIndex: 1 }\n'
new = old + '                        NavButton { iconText: "◉"; label: "RTD Providers"; pageIndex: 17 }\n'
if 'label: "RTD Providers"' not in text:
    text = text.replace(old, new, 1)

text = text.replace('currentIndex: window.webWorkspaceOpen ? 17 : window.selectedIndex', 'currentIndex: window.webWorkspaceOpen ? 18 : window.selectedIndex')

old = '                        {title: "Tool Execution", subtitle: "Central MCP mediation és policy outcome.", badge: "GATED", tone: window.magenta}\n'
new = '                        {title: "Tool Execution", subtitle: "Central MCP mediation és policy outcome.", badge: "GATED", tone: window.magenta},\n                        {title: "RTD Data Sources", subtitle: "Workflow-szintű élő adatforrás-kötések az RTD Providers policy- és freshness-határán keresztül.", badge: "DATA", tone: window.cyan}\n'
if 'title: "RTD Data Sources"' not in text:
    text = text.replace(old, new, 1)

old = '                                    {label: "Beállítások", value: "SETTING"},\n                                    {label: "Canonical rekordok", value: "CANONICAL"}\n'
new = '                                    {label: "Beállítások", value: "SETTING"},\n                                    {label: "Real-Time Data", value: "RTD"},\n                                    {label: "Canonical rekordok", value: "CANONICAL"}\n'
if '{label: "Real-Time Data", value: "RTD"}' not in text:
    text = text.replace(old, new, 1)

old = '                        {title: "MCP", subtitle: "Capabilities mediated through the central gateway.", badge: "GATED", tone: window.orange},\n                        {title: "Journal Share", subtitle: "E-mail adapter and chat/export bundle handoff.", badge: "ADAPTER", tone: window.green}\n'
new = '                        {title: "MCP", subtitle: "Capabilities mediated through the central gateway.", badge: "GATED", tone: window.orange},\n                        {title: "RTD Adapters", subtitle: "REST, WebSocket, RSS, webhook, MCP és local adapter kapcsolatok az RTD Providers számára.", badge: "ADAPTER", tone: window.cyan},\n                        {title: "Journal Share", subtitle: "E-mail adapter and chat/export bundle handoff.", badge: "ADAPTER", tone: window.green}\n'
if 'title: "RTD Adapters"' not in text:
    text = text.replace(old, new, 1)

marker = '''                WebWorkspace {
                    webUrl: window.webWorkspaceUrl
'''
insert = '''                RtdProvidersPage {
                    categories: window.rtdProviderCategories
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    cyan: window.cyan
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

'''
if 'RtdProvidersPage {' not in text:
    text = text.replace(marker, insert + marker, 1)
main.write_text(text, encoding='utf-8')

dashboard = Path('apps/fa3-control-center/qml/DashboardPage.qml')
d = dashboard.read_text(encoding='utf-8')
marker = '''                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Panel {
'''
insert = '''                Panel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 66
                    color: root.panelRaised
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        spacing: 10
                        StatusDot { dotColor: root.orange }
                        Label { text: "Real-Time Data"; color: root.textPrimary; font.pixelSize: 11; font.bold: true }
                        Label { text: "ADAPTER-GATED"; color: root.orange; font.pixelSize: 9; font.bold: true }
                        Item { Layout.fillWidth: true }
                        MutedLabel { text: "Freshness, auth, policy és provenance csak konfigurált RTD adapter evidence alapján jelenik meg." }
                    }
                }

'''
if 'text: "Real-Time Data"' not in d:
    d = d.replace(marker, insert + marker, 1)
dashboard.write_text(d, encoding='utf-8')

rtd = Path('apps/fa3-control-center/qml/RtdProvidersPage.qml')
rtd.write_text(r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property var categories: []
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property int selectedCategory: 0
    property string draftPath: ""

    function filteredCategories(query) {
        var needle = query.trim().toLowerCase()
        if (needle.length === 0) return categories
        return categories.filter(function(v) {
            return (v.code + " " + v.title + " " + v.description + " " + v.protocols).toLowerCase().indexOf(needle) >= 0
        })
    }
    function currentCategory() {
        var rows = filteredCategories(rtdSearch.text)
        if (rows.length === 0) return null
        return rows[Math.max(0, Math.min(selectedCategory, rows.length - 1))]
    }
    component Panel: Rectangle {
        radius: 9; color: root.panel; border.color: root.border; border.width: 1
    }
    component Metric: Panel {
        property string titleText: ""; property string valueText: "—"; property string noteText: ""; property color tone: root.accent
        implicitHeight: 94
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12; spacing: 3
            Label { text: parent.parent.titleText; color: root.textMuted; font.pixelSize: 9; font.bold: true }
            Label { text: parent.parent.valueText; color: parent.parent.tone; font.pixelSize: 17; font.bold: true }
            Label { text: parent.parent.noteText; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
        }
    }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth
        padding: 18
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        ColumnLayout {
            width: pageScroll.availableWidth
            spacing: 14
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                Label { text: "RTD Providers"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label { text: "Real-Time Data provider-ek központi operátori nézete · adatforrás, frissesség, auth, policy és provenance"; color: root.textMuted; font.pixelSize: 10 }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                Metric { Layout.fillWidth: true; titleText: "KATEGÓRIAFELÜLET"; valueText: root.categories.length.toString(); noteText: "RTD provider osztály"; tone: root.cyan }
                Metric { Layout.fillWidth: true; titleText: "LIVE ADAPTER"; valueText: "—"; noteText: "runtime evidence szükséges"; tone: root.orange }
                Metric { Layout.fillWidth: true; titleText: "FRESHNESS"; valueText: "GATED"; noteText: "provider / adapter SLA"; tone: root.orange }
                Metric { Layout.fillWidth: true; titleText: "POLICY"; valueText: "FAIL-CLOSED"; noteText: "explicit egress + auth"; tone: root.magenta }
            }
            Panel {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(500, pageScroll.availableHeight - 190)
                RowLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 12
                    ColumnLayout {
                        Layout.preferredWidth: 350; Layout.fillHeight: true; spacing: 8
                        TextField { id: rtdSearch; Layout.fillWidth: true; placeholderText: "RTD kategória keresése…"; onTextChanged: root.selectedCategory = 0 }
                        Label { text: root.filteredCategories(rtdSearch.text).length + " kategória"; color: root.textMuted; font.pixelSize: 9 }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; boundsBehavior: Flickable.StopAtBounds
                            model: root.filteredCategories(rtdSearch.text); currentIndex: root.selectedCategory
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                            delegate: ItemDelegate {
                                width: ListView.view.width; height: 60; highlighted: index === root.selectedCategory; onClicked: root.selectedCategory = index
                                background: Rectangle { radius: 6; color: index === root.selectedCategory ? root.panelRaised : hovered ? "#0d1f31" : "transparent"; border.color: index === root.selectedCategory ? root.accent : "transparent" }
                                contentItem: ColumnLayout {
                                    spacing: 1
                                    Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.code; color: root.textMuted; font.pixelSize: 8; font.family: "monospace" }
                                }
                            }
                        }
                    }
                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: root.border }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                        Label { text: root.currentCategory() ? root.currentCategory().title : "Nincs találat"; color: root.textPrimary; font.pixelSize: 18; font.bold: true }
                        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.currentCategory() ? root.currentCategory().description : "A szűréshez nincs RTD kategória."; color: root.textMuted; font.pixelSize: 10 }
                        GridLayout {
                            Layout.fillWidth: true; columns: 2; columnSpacing: 18; rowSpacing: 10
                            Label { text: "Provider state"; color: root.textMuted }
                            Label { text: "ADAPTER-GATED"; color: root.orange; font.bold: true }
                            Label { text: "Last update"; color: root.textMuted }
                            Label { text: "N/A — nincs runtime evidence"; color: root.textPrimary }
                            Label { text: "Freshness SLA"; color: root.textMuted }
                            Label { text: root.currentCategory() ? root.currentCategory().freshness : "—"; color: root.textPrimary }
                            Label { text: "Protocols"; color: root.textMuted }
                            Label { text: root.currentCategory() ? root.currentCategory().protocols : "—"; color: root.textPrimary }
                            Label { text: "Authentication"; color: root.textMuted }
                            Label { text: "NOT CONFIGURED"; color: root.orange; font.bold: true }
                            Label { text: "Policy"; color: root.textMuted }
                            Label { text: "FAIL-CLOSED"; color: root.magenta; font.bold: true }
                            Label { text: "Provenance"; color: root.textMuted }
                            Label { text: "REQUIRED"; color: root.cyan; font.bold: true }
                        }
                        Panel {
                            Layout.fillWidth: true; Layout.preferredHeight: 145; color: root.panelRaised
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 7
                                Label { text: "Authority boundary"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Az RTD Providers a live-data capability operátori projekciója. Az Integrations csak a technikai adaptert mutatja; az Agents & Workflows csak a felhasználást. A GUI nem állít ONLINE állapotot, nem talál ki frissességet és nem kerülheti meg az auth/egress policy-t."; color: root.textMuted; font.pixelSize: 9 }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Button {
                                text: "Adapter ChangeSet-tervezet"; enabled: root.currentCategory() !== null
                                onClicked: {
                                    var c = root.currentCategory()
                                    root.draftPath = fa3Repository.createDraftChangeSet("RTD_PROVIDER", "propose.rtd.adapter", c.code, "RTD adapter konfigurációs javaslat: " + c.title + ". Freshness/auth/policy/provenance evidence kötelező.")
                                }
                            }
                            Label { text: root.draftPath; color: root.accent; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideMiddle }
                        }
                    }
                }
            }
            Panel {
                Layout.fillWidth: true; Layout.preferredHeight: 170
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Canonical RTD projection"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Label { text: fa3Repository.searchRecords("RTD").length + " RTD-találat a canonical indexben"; color: root.textMuted; font.pixelSize: 9 }
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: fa3Repository.searchRecords("RTD")
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                        delegate: ItemDelegate {
                            width: ListView.view.width; height: 40
                            contentItem: RowLayout {
                                Label { text: modelData.id; color: root.textPrimary; font.family: "monospace"; Layout.preferredWidth: 330; elide: Text.ElideRight }
                                Label { text: modelData.title; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: modelData.status; color: root.orange; Layout.preferredWidth: 150; elide: Text.ElideRight }
                            }
                        }
                    }
                }
            }
        }
    }
}
''', encoding='utf-8')

cmake = Path('apps/fa3-control-center/CMakeLists.txt')
c = cmake.read_text(encoding='utf-8')
if 'qml/RtdProvidersPage.qml' not in c:
    c = c.replace('set_source_files_properties(qml/SystemSettingsPage.qml PROPERTIES QT_RESOURCE_ALIAS SystemSettingsPage.qml)\n', 'set_source_files_properties(qml/SystemSettingsPage.qml PROPERTIES QT_RESOURCE_ALIAS SystemSettingsPage.qml)\nset_source_files_properties(qml/RtdProvidersPage.qml PROPERTIES QT_RESOURCE_ALIAS RtdProvidersPage.qml)\n')
    c = c.replace('        qml/SystemSettingsPage.qml\n', '        qml/SystemSettingsPage.qml\n        qml/RtdProvidersPage.qml\n')
cmake.write_text(c, encoding='utf-8')

gate = Path('src/fa3_gui_gate.py')
g = gate.read_text(encoding='utf-8')
if '"rtd_qml"' not in g:
    g = g.replace('    "settings_qml": ROOT / "apps/fa3-control-center/qml/SystemSettingsPage.qml",\n', '    "settings_qml": ROOT / "apps/fa3-control-center/qml/SystemSettingsPage.qml",\n    "rtd_qml": ROOT / "apps/fa3-control-center/qml/RtdProvidersPage.qml",\n')
g = g.replace('NAVIGATION = ["Command Center", "Projects"', 'NAVIGATION = ["Command Center", "RTD Providers", "Projects"')
check_marker = '    model_cpp = REQUIRED["model_cpp"].read_text(encoding="utf-8")\n'
checks = '''    rtd_qml = REQUIRED["rtd_qml"].read_text(encoding="utf-8")
    for token in ["Real-Time Data", "ADAPTER-GATED", "Freshness SLA", "Provenance", "FAIL-CLOSED", "Adapter ChangeSet-tervezet"]:
        if token not in rtd_qml: failures.append(f"qml-rtd-provider-surface-missing:{token}")
    if "RtdProvidersPage" not in qml or "RTD Data Sources" not in qml or "RTD Adapters" not in qml or '{label: "Real-Time Data", value: "RTD"}' not in qml:
        failures.append("qml-rtd-cross-surface-projection-missing")

'''
if 'qml-rtd-provider-surface-missing' not in g:
    g = g.replace(check_marker, checks + check_marker, 1)
gate.write_text(g, encoding='utf-8')
