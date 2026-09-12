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

    function px(value) {
        return Math.max(9, Math.round(value * fontScale))
    }

    function managerRecords() {
        return repository.searchRecords("FA3-MODEL-MANAGER")
    }

    function modelRecords() {
        const query = searchText.trim().length > 0 ? searchText : "MODEL"
        return repository.searchRecords(query)
    }

    function providerRecords() {
        const all = repository.recordsByCategory("provider")
        const out = []
        for (let i = 0; i < all.length; ++i) {
            const text = (all[i].id + " " + all[i].title).toLowerCase()
            if (text.indexOf("model") >= 0 || text.indexOf("ollama") >= 0 || text.indexOf("lm-studio") >= 0 || text.indexOf("hugging") >= 0 || text.indexOf("stability") >= 0)
                out.push(all[i])
        }
        return out
    }

    component Card: Rectangle {
        radius: Math.round(12 * root.uiScale)
        color: root.surface1
        border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
    }

    component TitleBlock: Column {
        property string title: ""
        property string subtitle: ""
        spacing: 4
        Label {
            text: parent.title
            font.pixelSize: root.px(24)
            font.bold: true
        }
        Label {
            width: parent.width
            text: parent.subtitle
            color: root.textMuted
            font.pixelSize: root.px(13)
            wrapMode: Text.WordWrap
        }
    }

    component StateCard: Card {
        property string title: ""
        property string value: ""
        property string note: ""
        implicitWidth: Math.round(230 * root.uiScale)
        implicitHeight: Math.round(108 * root.uiScale)
        Column {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 6
            Label { text: parent.parent.title; color: root.textMuted; font.pixelSize: root.px(11) }
            Label { text: parent.parent.value; font.pixelSize: root.px(21); font.bold: true; width: parent.width; elide: Text.ElideRight }
            Label { text: parent.parent.note; color: root.textMuted; font.pixelSize: root.px(10); width: parent.width; elide: Text.ElideRight }
        }
    }

    component RecordList: ScrollView {
        id: recordList
        property var records: []
        property string emptyText: root.t("Nincs megjeleníthető rekord.", "No records to display.")
        contentWidth: availableWidth
        ColumnLayout {
            width: recordList.availableWidth
            spacing: 10
            Repeater {
                model: recordList.records
                delegate: Card {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 82
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: modelData.id; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: modelData.title; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideRight }
                        }
                        Label { text: modelData.category.toUpperCase(); color: root.textMuted; font.pixelSize: root.px(10) }
                        Label { text: modelData.status || "UNKNOWN"; color: root.accent; font.bold: true }
                        Button { text: root.t("Megnyitás", "Open"); onClicked: root.repository.openLocalPath(modelData.path) }
                    }
                }
            }
            Label {
                visible: recordList.records.length === 0
                text: recordList.emptyText
                color: root.textMuted
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: Math.round(230 * root.uiScale)
            Layout.fillHeight: true
            color: root.surface1
            border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.08)
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8
                Label { text: "Model Manager"; font.pixelSize: root.px(18); font.bold: true }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    model: root.sections
                    delegate: ItemDelegate {
                        required property int index
                        required property var modelData
                        width: ListView.view.width
                        height: Math.round(42 * root.uiScale)
                        highlighted: index === root.sectionIndex
                        text: modelData[1]
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
                id: inventoryView
                contentWidth: availableWidth
                ColumnLayout {
                    width: inventoryView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "Model Inventory"
                        subtitle: root.t("A canonical Model Manager elsődleges GUI-ja. A logikai model identity különválik a fizikai storage path-tól.", "Primary GUI for the canonical Model Manager. Logical model identity remains separate from physical storage paths.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        StateCard { title: "Canonical profile"; value: root.managerRecords().length > 0 ? "FOUND" : "MISSING"; note: "FA3-MODEL-MANAGER-001" }
                        StateCard { title: "Providers"; value: root.providerRecords().length.toString(); note: "model-related canonical providers" }
                        StateCard { title: "Identity chain"; value: "5 layers"; note: "Family → Revision → Variant → Artifact → Runtime" }
                        StateCard { title: "Mutation"; value: "GATED"; note: "move/delete/relink needs authorization" }
                    }
                    TextField {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        placeholderText: root.t("Canonical model/provider keresés…", "Search canonical model/provider records…")
                        text: root.searchText
                        onTextChanged: root.searchText = text
                    }
                    RecordList {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        records: root.modelRecords()
                    }
                }
            }

            ScrollView {
                id: installedView
                contentWidth: availableWidth
                ColumnLayout {
                    width: installedView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Telepített modellek", "Installed Models")
                        subtitle: root.t("A fizikai inventory provider-adapterekből érkezik; a GUI nem következtet modell-identitást pusztán elérési útból.", "Physical inventory comes from provider adapters; the GUI never infers model identity from paths alone.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: 160
                        Column {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Label { text: "Provider inventory adapters"; font.bold: true; font.pixelSize: root.px(16) }
                            Label { text: "Stability Matrix · Hugging Face · LM Studio · Ollama"; color: root.textMuted }
                            Label { text: root.t("A current-host tényleges modell-lista csak adapter/runtime evidence alapján jelenhet meg.", "The real current-host model list may appear only from adapter/runtime evidence."); wrapMode: Text.WordWrap; width: parent.width }
                        }
                    }
                }
            }

            ScrollView {
                id: providersView
                contentWidth: availableWidth
                ColumnLayout {
                    width: providersView.availableWidth
                    spacing: 12
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Providers"; subtitle: root.t("Canonical provider projection", "Canonical provider projection") }
                    RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; records: root.providerRecords() }
                }
            }

            ScrollView {
                id: runtimeView
                contentWidth: availableWidth
                ColumnLayout {
                    width: runtimeView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Runtime"; subtitle: root.t("Loaded instance, runtime projection és serving állapot", "Loaded instance, runtime projection and serving state") }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        StateCard { title: "Ollama"; value: "ADAPTER"; note: "runtime-native model store" }
                        StateCard { title: "LM Studio"; value: "ADAPTER"; note: "interactive LLM runtime" }
                        StateCard { title: "Comfy / Invoke"; value: "PROJECTION"; note: "media model residency" }
                    }
                }
            }

            ScrollView {
                id: compatibilityView
                contentWidth: availableWidth
                ColumnLayout {
                    width: compatibilityView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Compatibility"; subtitle: root.t("Runtime/backend/hardware kompatibilitás evidence alapján, nem becslésből.", "Runtime/backend/hardware compatibility from evidence, not guesswork.") }
                    StateCard { Layout.leftMargin: 24; title: "Policy"; value: "EVIDENCE REQUIRED"; note: "unknown until evidenced" }
                }
            }

            ScrollView {
                id: storageView
                contentWidth: availableWidth
                ColumnLayout {
                    width: storageView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Storage"; subtitle: root.t("Source cache, canonical artifact store és runtime projection store külön síkok.", "Source cache, canonical artifact store and runtime projection store are separate planes.") }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        StateCard { title: "Source cache"; value: "CONTENT ADDRESSED"; note: "upstream acquisition" }
                        StateCard { title: "Artifact store"; value: "POLICY BOUND"; note: "canonical identity" }
                        StateCard { title: "Runtime store"; value: "PROVIDER NATIVE"; note: "or verified shared projection" }
                    }
                }
            }

            ScrollView {
                id: securityView
                contentWidth: availableWidth
                ColumnLayout {
                    width: securityView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Security"; subtitle: root.t("Hash, provenance, artifact admission és scan state", "Hash, provenance, artifact admission and scan state") }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        StateCard { title: "Content identity"; value: "HASH REQUIRED"; note: "artifact identity" }
                        StateCard { title: "Promotion"; value: "SECURITY ADMITTED"; note: "required before production" }
                        StateCard { title: "Direct download bypass"; value: "FORBIDDEN"; note: "all acquisition paths mediated" }
                    }
                }
            }

            ScrollView {
                id: duplicateView
                contentWidth: availableWidth
                ColumnLayout {
                    width: duplicateView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Duplicates"; subtitle: root.t("Inventory dedup candidate ≠ fizikai törlés. Hash/format/compatibility/rollback evidence szükséges.", "Inventory dedup candidate ≠ physical deletion. Hash/format/compatibility/rollback evidence is required.") }
                }
            }

            ScrollView {
                id: downloadsView
                contentWidth: availableWidth
                ColumnLayout {
                    width: downloadsView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Downloads"; subtitle: root.t("Acquisition/import queue provider adapterből; floating latest production admission tiltott.", "Acquisition/import queue from provider adapters; floating-latest production admission is forbidden.") }
                }
            }

            ScrollView {
                id: evidenceView
                contentWidth: availableWidth
                ColumnLayout {
                    width: evidenceView.availableWidth
                    spacing: 12
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Evidence"; subtitle: root.t("Model Manager canonical, runtime és security evidence rekordok", "Model Manager canonical, runtime and security evidence records") }
                    RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; records: root.repository.searchRecords("MODEL-MANAGER") }
                }
            }
        }
    }
}
