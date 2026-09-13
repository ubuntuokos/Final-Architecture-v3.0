import QtQuick
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
        { key: "inventory", label: "Inventory" },
        { key: "installed", label: t("Telepített", "Installed") },
        { key: "providers", label: "Providers" },
        { key: "starter", label: t("Starter modellek", "Starter Models") },
        { key: "huggingface", label: "Hugging Face" },
        { key: "civitai", label: "CivitAI" },
        { key: "openmodeldb", label: "OpenModelDB" },
        { key: "llmfit", label: "llmfit" },
        { key: "remotehub", label: "Remote AI Hub" },
        { key: "runtime", label: "Runtime" },
        { key: "storage", label: "Storage" },
        { key: "security", label: "Security" },
        { key: "downloads", label: "Downloads" },
        { key: "evidence", label: "Evidence" }
    ]

    function t(hu, en) { return language === "en" ? en : hu }
    function px(value) { return Math.max(9, Math.round(value * fontScale)) }
    function managerRecords() { return repository.searchRecords("FA3-MODEL-MANAGER") }
    function modelRecords() {
        const query = searchText.trim().length > 0 ? searchText : "MODEL"
        return repository.searchRecords(query)
    }
    function providerRecords() {
        const all = repository.recordsByCategory("provider")
        const out = []
        for (let i = 0; i < all.length; ++i) {
            const text = (all[i].id + " " + all[i].title).toLowerCase()
            if (text.indexOf("model") >= 0 || text.indexOf("ollama") >= 0 || text.indexOf("lm-studio") >= 0 || text.indexOf("hugging") >= 0 || text.indexOf("stability") >= 0 || text.indexOf("civitai") >= 0 || text.indexOf("openmodeldb") >= 0)
                out.push(all[i])
        }
        return out
    }

    onSectionIndexChanged: {
        if (sections[sectionIndex].key === "llmfit")
            llmfitClient.refresh()
    }

    component Card: Rectangle {
        radius: Math.round(10 * root.uiScale)
        color: root.surface1
        border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
    }

    component RecordListPage: ScrollView {
        id: recordPage
        property string title: ""
        property string subtitle: ""
        property var records: []
        contentWidth: availableWidth
        ColumnLayout {
            width: recordPage.availableWidth
            spacing: 12
            Item { Layout.preferredHeight: 8 }
            Label { Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; text: recordPage.title; font.pixelSize: root.px(22); font.bold: true }
            Label { Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; text: recordPage.subtitle; color: root.textMuted; wrapMode: Text.WordWrap }
            Repeater {
                model: recordPage.records
                delegate: Card {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    Layout.preferredHeight: Math.max(90, recordColumn.implicitHeight + 24)
                    ColumnLayout {
                        id: recordColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 5
                        Label { Layout.fillWidth: true; text: modelData.id; font.bold: true; wrapMode: Text.WrapAnywhere }
                        Label { Layout.fillWidth: true; text: modelData.title; color: root.textMuted; wrapMode: Text.WordWrap }
                        Label { text: modelData.status || "UNKNOWN"; color: root.accent; font.bold: true }
                    }
                }
            }
            Item { Layout.preferredHeight: 20 }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.round(92 * root.uiScale)
            color: root.surface1
            border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.08)

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Model Manager"; font.pixelSize: root.px(20); font.bold: true }
                    Label { Layout.fillWidth: true; text: root.t("Modellek, upstream hubok, fit, acquisition, security és evidence egy helyen.", "Models, upstream hubs, fit, acquisition, security and evidence in one place."); color: root.textMuted; elide: Text.ElideRight }
                }
                ComboBox {
                    id: sectionSelector
                    Layout.preferredWidth: Math.min(Math.max(210, root.width * 0.30), 330)
                    model: root.sections
                    textRole: "label"
                    currentIndex: root.sectionIndex
                    onActivated: root.sectionIndex = currentIndex
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.sectionIndex

            ScrollView {
                id: inventoryView
                contentWidth: availableWidth
                ColumnLayout {
                    width: inventoryView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 8 }
                    Label { Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; text: "Model Inventory"; font.pixelSize: root.px(22); font.bold: true }
                    Label { Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; text: root.t("A canonical Model Manager elsődleges GUI-ja. A logikai model identity különválik a fizikai storage path-tól.", "Primary canonical Model Manager GUI. Logical model identity remains separate from physical storage paths."); color: root.textMuted; wrapMode: Text.WordWrap }
                    TextField {
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        placeholderText: root.t("Canonical model/provider keresés…", "Search canonical model/provider records…")
                        text: root.searchText
                        onTextChanged: root.searchText = text
                    }
                    Repeater {
                        model: root.modelRecords()
                        delegate: Card {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 20
                            Layout.rightMargin: 20
                            Layout.preferredHeight: 88
                            ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 4
                                Label { Layout.fillWidth: true; text: modelData.id; font.bold: true; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: modelData.title; color: root.textMuted; elide: Text.ElideRight }
                                Label { text: modelData.status || "UNKNOWN"; color: root.accent }
                            }
                        }
                    }
                    Item { Layout.preferredHeight: 20 }
                }
            }

            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item { Layout.preferredHeight: 8 }
                    Label { Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; text: root.t("Telepített modellek", "Installed Models"); font.pixelSize: root.px(22); font.bold: true }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        Layout.preferredHeight: 150
                        ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 7
                            Label { text: "Provider inventory adapters"; font.bold: true }
                            Label { Layout.fillWidth: true; text: "Stability Matrix · Hugging Face · LM Studio · Ollama"; color: root.textMuted; wrapMode: Text.WordWrap }
                            Label { Layout.fillWidth: true; text: root.t("A current-host tényleges modell-lista csak adapter/runtime evidence alapján jelenhet meg.", "The real current-host model list may appear only from adapter/runtime evidence."); wrapMode: Text.WordWrap }
                        }
                    }
                }
            }

            RecordListPage {
                title: "Providers"
                subtitle: root.t("Canonical model provider projection", "Canonical model provider projection")
                records: root.providerRecords()
            }

            StarterModelsPage {
                repository: root.repository
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }

            HuggingFaceModelPanel {
                repository: root.repository
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }

            CivitaiPanel {
                repository: root.repository
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }

            OpenModelDbPanel {
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }

            LlmfitPanel {
                client: llmfitClient
                textMuted: root.textMuted
                accent: root.accent
                surface1: root.surface1
            }

            RemoteAiHubPanel {
                textMuted: root.textMuted
                accent: root.accent
                surface1: root.surface1
            }

            RecordListPage {
                title: "Runtime"
                subtitle: root.t("Loaded instance, runtime projection és serving állapot", "Loaded instance, runtime projection and serving state")
                records: root.repository.searchRecords("runtime model")
            }

            RecordListPage {
                title: "Storage"
                subtitle: root.t("Source cache, canonical artifact store és runtime projection store külön síkok.", "Source cache, canonical artifact store and runtime projection store are separate planes.")
                records: root.repository.searchRecords("model storage")
            }

            RecordListPage {
                title: "Security"
                subtitle: root.t("Hash, provenance, artifact admission és scan state", "Hash, provenance, artifact admission and scan state")
                records: root.repository.searchRecords("MODEL-ARTIFACT-SECURITY")
            }

            RecordListPage {
                title: "Downloads"
                subtitle: root.t("Acquisition/import queue provider adapterből; floating latest production admission tiltott.", "Acquisition/import queue from provider adapters; floating-latest production admission is forbidden.")
                records: root.repository.searchRecords("acquisition")
            }

            RecordListPage {
                title: "Evidence"
                subtitle: root.t("Model Manager canonical, runtime és security evidence rekordok", "Model Manager canonical, runtime and security evidence records")
                records: root.repository.searchRecords("MODEL-MANAGER")
            }
        }
    }
}
