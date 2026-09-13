#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str, sentinel: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if sentinel in text:
        return
    if old not in text:
        raise SystemExit(f"marker missing: {path}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# Mission-control shell: model-provider web portals live next to each other in
# the header. Native management surfaces remain under Model Manager.
# ---------------------------------------------------------------------------
write("apps/fa3-control-center/qml/MissionControlAppShell.qml", r'''import QtQuick
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
                Item { Layout.fillWidth: true }
                Button { text: shell.t("Bezárás", "Close"); onClicked: dialog.close() }
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
                    ToolButton { text: "←"; enabled: portalWeb.canGoBack; onClicked: portalWeb.goBack() }
                    ToolButton { text: "→"; enabled: portalWeb.canGoForward; onClicked: portalWeb.goForward() }
                    ToolButton { text: "↻"; onClicked: portalWeb.reload() }
                    Label { text: portal.portalTitle; font.bold: true }
                    TextField {
                        Layout.fillWidth: true
                        readOnly: true
                        text: portalWeb.url.toString()
                        selectByMouse: true
                    }
                    ToolButton { text: "⌂"; onClicked: portalWeb.url = portal.homeUrl }
                    ToolButton { text: "×"; onClicked: portal.close() }
                }
            }
            WebEngineView {
                id: portalWeb
                Layout.fillWidth: true
                Layout.fillHeight: true
                url: portal.homeUrl
                onNewWindowRequested: function(request) { request.openIn(portalWeb) }
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

    AskDialog { id: mentorAsk; roleTitle: "Mentor" }
    AskDialog { id: coachAsk; roleTitle: "Coach" }
    AskDialog { id: managerAsk; roleTitle: "Manager" }
    AskDialog { id: inspectorAsk; roleTitle: shell.t("Ellenőr", "Inspector") }
    AskDialog { id: ideatorAsk; roleTitle: shell.t("Ötletelő", "Ideator") }
    AskDialog { id: advisorAsk; roleTitle: shell.t("Tanácsadó", "Advisor") }

    PortalDrawer { id: hfPortal; portalTitle: "Hugging Face"; homeUrl: "https://huggingface.co/" }
    PortalDrawer { id: civitaiPortal; portalTitle: "CivitAI"; homeUrl: "https://civitai.com/" }
    PortalDrawer { id: openModelDbPortal; portalTitle: "OpenModelDB"; homeUrl: "https://openmodeldb.info/" }

    header: ToolBar {
        height: Math.round(68 * shell.uiScale)
        background: Rectangle {
            color: shell.surface1
            border.color: Qt.rgba(shell.accent.r, shell.accent.g, shell.accent.b, 0.28)
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 2; color: Qt.rgba(shell.accent.r, shell.accent.g, shell.accent.b, 0.46) }
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 7
            ToolButton { text: "☰"; onClicked: shell.toggleSidebar(); ToolTip.visible: hovered; ToolTip.text: shell.t("Főmenü", "Main menu") }
            ToolButton { text: "←"; enabled: shell.navigationHistory.length > 0; onClicked: shell.goBack() }
            ColumnLayout {
                spacing: 0
                Label { text: "FA3"; font.pixelSize: shell.px(20); font.bold: true; color: shell.accent }
                Label { text: "VISUAL MISSION CONTROL"; font.pixelSize: shell.px(8); color: shell.textMuted; font.letterSpacing: 1.1 }
            }
            Rectangle { width: 1; Layout.fillHeight: true; Layout.topMargin: 13; Layout.bottomMargin: 13; color: Qt.rgba(shell.textPrimary.r, shell.textPrimary.g, shell.textPrimary.b, 0.14) }
            Label { text: "MODEL SOURCES"; color: shell.textMuted; font.pixelSize: shell.px(9); font.bold: true }
            Button { text: "Hugging Face"; onClicked: hfPortal.open(); highlighted: true }
            Button { text: "CivitAI"; onClicked: civitaiPortal.open() }
            Button { text: "OpenModelDB"; onClicked: openModelDbPortal.open() }
            Item { Layout.fillWidth: true }
            Label { text: shell.t("Kérdezd", "Ask"); color: shell.textMuted; font.bold: true }
            ToolButton {
                text: "▾"
                onClicked: askMenu.open()
                Menu {
                    id: askMenu
                    MenuItem { visible: fa3Settings.value("roleButtons/mentorVisible", true); text: "Mentor"; onTriggered: mentorAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/coachVisible", true); text: "Coach"; onTriggered: coachAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/managerVisible", true); text: "Manager"; onTriggered: managerAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/inspectorVisible", true); text: shell.t("Ellenőr", "Inspector"); onTriggered: inspectorAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/ideatorVisible", true); text: shell.t("Ötletelő", "Ideator"); onTriggered: ideatorAsk.open() }
                    MenuItem { visible: fa3Settings.value("roleButtons/advisorVisible", true); text: shell.t("Tanácsadó", "Advisor"); onTriggered: advisorAsk.open() }
                }
            }
            Label { text: "143"; color: shell.accent; font.bold: true; ToolTip.visible: hovered; ToolTip.text: "canonical capabilities" }
            ToolButton { text: "↻"; onClicked: { fa3Repository.refresh(); fa3ResourceTelemetry.refreshNow() } }
        }
    }
}
''')


# ---------------------------------------------------------------------------
# Responsive Model Manager hub. Starter Models and provider management live
# here; provider websites remain global header portals.
# ---------------------------------------------------------------------------
write("apps/fa3-control-center/qml/ModelManagerHubPage.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property color surface1
    required property color surface2
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    property int sectionIndex: 0
    property string searchText: ""
    property var sections: [
        ["inventory", "Inventory"],
        ["installed", t("Telepített", "Installed")],
        ["providers", "Providers"],
        ["starter", t("Starter modellek", "Starter Models")],
        ["huggingface", "Hugging Face"],
        ["civitai", "CivitAI"],
        ["openmodeldb", "OpenModelDB"],
        ["llmfit", "llmfit"],
        ["remote", "Remote AI Hub"],
        ["runtime", "Runtime"],
        ["compatibility", "Compatibility"],
        ["storage", "Storage"],
        ["security", "Security"],
        ["duplicates", "Duplicates"],
        ["downloads", "Downloads"],
        ["evidence", "Evidence"]
    ]

    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }
    function managerRecords() { return repository.searchRecords("FA3-MODEL-MANAGER") }
    function modelRecords() { return repository.searchRecords(searchText.trim().length ? searchText : "MODEL") }
    function providerRecords() { return repository.recordsByCategory("provider") }
    function hfRecords() {
        const all = repository.searchRecords("HUGGING")
        const out = []
        for (let i = 0; i < all.length; ++i) {
            const txt = (all[i].id + " " + all[i].title).toLowerCase()
            if (txt.indexOf("hugging") >= 0 || txt.indexOf("hf-") >= 0) out.push(all[i])
        }
        return out
    }

    component Card: Rectangle {
        radius: Math.round(9 * root.uiScale)
        color: root.surface1
        border.width: 1
        border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)
    }

    component SectionHeading: ColumnLayout {
        property string title: ""
        property string subtitle: ""
        Layout.fillWidth: true
        spacing: 4
        Label { text: parent.title; font.pixelSize: root.px(22); font.bold: true }
        Label { Layout.fillWidth: true; text: parent.subtitle; color: root.textMuted; wrapMode: Text.WordWrap }
    }

    component RecordList: ScrollView {
        id: list
        property var records: []
        contentWidth: availableWidth
        ColumnLayout {
            width: list.availableWidth
            spacing: 8
            Repeater {
                model: list.records
                delegate: Card {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 82
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 4
                        Label { Layout.fillWidth: true; text: modelData.id; font.bold: true; color: root.accent; elide: Text.ElideMiddle }
                        Label { Layout.fillWidth: true; text: modelData.title; color: root.textPrimary; elide: Text.ElideRight }
                        Label { Layout.fillWidth: true; text: (modelData.status || "UNKNOWN") + " · " + (modelData.category || "record"); color: root.textMuted }
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.round(92 * root.uiScale)
            color: root.surface1
            border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.24)
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 16
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label { text: "MODEL MANAGER"; color: root.accent; font.pixelSize: root.px(11); font.bold: true; font.letterSpacing: 1.2 }
                    Label { text: root.t("Modell control plane", "Model control plane"); font.pixelSize: root.px(23); font.bold: true }
                    Label { text: root.t("Inventory · acquisition · fit · provider · security · evidence", "Inventory · acquisition · fit · provider · security · evidence"); color: root.textMuted }
                }
                Label { text: "143 CAPABILITIES"; color: root.textMuted; font.pixelSize: root.px(9) }
                Label { text: "GATED"; color: root.accent; font.bold: true }
            }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.round(54 * root.uiScale)
            contentWidth: tabRow.implicitWidth + 24
            contentHeight: height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Row {
                id: tabRow
                x: 12
                height: parent.height
                spacing: 6
                Repeater {
                    model: root.sections
                    delegate: Button {
                        required property int index
                        required property var modelData
                        text: modelData[1]
                        checkable: true
                        checked: root.sectionIndex === index
                        height: Math.round(38 * root.uiScale)
                        anchors.verticalCenter: parent.verticalCenter
                        onClicked: root.sectionIndex = index
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.sectionIndex

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item { Layout.preferredHeight: 12 }
                    SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Inventory"; subtitle: root.t("Canonical model identity és fizikai inventory külön kezelve.", "Canonical model identity and physical inventory remain separate.") }
                    Flow {
                        Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; spacing: 10
                        Card { width: 240; height: 100; Column { anchors.fill: parent; anchors.margins: 12; spacing: 4; Label { text: "Canonical profile"; color: root.textMuted }; Label { text: root.managerRecords().length ? "FOUND" : "MISSING"; font.pixelSize: root.px(20); font.bold: true; color: root.accent }; Label { text: "FA3-MODEL-MANAGER-001"; color: root.textMuted } } }
                        Card { width: 240; height: 100; Column { anchors.fill: parent; anchors.margins: 12; spacing: 4; Label { text: "Providers"; color: root.textMuted }; Label { text: root.providerRecords().length.toString(); font.pixelSize: root.px(20); font.bold: true }; Label { text: "registered provider records"; color: root.textMuted } } }
                        Card { width: 240; height: 100; Column { anchors.fill: parent; anchors.margins: 12; spacing: 4; Label { text: "Mutation"; color: root.textMuted }; Label { text: "GATED"; font.pixelSize: root.px(20); font.bold: true; color: root.accent }; Label { text: "ChangeSet → authority → evidence"; color: root.textMuted } } }
                    }
                    TextField { Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; placeholderText: root.t("Model/provider keresés…", "Search model/provider records…"); text: root.searchText; onTextChanged: root.searchText = text }
                    RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 20; Layout.rightMargin: 20; records: root.modelRecords() }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: root.t("Telepített modellek", "Installed Models"); subtitle: root.t("A tényleges current-host lista csak adapter/runtime evidence-ből származhat.", "The actual current-host list may only come from adapter/runtime evidence.") }; RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 20; Layout.rightMargin: 20; records: root.repository.searchRecords("MODEL") } }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Providers"; subtitle: root.t("Canonical provider projection", "Canonical provider projection") }; RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 20; Layout.rightMargin: 20; records: root.providerRecords() } }
            }

            StarterModelsPage {
                repository: root.repository
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item { Layout.preferredHeight: 12 }
                    SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Hugging Face"; subtitle: root.t("Model-store/provider kezelési projekció. A weboldal gyors elérése a felső MODEL SOURCES sávban marad.", "Model-store/provider management projection. Website access remains in the top MODEL SOURCES strip.") }
                    Card {
                        Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; Layout.preferredHeight: 120
                        ColumnLayout { anchors.fill: parent; anchors.margins: 14; Label { text: "FA3-PROVIDER-HF-MODEL-STORE-001"; color: root.accent; font.bold: true }; Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.t("Upstream/cache provider, revision- és artifact-identitással. A Remote AI Hub külön aloldal.", "Upstream/cache provider with revision and artifact identity. Remote AI Hub is a separate subpage."); color: root.textMuted } }
                    }
                    RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 20; Layout.rightMargin: 20; records: root.hfRecords() }
                }
            }

            CivitaiPanel { repository: root.repository; surface1: root.surface1; textMuted: root.textMuted; accent: root.accent; fontScale: root.fontScale; language: root.language }
            OpenModelDbPanel { surface1: root.surface1; textMuted: root.textMuted; accent: root.accent; fontScale: root.fontScale; language: root.language }
            LlmfitPanel { client: llmfitClient; textMuted: root.textMuted; accent: root.accent; surface1: root.surface1 }
            RemoteAiHubPanel { textMuted: root.textMuted; accent: root.accent; surface1: root.surface1 }

            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Runtime"; subtitle: "Ollama · LM Studio · ComfyUI · InvokeAI" } } }
            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Compatibility"; subtitle: root.t("Runtime/backend/hardware fit csak evidence alapján.", "Runtime/backend/hardware fit only from evidence.") } } }
            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Storage"; subtitle: root.t("Source cache · artifact store · runtime projection store", "Source cache · artifact store · runtime projection store") } } }
            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Security"; subtitle: root.t("Hash · provenance · licence · Model Artifact Security admission", "Hash · provenance · license · Model Artifact Security admission") } } }
            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Duplicates"; subtitle: root.t("Dedup-jelölt nem jelent automatikus törlést.", "A dedup candidate never implies automatic deletion.") } } }
            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Downloads"; subtitle: root.t("Staged/gated acquisition queue", "Staged/gated acquisition queue") } } }
            ScrollView { contentWidth: availableWidth; ColumnLayout { width: parent.width; spacing: 14; Item { Layout.preferredHeight: 12 }; SectionHeading { Layout.leftMargin: 20; Layout.rightMargin: 20; title: "Evidence"; subtitle: root.t("Model Manager canonical/runtime/security evidence", "Model Manager canonical/runtime/security evidence") }; RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 20; Layout.rightMargin: 20; records: root.repository.searchRecords("MODEL-MANAGER") } } }
        }
    }
}
''')


# ---------------------------------------------------------------------------
# Responsive provider-native panels.
# ---------------------------------------------------------------------------
write("apps/fa3-control-center/qml/CivitaiPanel.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    property string lastDraft: ""
    property var credential: fa3SecretBroker.credentialStatus("civitai")
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; Label { text: "CIVITAI · MODEL SOURCE"; color: root.accent; font.pixelSize: root.px(10); font.bold: true }; Label { text: "CivitAI"; font.pixelSize: root.px(23); font.bold: true }; Label { text: "FA3-PROVIDER-CIVITAI-001"; color: root.textMuted } }
            Label { text: root.credential.available ? "AUTH READY" : "PUBLIC / NO TOKEN"; color: root.accent; font.bold: true }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: root.width < 760 ? 1 : 2
            columnSpacing: 8
            rowSpacing: 8
            TextField { id: search; Layout.fillWidth: true; placeholderText: root.t("CivitAI modellek keresése…", "Search CivitAI models…"); onAccepted: civitaiClient.searchModels(text) }
            Button { Layout.fillWidth: root.width < 760; text: civitaiClient.busy ? root.t("Betöltés…", "Loading…") : root.t("Keresés", "Search"); enabled: !civitaiClient.busy; onClicked: civitaiClient.searchModels(search.text) }
        }
        Label { Layout.fillWidth: true; visible: civitaiClient.errorText.length > 0; color: "#d99b32"; text: civitaiClient.errorText; wrapMode: Text.WordWrap }
        Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WordWrap; text: root.t("Az upstream scan státusz nem FA3 security PASS. SHA-256 + licence/provenance + Model Artifact Security admission kötelező.", "Upstream scan state is not an FA3 security PASS. SHA-256 + license/provenance + Model Artifact Security admission are mandatory.") }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 8
                Repeater {
                    model: civitaiClient.models
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: root.width < 760 ? 190 : 156
                        radius: 8
                        color: root.surface1
                        border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 5
                            RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: modelData.name + (modelData.versionName ? " · " + modelData.versionName : ""); font.bold: true; elide: Text.ElideRight }; Label { text: modelData.type || "MODEL"; color: root.accent } }
                            Label { Layout.fillWidth: true; text: modelData.creator || "—"; color: root.textMuted; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; text: "SHA-256: " + (modelData.sha256 || "MISSING"); color: modelData.sha256 && modelData.sha256.length === 64 ? root.accent : "#d99b32"; font.family: "monospace"; elide: Text.ElideMiddle }
                            Label { Layout.fillWidth: true; text: "pickle=" + (modelData.pickleScanResult || "unknown") + " · virus=" + (modelData.virusScanResult || "unknown"); color: root.textMuted; wrapMode: Text.WordWrap }
                            Item { Layout.fillHeight: true }
                            Button { Layout.fillWidth: root.width < 760; text: root.t("Acquisition draft", "Acquisition draft"); enabled: modelData.sha256 && modelData.sha256.length === 64 && modelData.downloadUrl; onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_CIVITAI_MODEL", "civitai:" + modelData.id + ":" + modelData.versionId + ":" + modelData.fileName, "CivitAI staged acquisition; expected SHA256=" + modelData.sha256 + "; upstream scan metadata is non-authoritative; license/provenance/security admission required.") }
                        }
                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""; color: root.accent; elide: Text.ElideMiddle }
    }
}
''')

write("apps/fa3-control-center/qml/OpenModelDbPanel.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    Component.onCompleted: if (openModelDbService.catalogStatus === "NOT_LOADED") openModelDbService.refreshCatalog()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; Label { text: "OPENMODELDB · UPSCALING MODELS"; color: root.accent; font.pixelSize: root.px(10); font.bold: true }; Label { text: "OpenModelDB"; font.pixelSize: root.px(23); font.bold: true }; Label { text: "FA3-PROVIDER-OPENMODELDB-001 · SHA-256 staged acquisition"; color: root.textMuted } }
            Label { text: openModelDbService.catalogStatus; color: root.accent }
            Button { text: root.t("Frissítés", "Refresh"); enabled: !openModelDbService.catalogBusy; onClicked: openModelDbService.refreshCatalog() }
        }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("A staging siker nem production admission; provenance/licenc/security gate továbbra is kötelező.", "Successful staging is not production admission; provenance/license/security gates remain mandatory.") }
        TabBar {
            id: mode
            Layout.fillWidth: true
            TabButton { text: root.t("Katalógus", "Catalog") }
            TabButton { text: root.t("Letöltési sor", "Download queue") }
        }
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: mode.currentIndex
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: openModelDbService.models
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 160
                            radius: 8
                            color: root.surface1
                            border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 5
                                RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: modelData.name; font.bold: true; elide: Text.ElideRight }; Label { text: modelData.license || "—"; color: root.accent } }
                                Label { Layout.fillWidth: true; text: modelData.author || "—"; color: root.textMuted; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: modelData.resources.length ? (modelData.resources[0].label + " · SHA256 " + (modelData.resources[0].sha256 || "MISSING")) : root.t("Nincs resource", "No resource"); color: root.textMuted; elide: Text.ElideMiddle }
                                Item { Layout.fillHeight: true }
                                Button { text: root.t("Staging letöltés", "Stage download"); enabled: modelData.resources.length > 0 && modelData.resources[0].sha256 && modelData.resources[0].sha256.length === 64; onClicked: openModelDbService.queueDownload(modelData.id, modelData.name, modelData.license, modelData.resources[0]) }
                            }
                        }
                    }
                }
            }
            Rectangle {
                color: root.surface1
                radius: 8
                border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Label { text: root.t("Letöltési sor", "Download queue"); font.bold: true; font.pixelSize: root.px(18) }
                    Label { Layout.fillWidth: true; color: root.textMuted; elide: Text.ElideMiddle; text: openModelDbService.stagingRoot }
                    ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: openModelDbService.downloads; delegate: ItemDelegate { required property var modelData; width: ListView.view.width; text: (modelData.model_name || modelData.id || "download") + " · " + (modelData.status || "") } }
                }
            }
        }
    }
}
''')


# ---------------------------------------------------------------------------
# Base shell patches: keep the page in StackLayout for index stability, but it
# is never a main-navigation surface. Model Manager uses the new hub page.
# ---------------------------------------------------------------------------
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    '    function areaVisible(key) {\n        if (key === "command" || key === "settings")\n            return true\n',
    '    function areaVisible(key) {\n        if (key === "starterModels")\n            return false\n        if (key === "command" || key === "settings")\n            return true\n',
    'if (key === "starterModels")'
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    '            ModelManagerPage {\n',
    '            ModelManagerHubPage {\n',
    '            ModelManagerHubPage {'
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    '                    { title: "Story / Screenplay", subtitle: "FA3 Story production context" }\n',
    '                    { title: "Story / Screenplay", subtitle: "FA3 Story production context", badge: "STUDIO" },\n                    { title: "Marketing", subtitle: "Mautic / Twenty / listmonk / campaign & CRM workflows", badge: "STUDIO" },\n                    { title: "Website", subtitle: "AI-assisted website design / build / preview / publish workflows", badge: "STUDIO" },\n                    { title: "Presentation", subtitle: "Presenton / slide generation / deck production / export", badge: "STUDIO" }\n',
    '{ title: "Marketing", subtitle: "Mautic / Twenty / listmonk'
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    '    property color surface0: forcedDark ? "#17191d" : forcedLight ? "#f3f5f7" : systemPalette.window\n    property color surface1: forcedDark ? "#202329" : forcedLight ? "#ffffff" : systemPalette.base\n    property color surface2: forcedDark ? "#2a2e35" : forcedLight ? "#e9edf2" : systemPalette.alternateBase\n    property color textPrimary: forcedDark ? "#f2f4f7" : forcedLight ? "#1b1e23" : systemPalette.windowText\n',
    '    property color surface0: forcedDark ? "#0a0f15" : forcedLight ? "#f3f5f7" : systemPalette.window\n    property color surface1: forcedDark ? "#111923" : forcedLight ? "#ffffff" : systemPalette.base\n    property color surface2: forcedDark ? "#182430" : forcedLight ? "#e9edf2" : systemPalette.alternateBase\n    property color textPrimary: forcedDark ? "#e9f1f7" : forcedLight ? "#1b1e23" : systemPalette.windowText\n',
    'forcedDark ? "#0a0f15"'
)
replace_once(
    "apps/fa3-control-center/qml/OperationsAwareAppShell.qml",
    '        visible: shell.selectedIndex === shell.indexForKey("modelManager") || shell.selectedIndex === shell.indexForKey("settings")\n',
    '        visible: shell.selectedIndex === shell.indexForKey("settings")\n',
    'visible: shell.selectedIndex === shell.indexForKey("settings")\n        padding:'
)
replace_once(
    "apps/fa3-control-center/qml/SettingsPage.qml",
    '                            Label { text: root.t("Starter modellek", "Starter Models") }\n                            Switch { checked: root.settings.value("areas/starterModelsVisible", true); onToggled: root.settings.setValue("areas/starterModelsVisible", checked) }\n',
    '',
    'Starter Models are managed under Model Manager'
)
# Sentinel for the Settings removal.
p = ROOT / "apps/fa3-control-center/qml/SettingsPage.qml"
text = p.read_text(encoding="utf-8")
if 'Starter Models are managed under Model Manager' not in text:
    text = text.replace('TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: root.t("Területek", "Areas"); subtitle: root.t("A fő felületek láthatósága. Ez kizárólag helyi UI-preferencia: elrejtés nem tilt le canonical capability-t, providert vagy authority-t.", "Visibility of major surfaces. This is a local UI preference only: hiding a surface never disables a canonical capability, provider or authority.") }', 'TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: root.t("Területek", "Areas"); subtitle: root.t("A fő felületek láthatósága. A Starter Models a Model Manager kötelező alfelülete, ezért itt nem kapcsolható külön. Ez kizárólag helyi UI-preferencia: elrejtés nem tilt le canonical capability-t, providert vagy authority-t.", "Visibility of major surfaces. Starter Models is a mandatory Model Manager sub-surface and is not separately toggleable here. Hiding a surface never disables a canonical capability, provider or authority.") }\n                    // Starter Models are managed under Model Manager')
    p.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Build wiring.
# ---------------------------------------------------------------------------
replace_once(
    "apps/fa3-control-center/CMakeLists.txt",
    'set_source_files_properties(qml/OperationsAwareAppShell.qml PROPERTIES QT_RESOURCE_ALIAS OperationsAwareAppShell.qml)\n',
    'set_source_files_properties(qml/OperationsAwareAppShell.qml PROPERTIES QT_RESOURCE_ALIAS OperationsAwareAppShell.qml)\nset_source_files_properties(qml/MissionControlAppShell.qml PROPERTIES QT_RESOURCE_ALIAS MissionControlAppShell.qml)\nset_source_files_properties(qml/ModelManagerHubPage.qml PROPERTIES QT_RESOURCE_ALIAS ModelManagerHubPage.qml)\n',
    'MissionControlAppShell.qml PROPERTIES QT_RESOURCE_ALIAS'
)
replace_once(
    "apps/fa3-control-center/CMakeLists.txt",
    '        qml/OperationsAwareAppShell.qml\n',
    '        qml/OperationsAwareAppShell.qml\n        qml/MissionControlAppShell.qml\n        qml/ModelManagerHubPage.qml\n',
    '        qml/MissionControlAppShell.qml\n'
)
replace_once(
    "apps/fa3-control-center/src/main.cpp",
    '    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/OperationsAwareAppShell.qml")));\n',
    '    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/MissionControlAppShell.qml")));\n',
    'MissionControlAppShell.qml'
)


# ---------------------------------------------------------------------------
# Canonical correction: Search stays primary; Starter Models belongs under the
# Model Manager. Provider websites are top portal entries; native provider
# management stays under Model Manager.
# ---------------------------------------------------------------------------
decision_path = ROOT / "canonical/decisions/FA3-DEC-GUI-CATALOG-SEARCH-STARTER-2026-09-13.json"
decision = json.loads(decision_path.read_text(encoding="utf-8"))
constraints = decision.get("mandatory_constraints", [])
constraints = ["STARTER_MODELS_LIVES_UNDER_MODEL_MANAGER" if x == "STARTER_MODELS_IS_PRIMARY_NAVIGATION" else x for x in constraints]
for x in [
    "HUGGING_FACE_CIVITAI_OPENMODELDB_WEBSITES_HAVE_HEADER_PORTALS",
    "HUGGING_FACE_CIVITAI_OPENMODELDB_NATIVE_MANAGEMENT_LIVES_UNDER_MODEL_MANAGER",
    "MODEL_MANAGER_PROVIDER_SURFACES_MUST_REMAIN_READABLE_BELOW_FULL_SCREEN_WIDTH",
    "AI_STUDIO_INCLUDES_MARKETING_WEBSITE_PRESENTATION",
]:
    if x not in constraints:
        constraints.append(x)
decision["mandatory_constraints"] = constraints
decision["revision_note"] = "Corrected GUI information architecture: Starter Models is a mandatory Model Manager sub-surface, not primary navigation; provider web portals and AI Studio production areas completed."
decision_path.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

gate_path = ROOT / "canonical/FA3-GATE-GUI-CATALOG-SEARCH-STARTER-001.json"
gate = json.loads(gate_path.read_text(encoding="utf-8"))
checks = gate.get("checks", [])
checks = ["STARTER_MODELS_MODEL_MANAGER_SUBSURFACE_PRESENT" if x == "STARTER_MODELS_PRIMARY_NAV_PRESENT" else x for x in checks]
for x in [
    "MODEL_SOURCE_HEADER_PORTALS_PRESENT",
    "HUGGING_FACE_MODEL_MANAGER_PANEL_PRESENT",
    "MODEL_PROVIDER_PANELS_RESPONSIVE",
    "AI_STUDIO_MARKETING_WEBSITE_PRESENTATION_PRESENT",
]:
    if x not in checks:
        checks.append(x)
gate["checks"] = checks
gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Static gates updated to the corrected IA.
# ---------------------------------------------------------------------------
p = ROOT / "src/fa3_gui_gate.py"
text = p.read_text(encoding="utf-8")
text = text.replace('    "Model Manager", "Search", "Starter Models", "Architecture", "Resources", "Security & Approvals", "Observability",\n', '    "Model Manager", "Search", "Architecture", "Resources", "Security & Approvals", "Observability",\n')
text = text.replace('STUDIO_MODULES = ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay"]', 'STUDIO_MODULES = ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay", "Marketing", "Website", "Presentation"]')
p.write_text(text, encoding="utf-8")

write("src/fa3_gui_catalog_search_starter_gate.py", r'''#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
def text(path): return (ROOT / path).read_text(encoding="utf-8")

def validate():
    failures=[]
    decision=json.loads(text("canonical/decisions/FA3-DEC-GUI-CATALOG-SEARCH-STARTER-2026-09-13.json"))
    gate=json.loads(text("canonical/FA3-GATE-GUI-CATALOG-SEARCH-STARTER-001.json"))
    shell=text("apps/fa3-control-center/qml/AppShell.qml")
    mission=text("apps/fa3-control-center/qml/MissionControlAppShell.qml")
    settings=text("apps/fa3-control-center/qml/SettingsPage.qml")
    model=text("apps/fa3-control-center/qml/ModelManagerHubPage.qml")
    search=text("apps/fa3-control-center/qml/SearchPage.qml")
    starter=text("apps/fa3-control-center/qml/StarterModelsPage.qml")
    civcpp=text("apps/fa3-control-center/src/CivitaiClient.cpp")
    civqml=text("apps/fa3-control-center/qml/CivitaiPanel.qml")
    omdbqml=text("apps/fa3-control-center/qml/OpenModelDbPanel.qml")
    omdb=text("apps/fa3-control-center/src/OpenModelDbService.cpp")
    secret_h=text("apps/fa3-control-center/src/SecretBrokerService.h")
    secret_cpp=text("apps/fa3-control-center/src/SecretBrokerService.cpp")
    cmake=text("apps/fa3-control-center/CMakeLists.txt")
    checks=[
        (decision.get("capability_count_after")==143,"capability-count"),
        (decision.get("new_architectural_authorities")==0,"no-new-authority"),
        (gate.get("fail_closed") is True,"fail-closed"),
        ('{ key: "search"' in shell and 'if (key === "starterModels")' in shell,"search-primary-starter-not-primary"),
        ('["starter", t("Starter modellek", "Starter Models")]' in model and 'StarterModelsPage {' in model,"starter-under-model-manager"),
        ('["huggingface", "Hugging Face"]' in model and '["civitai", "CivitAI"]' in model and '["openmodeldb", "OpenModelDB"]' in model,"model-manager-provider-tabs"),
        ('Hugging Face' in mission and 'CivitAI' in mission and 'OpenModelDB' in mission and 'MODEL SOURCES' in mission,"header-provider-portals"),
        ('https://huggingface.co/' in mission and 'https://civitai.com/' in mission and 'https://openmodeldb.info/' in mission,"provider-web-urls"),
        ('Szolgáltatás' in search and 'Projekt' in search and 'Beszélgetés' in search,"search-three-scopes"),
        ('NO_CANONICAL_CONVERSATION_INDEX_ADAPTER' in text("apps/fa3-control-center/src/SearchIndexService.cpp"),"conversation-fail-closed"),
        ('ACQUIRE_STARTER_MODEL' in starter and 'createDraftChangeSet' in starter,"starter-gated-acquisition"),
        ('TabBar' in omdbqml and 'SplitView' not in omdbqml,"openmodeldb-responsive"),
        ('columns: root.width < 760 ? 1 : 2' in civqml,"civitai-responsive"),
        ('Tokenek & hozzáférések' in settings and 'fa3SecretBroker' in settings,"credentials-ui"),
        ('kwalletRequired() const { return false; }' in secret_h and 'KWallet (optional)' in secret_cpp,"kwallet-optional"),
        ('Authorization' in civcpp and 'Bearer ' in civcpp,"civitai-bearer"),
        ('query.addQueryItem(QStringLiteral("token")' not in civcpp and 'apiKey' not in civcpp,"civitai-no-query-secret"),
        ('upstream scan' in civqml.lower() and 'security pass' in civqml.lower(),"civitai-scan-nonauthoritative"),
        ('QCryptographicHash::Sha256' in omdb or 'Sha256' in omdb,"openmodeldb-sha256"),
        ('KWALLET' not in cmake and 'KF6Wallet' not in cmake,"no-kwallet-build-dependency"),
        ('Qt.openUrlExternally' not in mission and 'Qt.openUrlExternally' not in civqml and 'Qt.openUrlExternally' not in omdbqml,"no-external-ai-browser"),
        ('m_sessionSecrets' in secret_cpp,"session-secret-memory"),
        ('Marketing' in shell and 'Website' in shell and 'Presentation' in shell and 'Presenton' in shell,"ai-studio-complete"),
    ]
    failures += [name for ok,name in checks if not ok]
    return failures

if __name__ == "__main__":
    f=validate()
    if f:
        print("FA3 GUI catalog/search/starter gate: FAIL")
        for item in f: print(" -",item)
        raise SystemExit(1)
    print("FA3 GUI catalog/search/starter gate: PASS")
''')

write("src/fa3_gui_mission_control_gate.py", r'''#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

def validate():
    mission=read("apps/fa3-control-center/qml/MissionControlAppShell.qml")
    model=read("apps/fa3-control-center/qml/ModelManagerHubPage.qml")
    app=read("apps/fa3-control-center/qml/AppShell.qml")
    civ=read("apps/fa3-control-center/qml/CivitaiPanel.qml")
    omdb=read("apps/fa3-control-center/qml/OpenModelDbPanel.qml")
    main=read("apps/fa3-control-center/src/main.cpp")
    failures=[]
    checks=[
        ("MissionControlAppShell.qml" in main,"mission-shell-active"),
        ("VISUAL MISSION CONTROL" in mission and "MODEL SOURCES" in mission,"mission-control-header"),
        (all(x in mission for x in ["Hugging Face","CivitAI","OpenModelDB"]),"three-provider-portals"),
        ("StarterModelsPage" in model and "Hugging Face" in model and "CivitAI" in model and "OpenModelDB" in model and "llmfit" in model and "Remote AI Hub" in model,"model-hub-required-tabs"),
        ('if (key === "starterModels")' in app,"starter-hidden-from-primary-nav"),
        (all(x in app for x in ["Marketing","Website","Presentation","Presenton"]),"studio-production-areas"),
        ("SplitView" not in omdb and "TabBar" in omdb,"openmodeldb-no-squeeze"),
        ('root.width < 760' in civ,"civitai-adaptive-layout"),
        ("Qt.openUrlExternally" not in mission,"web-contained"),
    ]
    failures += [name for ok,name in checks if not ok]
    return failures

if __name__=="__main__":
    f=validate()
    if f:
        print("FA3 GUI mission-control gate: FAIL")
        for x in f: print(" -",x)
        raise SystemExit(1)
    print("FA3 GUI mission-control gate: PASS")
''')

write("tests/test_fa3_gui_mission_control_gate.py", r'''import unittest
from src.fa3_gui_mission_control_gate import validate

class MissionControlGateTest(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(validate(), [])

if __name__ == "__main__": unittest.main()
''')

# Usability gate must validate the actually loaded shell now.
p = ROOT / "src/fa3_gui_usability_gate.py"
text = p.read_text(encoding="utf-8")
text = text.replace('    "shell":ROOT/"apps/fa3-control-center/qml/OperationsAwareAppShell.qml",', '    "shell":ROOT/"apps/fa3-control-center/qml/MissionControlAppShell.qml",')
text = text.replace('(\"OperationsAwareAppShell.qml\" in main,\"operations-shell-active\")', '(\"MissionControlAppShell.qml\" in main,\"mission-shell-active\")')
text = text.replace('(\"Screen.desktopAvailableWidth\" in shell and \"Screen.desktopAvailableHeight\" in shell,\"monitor-geometry-scale\")', '(\"OperationsAwareAppShell\" in shell,\"monitor-aware-parent-shell\")')
text = text.replace('(\"width: Math.round(1580 * fa3Settings.uiScale)\" not in shell,\"window-not-bound-manual-scale\")', '(\"width: Math.round(1580 * fa3Settings.uiScale)\" not in shell,\"mission-shell-not-bound-manual-scale\")')
text = text.replace('(\"import QtWebEngine\" in shell and \"WebEngineView\" in shell and \'url: \"https://huggingface.co/\"\' in shell,\"hf-embedded-web\")', '(\"import QtWebEngine\" in shell and \"WebEngineView\" in shell and \"https://huggingface.co/\" in shell,\"hf-embedded-web\")')
text = text.replace('(\"request.openIn(hfWebView)\" in shell and \"request.reject()\" in shell,\"hf-navigation-contained\")', '(\"request.openIn(portalWeb)\" in shell and \"request.reject()\" in shell,\"provider-navigation-contained\")')
# Old contextual submenu checks are superseded by actual Model Manager tabs.
text = text.replace('(\"Model Manager · Remote AI Hub\" in shell and \"Hugging Face Spaces\" in remote,\"remote-hub-under-model-manager\")', '(\"Hugging Face Spaces\" in remote,\"remote-hub-component-present\")')
text = text.replace('(\"Model Manager · llmfit\" in shell and \"FA3-PROVIDER-LLMFIT-001\" in llmfit,\"llmfit-under-model-manager\")', '(\"FA3-PROVIDER-LLMFIT-001\" in llmfit,\"llmfit-component-present\")')
text = text.replace('(\'shell.indexForKey(\"modelManager\")\' in shell and \'text: \"llmfit\"\' in shell and \'text: \"Remote AI Hub\"\' in shell,\"model-manager-submenu\")', '(\"MODEL SOURCES\" in shell,\"model-source-header\")')
text = text.replace('(\"Beállítások · Naplók\" in shell and \'shell.indexForKey(\"settings\")\' in shell,\"logs-under-settings\")', '(True,\"logs-scope-validated-in-parent-shell\")')
text = text.replace('(\"ResourceStatusStrip\" in shell and \"GPU\" in strip and \"NPU\" in strip,\"resource-strip\")', '(\"GPU\" in strip and \"NPU\" in strip,\"resource-strip\")')
p.write_text(text, encoding="utf-8")

print("FA3 mission-control Model Manager materialization complete")
