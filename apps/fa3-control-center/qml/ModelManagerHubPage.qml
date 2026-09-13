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
    function t(hu, en) {
        return language === "en" ? en : hu
    }
    function px(v) {
        return Math.max(9, Math.round(v * fontScale))
    }
    function managerRecords() {
        return repository.searchRecords("FA3-MODEL-MANAGER")
    }
    function modelRecords() {
        return repository.searchRecords(searchText.trim().length ? searchText : "MODEL")
    }
    function providerRecords() {
        return repository.recordsByCategory("provider")
    }
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
        Label {
            text: parent.title
            font.pixelSize: root.px(22)
            font.bold: true
        }
        Label {
            Layout.fillWidth: true
            text: parent.subtitle
            color: root.textMuted
            wrapMode: Text.WordWrap
        }
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
                        Label {
                            Layout.fillWidth: true
                            text: modelData.id
                            font.bold: true
                            color: root.accent
                            elide: Text.ElideMiddle
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData.title
                            color: root.textPrimary
                            elide: Text.ElideRight
                        }
                        Label {
                            Layout.fillWidth: true
                            text: (modelData.status || "UNKNOWN") + " · " + (modelData.category || "record")
                            color: root.textMuted
                        }
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
                    Label {
                        text: "MODEL MANAGER"
                        color: root.accent
                        font.pixelSize: root.px(11)
                        font.bold: true
                        font.letterSpacing: 1.2
                    }
                    Label {
                        text: root.t("Modell control plane", "Model control plane")
                        font.pixelSize: root.px(23)
                        font.bold: true
                    }
                    Label {
                        text: root.t("Inventory · acquisition · fit · provider · security · evidence", "Inventory · acquisition · fit · provider · security · evidence")
                        color: root.textMuted
                    }
                }
                Label {
                    text: "143 CAPABILITIES"
                    color: root.textMuted
                    font.pixelSize: root.px(9)
                }
                Label {
                    text: "GATED"
                    color: root.accent
                    font.bold: true
                }
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
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Inventory"
                        subtitle: root.t("Canonical model identity és fizikai inventory külön kezelve.", "Canonical model identity and physical inventory remain separate.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        spacing: 10
                        Card {
                            width: 240
                            height: 100
                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 4
                                Label {
                                    text: "Canonical profile"
                                    color: root.textMuted
                                }
                                Label {
                                    text: root.managerRecords().length ? "FOUND" : "MISSING"
                                    font.pixelSize: root.px(20)
                                    font.bold: true
                                    color: root.accent
                                }
                                Label {
                                    text: "FA3-MODEL-MANAGER-001"
                                    color: root.textMuted
                                }
                            }
                        }
                        Card {
                            width: 240
                            height: 100
                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 4
                                Label {
                                    text: "Providers"
                                    color: root.textMuted
                                }
                                Label {
                                    text: root.providerRecords().length.toString()
                                    font.pixelSize: root.px(20)
                                    font.bold: true
                                }
                                Label {
                                    text: "registered provider records"
                                    color: root.textMuted
                                }
                            }
                        }
                        Card {
                            width: 240
                            height: 100
                            Column {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 4
                                Label {
                                    text: "Mutation"
                                    color: root.textMuted
                                }
                                Label {
                                    text: "GATED"
                                    font.pixelSize: root.px(20)
                                    font.bold: true
                                    color: root.accent
                                }
                                Label {
                                    text: "ChangeSet → authority → evidence"
                                    color: root.textMuted
                                }
                            }
                        }
                    }
                    TextField {
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        placeholderText: root.t("Model/provider keresés…", "Search model/provider records…")
                        text: root.searchText
                        onTextChanged: root.searchText = text
                    }
                    RecordList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        records: root.modelRecords()
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: root.t("Telepített modellek", "Installed Models")
                        subtitle: root.t("A tényleges current-host lista csak adapter/runtime evidence-ből származhat.", "The actual current-host list may only come from adapter/runtime evidence.")
                    }
                    RecordList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        records: root.repository.searchRecords("MODEL")
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Providers"
                        subtitle: root.t("Canonical provider projection", "Canonical provider projection")
                    }
                    RecordList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        records: root.providerRecords()
                    }
                }
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
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Hugging Face"
                        subtitle: root.t("Model-store/provider kezelési projekció. A weboldal gyors elérése a felső MODEL SOURCES sávban marad.", "Model-store/provider management projection. Website access remains in the top MODEL SOURCES strip.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        Layout.preferredHeight: 120
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            Label {
                                text: "FA3-PROVIDER-HF-MODEL-STORE-001"
                                color: root.accent
                                font.bold: true
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: root.t("Upstream/cache provider, revision- és artifact-identitással. A Remote AI Hub külön aloldal.", "Upstream/cache provider with revision and artifact identity. Remote AI Hub is a separate subpage.")
                                color: root.textMuted
                            }
                        }
                    }
                    RecordList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        records: root.hfRecords()
                    }
                }
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
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Runtime"
                        subtitle: "Ollama · LM Studio · ComfyUI · InvokeAI"
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Compatibility"
                        subtitle: root.t("Runtime/backend/hardware fit csak evidence alapján.", "Runtime/backend/hardware fit only from evidence.")
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Storage"
                        subtitle: root.t("Source cache · artifact store · runtime projection store", "Source cache · artifact store · runtime projection store")
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Security"
                        subtitle: root.t("Hash · provenance · licence · Model Artifact Security admission", "Hash · provenance · license · Model Artifact Security admission")
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Duplicates"
                        subtitle: root.t("Dedup-jelölt nem jelent automatikus törlést.", "A dedup candidate never implies automatic deletion.")
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Downloads"
                        subtitle: root.t("Staged/gated acquisition queue", "Staged/gated acquisition queue")
                    }
                }
            }
            ScrollView {
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 14
                    Item {
                        Layout.preferredHeight: 12
                    }
                    SectionHeading {
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        title: "Evidence"
                        subtitle: root.t("Model Manager canonical/runtime/security evidence", "Model Manager canonical/runtime/security evidence")
                    }
                    RecordList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 20
                        Layout.rightMargin: 20
                        records: root.repository.searchRecords("MODEL-MANAGER")
                    }
                }
            }
        }
    }
}
