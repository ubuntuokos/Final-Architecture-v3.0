import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: window

    width: Math.round(1580 * fa3Settings.uiScale)
    height: Math.round(980 * fa3Settings.uiScale)
    minimumWidth: 1120
    minimumHeight: 700
    visible: true
    title: "Final Architecture 3.0 — Control Center"

    SystemPalette { id: systemPalette }

    property real uiScale: fa3Settings.uiScale
    property real fontScale: fa3Settings.baseFontSize / 13.0
    property bool forcedDark: fa3Settings.themeMode === "dark"
    property bool forcedLight: fa3Settings.themeMode === "light"
    property color surface0: forcedDark ? "#17191d" : forcedLight ? "#f3f5f7" : systemPalette.window
    property color surface1: forcedDark ? "#202329" : forcedLight ? "#ffffff" : systemPalette.base
    property color surface2: forcedDark ? "#2a2e35" : forcedLight ? "#e9edf2" : systemPalette.alternateBase
    property color textPrimary: forcedDark ? "#f2f4f7" : forcedLight ? "#1b1e23" : systemPalette.windowText
    property color textMuted: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.62)
    property color accent: systemPalette.highlight
    property int selectedIndex: 0
    property int shortcutRevision: 0
    property var navigationHistory: []
    property bool sidebarCollapsed: fa3Settings.value("appearance/sidebarCollapsed", false)
    property string draftResultText: ""

    color: surface0
    palette.window: surface0
    palette.base: surface1
    palette.alternateBase: surface2
    palette.windowText: textPrimary
    palette.text: textPrimary
    palette.button: surface2
    palette.buttonText: textPrimary
    palette.highlight: accent
    palette.highlightedText: systemPalette.highlightedText

    function t(hu, en) { return fa3Settings.language === "en" ? en : hu }
    function px(value) { return Math.max(9, Math.round(value * fontScale)) }
    function shortcut(key, fallback) { const revision = window.shortcutRevision; return fa3Settings.value(key, fallback) }

    function indexForKey(key) {
        for (let i = 0; i < navigationModel.length; ++i) {
            if (navigationModel[i].key === key)
                return i
        }
        return -1
    }

    function navigateTo(index, remember) {
        const keepHistory = remember === undefined ? true : remember
        if (index < 0 || index >= navigationModel.length || index === selectedIndex)
            return
        if (keepHistory)
            navigationHistory = navigationHistory.concat([selectedIndex])
        selectedIndex = index
    }

    function navigateKey(key, remember) { navigateTo(indexForKey(key), remember) }

    function goBack() {
        if (navigationHistory.length === 0)
            return
        const target = navigationHistory[navigationHistory.length - 1]
        navigationHistory = navigationHistory.slice(0, navigationHistory.length - 1)
        selectedIndex = target
    }

    function toggleSidebar() {
        sidebarCollapsed = !sidebarCollapsed
        fa3Settings.setValue("appearance/sidebarCollapsed", sidebarCollapsed)
    }

    function navLabel(key) {
        const labels = {
            command: ["Command Center", "Command Center"],
            projects: ["Projektek", "Projects"],
            studio: ["AI Studio", "AI Studio"],
            aiApps: ["AI alkalmazások", "AI Applications"],
            agents: ["Agentek & Workflow-k", "Agents & Workflows"],
            modelManager: ["Model Manager", "Model Manager"],
            architecture: ["Architektúra", "Architecture"],
            resources: ["Erőforrások", "Resources"],
            security: ["Biztonság & Jóváhagyás", "Security & Approvals"],
            observability: ["Observability", "Observability"],
            evidence: ["Evidence", "Evidence"],
            integrations: ["Integrációk", "Integrations"],
            system: ["Rendszer", "System"],
            settings: ["Beállítások", "Settings"]
        }
        return fa3Settings.language === "en" ? labels[key][1] : labels[key][0]
    }

    property var navigationModel: [
        { key: "command", iconText: "⌂" },
        { key: "projects", iconText: "▣" },
        { key: "studio", iconText: "✦" },
        { key: "aiApps", iconText: "◎" },
        { key: "agents", iconText: "⌘" },
        { key: "modelManager", iconText: "◫" },
        { key: "architecture", iconText: "◇" },
        { key: "resources", iconText: "▤" },
        { key: "security", iconText: "◆" },
        { key: "observability", iconText: "⌁" },
        { key: "evidence", iconText: "✓" },
        { key: "integrations", iconText: "↔" },
        { key: "system", iconText: "⚙" },
        { key: "settings", iconText: "☰" }
    ]

    Connections {
        target: fa3Settings
        function onSettingChanged(key) {
            if (key.indexOf("shortcuts/") === 0)
                window.shortcutRevision += 1
        }
        function onSettingsReset() { window.shortcutRevision += 1 }
    }

    Shortcut { sequence: window.shortcut("shortcuts/commandCenter", "Ctrl+1"); onActivated: window.navigateKey("command") }
    Shortcut { sequence: window.shortcut("shortcuts/projects", "Ctrl+2"); onActivated: window.navigateKey("projects") }
    Shortcut { sequence: window.shortcut("shortcuts/studio", "Ctrl+3"); onActivated: window.navigateKey("studio") }
    Shortcut {
        sequence: window.shortcut("shortcuts/mentor", "Ctrl+4")
        enabled: fa3Settings.value("roleButtons/mentorVisible", true) && fa3Settings.value("mentor/enabled", true)
        onActivated: mentorDialog.open()
    }
    Shortcut {
        sequence: window.shortcut("shortcuts/coach", "Ctrl+5")
        enabled: fa3Settings.value("roleButtons/coachVisible", true) && fa3Settings.value("coach/enabled", true)
        onActivated: coachDialog.open()
    }
    Shortcut {
        sequence: window.shortcut("shortcuts/manager", "Ctrl+6")
        enabled: fa3Settings.value("roleButtons/managerVisible", true)
        onActivated: managerDialog.open()
    }
    Shortcut { sequence: window.shortcut("shortcuts/modelManager", "Ctrl+7"); onActivated: window.navigateKey("modelManager") }
    Shortcut { sequence: window.shortcut("shortcuts/system", "Ctrl+8"); onActivated: window.navigateKey("system") }
    Shortcut {
        sequence: window.shortcut("shortcuts/inspector", "Ctrl+9")
        enabled: fa3Settings.value("roleButtons/inspectorVisible", true)
        onActivated: inspectorDialog.open()
    }
    Shortcut {
        sequence: window.shortcut("shortcuts/ideator", "Ctrl+Alt+I")
        enabled: fa3Settings.value("roleButtons/ideatorVisible", true)
        onActivated: ideatorDialog.open()
    }
    Shortcut {
        sequence: window.shortcut("shortcuts/advisor", "Ctrl+Alt+A")
        enabled: fa3Settings.value("roleButtons/advisorVisible", true)
        onActivated: advisorDialog.open()
    }
    Shortcut { sequence: window.shortcut("shortcuts/settings", "Ctrl+,"); onActivated: window.navigateKey("settings") }
    Shortcut { sequence: window.shortcut("shortcuts/assistant", "Ctrl+Space"); onActivated: assistantDrawer.open() }
    Shortcut { sequence: window.shortcut("shortcuts/refresh", "Ctrl+R"); onActivated: fa3Repository.refresh() }

    component Panel: Rectangle {
        radius: Math.round(12 * window.uiScale)
        color: window.surface1
        border.color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.10)
    }

    component SectionTitle: Column {
        property string title: ""
        property string subtitle: ""
        spacing: 4
        Label { text: parent.title; font.pixelSize: window.px(24); font.bold: true }
        Label { width: parent.width; text: parent.subtitle; color: window.textMuted; font.pixelSize: window.px(13); wrapMode: Text.WordWrap }
    }

    component MetricCard: Panel {
        id: metricCard
        property string label: ""
        property string value: ""
        property string note: ""
        implicitWidth: Math.round(195 * window.uiScale)
        implicitHeight: Math.round(112 * window.uiScale)
        Column {
            anchors.fill: parent
            anchors.margins: Math.round(16 * window.uiScale)
            spacing: 6
            Label { text: metricCard.label; color: window.textMuted; font.pixelSize: window.px(12) }
            Label { text: metricCard.value; font.pixelSize: window.px(27); font.bold: true; width: parent.width; elide: Text.ElideRight }
            Label { text: metricCard.note; color: window.textMuted; font.pixelSize: window.px(11); width: parent.width; elide: Text.ElideRight }
        }
    }

    component ModuleCard: Panel {
        id: moduleCard
        property string title: ""
        property string subtitle: ""
        property string badge: "READY"
        implicitWidth: Math.round(255 * window.uiScale)
        implicitHeight: Math.round(124 * window.uiScale)
        Column {
            anchors.fill: parent
            anchors.margins: Math.round(16 * window.uiScale)
            spacing: 8
            RowLayout {
                width: parent.width
                Label { text: moduleCard.title; font.pixelSize: window.px(16); font.bold: true; Layout.fillWidth: true }
                Label { text: moduleCard.badge; color: window.accent; font.pixelSize: window.px(10); font.bold: true }
            }
            Label { text: moduleCard.subtitle; color: window.textMuted; wrapMode: Text.WordWrap; width: parent.width; font.pixelSize: window.px(12) }
        }
    }

    component BasicPage: ScrollView {
        id: basicPage
        property string pageTitle: ""
        property string pageSubtitle: ""
        property var cards: []
        contentWidth: availableWidth
        ColumnLayout {
            width: basicPage.availableWidth
            spacing: 18
            Item { Layout.preferredHeight: 20 }
            SectionTitle { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: basicPage.pageTitle; subtitle: basicPage.pageSubtitle }
            Flow {
                Layout.fillWidth: true
                Layout.leftMargin: 24
                Layout.rightMargin: 24
                spacing: 12
                Repeater {
                    model: basicPage.cards
                    delegate: ModuleCard {
                        required property var modelData
                        title: modelData.title
                        subtitle: modelData.subtitle
                        badge: modelData.badge || "READY"
                    }
                }
            }
            Item { Layout.preferredHeight: 24 }
        }
    }

    component RoleChatDialog: Dialog {
        id: roleDialog
        property string roleKey: ""
        property string roleTitle: ""
        property string roleDescription: ""
        property string settingsSectionKey: ""
        property string transcript: ""

        title: window.t("Párbeszéd — ", "Conversation — ") + roleTitle
        modal: true
        anchors.centerIn: parent
        width: Math.min(window.width * 0.68, Math.round(880 * window.uiScale))
        height: Math.min(window.height * 0.78, Math.round(700 * window.uiScale))
        closePolicy: Popup.CloseOnEscape

        contentItem: ColumnLayout {
            spacing: 12
            Label { Layout.fillWidth: true; text: roleDialog.roleDescription; color: window.textMuted; wrapMode: Text.WordWrap }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Math.round(10 * window.uiScale)
                color: window.surface1
                border.color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.10)
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 10
                    TextArea {
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        text: roleDialog.transcript.length > 0 ? roleDialog.transcript : window.t("Nincs még üzenet ebben a helyi párbeszédben.", "No messages in this local conversation yet.")
                        color: window.textPrimary
                    }
                }
            }
            Label {
                Layout.fillWidth: true
                text: window.t("Ez a párbeszéd külön van a beállításoktól. A runtime adapter csak meglévő FA3 authority-kon keresztül működhet; a GUI nem talál ki AI-választ és nem futtat közvetlen toolt.", "This conversation is separate from settings. The runtime adapter may operate only through existing FA3 authorities; the GUI does not fabricate AI responses or execute tools directly.")
                color: "#d99b32"
                wrapMode: Text.WordWrap
                font.pixelSize: window.px(11)
            }
            TextArea {
                id: rolePrompt
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(105 * window.uiScale)
                placeholderText: window.t("Írd be a kérdésed…", "Type your question…")
                wrapMode: TextEdit.Wrap
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: window.t("Küldés", "Send")
                    enabled: rolePrompt.text.trim().length > 0
                    onClicked: {
                        const question = rolePrompt.text.trim()
                        const prefix = roleDialog.transcript.length > 0 ? "\n\n" : ""
                        roleDialog.transcript += prefix + window.t("Te: ", "You: ") + question + "\n\n" + roleDialog.roleTitle + ": " + window.t("A kérdés rögzítve. A production runtime válaszadapter státusza külön evidence-t igényel.", "Question recorded. Production runtime response adapter status requires separate evidence.")
                        rolePrompt.clear()
                    }
                }
                Button {
                    text: window.t("Feladat-draft", "Task draft")
                    visible: roleDialog.roleKey === "manager"
                    enabled: rolePrompt.text.trim().length > 0
                    onClicked: {
                        window.draftResultText = fa3Repository.createDraftChangeSet("manager", "MANAGER_CONVERSATION_TASK_PROPOSAL", "FA3-MANAGER-001", rolePrompt.text.trim())
                        rolePrompt.clear()
                    }
                }
                Item { Layout.fillWidth: true }
                Button {
                    text: window.t("Beállítások", "Settings")
                    onClicked: {
                        roleDialog.close()
                        window.navigateKey("settings")
                        settingsPage.openSection(roleDialog.settingsSectionKey)
                    }
                }
                Button { text: window.t("Bezárás", "Close"); onClicked: roleDialog.close() }
            }
        }
    }

    header: ToolBar {
        height: Math.round(64 * window.uiScale)
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8
            ToolButton {
                text: "☰"
                ToolTip.visible: hovered
                ToolTip.text: window.sidebarCollapsed ? window.t("Főmenü megjelenítése", "Show main menu") : window.t("Főmenü elrejtése", "Hide main menu")
                onClicked: window.toggleSidebar()
            }
            ToolButton { text: "←"; enabled: window.navigationHistory.length > 0; ToolTip.visible: hovered; ToolTip.text: window.t("Vissza", "Back"); onClicked: window.goBack() }
            Label { text: "FA3"; font.pixelSize: window.px(21); font.bold: true }
            Rectangle { width: 1; height: 28; color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.16) }
            Label { text: "Final Architecture 3.0"; font.pixelSize: window.px(15); font.bold: true }
            Item { Layout.fillWidth: true }

            Button { visible: fa3Settings.value("roleButtons/mentorVisible", true); text: window.t("Kérdezd a Mentort", "Ask Mentor"); enabled: fa3Settings.value("mentor/enabled", true); onClicked: mentorDialog.open() }
            Button { visible: fa3Settings.value("roleButtons/coachVisible", true); text: window.t("Kérdezd a Coachot", "Ask Coach"); enabled: fa3Settings.value("coach/enabled", true); onClicked: coachDialog.open() }
            Button { visible: fa3Settings.value("roleButtons/managerVisible", true); text: window.t("Kérdezd a Managert", "Ask Manager"); onClicked: managerDialog.open() }
            Button { visible: fa3Settings.value("roleButtons/inspectorVisible", true); text: window.t("Kérdezd az Ellenőrt", "Ask Inspector"); onClicked: inspectorDialog.open() }
            Button { visible: fa3Settings.value("roleButtons/ideatorVisible", true); text: window.t("Kérdezd az Ötletelőt", "Ask Ideator"); onClicked: ideatorDialog.open() }
            Button { visible: fa3Settings.value("roleButtons/advisorVisible", true); text: window.t("Kérdezd a Tanácsadót", "Ask Advisor"); onClicked: advisorDialog.open() }
            Button { text: window.t("Asszisztens", "Assistant"); onClicked: assistantDrawer.open() }
            Label { text: "143 capabilities"; color: window.textMuted; font.pixelSize: window.px(11) }
            ToolButton { text: "↻"; ToolTip.visible: hovered; ToolTip.text: window.t("Canonical és host állapot frissítése", "Refresh canonical and host state"); onClicked: fa3Repository.refresh() }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: window.sidebarCollapsed ? Math.round(58 * window.uiScale) : Math.round(260 * window.uiScale)
            Layout.fillHeight: true
            color: window.surface1
            border.color: Qt.rgba(window.textPrimary.r, window.textPrimary.g, window.textPrimary.b, 0.08)
            Behavior on Layout.preferredWidth { NumberAnimation { duration: 140 } }
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: window.sidebarCollapsed ? 6 : 10
                spacing: 8
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: window.navigationModel
                    currentIndex: window.selectedIndex
                    delegate: ItemDelegate {
                        required property int index
                        required property var modelData
                        width: ListView.view.width
                        height: Math.round(44 * window.uiScale)
                        highlighted: index === window.selectedIndex
                        onClicked: window.navigateTo(index)
                        ToolTip.visible: hovered && window.sidebarCollapsed
                        ToolTip.text: window.navLabel(modelData.key)
                        contentItem: Row {
                            spacing: 12
                            Label { text: modelData.iconText; width: window.sidebarCollapsed ? parent.width : 24; horizontalAlignment: Text.AlignHCenter; font.pixelSize: window.px(12) }
                            Label { visible: !window.sidebarCollapsed; text: window.navLabel(modelData.key); font.pixelSize: window.px(12) }
                        }
                    }
                }
                Panel {
                    visible: !window.sidebarCollapsed
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.round(116 * window.uiScale)
                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 5
                        Label { text: "Repository"; font.bold: true; font.pixelSize: window.px(11) }
                        Label { width: parent.width; text: fa3Repository.repoRoot; color: window.textMuted; elide: Text.ElideMiddle; font.pixelSize: window.px(9) }
                        Label { text: window.t("Frissítve: ", "Updated: ") + fa3Repository.lastRefresh; color: window.textMuted; font.pixelSize: window.px(9) }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.selectedIndex

            ScrollView {
                id: commandPage
                contentWidth: availableWidth
                ColumnLayout {
                    width: commandPage.availableWidth
                    spacing: 18
                    Item { Layout.preferredHeight: 20 }
                    SectionTitle { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Command Center"; subtitle: window.t("FA3 rendszerállapot, canonical integritás és operátori fókusz", "FA3 state, canonical integrity and operator focus") }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        MetricCard { label: window.t("Canonical rekord", "Canonical records"); value: fa3Repository.canonicalRecordCount.toString(); note: "read-only projection" }
                        MetricCard { label: "Provider"; value: fa3Repository.providerCount.toString(); note: "registered providers" }
                        MetricCard { label: "Evidence"; value: fa3Repository.evidenceCount.toString(); note: "evidence records" }
                        MetricCard { label: "Pending"; value: fa3Repository.pendingCount.toString(); note: "requires attention" }
                        MetricCard { label: "GPU"; value: fa3Repository.gpuDevices.length.toString(); note: "host discovery" }
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        ModuleCard { title: "AI Applications"; subtitle: window.t("Open WebUI, ComfyUI, InvokeAI és más web UI-k közvetlenül az FA3-ban", "Open WebUI, ComfyUI, InvokeAI and other web UIs directly inside FA3"); badge: "EMBEDDED" }
                        ModuleCard { title: window.t("AI szerepek", "AI roles"); subtitle: "Mentor / Coach / Manager / Inspector / Ideator / Advisor · Settings"; badge: "SETTINGS" }
                        ModuleCard { title: "Model Manager"; subtitle: window.t("Inventory, runtime, storage, security és evidence", "Inventory, runtime, storage, security and evidence"); badge: "P0" }
                        ModuleCard { title: window.t("Karbantartás", "Maintenance"); subtitle: "Temp/cache/runtime cleanup proposal flow"; badge: "GATED" }
                    }
                }
            }

            BasicPage {
                pageTitle: "Projects & Workspaces"
                pageSubtitle: window.t("Projektek, assetek és knowledge-context egy közös operátori nézetben", "Projects, assets and knowledge context in one operator view")
                cards: [
                    { title: "Active Workspace", subtitle: fa3Settings.value("paths/workspaces", "~/FA3-Workspaces"), badge: "LOCAL" },
                    { title: "Projects", subtitle: fa3Settings.value("paths/projects", "~/FA3-Projects"), badge: "PATH" },
                    { title: "Knowledge", subtitle: "Canonical RAG/read projection", badge: "READ" }
                ]
            }

            BasicPage {
                pageTitle: "AI Studio"
                pageSubtitle: window.t("A lokális kreatív pipeline egységes felülete", "Unified surface for the local creative pipeline")
                cards: [
                    { title: "Image", subtitle: "ComfyUI / InvokeAI / GIMP / Krita" },
                    { title: "Video", subtitle: "Generation / Kdenlive / OpenShot / editorial" },
                    { title: "Animation", subtitle: "Motion, character and timeline workflows" },
                    { title: "3D / VFX", subtitle: "Geometry / Blender / Bforartist / Natron / Gaffer" },
                    { title: "Audio", subtitle: "Ardour / Audacity / STT / TTS / restoration" },
                    { title: "Music", subtitle: "Generation, stems, DAW, mastering" },
                    { title: "Story / Screenplay", subtitle: "FA3 Story production context" }
                ]
            }

            EmbeddedAppsPage {
                settings: fa3Settings
                surface1: window.surface1
                surface2: window.surface2
                textPrimary: window.textPrimary
                textMuted: window.textMuted
                accent: window.accent
                uiScale: window.uiScale
                fontScale: window.fontScale
                language: fa3Settings.language
            }

            BasicPage {
                pageTitle: "Agents & Workflows"
                pageSubtitle: window.t("Agentek, durable workflow-k és gated tool execution", "Agents, durable workflows and gated tool execution")
                cards: [
                    { title: "Interactive Agents", subtitle: "Goose / desktop agent projection", badge: "ROUTED" },
                    { title: "Durable Workflows", subtitle: "Temporal authority projection", badge: "READ" },
                    { title: "Tool Execution", subtitle: "Central MCP mediation", badge: "GATED" }
                ]
            }

            ModelManagerPage {
                repository: fa3Repository
                surface1: window.surface1
                surface2: window.surface2
                textPrimary: window.textPrimary
                textMuted: window.textMuted
                accent: window.accent
                uiScale: window.uiScale
                fontScale: window.fontScale
                language: fa3Settings.language
            }

            BasicPage {
                pageTitle: "Architecture Explorer"
                pageSubtitle: window.t("Profiles, contracts, providers, decisions, gates és conformance rekordok", "Profiles, contracts, providers, decisions, gates and conformance records")
                cards: [
                    { title: "Canonical records", subtitle: fa3Repository.canonicalRecordCount.toString(), badge: "READ" },
                    { title: "Profiles", subtitle: fa3Repository.profileCount.toString(), badge: "READ" },
                    { title: "Decisions", subtitle: fa3Repository.decisionCount.toString(), badge: "READ" }
                ]
            }

            ScrollView {
                id: resourcesPage
                contentWidth: availableWidth
                ColumnLayout {
                    width: resourcesPage.availableWidth
                    spacing: 18
                    Item { Layout.preferredHeight: 20 }
                    SectionTitle { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Resources"; subtitle: window.t("FA3 workload utilization, placement és ChangeSet-alapú intent", "FA3 workload utilization, placement and ChangeSet-based intent") }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        MetricCard { label: "Host"; value: fa3Repository.hostName; note: "local host" }
                        MetricCard { label: "CPU threads"; value: fa3Repository.cpuThreads.toString(); note: "discovery" }
                        MetricCard { label: "Memory"; value: fa3Repository.memoryAvailableGiB.toFixed(1) + " GiB"; note: "available" }
                        MetricCard { label: "GPU"; value: fa3Repository.gpuDevices.length.toString(); note: "discovered" }
                    }
                    Button { Layout.leftMargin: 24; text: window.t("Új typed ChangeSet draft", "New typed ChangeSet draft"); onClicked: changeSetDialog.open() }
                    Label { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; color: window.accent; text: window.draftResultText; elide: Text.ElideMiddle }
                }
            }

            BasicPage {
                pageTitle: "Security & Approvals"
                pageSubtitle: window.t("Policy, approval és security evidence projection", "Policy, approval and security evidence projection")
                cards: [
                    { title: "Policies", subtitle: "Effective policy state", badge: "READ" },
                    { title: "Approvals", subtitle: "Pending ChangeSet and execution approvals", badge: "GATED" },
                    { title: "Secrets", subtitle: "Metadata/projection only; no secret values", badge: "NO VALUES" }
                ]
            }

            BasicPage {
                pageTitle: "Observability"
                pageSubtitle: window.t("Metrics, traces, provenance és rendszerállapot", "Metrics, traces, provenance and system state")
                cards: [
                    { title: "Metrics", subtitle: "Resource and service telemetry", badge: "READ" },
                    { title: "Traces", subtitle: "Workflow/tool/model execution trace", badge: "READ" },
                    { title: "Provenance", subtitle: "Artifact and execution provenance", badge: "READ" }
                ]
            }

            BasicPage {
                pageTitle: "Evidence"
                pageSubtitle: window.t("Conformance, receipts és promotion bizonyítékok", "Conformance, receipts and promotion evidence")
                cards: [
                    { title: "Evidence records", subtitle: fa3Repository.evidenceCount.toString(), badge: "READ" },
                    { title: "Pending", subtitle: fa3Repository.pendingCount.toString(), badge: "ATTENTION" },
                    { title: "Inspector", subtitle: "FA3-INSPECTOR-001 · independent verification & assurance", badge: "P0" },
                    { title: "Promotion boundary", subtitle: "GUI cannot self-declare PASS or promote runtime", badge: "GATED" }
                ]
            }

            BasicPage {
                pageTitle: "Integrations"
                pageSubtitle: window.t("Kreatív, irodai, knowledge és publikálási kapcsolatok", "Creative, office, knowledge and publishing connections")
                cards: [
                    { title: window.t("Grafika", "Graphics"), subtitle: "GIMP / Krita · default: " + fa3Settings.value("integrations/imageEditor", "Krita"), badge: "EDITORS" },
                    { title: "Video", subtitle: "Kdenlive / OpenShot · default: " + fa3Settings.value("integrations/videoEditor", "Kdenlive"), badge: "EDITORS" },
                    { title: "Audio", subtitle: "Ardour / Audacity · default: " + fa3Settings.value("integrations/audioEditor", "Ardour"), badge: "EDITORS" },
                    { title: "3D", subtitle: "Blender / Bforartist · default: " + fa3Settings.value("integrations/threeDEditor", "Bforartist"), badge: "DCC" },
                    { title: "LibreOffice", subtitle: window.t("Dokumentum / iroda", "Documents / office"), badge: fa3Settings.value("integrations/libreOfficeEnabled", true) ? "ON" : "OFF" },
                    { title: "Obsidian", subtitle: window.t("Knowledge / jegyzet workspace", "Knowledge / notes workspace"), badge: fa3Settings.value("integrations/obsidianEnabled", true) ? "ON" : "OFF" },
                    { title: window.t("Publikálás", "Publishing"), subtitle: "YouTube / Facebook / TikTok / Website", badge: "TARGETS" },
                    { title: "HDR", subtitle: window.t("Fenntartott pont — specifikáció következik", "Reserved — specification pending"), badge: "RESERVED" }
                ]
            }

            SystemPage {
                repository: fa3Repository
                settings: fa3Settings
                surface1: window.surface1
                surface2: window.surface2
                textPrimary: window.textPrimary
                textMuted: window.textMuted
                accent: window.accent
                uiScale: window.uiScale
                fontScale: window.fontScale
                language: fa3Settings.language
            }

            SettingsPage {
                id: settingsPage
                settings: fa3Settings
                repository: fa3Repository
                surface1: window.surface1
                surface2: window.surface2
                textPrimary: window.textPrimary
                textMuted: window.textMuted
                accent: window.accent
                uiScale: window.uiScale
                fontScale: window.fontScale
                language: fa3Settings.language
            }
        }
    }

    RoleChatDialog {
        id: mentorDialog
        roleKey: "mentor"
        roleTitle: "AI Mentor"
        roleDescription: window.t("Tanítás, magyarázat, Practice Lab és mastery fókusz.", "Teaching, explanation, Practice Lab and mastery focus.")
        settingsSectionKey: "mentor"
    }
    RoleChatDialog {
        id: coachDialog
        roleKey: "coach"
        roleTitle: "AI Coach"
        roleDescription: window.t("Célok, haladás, blockerek és következő lépések.", "Goals, progress, blockers and next actions.")
        settingsSectionKey: "coach"
    }
    RoleChatDialog {
        id: managerDialog
        roleKey: "manager"
        roleTitle: "Manager"
        roleDescription: window.t("Munka, delegálás, függőségek és evidence closure.", "Work, delegation, dependencies and evidence closure.")
        settingsSectionKey: "manager"
    }
    RoleChatDialog {
        id: inspectorDialog
        roleKey: "inspector"
        roleTitle: window.t("Ellenőr", "Inspector")
        roleDescription: window.t("Független verification & assurance: evidence, frissesség, reprodukálhatóság, drift és production PASS ellenőrzése.", "Independent verification & assurance: evidence, freshness, reproducibility, drift and production PASS inspection.")
        settingsSectionKey: "inspector"
    }
    RoleChatDialog {
        id: ideatorDialog
        roleKey: "ideator"
        roleTitle: window.t("Ötletelő", "Ideator")
        roleDescription: window.t("Divergens ötletelés, alternatívák, gap discovery, kombinációk és hipotézisek. Ötlet vagy hipotézis nem tény és nem evidence.", "Divergent ideation, alternatives, gap discovery, combinations and hypotheses. An idea or hypothesis is not a fact or evidence.")
        settingsSectionKey: "ideator"
    }
    RoleChatDialog {
        id: advisorDialog
        roleKey: "advisor"
        roleTitle: window.t("Tanácsadó", "Advisor")
        roleDescription: window.t("Evidence-alapú összehasonlítás, trade-off, kockázat, bizonytalanság és ajánlás. Az ajánlás nem döntés; high-impact/promotion állítás független Ellenőr-validációt igényel.", "Evidence-grounded comparison, trade-offs, risk, uncertainty and recommendation. A recommendation is not a decision; high-impact or promotion claims require independent Inspector validation.")
        settingsSectionKey: "advisor"
    }

    Drawer {
        id: assistantDrawer
        edge: Qt.RightEdge
        width: Math.min(window.width * 0.38, Math.round(560 * window.uiScale))
        height: window.height
        modal: false
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Label { text: "AI Assistant"; font.pixelSize: window.px(20); font.bold: true; Layout.fillWidth: true }
                ToolButton { text: "×"; onClicked: assistantDrawer.close() }
            }
            Label { Layout.fillWidth: true; text: window.t("Aktuális nézet: ", "Current view: ") + window.navLabel(window.navigationModel[window.selectedIndex].key); color: window.textMuted }
            Label { Layout.fillWidth: true; text: window.t("Az Assistant operátori context projection. Közvetlen tool/system végrehajtás nincs bekötve.", "Assistant is an operator-context projection. Direct tool/system execution is not wired."); wrapMode: Text.WordWrap; color: window.textMuted }
            TextArea { id: assistantPrompt; Layout.fillWidth: true; Layout.fillHeight: true; placeholderText: window.t("Kérdezz a jelenlegi nézetről vagy készíts feladatjavaslatot…", "Ask about the current view or draft a task proposal…"); wrapMode: TextEdit.Wrap }
            Label { Layout.fillWidth: true; text: window.draftResultText; color: window.accent; elide: Text.ElideMiddle }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: window.t("Feladat-draft", "Task draft")
                    enabled: assistantPrompt.text.trim().length > 0
                    onClicked: window.draftResultText = fa3Repository.createDraftChangeSet("assistant", "ASSISTANT_TASK_PROPOSAL", window.navLabel(window.navigationModel[window.selectedIndex].key), assistantPrompt.text)
                }
                Button { text: "MCP"; enabled: false; ToolTip.visible: hovered; ToolTip.text: window.t("Assistant MCP adapter még nincs runtime-promotálva", "Assistant MCP adapter is not runtime-promoted yet") }
                Item { Layout.fillWidth: true }
                Button { text: window.t("Törlés", "Clear"); onClicked: assistantPrompt.clear() }
            }
        }
    }

    Dialog {
        id: changeSetDialog
        title: "Typed ChangeSet draft"
        modal: true
        anchors.centerIn: parent
        width: 580
        standardButtons: Dialog.Save | Dialog.Cancel
        ColumnLayout {
            width: parent.width
            spacing: 10
            TextField { id: csScope; Layout.fillWidth: true; placeholderText: "Scope" }
            TextField { id: csAction; Layout.fillWidth: true; placeholderText: "Action" }
            TextField { id: csTarget; Layout.fillWidth: true; placeholderText: "Target" }
            TextArea { id: csRationale; Layout.fillWidth: true; Layout.preferredHeight: 120; placeholderText: window.t("Indoklás", "Rationale"); wrapMode: TextEdit.Wrap }
            Label { Layout.fillWidth: true; color: window.textMuted; wrapMode: Text.WordWrap; text: "Save → local DRAFT_NOT_SUBMITTED JSON only; no command execution or canonical mutation." }
        }
        onAccepted: {
            window.draftResultText = fa3Repository.createDraftChangeSet(csScope.text, csAction.text, csTarget.text, csRationale.text)
            csScope.clear(); csAction.clear(); csTarget.clear(); csRationale.clear()
        }
    }
}
