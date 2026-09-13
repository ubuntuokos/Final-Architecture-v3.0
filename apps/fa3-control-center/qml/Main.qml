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
    property url webWorkspaceUrl: "about:blank"
    property string webWorkspaceTitle: "Web Workspace"

    function openInternalWeb(targetUrl, titleText) {
        webWorkspaceUrl = targetUrl
        webWorkspaceTitle = titleText
        webWorkspaceOpen = true
    }

    property color canvas: "#07111f"
    property color sidebar: "#081421"
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color borderSoft: "#14283e"
    property color accent: "#25a7ff"
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"

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
        implicitHeight: 36
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
            onClicked: window.selectedIndex = parent.pageIndex
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

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 224
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
                        NavButton { iconText: "▣"; label: "Projects"; pageIndex: 2 }
                        NavButton { iconText: "⌘"; label: "Agents & Workflows"; pageIndex: 4 }
                        NavButton { iconText: "◫"; label: "Models & Providers"; pageIndex: 5 }
                        NavButton { iconText: "▦"; label: "Model Manager"; pageIndex: 6 }
                        NavButton { iconText: "⌕"; label: "Keresés"; pageIndex: 7 }
                        NavButton { iconText: "◇"; label: "Architecture"; pageIndex: 8 }
                        NavButton { iconText: "⚙"; label: "Rendszerbeállítások"; pageIndex: 15 }
                        NavButton { iconText: "ⓘ"; label: "System"; pageIndex: 16 }

                        Item { Layout.preferredHeight: 8 }
                        Label { text: "STUDIO"; color: "#50667e"; font.pixelSize: 8; font.bold: true; Layout.leftMargin: 10 }
                        NavButton { iconText: "✦"; label: "AI Studio"; pageIndex: 3 }

                        Item { Layout.preferredHeight: 8 }
                        Label { text: "MONITOR"; color: "#50667e"; font.pixelSize: 8; font.bold: true; Layout.leftMargin: 10 }
                        NavButton { iconText: "▤"; label: "Resources"; pageIndex: 9 }
                        NavButton { iconText: "◆"; label: "Security & Approvals"; pageIndex: 10 }
                        NavButton { iconText: "⌁"; label: "Observability"; pageIndex: 11 }
                        NavButton { iconText: "≡"; label: "Napló / Journal"; pageIndex: 12 }
                        NavButton { iconText: "✓"; label: "Evidence"; pageIndex: 13 }
                        NavButton { iconText: "↔"; label: "Integrations"; pageIndex: 14 }
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
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                color: "#081421"
                border.color: window.borderSoft
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 8

                    ColumnLayout {
                        spacing: 0
                        Label { text: "Current Environment"; color: window.textMuted; font.pixelSize: 8 }
                        RowLayout {
                            spacing: 7
                            Rectangle { width: 7; height: 7; radius: 4; color: window.green }
                            Label { text: "LOCAL / FA3"; color: window.textPrimary; font.pixelSize: 10; font.bold: true }
                        }
                    }

                    Rectangle { width: 1; height: 26; color: window.border }
                    QuickLink { linkText: "Hugging Face"; targetUrl: "https://huggingface.co/" }
                    QuickLink { linkText: "CivitAI"; targetUrl: "https://civitai.com/" }
                    QuickLink { linkText: "OpenModelDB"; targetUrl: "https://openmodeldb.info/" }

                    ToolButton {
                        id: askButton
                        text: "Kérdezd: " + window.askRole + " ▾"
                        onClicked: askMenu.open()
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
                            border.color: window.border
                        }
                        Menu {
                            id: askMenu
                            y: parent.height
                            MenuItem { text: "Mentor"; onTriggered: window.askRole = "Mentor" }
                            MenuItem { text: "Coach"; onTriggered: window.askRole = "Coach" }
                            MenuItem { text: "Manager"; onTriggered: window.askRole = "Manager" }
                            MenuItem { text: "Ellenőr"; onTriggered: window.askRole = "Ellenőr" }
                            MenuItem { text: "Ötletelő"; onTriggered: window.askRole = "Ötletelő" }
                            MenuItem { text: "Tanácsadó"; onTriggered: window.askRole = "Tanácsadó" }
                        }
                    }

                    Item { Layout.fillWidth: true }
                    Label { text: "CANONICAL"; color: window.accent; font.pixelSize: 9; font.bold: true }
                    Rectangle { width: 1; height: 25; color: window.border }
                    Label { text: fa3Repository.canonicalRecordCount + " records"; color: window.textMuted; font.pixelSize: 9 }
                    Rectangle {
                        width: 30; height: 30; radius: 6; color: "#0d1c2f"; border.color: window.border
                        Label { anchors.centerIn: parent; text: "↻"; color: window.textPrimary; font.pixelSize: 13 }
                        MouseArea { anchors.fill: parent; onClicked: { fa3Repository.refresh(); fa3Journal.refresh() } }
                    }
                }
            }

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: window.webWorkspaceOpen ? 17 : window.selectedIndex

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

                ModulePage {
                    pageTitle: "AI Studio"
                    pageSubtitle: "A teljes lokális kreatív és publikációs pipeline egységes FA3-felülete"
                    cards: [
                        {title: "Image", subtitle: "ComfyUI / InvokeAI / editor bridge projection.", badge: "READY", tone: window.magenta},
                        {title: "Video", subtitle: "Kdenlive, generation, compositing és editorial pipeline.", badge: "READY", tone: window.accent},
                        {title: "Animation", subtitle: "Motion, character és timeline workflow-k.", badge: "READY", tone: window.cyan},
                        {title: "3D / VFX", subtitle: "Geometry, Blender/Bforartist, Natron/Gaffer kapcsolatok.", badge: "READY", tone: window.orange},
                        {title: "Audio", subtitle: "STT, TTS, restoration, separation és voice fabric.", badge: "READY", tone: window.green},
                        {title: "Music", subtitle: "Music generation, stems, DAW és mastering workflow-k.", badge: "READY", tone: window.magenta},
                        {title: "Story / Screenplay", subtitle: "FA3 Story profile és production context projection.", badge: "READY", tone: window.accent},
                        {title: "Marketing", subtitle: "Kampány-, tartalom- és publikációs workflow-k.", badge: "PUBLISH", tone: window.orange},
                        {title: "Weboldal", subtitle: "Webes publikáció, preview és deployment workflow-k.", badge: "PUBLISH", tone: window.cyan},
                        {title: "Prezentáció", subtitle: "Prezentációk készítése, exportja és publikációs átadása.", badge: "PUBLISH", tone: window.green}
                    ]
                }

                ModulePage {
                    pageTitle: "Agents & Workflows"
                    pageSubtitle: "Interaktív agentek, durable workflow-k és policy-gated execution"
                    cards: [
                        {title: "Interactive Agents", subtitle: "Goose és desktop agent projection.", badge: "ROUTED", tone: window.accent},
                        {title: "Durable Workflows", subtitle: "Temporal authority állapot és futások.", badge: "READ", tone: window.green},
                        {title: "Tasks", subtitle: "Current tasks, approvals és blockers.", badge: "QUEUE", tone: window.orange},
                        {title: "Tool Execution", subtitle: "Central MCP mediation és policy outcome.", badge: "GATED", tone: window.magenta}
                    ]
                }

                ScrollView {
                    id: providerView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: providerView.availableWidth
                        spacing: 13
                        SectionTitle { title: "Models & Providers"; subtitle: "Model Registry, provider projections and local inference surfaces" }
                        RowLayout {
                            Layout.fillWidth: true
                            ModuleCard { title: "Provider Registry"; subtitle: fa3Repository.providerCount + " canonical provider records"; badge: "CANONICAL"; tone: window.accent; Layout.fillWidth: true }
                            ModuleCard { title: "Capability Baseline"; subtitle: "FA3 baseline remains authority-stable"; badge: "143"; tone: window.green; Layout.fillWidth: true }
                            ModuleCard { title: "Pending"; subtitle: "Runtime/conformance attention"; badge: fa3Repository.pendingCount.toString(); tone: fa3Repository.pendingCount > 0 ? window.orange : window.green; Layout.fillWidth: true }
                        }
                        TextField { id: providerSearch; Layout.fillWidth: true; placeholderText: "Search provider registry…" }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 500
                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                model: fa3Repository.recordsByCategory("provider").filter(function(v) {
                                    return providerSearch.text.length === 0 || v.id.toLowerCase().indexOf(providerSearch.text.toLowerCase()) >= 0 || v.title.toLowerCase().indexOf(providerSearch.text.toLowerCase()) >= 0
                                })
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 50
                                    background: Rectangle { color: hovered ? window.panelRaised : "transparent"; radius: 5 }
                                    contentItem: RowLayout {
                                        Rectangle { width: 7; height: 7; radius: 4; color: window.green }
                                        Label { text: modelData.id; color: window.textPrimary; font.family: "monospace"; Layout.preferredWidth: 310; elide: Text.ElideRight }
                                        Label { text: modelData.title; color: window.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                                        StatusChip { chipText: modelData.status || "REGISTERED"; tone: modelData.status && modelData.status.indexOf("PENDING") >= 0 ? window.orange : window.green }
                                    }
                                }
                            }
                        }
                    }
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
                            Item { Layout.fillWidth: true }
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
                        SectionTitle { title: "Keresés"; subtitle: "Egységes keresés a canonical rekordok, provider-ek, döntések és evidence-projekciók között" }
                        TextField { id: globalSearch; Layout.fillWidth: true; placeholderText: "Keresés ID, cím, státusz vagy útvonal alapján…" }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 620
                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                model: fa3Repository.searchRecords(globalSearch.text)
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 56
                                    background: Rectangle { color: hovered ? window.panelRaised : "transparent"; radius: 5 }
                                    onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                                    contentItem: RowLayout {
                                        StatusChip { chipText: modelData.category.toUpperCase(); tone: window.accent }
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
                    id: architectureView
                    contentWidth: availableWidth
                    clip: true
                    padding: 18
                    ColumnLayout {
                        width: architectureView.availableWidth
                        spacing: 13
                        SectionTitle { title: "Architecture Explorer"; subtitle: "Profiles, contracts, providers, decisions, gates and conformance records" }
                        TextField { id: architectureSearch; Layout.fillWidth: true; placeholderText: "Search canonical graph…" }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 620
                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                model: fa3Repository.searchRecords(architectureSearch.text)
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    height: 56
                                    background: Rectangle { color: hovered ? window.panelRaised : "transparent"; radius: 5 }
                                    onDoubleClicked: fa3Repository.openLocalPath(modelData.path)
                                    contentItem: RowLayout {
                                        StatusChip { chipText: modelData.category.toUpperCase(); tone: window.accent }
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

                ModulePage {
                    pageTitle: "Integrations"
                    pageSubtitle: "Desktop, DCC, editor, MCP and provider connections"
                    cards: [
                        {title: "Creative Apps", subtitle: "Krita, GIMP, Kdenlive, Bforartist/Blender, Natron/Gaffer.", badge: "DESKTOP", tone: window.magenta},
                        {title: "Agent Clients", subtitle: "Goose, Open WebUI, OpenYak and related projections.", badge: "ROUTED", tone: window.accent},
                        {title: "MCP", subtitle: "Capabilities mediated through the central gateway.", badge: "GATED", tone: window.orange},
                        {title: "Journal Share", subtitle: "E-mail adapter and chat/export bundle handoff.", badge: "ADAPTER", tone: window.green}
                    ]
                }

                ModulePage {
                    pageTitle: "Rendszerbeállítások"
                    pageSubtitle: "Az FA3 GUI és host-beállítások policy- és ChangeSet-határon belüli kezelési felülete"
                    cards: [
                        {title: "Megjelenés", subtitle: "FA3 téma, sűrűség, betűméret és felületi preferenciák.", badge: "GUI", tone: window.accent},
                        {title: "Erőforrás-policy", subtitle: "CPU/GPU/NPU/NUMA preferenciák csak ChangeSet-intentként.", badge: "GATED", tone: window.orange},
                        {title: "Hálózat", subtitle: "Lokális szolgáltatások, provider-hozzáférés és egress policy projekció.", badge: "POLICY", tone: window.cyan},
                        {title: "Biztonság", subtitle: "Security policy, approval és secret-metadata beállítási felület.", badge: "FAIL-CLOSED", tone: window.magenta},
                        {title: "Frissítések", subtitle: "FA3 komponens- és provider-frissítési állapotok.", badge: "CONTROLLED", tone: window.green},
                        {title: "Naplózás", subtitle: "Retention, export és archive-kezelési preferenciák authority-határral.", badge: "JOURNAL", tone: window.accent}
                    ]
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
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 34
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
