import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtWebEngine

ApplicationWindow {
    id: window
    width: 1600
    height: 980
    minimumWidth: 1280
    minimumHeight: 760
    visible: true
    color: canvas
    title: "Final Architecture 3.0 — Control Center"

    property string dashboardCanonicalName: "Command Center"
    property int selectedIndex: 0
    property string askRole: "Mentor"
    property bool webWorkspaceOpen: false
    property bool chatWorkspaceOpen: false
    property string chatWorkspaceMode: "ASSISTANT"
    property string mcpChatTarget: "AUTO"
    property url webWorkspaceUrl: "about:blank"
    property string webWorkspaceTitle: "Web Workspace"
    property bool llmFitExpanded: false
    property bool compactNavigation: Boolean(fa3Preferences.value("appearance/compactNavigation", false))
    property bool statusStripVisible: Boolean(fa3Preferences.value("appearance/statusStripVisible", true))
    property string colorTheme: String(fa3Preferences.value("appearance/colorTheme", "Blue"))
    property string navigationPosition: String(fa3Preferences.value("appearance/navigationBarPosition", "Left"))
    property string shortcutDashboard: String(fa3Preferences.value("shortcuts/dashboard", "Ctrl+1"))
    property string shortcutProjects: String(fa3Preferences.value("shortcuts/projects", "Ctrl+2"))
    property string shortcutAiStudio: String(fa3Preferences.value("shortcuts/aiStudio", "Ctrl+3"))
    property string shortcutSearch: String(fa3Preferences.value("shortcuts/search", "Ctrl+K"))
    property string shortcutSettings: String(fa3Preferences.value("shortcuts/settings", "Ctrl+,"))
    property string shortcutToggleStatus: String(fa3Preferences.value("shortcuts/toggleStatus", "Ctrl+Shift+S"))

    function accentForTheme(name) {
        if (name === "Cyan") return "#22d3ee"
        if (name === "Green") return "#35e0a1"
        if (name === "Magenta") return "#b778ff"
        if (name === "Amber") return "#f0b14a"
        return "#25a7ff"
    }

    function openInternalWeb(targetUrl, titleText) {
        chatWorkspaceOpen = false
        webWorkspaceUrl = targetUrl
        webWorkspaceTitle = titleText
        webWorkspaceOpen = true
    }

    function openRoleChat(roleName) {
        askRole = roleName
        chatWorkspaceMode = "ASSISTANT"
        mcpChatTarget = "AUTO"
        webWorkspaceOpen = false
        chatWorkspaceOpen = true
    }

    function openMcpChat(targetId) {
        chatWorkspaceMode = "MCP CONTROL"
        mcpChatTarget = targetId && targetId.length > 0 ? targetId : "AUTO"
        webWorkspaceOpen = false
        chatWorkspaceOpen = true
    }

    function closeTransientWorkspaces() {
        webWorkspaceOpen = false
        chatWorkspaceOpen = false
    }

    function openLanguageControl() {
        closeTransientWorkspaces()
        selectedIndex = 23
        if (languageDrawer.opened) languageDrawer.close()
    }

    property var uiSearchIndex: [
        {title: "Dashboard", detail: "Command Center és rendszerállapot", category: "FUNCTION", pageIndex: 0},
        {title: "Remote AI Hub", detail: "Távoli AI-kapacitás és hosted execution", category: "FUNCTION", pageIndex: 1},
        {title: "RTD Providers", detail: "Real-Time Data provider-ek, frissesség, policy és provenance", category: "FUNCTION", pageIndex: 17},
        {title: "Projects & Workspaces", detail: "Projektek, assetek és knowledge-contextus", category: "FUNCTION", pageIndex: 2},
        {title: "Knowledge & Retrieval", detail: "Hierarchical + hybrid retrieval, PageIndex Local, trace és provenance", category: "FUNCTION", pageIndex: 28},
        {title: "Work Management", detail: "Kaneo + Kanboard provider-neutral projects, boards, tasks és automation", category: "FUNCTION", pageIndex: 24},
        {title: "Tasks & Boards", detail: "Provider-neutral work-item projection és reconciliation", category: "FUNCTION", pageIndex: 24},
        {title: "Accelerator Guard", detail: "GPU/NPU contention és explicit user arbitration", category: "FUNCTION", pageIndex: 25},
        {title: "AI Studio", detail: "Kreatív és publikációs pipeline", category: "FUNCTION", pageIndex: 3},
        {title: "Subtitle Studio", detail: "Fókuszált felirat authoring, sync, QC és formátumkezelés", category: "FUNCTION", pageIndex: 35},
        {title: "Narration Studio", detail: "Feliratból narráció, voice-over és dubbing tervezés", category: "FUNCTION", pageIndex: 36},
        {title: "Image", detail: "AI Studio kép pipeline", category: "FUNCTION", pageIndex: 3},
        {title: "Video", detail: "AI Studio videó pipeline", category: "FUNCTION", pageIndex: 3},
        {title: "Animation", detail: "AI Studio animáció", category: "FUNCTION", pageIndex: 3},
        {title: "3D / VFX", detail: "AI Studio 3D és VFX", category: "FUNCTION", pageIndex: 3},
        {title: "Audio", detail: "AI Studio audio", category: "FUNCTION", pageIndex: 3},
        {title: "Music", detail: "AI Studio zenei workflow", category: "FUNCTION", pageIndex: 3},
        {title: "Story / Screenplay", detail: "Történet és forgatókönyv", category: "FUNCTION", pageIndex: 3},
        {title: "Marketing", detail: "Marketing és publikációs workflow", category: "FUNCTION", pageIndex: 3},
        {title: "Weboldal", detail: "Webes publikáció", category: "FUNCTION", pageIndex: 3},
        {title: "Prezentáció", detail: "Prezentáció készítés és export", category: "FUNCTION", pageIndex: 3},
        {title: "Agents & Workflows", detail: "Agentek, taskok és durable workflow-k", category: "FUNCTION", pageIndex: 4},
        {title: "Models & Providers", detail: "Provider registry és inference felületek", category: "FUNCTION", pageIndex: 5},
        {title: "Model Manager", detail: "Modellek felderítése és nyilvántartása", category: "FUNCTION", pageIndex: 6},
        {title: "Checkpoint Manager", detail: "Checkpoint, LoRA, VAE és adapter artifact governance", category: "FUNCTION", pageIndex: 20},
        {title: "External Providers Setup", detail: "Külső/fizetős provider engedélyezés, budget és credential state", category: "FUNCTION", pageIndex: 21},
        {title: "Token Control Center", detail: "Credential és AI token governance, budget, audit és költség", category: "FUNCTION", pageIndex: 22},
        {title: "Tolmács", detail: "Nyelvi híd ember, FA3 és AI modellek között", category: "FUNCTION", pageIndex: 23},
        {title: "LLM Fit", detail: "Model Manager hardver- és kompatibilitási felület", category: "FUNCTION", pageIndex: 6},
        {title: "Architecture", detail: "Canonical architektúra böngésző", category: "FUNCTION", pageIndex: 8},
        {title: "Resources", detail: "CPU/GPU/NPU/NUMA erőforrások", category: "FUNCTION", pageIndex: 9},
        {title: "Security & Approvals", detail: "Policy, approval és security evidence", category: "FUNCTION", pageIndex: 10},
        {title: "Observability", detail: "Metrics, traces és provenance", category: "FUNCTION", pageIndex: 11},
        {title: "Napló / Journal", detail: "Rendszer-, beszélgetés- és projektnapló", category: "FUNCTION", pageIndex: 12},
        {title: "FA3 OS", detail: "Aktivitás, workstream, privacy és provenance kontextus", category: "FUNCTION", pageIndex: 26},
        {title: "Evidence", detail: "Conformance és promotion evidence", category: "FUNCTION", pageIndex: 13},
        {title: "Integrations", detail: "Desktop, MCP és provider integrációk", category: "FUNCTION", pageIndex: 14},
        {title: "MCP Gateway", detail: "Central MCP Gateway registry, routing, policy és security operátori felület", category: "FUNCTION", pageIndex: 27},
        {title: "Trust & Certificates", detail: "Belső PKI, machine identity, ACME, mTLS és SSH certificate állapot", category: "FUNCTION", pageIndex: 29},
        {title: "Session Vault / Kulcsvault", detail: "LUKS2 key-vault image, automatikus jelszókezelős feloldás és kulcskezelés", category: "FUNCTION", pageIndex: 30},
        {title: "Decision Fabric", detail: "Provider-neutral bounded semantic decision fabric", category: "FUNCTION", pageIndex: 31},
        {title: "Decision Inspector", detail: "Read-only append-only Decision Trace inspection", category: "FUNCTION", pageIndex: 32},
        {title: "External Project Radar", detail: "Pinned Jev ecosystem source, license and reuse radar", category: "FUNCTION", pageIndex: 33},
        {title: "Context Inspector", detail: "PROTECTED / ACTIVE / HIDDEN / ARCHIVED context projection", category: "FUNCTION", pageIndex: 34},
        {title: "MCP Control Chat", detail: "GIMP, Krita, Blender, Kdenlive, OpenShot és más MCP-vezérelt alkalmazások természetes nyelvű orchestration felülete", category: "FUNCTION", pageIndex: 14},
        {title: "Rendszerbeállítások", detail: "FA3 GUI és host beállítások", category: "FUNCTION", pageIndex: 15},
        {title: "System", detail: "Runtime és platform információ", category: "FUNCTION", pageIndex: 16},
        {title: "Megjelenés", detail: "Téma, sűrűség és betűméret", category: "SETTING", pageIndex: 15},
        {title: "Erőforrás-policy", detail: "CPU/GPU/NPU/NUMA preferenciák", category: "SETTING", pageIndex: 15},
        {title: "Hálózat", detail: "Lokális szolgáltatások és egress policy", category: "SETTING", pageIndex: 15},
        {title: "Biztonság", detail: "Security policy és approval beállítások", category: "SETTING", pageIndex: 15},
        {title: "Frissítések", detail: "FA3 komponens- és provider-frissítések", category: "SETTING", pageIndex: 15},
        {title: "Naplózás", detail: "Retention, export és archive preferenciák", category: "SETTING", pageIndex: 15},
        {title: "Appearance", detail: "Színes téma és Navigation Bar position", category: "SETTING", pageIndex: 15},
        {title: "Chat Style", detail: "Chat nézet, tipográfia és message-flow", category: "SETTING", pageIndex: 15},
        {title: "Reasoning", detail: "Reasoning blokk megjelenítési preferenciák", category: "SETTING", pageIndex: 15},
        {title: "Gyorsbillentyűk", detail: "FA3 Control Center shortcut beállítások", category: "SETTING", pageIndex: 15},
        {title: "CPU GPU NPU DGX", detail: "Compute és accelerator policy", category: "SETTING", pageIndex: 15},
        {title: "Webkamera Nyomtató Scanner", detail: "Periféria felderítés és adapter policy", category: "SETTING", pageIndex: 15},
        {title: "MIDI GIMP Ardour", detail: "MIDI és control-surface mapping", category: "SETTING", pageIndex: 15}
    ]

    // User-facing applications represented inside FA3. This catalog is deliberately
    // independent from the host XDG/.desktop application inventory.
    property var fa3ApplicationIndex: [
        {title: "ComfyUI", detail: "FA3 image/video generation frontend · Shared Models", pageIndex: 20},
        {title: "Automatic1111", detail: "FA3 Stable Diffusion frontend · Shared Models", pageIndex: 20},
        {title: "Forge", detail: "FA3 Stable Diffusion Forge frontend · Shared Models", pageIndex: 20},
        {title: "Fooocus", detail: "FA3 image generation frontend · Shared Models", pageIndex: 20},
        {title: "Krita", detail: "FA3 creative editor integration", pageIndex: 14},
        {title: "GIMP", detail: "FA3 creative editor integration", pageIndex: 14},
        {title: "Kdenlive", detail: "FA3 video editor integration", pageIndex: 14},
        {title: "Bforartist", detail: "FA3 3D/DCC integration", pageIndex: 14},
        {title: "Blender", detail: "FA3 3D/DCC integration", pageIndex: 14},
        {title: "Natron", detail: "FA3 compositing integration", pageIndex: 14},
        {title: "Gaffer", detail: "FA3 compositing/look-dev integration", pageIndex: 14},
        {title: "Goose", detail: "FA3 agent client integration", pageIndex: 14},
        {title: "Open WebUI", detail: "FA3 local AI client integration", pageIndex: 14},
        {title: "OpenYak", detail: "FA3 desktop agent workbench integration", pageIndex: 14},
        {title: "n8n", detail: "FA3 workflow orchestration application", pageIndex: 4},
        {title: "Temporal", detail: "FA3 durable workflow runtime", pageIndex: 4},
        {title: "Ollama", detail: "FA3 local model runtime/provider", pageIndex: 5},
        {title: "LM Studio", detail: "FA3 local model client/provider", pageIndex: 5}
    ]

    function searchFa3Applications(query) {
        var needle = query.trim().toLowerCase()
        var out = []
        for (var i = 0; i < fa3ApplicationIndex.length; ++i) {
            var app = fa3ApplicationIndex[i]
            var haystack = (app.title + " " + app.detail).toLowerCase()
            if (needle.length === 0 || haystack.indexOf(needle) >= 0) {
                out.push({
                    id: app.title,
                    title: app.title,
                    subtitle: app.detail,
                    status: "FA3 APP",
                    category: "APPLICATION",
                    sourceType: "APPLICATION",
                    pageIndex: app.pageIndex,
                    path: ""
                })
            }
        }
        return out
    }

    property var rtdProviderCategories: [
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

    function searchUiEntries(query, category) {
        var needle = query.trim().toLowerCase()
        var out = []
        for (var i = 0; i < uiSearchIndex.length; ++i) {
            var entry = uiSearchIndex[i]
            if (category !== "ALL" && entry.category !== category)
                continue
            var haystack = (entry.title + " " + entry.detail).toLowerCase()
            if (needle.length === 0 || haystack.indexOf(needle) >= 0) {
                out.push({id: entry.title, title: entry.title, subtitle: entry.detail, status: "FA3 UI", category: entry.category, sourceType: entry.category, pageIndex: entry.pageIndex, path: ""})
            }
        }
        return out
    }

    function unifiedSearchResults(query, scope) {
        var needle = query.trim()
        var out = []
        var i
        if (scope === "ALL" || scope === "PROJECT") {
            var projectRows = fa3Journal.filteredEvents("ALL", needle)
            var seenProjects = ({})
            for (i = projectRows.length - 1; i >= 0; --i) {
                var p = projectRows[i]
                var projectId = p.project_id || ""
                if (projectId.length === 0 || seenProjects[projectId])
                    continue
                seenProjects[projectId] = true
                out.push({id: projectId, title: projectId, subtitle: p.summary || p.details || "Projekt naplóbejegyzés", status: p.lifecycle || "PROJECT", category: "PROJECT", sourceType: "PROJECT", pageIndex: 2, path: ""})
            }
        }
        if (scope === "ALL" || scope === "CONVERSATION") {
            var conversationRows = fa3Journal.filteredEvents("CONVERSATION", needle)
            for (i = conversationRows.length - 1; i >= 0; --i) {
                var c = conversationRows[i]
                out.push({id: c.id || "CONVERSATION", title: c.summary || "Beszélgetés", subtitle: c.details || c.source || "Conversation journal", status: c.lifecycle || "RECORDED", category: "CONVERSATION", sourceType: "CONVERSATION", pageIndex: 12, path: ""})
                if (out.length >= 300) break
            }
        }
        if (scope === "ALL" || scope === "APPLICATION") {
            var apps = searchFa3Applications(needle)
            for (i = 0; i < apps.length; ++i) out.push(apps[i])
        }
        if (scope === "ALL" || scope === "FUNCTION") {
            var functions = searchUiEntries(needle, "FUNCTION")
            for (i = 0; i < functions.length; ++i) out.push(functions[i])
        }
        if (scope === "ALL" || scope === "SETTING") {
            var settings = searchUiEntries(needle, "SETTING")
            for (i = 0; i < settings.length; ++i) out.push(settings[i])
        }
        if (scope === "ALL" || scope === "RTD") {
            var rtdRows = searchRtdEntries(needle)
            for (i = 0; i < rtdRows.length; ++i) out.push(rtdRows[i])
        }
        if (scope === "ALL" || scope === "CANONICAL") {
            var records = fa3Repository.searchRecords(needle)
            for (i = 0; i < records.length; ++i) {
                var r = records[i]
                out.push({id: r.id, title: r.title, subtitle: r.path, status: r.status, category: r.category.toUpperCase(), sourceType: "CANONICAL", pageIndex: -1, path: r.path})
            }
        }
        return out
    }

    function architectureResults(query, scope) {
        var records = fa3Repository.searchRecords(query)
        if (scope === "ALL") return records
        var wanted = scope.toLowerCase()
        return records.filter(function(v) { return v.category.toLowerCase() === wanted })
    }

    property color canvas: "#07111f"
    property color sidebar: "#081421"
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color borderSoft: "#14283e"
    property color accent: accentForTheme(window.colorTheme)
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"

    Connections {
        target: fa3Preferences
        function onPreferenceChanged(key, value) {
            if (key === "appearance/colorTheme") window.colorTheme = String(value)
            else if (key === "appearance/navigationBarPosition") window.navigationPosition = String(value)
            else if (key === "appearance/compactNavigation") window.compactNavigation = Boolean(value)
            else if (key === "appearance/statusStripVisible") window.statusStripVisible = Boolean(value)
            else if (key === "shortcuts/dashboard") window.shortcutDashboard = String(value)
            else if (key === "shortcuts/projects") window.shortcutProjects = String(value)
            else if (key === "shortcuts/aiStudio") window.shortcutAiStudio = String(value)
            else if (key === "shortcuts/search") window.shortcutSearch = String(value)
            else if (key === "shortcuts/settings") window.shortcutSettings = String(value)
            else if (key === "shortcuts/toggleStatus") window.shortcutToggleStatus = String(value)
        }
    }

    Shortcut { sequence: "Ctrl+Shift+L"; context: Qt.ApplicationShortcut; onActivated: window.openLanguageControl() }
    Shortcut { sequence: window.shortcutDashboard; context: Qt.ApplicationShortcut; onActivated: { window.closeTransientWorkspaces(); window.selectedIndex = 0 } }
    Shortcut { sequence: window.shortcutProjects; context: Qt.ApplicationShortcut; onActivated: { window.closeTransientWorkspaces(); window.selectedIndex = 2 } }
    Shortcut { sequence: window.shortcutAiStudio; context: Qt.ApplicationShortcut; onActivated: { window.closeTransientWorkspaces(); window.selectedIndex = 3 } }
    Shortcut { sequence: window.shortcutSearch; context: Qt.ApplicationShortcut; onActivated: { window.closeTransientWorkspaces(); window.selectedIndex = 7 } }
    Shortcut { sequence: window.shortcutSettings; context: Qt.ApplicationShortcut; onActivated: { window.closeTransientWorkspaces(); window.selectedIndex = 15 } }
    Shortcut { sequence: window.shortcutToggleStatus; context: Qt.ApplicationShortcut; onActivated: { window.statusStripVisible = !window.statusStripVisible; fa3Preferences.setValue("appearance/statusStripVisible", window.statusStripVisible) } }

    component Panel: Rectangle {
        radius: 9
        color: window.panel
        border.color: window.border
        border.width: 1
    }

    component SectionTitle: ColumnLayout {
        property string title: ""
        property string subtitle: ""
        spacing: 2
        Label { text: parent.title; color: window.textPrimary; font.pixelSize: 22; font.bold: true }
        Label { text: parent.subtitle; color: window.textMuted; font.pixelSize: 11 }
    }

    component StatusChip: Rectangle {
        property string chipText: "READY"
        property color tone: window.green
        implicitWidth: chipLabel.implicitWidth + 16
        implicitHeight: 22
        radius: 5
        color: Qt.rgba(tone.r, tone.g, tone.b, 0.10)
        border.color: Qt.rgba(tone.r, tone.g, tone.b, 0.34)
        Label {
            id: chipLabel
            anchors.centerIn: parent
            text: parent.chipText
            color: parent.tone
            font.pixelSize: 8
            font.bold: true
        }
    }

    component NavButton: Rectangle {
        property string iconText: "•"
        property string label: ""
        property int pageIndex: 0
        property bool active: window.selectedIndex === pageIndex
        Layout.fillWidth: true
        implicitHeight: window.compactNavigation ? 32 : 36
        radius: 6
        color: active ? "#102a43" : navMouse.containsMouse ? "#0d1f31" : "transparent"
        border.color: active ? "#1f4c70" : "transparent"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 11
            anchors.rightMargin: 8
            spacing: 10
            Label {
                text: parent.parent.iconText
                color: parent.parent.active ? window.accent : window.textMuted
                font.pixelSize: 13
                Layout.preferredWidth: 18
                horizontalAlignment: Text.AlignHCenter
            }
            Label {
                text: parent.parent.label
                color: parent.parent.active ? window.textPrimary : window.textMuted
                font.pixelSize: 10
                font.bold: parent.parent.active
                Layout.fillWidth: true
            }
        }
        MouseArea {
            id: navMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: { window.closeTransientWorkspaces(); window.selectedIndex = parent.pageIndex }
        }
    }

    component ModuleCard: Panel {
        property string title: ""
        property string subtitle: ""
        property string badge: "READY"
        property color tone: window.accent
        implicitWidth: 250
        implicitHeight: 126
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Rectangle { width: 8; height: 8; radius: 4; color: parent.parent.parent.tone }
                Label {
                    text: parent.parent.parent.title
                    color: window.textPrimary
                    font.pixelSize: 14
                    font.bold: true
                    Layout.fillWidth: true
                }
                StatusChip { chipText: parent.parent.parent.badge; tone: parent.parent.parent.tone }
            }
            Label {
                text: parent.parent.subtitle
                color: window.textMuted
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    component ModulePage: ScrollView {
        id: modulePage
        property string pageTitle: ""
        property string pageSubtitle: ""
        property var cards: []
        clip: true
        contentWidth: availableWidth
        padding: 18
        ColumnLayout {
            width: modulePage.availableWidth
            spacing: 16
            SectionTitle { title: modulePage.pageTitle; subtitle: modulePage.pageSubtitle }
            Flow {
                Layout.fillWidth: true
                spacing: 12
                Repeater {
                    model: modulePage.cards
                    delegate: ModuleCard {
                        required property var modelData
                        title: modelData.title || ""
                        subtitle: modelData.subtitle || ""
                        badge: modelData.badge || "READY"
                        tone: modelData.tone || window.accent
                    }
                }
            }
        }
    }

    component QuickLink: Rectangle {
        id: quickLinkRoot
        property string linkText: ""
        property string targetUrl: ""
        implicitWidth: quickLinkLabel.implicitWidth + 18
        implicitHeight: 28
        radius: 6
        color: quickMouse.containsMouse ? "#132a42" : "#0d1c2f"
        border.color: window.border
        Label {
            id: quickLinkLabel
            anchors.centerIn: parent
            text: quickLinkRoot.linkText
            color: window.textPrimary
            font.pixelSize: 9
            font.bold: true
        }
        MouseArea {
            id: quickMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: window.openInternalWeb(quickLinkRoot.targetUrl, quickLinkRoot.linkText)
        }
    }

    component StatusItem: RowLayout {
        property string labelText: ""
        property string valueText: "N/A"
        property color tone: window.orange
        spacing: 5
        Rectangle { width: 6; height: 6; radius: 3; color: parent.tone }
        Label { text: parent.labelText; color: window.textMuted; font.pixelSize: 8; font.bold: true }
        Label { text: parent.valueText; color: window.textPrimary; font.pixelSize: 8 }
    }

    Drawer {
        id: languageDrawer
        parent: Overlay.overlay
        edge: Qt.RightEdge
        modal: true
        interactive: true
        width: Math.min(window.width * 0.68, 980)
        height: window.height
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: window.canvas
            border.color: window.border
        }

        contentItem: ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                color: "#081421"
                border.color: window.borderSoft
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 12
                    spacing: 10
                    Label {
                        text: "文/A  Tolmács / Nyelvi híd"
                        color: window.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                        Layout.fillWidth: true
                    }
                    Label {
                        text: "FA3-GUI-LANGUAGE-CONTROL-001"
                        color: window.textMuted
                        font.pixelSize: 8
                    }
                    ToolButton {
                        text: "×"
                        onClicked: languageDrawer.close()
                    }
                }
            }

            LanguageControlPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
                preferences: fa3Preferences
                panel: window.panel
                panelRaised: window.panelRaised
                border: window.border
                textPrimary: window.textPrimary
                textMuted: window.textMuted
                accent: window.accent
                green: window.green
                orange: window.orange
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        LayoutMirroring.enabled: window.navigationPosition === "Right"
        LayoutMirroring.childrenInherit: false

        Rectangle {
            Layout.preferredWidth: window.compactNavigation ? 190 : 224
            Layout.fillHeight: true
            color: window.sidebar
            border.color: window.borderSoft

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 12
                        spacing: 11
                        Rectangle {
                            width: 30; height: 30; radius: 7
                            color: window.accent
                            Label { anchors.centerIn: parent; text: "F"; color: "white"; font.pixelSize: 17; font.bold: true }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: -1
                            Label { text: "FA3"; color: window.textPrimary; font.pixelSize: 15; font.bold: true }
                            Label { text: "Final Architecture"; color: window.textMuted; font.pixelSize: 8 }
                        }
                        Rectangle { width: 7; height: 7; radius: 4; color: window.green }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: window.borderSoft }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth
                    background: Item {}
                    ColumnLayout {
                        width: parent.width
                        spacing: 3
                        anchors.leftMargin: 9
                        anchors.rightMargin: 9

                        Item { Layout.preferredHeight: 8 }
                        Label { text: "SYSTEM"; color: "#50667e"; font.pixelSize: 8; font.bold: true; Layout.leftMargin: 10 }
                        NavButton { iconText: "⌂"; label: "Dashboard"; pageIndex: 0 }
                        NavButton { iconText: "☁"; label: "Remote AI Hub"; pageIndex: 1 }
                        NavButton { iconText: "⇄"; label: "External Providers Setup"; pageIndex: 21 }
                        NavButton { iconText: "◉"; label: "RTD Providers"; pageIndex: 17 }
                        NavButton { iconText: "▣"; label: "Projects"; pageIndex: 2 }
                        NavButton { iconText: "⌘"; label: "Knowledge & Retrieval"; pageIndex: 28 }
                        NavButton { iconText: "✓"; label: "Work Management"; pageIndex: 24 }
                        NavButton { iconText: "⚡"; label: "Accelerator Guard"; pageIndex: 25 }
                        NavButton { iconText: "⌘"; label: "Agents & Workflows"; pageIndex: 4 }
                        NavButton { iconText: "◫"; label: "Models & Providers"; pageIndex: 5 }
                        NavButton { iconText: "▦"; label: "Model Manager"; pageIndex: 6 }
                        NavButton { iconText: "◧"; label: "Checkpoint Manager"; pageIndex: 20 }
                        NavButton { iconText: "#"; label: "Token Control Center"; pageIndex: 22 }
                        NavButton { iconText: "⌕"; label: "Keresés"; pageIndex: 7 }
                        NavButton { iconText: "文"; label: "Tolmács"; pageIndex: 23 }
                        NavButton { iconText: "◇"; label: "Architecture"; pageIndex: 8 }
                        NavButton { iconText: "⚙"; label: "Rendszerbeállítások"; pageIndex: 15 }
                        NavButton { iconText: "ⓘ"; label: "System"; pageIndex: 16 }

                        Item { Layout.preferredHeight: 8 }
                        Label { text: "STUDIO"; color: "#50667e"; font.pixelSize: 8; font.bold: true; Layout.leftMargin: 10 }
                        NavButton { iconText: "✦"; label: "AI Studio"; pageIndex: 3 }
                        NavButton { iconText: "CC"; label: "Subtitle Studio"; pageIndex: 35 }
                        NavButton { iconText: "VO"; label: "Narration Studio"; pageIndex: 36 }
                        NavButton { iconText: "↔"; label: "Integrations"; pageIndex: 14 }
                        NavButton { iconText: "⇄"; label: "MCP Gateway"; pageIndex: 27 }
                        NavButton { iconText: "⌾"; label: "Trust & Certificates"; pageIndex: 29 }
                        NavButton { iconText: "▣"; label: "Session Vault / Kulcsvault"; pageIndex: 30 }
                        NavButton { iconText: "◇"; label: "Decision Fabric"; pageIndex: 31 }
                        NavButton { iconText: "⊙"; label: "Decision Inspector"; pageIndex: 32 }
                        NavButton { iconText: "⌕"; label: "External Project Radar"; pageIndex: 33 }

                        Item { Layout.preferredHeight: 8 }
                        Label { text: "MONITOR"; color: "#50667e"; font.pixelSize: 8; font.bold: true; Layout.leftMargin: 10 }
                        NavButton { iconText: "▤"; label: "Resources"; pageIndex: 9 }
                        NavButton { iconText: "◆"; label: "Security & Approvals"; pageIndex: 10 }
                        NavButton { iconText: "⌁"; label: "Observability"; pageIndex: 11 }
                        NavButton { iconText: "≡"; label: "Napló / Journal"; pageIndex: 12 }
                        NavButton { iconText: "◎"; label: "FA3 OS"; pageIndex: 26 }
                        NavButton { iconText: "✓"; label: "Evidence"; pageIndex: 13 }
                        NavButton { iconText: "▤"; label: "Context Inspector"; pageIndex: 34 }
                    }
                }

                Panel {
                    Layout.fillWidth: true
                    Layout.leftMargin: 10
                    Layout.rightMargin: 10
                    Layout.bottomMargin: 10
                    Layout.preferredHeight: 102
                    color: "#0a1928"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 11
                        spacing: 4
                        RowLayout {
                            Rectangle { width: 7; height: 7; radius: 4; color: window.green }
                            Label { text: "SYSTEM ONLINE"; color: window.green; font.pixelSize: 8; font.bold: true }
                        }
                        Label { text: fa3Repository.hostName; color: window.textPrimary; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: "Kernel " + fa3Repository.kernelVersion; color: window.textMuted; font.pixelSize: 8; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: "Journal " + fa3Journal.eventCount + " / " + fa3Journal.archiveCount; color: window.textMuted; font.pixelSize: 8 }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                id: assistantToolbar
                Layout.fillWidth: true
                Layout.preferredHeight: 104
                color: "#081421"
                border.color: window.borderSoft

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 10

                            ColumnLayout {
                                spacing: 0
                                Label { text: "Current Environment"; color: window.textMuted; font.pixelSize: 8 }
                                RowLayout {
                                    spacing: 7
                                    Rectangle { width: 7; height: 7; radius: 4; color: window.green }
                                    Label { text: "LOCAL / FA3"; color: window.textPrimary; font.pixelSize: 10; font.bold: true }
                                }
                            }

                            Item { Layout.fillWidth: true }
                            Label { text: "CANONICAL"; color: window.accent; font.pixelSize: 9; font.bold: true }
                            Rectangle { width: 1; height: 22; color: window.border }
                            Label { text: fa3Repository.canonicalRecordCount + " records"; color: window.textMuted; font.pixelSize: 9 }
                            ToolButton {
                                implicitWidth: 30
                                implicitHeight: 30
                                text: "↻"
                                ToolTip.visible: hovered
                                ToolTip.text: "FA3 állapot frissítése"
                                onClicked: { fa3Repository.refresh(); fa3Journal.refresh() }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.borderSoft }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 8

                            Label {
                                text: "ASSZISZTENS"
                                color: window.textMuted
                                font.pixelSize: 8
                                font.bold: true
                                Layout.preferredWidth: 72
                            }
                            Rectangle { width: 1; height: 26; color: window.border }

                            ToolButton {
                                id: askButton
                                Layout.minimumWidth: 180
                                Layout.preferredWidth: 210
                                Layout.preferredHeight: 32
                                text: "Kérdezd: " + window.askRole + " ▾"
                                onClicked: askMenu.open()
                                contentItem: Label {
                                    text: parent.text
                                    color: window.textPrimary
                                    font.pixelSize: 9
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#132a42" : "#0d1c2f"
                                    border.color: window.border
                                }
                                Menu {
                                    id: askMenu
                                    y: parent.height
                                    MenuItem { text: "Mentor"; onTriggered: window.openRoleChat("Mentor") }
                                    MenuItem { text: "Coach"; onTriggered: window.openRoleChat("Coach") }
                                    MenuItem { text: "Manager"; onTriggered: window.openRoleChat("Manager") }
                                    MenuItem { text: "Ellenőr"; onTriggered: window.openRoleChat("Ellenőr") }
                                    MenuItem { text: "Ötletelő"; onTriggered: window.openRoleChat("Ötletelő") }
                                    MenuItem { text: "Tanácsadó"; onTriggered: window.openRoleChat("Tanácsadó") }
                                    MenuSeparator {}
                                    MenuItem { text: "MCP Control Chat"; onTriggered: window.openMcpChat("AUTO") }
                                }
                            }

                            ToolButton {
                                id: languageButton
                                Layout.minimumWidth: 118
                                Layout.preferredWidth: 126
                                Layout.preferredHeight: 32
                                text: "文/A  Tolmács"
                                onClicked: window.openLanguageControl()
                                ToolTip.visible: hovered
                                ToolTip.text: "Tolmács / Nyelvi híd · Ctrl+Shift+L"
                                Accessible.name: "Tolmács / Nyelvi híd"
                                contentItem: Label {
                                    text: parent.text
                                    color: window.textPrimary
                                    font.pixelSize: 9
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#132a42" : "#0d1c2f"
                                    border.color: window.accent
                                }
                            }

                            Item { Layout.fillWidth: true }
                            QuickLink { linkText: "Hugging Face"; targetUrl: "https://huggingface.co/" }
                            QuickLink { linkText: "CivitAI"; targetUrl: "https://civitai.com/" }
                            QuickLink { linkText: "OpenModelDB"; targetUrl: "https://openmodeldb.info/" }
                        }
                    }
                }
            }

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.chatWorkspaceOpen ? 19 : (window.webWorkspaceOpen ? 18 : window.selectedIndex)

                Item {
                    DashboardPage {
                        anchors.fill: parent
                        anchors.margins: 16
                        canvas: window.canvas
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
                }

                ModulePage {
                    pageTitle: "Remote AI Hub"
                    pageSubtitle: "Providerfüggetlen hosted execution és távoli AI-kapacitás, policy-gated módon"
                    cards: [
                        {title: "Hosted Execution", subtitle: "Távoli inference/execution csak explicit provider- és policy-adapteren át.", badge: "GATED", tone: window.orange},
                        {title: "Hugging Face Spaces", subtitle: "Hosted-execution provider; külön a HF Model Store modelltár-projekciótól.", badge: "PROVIDER", tone: window.accent},
                        {title: "Remote Queue", subtitle: "Távoli munkák és visszaérkező artifactok operátori projekciója.", badge: "ROUTED", tone: window.cyan},
                        {title: "Egress Policy", subtitle: "Adat- és artifact-kiküldés fail-closed engedélyezési határral.", badge: "FAIL-CLOSED", tone: window.magenta}
                    ]
                }

                ModulePage {
                    pageTitle: "Projects & Workspaces"
                    pageSubtitle: "Projekt-, asset- és knowledge-contextus az operátori felületen"
                    cards: [
                        {title: "Active Workspace", subtitle: "FA3 repository és az aktuális canonical graph.", badge: "LOCAL", tone: window.cyan},
                        {title: "Assets", subtitle: "Kép, videó, 3D, audio és dokumentum projekció.", badge: "INDEX", tone: window.accent},
                        {title: "Knowledge", subtitle: "Canonical RAG/read projection párhuzamos authority nélkül.", badge: "READ", tone: window.green},
                        {title: "Project Journal", subtitle: "Aktív, lezárt és tervezett projektek lifecycle-naplója.", badge: "JOURNAL", tone: window.magenta}
                    ]
                }

                AiStudioPage {
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

                ModulePage {
                    pageTitle: "Agents & Workflows"
                    pageSubtitle: "Interaktív agentek, durable workflow-k és policy-gated execution"
                    cards: [
                        {title: "Interactive Agents", subtitle: "Goose és desktop agent projection.", badge: "ROUTED", tone: window.accent},
                        {title: "Durable Workflows", subtitle: "Temporal authority állapot és futások.", badge: "READ", tone: window.green},
                        {title: "Tasks", subtitle: "Current tasks, approvals és blockers.", badge: "QUEUE", tone: window.orange},
                        {title: "Tool Execution", subtitle: "Central MCP mediation és policy outcome.", badge: "GATED", tone: window.magenta},
                        {title: "RTD Data Sources", subtitle: "Workflow-szintű élő adatforrás-kötések az RTD Providers policy- és freshness-határán keresztül.", badge: "DATA", tone: window.cyan}
                    ]
                }

                ModelsProvidersPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    cyan: window.cyan
                    green: window.green
                    orange: window.orange
                }

                ScrollView {
                    id: modelManagerView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: modelManagerView.availableWidth
                        spacing: 14
                        SectionTitle { title: "Model Manager"; subtitle: "FA3-MODEL-MANAGER-001 · modellek felderítése, beszerzése, nyilvántartása és provider-projekciója" }
                        RowLayout {
                            Layout.fillWidth: true
                            ModuleCard { Layout.fillWidth: true; title: "Starter modellek"; subtitle: "Ajánlott induló modellek hardver- és capability-szűréssel."; badge: "CURATED"; tone: window.green }
                            ModuleCard { Layout.fillWidth: true; title: "Local Registry"; subtitle: "Lokális modellek és provider-kapcsolatok canonical projekciója."; badge: "CANONICAL"; tone: window.accent }
                            ModuleCard { Layout.fillWidth: true; title: "Compatibility"; subtitle: "Formátum, runtime és hardver-kompatibilitás ellenőrzése."; badge: "GATED"; tone: window.orange }
                        }
                        RowLayout {
                            spacing: 8
                            QuickLink { linkText: "Hugging Face"; targetUrl: "https://huggingface.co/" }
                            QuickLink { linkText: "CivitAI"; targetUrl: "https://civitai.com/" }
                            QuickLink { linkText: "OpenModelDB"; targetUrl: "https://openmodeldb.info/" }
                            ToolButton {
                                id: llmFitButton
                                text: "LLM Fit"
                                checkable: true
                                checked: window.llmFitExpanded
                                onClicked: window.llmFitExpanded = !window.llmFitExpanded
                                contentItem: Label {
                                    text: parent.text
                                    color: window.llmFitExpanded ? window.cyan : window.textPrimary
                                    font.pixelSize: 9
                                    font.bold: true
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    radius: 6
                                    color: window.llmFitExpanded ? "#12324a" : (parent.hovered ? "#132a42" : "#0d1c2f")
                                    border.color: window.llmFitExpanded ? window.cyan : window.border
                                }
                            }
                            Item { Layout.fillWidth: true }
                        }
                        Panel {
                            visible: window.llmFitExpanded
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? 215 : 0
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 15
                                spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: "LLM Fit"; color: window.textPrimary; font.pixelSize: 15; font.bold: true }
                                    StatusChip { chipText: "IN-APP"; tone: window.cyan }
                                    Item { Layout.fillWidth: true }
                                    Label { text: "nincs terminálindítás"; color: window.textMuted; font.pixelSize: 9 }
                                }
                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 4
                                    columnSpacing: 18
                                    rowSpacing: 8
                                    Label { text: "CPU"; color: window.textMuted; font.pixelSize: 9 }
                                    Label { text: fa3Repository.cpuThreads + " szál"; color: window.textPrimary; font.pixelSize: 11; font.bold: true }
                                    Label { text: "RAM"; color: window.textMuted; font.pixelSize: 9 }
                                    Label { text: fa3Repository.memoryGiB.toFixed(1) + " GiB"; color: window.textPrimary; font.pixelSize: 11; font.bold: true }
                                    Label { text: "GPU / NPU"; color: window.textMuted; font.pixelSize: 9 }
                                    Label { text: "adapter-gated"; color: window.orange; font.pixelSize: 10; font.bold: true }
                                    Label { text: "Model-fit"; color: window.textMuted; font.pixelSize: 9 }
                                    Label { text: "modell + runtime adapter szükséges"; color: window.orange; font.pixelSize: 10; font.bold: true }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    text: "Az LLM Fit az FA3 GUI részeként jelenik meg. A hostból közvetlenül ismert értékeket mutatja; kompatibilitási vagy kapacitás-ajánlást csak tényleges adapter-evidence alapján jelenít meg, szintetikus eredmény nélkül."
                                    color: window.textMuted
                                    font.pixelSize: 10
                                }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(350, modelManagerView.availableHeight - 250)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 15
                                spacing: 10
                                Label { text: "Model registry projection"; color: window.textPrimary; font.pixelSize: 14; font.bold: true }
                                ListView {
                                    id: modelRegistryList
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    clip: true
                                    boundsBehavior: Flickable.StopAtBounds
                                    ScrollBar.vertical: ScrollBar {
                                        policy: ScrollBar.AlwaysOn
                                        active: true
                                    }
                                    model: fa3Repository.recordsByCategory("provider")
                                    delegate: ItemDelegate {
                                        width: ListView.view.width
                                        height: 46
                                        background: Rectangle { color: hovered ? window.panelRaised : "transparent"; radius: 5 }
                                        contentItem: RowLayout {
                                            Label { text: modelData.id; color: window.textPrimary; font.family: "monospace"; Layout.preferredWidth: 330; elide: Text.ElideRight }
                                            Label { text: modelData.title; color: window.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                                            StatusChip { chipText: modelData.status || "REGISTERED"; tone: window.green }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    id: searchView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: searchView.availableWidth
                        spacing: 13
                        SectionTitle { title: "Keresés"; subtitle: "Projekt, beszélgetés, FA3-alkalmazás, FA3-funkció, beállítás és canonical rekord egy helyen" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            ComboBox {
                                id: searchScope
                                Layout.preferredWidth: 230
                                textRole: "label"
                                valueRole: "value"
                                model: [
                                    {label: "Minden", value: "ALL"},
                                    {label: "Projektek", value: "PROJECT"},
                                    {label: "Beszélgetések", value: "CONVERSATION"},
                                    {label: "FA3 alkalmazások", value: "APPLICATION"},
                                    {label: "FA3 funkciók", value: "FUNCTION"},
                                    {label: "Beállítások", value: "SETTING"},
                                    {label: "Real-Time Data", value: "RTD"},
                                    {label: "Canonical rekordok", value: "CANONICAL"}
                                ]
                            }
                            TextField { id: globalSearch; Layout.fillWidth: true; placeholderText: "Mit keresel?" }
                        }
                        Label {
                            text: window.unifiedSearchResults(globalSearch.text, searchScope.currentValue).length + " találat · " + searchScope.currentText
                            color: window.textMuted
                            font.pixelSize: 9
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(430, searchView.availableHeight - 155)
                            ListView {
                                id: unifiedSearchList
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                                model: window.unifiedSearchResults(globalSearch.text, searchScope.currentValue)
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 62
                                    background: Rectangle { color: hovered ? window.panelRaised : "transparent"; radius: 5 }
                                    onDoubleClicked: {
                                        if (modelData.pageIndex !== undefined && modelData.pageIndex >= 0)
                                            window.selectedIndex = modelData.pageIndex
                                        else if (modelData.sourceType === "CANONICAL" && modelData.path)
                                            fa3Repository.openLocalPath(modelData.path)
                                    }
                                    contentItem: RowLayout {
                                        StatusChip { chipText: modelData.category || modelData.sourceType || "RESULT"; tone: modelData.sourceType === "SETTING" ? window.orange : window.accent }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1
                                            Label { text: modelData.title || modelData.id; color: window.textPrimary; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            Label { text: modelData.subtitle || modelData.id || ""; color: window.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                        Label { text: modelData.status || ""; color: (modelData.status || "").indexOf("PENDING") >= 0 ? window.orange : window.textMuted; font.pixelSize: 9; Layout.preferredWidth: 150; elide: Text.ElideRight }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    id: architectureView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: architectureView.availableWidth
                        spacing: 13
                        SectionTitle { title: "Architecture"; subtitle: "Az FA3 canonical szerkezetének külön nézete: core, execution fabric, gates, runtime és evidence" }
                        RowLayout {
                            Layout.fillWidth: true
                            ModuleCard { Layout.fillWidth: true; title: "Canonical Core"; subtitle: fa3Repository.profileCount + " profile · " + fa3Repository.recordsByCategory("contract").length + " contract · " + fa3Repository.decisionCount + " decision"; badge: "CORE"; tone: window.accent }
                            ModuleCard { Layout.fillWidth: true; title: "Execution Fabric"; subtitle: fa3Repository.providerCount + " provider · " + fa3Repository.recordsByCategory("gate").length + " gate · " + fa3Repository.recordsByCategory("runtime").length + " runtime"; badge: "FABRIC"; tone: window.cyan }
                            ModuleCard { Layout.fillWidth: true; title: "Evidence & Release"; subtitle: fa3Repository.evidenceCount + " evidence · " + fa3Repository.pendingCount + " pending canonical item"; badge: "EVIDENCE"; tone: fa3Repository.pendingCount > 0 ? window.orange : window.green }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            ComboBox {
                                id: architectureScope
                                Layout.preferredWidth: 210
                                textRole: "label"
                                valueRole: "value"
                                model: [
                                    {label: "Teljes architektúra", value: "ALL"},
                                    {label: "Profiles", value: "PROFILE"},
                                    {label: "Contracts", value: "CONTRACT"},
                                    {label: "Providers", value: "PROVIDER"},
                                    {label: "Decisions", value: "DECISION"},
                                    {label: "Gates", value: "GATE"},
                                    {label: "Runtime conformance", value: "RUNTIME"}
                                ]
                            }
                            TextField { id: architectureSearch; Layout.fillWidth: true; placeholderText: "Architektúra rekord szűrése…" }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(390, architectureView.availableHeight - 300)
                            ListView {
                                id: architectureList
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                                model: window.architectureResults(architectureSearch.text, architectureScope.currentValue)
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 58
                                    background: Rectangle { color: hovered ? window.panelRaised : "transparent"; radius: 5 }
                                    onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                                    contentItem: RowLayout {
                                        StatusChip { chipText: modelData.category.toUpperCase(); tone: modelData.category === "gate" ? window.orange : window.accent }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1
                                            Label { text: modelData.id; color: window.textPrimary; font.family: "monospace"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            Label { text: modelData.title; color: window.textMuted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                        Label { text: modelData.status; color: modelData.status.indexOf("PENDING") >= 0 ? window.orange : window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 170 }
                                    }
                                }
                            }
                        }
                    }
                }

                ScrollView {
                    id: resourcesView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: resourcesView.availableWidth
                        spacing: 14
                        SectionTitle { title: "Resources"; subtitle: "Host Resource Broker projection and ChangeSet-based operator intent" }
                        RowLayout {
                            Layout.fillWidth: true
                            ModuleCard { Layout.fillWidth: true; title: "Host"; subtitle: fa3Repository.hostName; badge: "LOCAL"; tone: window.green }
                            ModuleCard { Layout.fillWidth: true; title: "CPU"; subtitle: fa3Repository.cpuThreads + " hardware threads"; badge: "DISCOVERED"; tone: window.cyan }
                            ModuleCard { Layout.fillWidth: true; title: "Memory"; subtitle: fa3Repository.memoryGiB.toFixed(1) + " GiB physical memory"; badge: "DISCOVERED"; tone: window.accent }
                            ModuleCard { Layout.fillWidth: true; title: "Accelerators"; subtitle: "GPU/NPU execution remains HRB-admitted"; badge: "GATED"; tone: window.magenta }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 225
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 10
                                Label { text: "Host Resource Governance"; color: window.textPrimary; font.pixelSize: 15; font.bold: true }
                                Label {
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                    color: window.textMuted
                                    font.pixelSize: 10
                                    text: "CPU/GPU/NPU/NUMA/memory placement changes are not executed directly from this GUI. Operator intent becomes a typed ChangeSet and follows the existing broker and approval chain."
                                }
                                Button { text: "Create ChangeSet draft"; onClicked: changeSetDialog.open() }
                                Label { id: draftResult; color: window.accent; Layout.fillWidth: true; elide: Text.ElideMiddle; font.pixelSize: 10 }
                            }
                        }
                    }
                }

                ModulePage {
                    pageTitle: "Security & Approvals"
                    pageSubtitle: "Policy state, approvals and security evidence projections"
                    cards: [
                        {title: "Policies", subtitle: "Effective policy state and decision outcomes.", badge: "READ", tone: window.green},
                        {title: "Approvals", subtitle: "Pending ChangeSet and execution approvals.", badge: "GATED", tone: window.orange},
                        {title: "Secrets", subtitle: "Metadata projection only; no secret values.", badge: "NO VALUES", tone: window.magenta},
                        {title: "Journal Retention", subtitle: "Archive retirement and purge policy remain separated.", badge: "FAIL-CLOSED", tone: window.accent}
                    ]
                }

                ModulePage {
                    pageTitle: "Observability"
                    pageSubtitle: "Metrics, traces, provenance and operating-state projections"
                    cards: [
                        {title: "Metrics", subtitle: "Resource and service telemetry projection.", badge: "READ", tone: window.cyan},
                        {title: "Traces", subtitle: "Workflow/tool/model execution trace projection.", badge: "READ", tone: window.accent},
                        {title: "Provenance", subtitle: "Artifact and execution provenance chain.", badge: "READ", tone: window.green},
                        {title: "Journal ingestion", subtitle: "Runtime events projected into the unified journal.", badge: "APPEND", tone: window.magenta}
                    ]
                }

                JournalPage {
                    surface1: window.panel
                    surface2: window.panelRaised
                    accent: window.accent
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                }

                ScrollView {
                    id: evidenceView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: evidenceView.availableWidth
                        spacing: 14
                        SectionTitle { title: "Evidence"; subtitle: "Conformance, receipts and promotion evidence" }
                        RowLayout {
                            Layout.fillWidth: true
                            ModuleCard { Layout.fillWidth: true; title: "Evidence Records"; subtitle: fa3Repository.evidenceCount + " repository records"; badge: "INDEXED"; tone: window.green }
                            ModuleCard { Layout.fillWidth: true; title: "Pending Canonical"; subtitle: "Items requiring fresh conformance evidence"; badge: fa3Repository.pendingCount.toString(); tone: fa3Repository.pendingCount > 0 ? window.orange : window.green }
                        }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 190
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 16
                                spacing: 8
                                Label { text: "Evidence authority boundary"; color: window.textPrimary; font.pixelSize: 15; font.bold: true }
                                Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: window.textMuted; font.pixelSize: 10; text: "The GUI can display evidence but cannot self-promote a runtime, fabricate PASS state or override the Unified Observability/Evidence authority." }
                            }
                        }
                    }
                }

                IntegrationsPage {
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
                    onOpenMcpControlRequested: function(targetId) { window.openMcpChat(targetId) }
                    onOpenMcpGatewayRequested: function() { window.closeTransientWorkspaces(); window.selectedIndex = 27 }
                }

                SystemSettingsPage {
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
                    compactNavigation: window.compactNavigation
                    statusStripVisible: window.statusStripVisible
                    onCompactNavigationRequested: function(enabled) { window.compactNavigation = enabled; fa3Preferences.setValue("appearance/compactNavigation", enabled) }
                    onStatusStripRequested: function(enabled) { window.statusStripVisible = enabled; fa3Preferences.setValue("appearance/statusStripVisible", enabled) }
                    onNavigateRequested: function(pageIndex) { window.selectedIndex = pageIndex }
                }

                ScrollView {
                    id: systemView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: systemView.availableWidth
                        spacing: 14
                        SectionTitle { title: "System"; subtitle: "GUI runtime, repository and platform information" }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 360
                            GridLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                columns: 2
                                columnSpacing: 24
                                rowSpacing: 13
                                Label { text: "Application"; color: window.textMuted }
                                Label { text: "FA3 Control Center 0.3.x"; color: window.textPrimary }
                                Label { text: "Toolkit"; color: window.textMuted }
                                Label { text: "Qt 6 / QML / Basic controls"; color: window.textPrimary }
                                Label { text: "Repository"; color: window.textMuted }
                                Label { text: fa3Repository.repoRoot; color: window.textPrimary; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                Label { text: "Journal storage"; color: window.textMuted }
                                Label { text: fa3Journal.storageRoot; color: window.textPrimary; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                Label { text: "Host"; color: window.textMuted }
                                Label { text: fa3Repository.hostName; color: window.textPrimary }
                                Label { text: "Kernel"; color: window.textMuted }
                                Label { text: fa3Repository.kernelVersion; color: window.textPrimary }
                                Label { text: "Mutation policy"; color: window.textMuted }
                                Label { text: "Privileged changes: Draft ChangeSet only"; color: window.textPrimary }
                                Label { text: "Display target"; color: window.textMuted }
                                Label { text: "KDE Plasma / Wayland"; color: window.textPrimary }
                            }
                        }
                    }
                }

                RtdProvidersPage {
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

                WebWorkspace {
                    webUrl: window.webWorkspaceUrl
                    titleText: window.webWorkspaceTitle
                    surface: window.panel
                    surfaceRaised: window.panelRaised
                    borderTone: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    onCloseRequested: window.webWorkspaceOpen = false
                }

                ChatWorkspace {
                    role: window.askRole
                    workspaceMode: window.chatWorkspaceMode
                    requestedMcpTarget: window.mcpChatTarget
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                    onModeChangeRequested: function(mode) { window.chatWorkspaceMode = mode }
                    onCloseRequested: window.chatWorkspaceOpen = false
                    onNavigateRequested: function(pageIndex) {
                        window.chatWorkspaceOpen = false
                        window.webWorkspaceOpen = false
                        window.selectedIndex = pageIndex
                    }
                }

                CheckpointManagerPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                ExternalProvidersSetupPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                TokenControlCenterPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                LanguageControlPage {
                    preferences: fa3Preferences
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                }

                WorkManagementPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                AcceleratorGuardPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                Fa3OsPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                    onNavigateRequested: function(pageIndex) { window.selectedIndex = pageIndex }
                }

                McpGatewayPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                KnowledgePage {
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

                TrustCertificatesPage {
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

                SessionVaultPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                DecisionFabricPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                DecisionInspectorPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }

                ProjectRadarPage {
                    panel: window.panel
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                }

                ContextInspectorPage {
                    panel: window.panel
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                    orange: window.orange
                    magenta: window.magenta
                }
                SubtitleStudioPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.accent
                    green: window.green
                }

                NarrationStudioPage {
                    panel: window.panel
                    panelRaised: window.panelRaised
                    border: window.border
                    textPrimary: window.textPrimary
                    textMuted: window.textMuted
                    accent: window.magenta
                    green: window.green
                    orange: window.orange
                }

            }

            Rectangle {
                visible: window.statusStripVisible
                Layout.fillWidth: true
                Layout.preferredHeight: visible ? 34 : 0
                color: "#06101c"
                border.color: window.borderSoft
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 18
                    StatusItem { labelText: "CPU"; valueText: "N/A · " + fa3Repository.cpuThreads + " thr"; tone: window.orange }
                    StatusItem { labelText: "GPU"; valueText: "N/A"; tone: window.orange }
                    StatusItem { labelText: "NPU"; valueText: "N/A"; tone: window.orange }
                    StatusItem { labelText: "RAM"; valueText: "N/A · " + fa3Repository.memoryGiB.toFixed(1) + " GiB total"; tone: window.orange }
                    StatusItem { labelText: "PRESSURE"; valueText: "N/A"; tone: window.orange }
                    Item { Layout.fillWidth: true }
                    Label { text: "TELEMETRY ADAPTER GATED"; color: window.textMuted; font.pixelSize: 8; font.bold: true }
                }
            }
        }
    }

    Dialog {
        id: changeSetDialog
        title: "Typed ChangeSet draft"
        modal: true
        anchors.centerIn: parent
        width: 560
        standardButtons: Dialog.Save | Dialog.Cancel
        ColumnLayout {
            width: parent.width
            spacing: 10
            TextField { id: csScope; Layout.fillWidth: true; placeholderText: "Scope (e.g. HOST_RESOURCE_GOVERNANCE)" }
            TextField { id: csAction; Layout.fillWidth: true; placeholderText: "Action (e.g. propose.memory.hugepages)" }
            TextField { id: csTarget; Layout.fillWidth: true; placeholderText: "Target canonical ID or host resource" }
            TextArea { id: csRationale; Layout.fillWidth: true; Layout.preferredHeight: 120; placeholderText: "Rationale"; wrapMode: TextEdit.Wrap }
            Label { Layout.fillWidth: true; color: window.textMuted; wrapMode: Text.WordWrap; font.pixelSize: 10; text: "Save creates a local DRAFT_NOT_SUBMITTED JSON only. It executes no command and performs no canonical write." }
        }
        onAccepted: {
            draftResult.text = fa3Repository.createDraftChangeSet(csScope.text, csAction.text, csTarget.text, csRationale.text)
            csScope.clear(); csAction.clear(); csTarget.clear(); csRationale.clear()
        }
    }
}