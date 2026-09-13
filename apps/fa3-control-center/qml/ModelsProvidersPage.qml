import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property color surface0: palette.window
    property color surface1: palette.base
    property color surface2: palette.alternateBase
    property color accent: palette.highlight
    property color textPrimary: palette.windowText
    property color textMuted: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.62)
    property var selectedModel: null
    property string selectedTagId: ""

    color: surface0

    function lowered(value) {
        return (value || "").toString().toLowerCase()
    }

    function tagsText(tags) {
        if (!tags || tags.length === 0)
            return "No OpenModelDB tags"
        var parts = []
        for (var i = 0; i < tags.length && i < 4; ++i) {
            var tag = tags[i]
            parts.push((tag.category ? tag.category + ": " : "") + tag.name)
        }
        if (tags.length > 4)
            parts.push("+" + (tags.length - 4))
        return parts.join("  ·  ")
    }

    function resourceMatches(resource) {
        if (scaleFilter.currentText !== "All" && resource.scale_label !== scaleFilter.currentText)
            return false
        if (architectureFilter.currentText !== "All"
                && lowered(resource.architecture) !== lowered(architectureFilter.currentText))
            return false
        if (platformFilter.currentText !== "All"
                && lowered(resource.platform) !== lowered(platformFilter.currentText))
            return false
        return true
    }

    function modelMatches(model) {
        var query = lowered(modelSearch.text)
        if (query.length > 0) {
            var haystack = lowered(model.name) + " " + lowered(model.author) + " " + lowered(model.description)
            var tagList = model.tags || []
            for (var t = 0; t < tagList.length; ++t)
                haystack += " " + lowered(tagList[t].name) + " " + lowered(tagList[t].category)
            if (haystack.indexOf(query) < 0)
                return false
        }

        if (selectedTagId.length > 0) {
            var tagHit = false
            var tags = model.tags || []
            for (var i = 0; i < tags.length; ++i) {
                if (tags[i].id === selectedTagId) {
                    tagHit = true
                    break
                }
            }
            if (!tagHit)
                return false
        }

        if (scaleFilter.currentText === "All"
                && architectureFilter.currentText === "All"
                && platformFilter.currentText === "All")
            return true

        var resources = model.resources || []
        for (var r = 0; r < resources.length; ++r) {
            if (resourceMatches(resources[r]))
                return true
        }
        return false
    }

    property var filteredModels: {
        var source = fa3OpenModelDb.models
        var result = []
        for (var i = 0; i < source.length; ++i) {
            if (modelMatches(source[i]))
                result.push(source[i])
        }
        return result
    }

    property var tagOptions: {
        var result = [{id: "", label: "All tags"}]
        var source = fa3OpenModelDb.tags
        for (var i = 0; i < source.length; ++i) {
            result.push({
                id: source[i].id,
                label: (source[i].category ? source[i].category + " · " : "") + source[i].name
            })
        }
        return result
    }

    Component.onCompleted: {
        if (fa3OpenModelDb.models.length === 0)
            fa3OpenModelDb.refreshCatalog()
    }

    Connections {
        target: fa3OpenModelDb
        function onModelsChanged() {
            if (!root.selectedModel && fa3OpenModelDb.models.length > 0)
                root.selectedModel = fa3OpenModelDb.models[0]
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "Models & Providers"; font.pixelSize: 24; font.bold: true }
                Label {
                    text: "OpenModelDB catalog + FA3 staged download manager. Tags remain upstream metadata; runtime compatibility still requires evidence."
                    color: root.textMuted
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                }
            }
            Label {
                text: fa3OpenModelDb.catalogStatus
                color: fa3OpenModelDb.catalogStatus.indexOf("ERROR") === 0 ? "#d94f4f" : root.textMuted
                font.pixelSize: 11
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Label { text: "Model sources"; font.bold: true; color: root.textMuted }
            Button {
                text: "Hugging Face ↗"
                ToolTip.visible: hovered
                ToolTip.text: "Open Hugging Face models"
                onClicked: fa3OpenModelDb.openExternalUrl("https://huggingface.co/models")
            }
            Button {
                text: "★ OpenModelDB ↗"
                highlighted: true
                font.bold: true
                ToolTip.visible: hovered
                ToolTip.text: "Open the OpenModelDB website"
                onClicked: fa3OpenModelDb.openExternalUrl("https://openmodeldb.info/")
            }
            Item { Layout.fillWidth: true }
            Button {
                text: "Staging folder"
                onClicked: fa3OpenModelDb.openStagingFolder()
            }
            Button {
                text: fa3OpenModelDb.catalogBusy ? "Refreshing…" : "Refresh catalog"
                enabled: !fa3OpenModelDb.catalogBusy
                onClicked: fa3OpenModelDb.refreshCatalog()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            TextField {
                id: modelSearch
                Layout.fillWidth: true
                placeholderText: "Search model, author, description or OpenModelDB tag…"
                clearButtonEnabled: true
            }
            ComboBox {
                id: scaleFilter
                Layout.preferredWidth: 115
                model: ["All"].concat(fa3OpenModelDb.scales)
                ToolTip.visible: hovered
                ToolTip.text: "Scale"
            }
            ComboBox {
                id: architectureFilter
                Layout.preferredWidth: 160
                model: ["All"].concat(fa3OpenModelDb.architectures)
                ToolTip.visible: hovered
                ToolTip.text: "Architecture"
            }
            ComboBox {
                id: platformFilter
                Layout.preferredWidth: 150
                model: ["All"].concat(fa3OpenModelDb.platforms)
                ToolTip.visible: hovered
                ToolTip.text: "Platform"
            }
            ComboBox {
                id: tagFilter
                Layout.preferredWidth: 250
                model: root.tagOptions
                textRole: "label"
                onActivated: root.selectedTagId = model[index].id || ""
                ToolTip.visible: hovered
                ToolTip.text: "OpenModelDB compatibility / use-case tag"
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Rectangle {
                SplitView.preferredWidth: 560
                SplitView.minimumWidth: 390
                color: root.surface1
                radius: 10
                border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "OpenModelDB catalog"; font.bold: true; font.pixelSize: 15 }
                        Item { Layout.fillWidth: true }
                        Label { text: root.filteredModels.length + " model"; color: root.textMuted }
                    }
                    ListView {
                        id: modelList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: root.filteredModels
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 86
                            radius: 8
                            color: root.selectedModel && root.selectedModel.id === modelData.id
                                   ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.16)
                                   : root.surface2
                            border.color: root.selectedModel && root.selectedModel.id === modelData.id
                                          ? root.accent
                                          : Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.07)
                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.selectedModel = parent.modelData
                            }
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.name; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.license; color: modelData.license === "UNKNOWN" ? "#d99b32" : root.textMuted; font.pixelSize: 10 }
                                }
                                Label { text: modelData.author; color: root.textMuted; font.pixelSize: 11 }
                                Label {
                                    text: root.tagsText(modelData.tags)
                                    color: root.textMuted
                                    font.pixelSize: 10
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                Label { text: modelData.resources.length + " resource"; color: root.accent; font.pixelSize: 10 }
                            }
                        }
                    }
                }
            }

            Rectangle {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 430
                color: root.surface1
                radius: 10
                border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 12
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: 10

                        Label {
                            text: root.selectedModel ? root.selectedModel.name : "Select an OpenModelDB model"
                            font.pixelSize: 20
                            font.bold: true
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }
                        RowLayout {
                            visible: root.selectedModel !== null
                            Layout.fillWidth: true
                            Label { text: root.selectedModel ? root.selectedModel.author : ""; color: root.textMuted }
                            Label { text: "•"; color: root.textMuted }
                            Label {
                                text: root.selectedModel ? root.selectedModel.license : ""
                                color: root.selectedModel && root.selectedModel.license === "UNKNOWN" ? "#d99b32" : root.textMuted
                            }
                            Item { Layout.fillWidth: true }
                            Button {
                                text: "Model page ↗"
                                enabled: root.selectedModel !== null
                                onClicked: fa3OpenModelDb.openExternalUrl(root.selectedModel.model_url)
                            }
                        }

                        Label {
                            visible: root.selectedModel !== null
                            text: root.selectedModel ? root.selectedModel.description : ""
                            color: root.textMuted
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                        }

                        Label { visible: root.selectedModel !== null; text: "OpenModelDB tags"; font.bold: true }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: root.selectedModel !== null
                            Repeater {
                                model: root.selectedModel ? root.selectedModel.tags : []
                                delegate: Rectangle {
                                    required property var modelData
                                    height: 26
                                    width: tagLabel.implicitWidth + 18
                                    radius: 13
                                    color: root.surface2
                                    border.width: 1
                                    border.color: modelData.color && modelData.color.length > 0 ? modelData.color : root.accent
                                    Label {
                                        id: tagLabel
                                        anchors.centerIn: parent
                                        text: (modelData.category ? modelData.category + ": " : "") + modelData.name
                                        font.pixelSize: 10
                                    }
                                }
                            }
                        }
                        Label {
                            visible: root.selectedModel !== null
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: root.textMuted
                            font.pixelSize: 10
                            text: "The tags above are shown exactly as discovery metadata from OpenModelDB. They help choose a model, but do not by themselves constitute FA3 runtime-conformance evidence."
                        }

                        Rectangle {
                            visible: root.selectedModel !== null
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)
                        }

                        Label { visible: root.selectedModel !== null; text: "Resource / build"; font.bold: true }
                        ComboBox {
                            id: resourcePicker
                            visible: root.selectedModel !== null
                            Layout.fillWidth: true
                            model: root.selectedModel ? root.selectedModel.resources : []
                            textRole: "label"
                        }
                        GridLayout {
                            visible: root.selectedModel !== null && resourcePicker.currentIndex >= 0
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 12
                            rowSpacing: 4
                            Label { text: "Platform"; color: root.textMuted }
                            Label { text: resourcePicker.currentIndex >= 0 ? resourcePicker.model[resourcePicker.currentIndex].platform : "" }
                            Label { text: "Architecture"; color: root.textMuted }
                            Label { text: resourcePicker.currentIndex >= 0 ? resourcePicker.model[resourcePicker.currentIndex].architecture : "" }
                            Label { text: "Format"; color: root.textMuted }
                            Label { text: resourcePicker.currentIndex >= 0 ? resourcePicker.model[resourcePicker.currentIndex].format : "" }
                            Label { text: "Scale"; color: root.textMuted }
                            Label { text: resourcePicker.currentIndex >= 0 ? resourcePicker.model[resourcePicker.currentIndex].scale_label : "" }
                            Label { text: "SHA-256"; color: root.textMuted }
                            Label {
                                text: resourcePicker.currentIndex >= 0 ? resourcePicker.model[resourcePicker.currentIndex].sha256 : ""
                                font.family: "monospace"
                                elide: Text.ElideMiddle
                                Layout.fillWidth: true
                            }
                        }
                        RowLayout {
                            visible: root.selectedModel !== null
                            Layout.fillWidth: true
                            Button {
                                text: "Download to FA3 staging"
                                highlighted: true
                                enabled: resourcePicker.currentIndex >= 0
                                onClicked: {
                                    var resource = resourcePicker.model[resourcePicker.currentIndex]
                                    fa3OpenModelDb.queueDownload(root.selectedModel.id,
                                                                 root.selectedModel.name,
                                                                 root.selectedModel.license,
                                                                 resource)
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                color: root.textMuted
                                font.pixelSize: 10
                                text: "Download → SHA-256 verify → staging → Model Artifact Security → runtime evidence → promotion"
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 205
            color: root.surface1
            radius: 10
            border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.10)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 5
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Download manager"; font.bold: true; font.pixelSize: 15 }
                    Label { text: "Stability Matrix style queue · one mediated transfer at a time"; color: root.textMuted; font.pixelSize: 10 }
                    Item { Layout.fillWidth: true }
                    Label { text: fa3OpenModelDb.stagingRoot; color: root.textMuted; font.pixelSize: 10; elide: Text.ElideMiddle; Layout.preferredWidth: 410 }
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 3
                    model: fa3OpenModelDb.downloads
                    delegate: Rectangle {
                        required property var modelData
                        width: ListView.view.width
                        height: 68
                        radius: 7
                        color: root.surface2
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 10
                            ColumnLayout {
                                Layout.preferredWidth: 250
                                Label { text: modelData.model_name; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Label { text: modelData.filename; color: root.textMuted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideMiddle }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Label {
                                    text: modelData.status
                                    color: modelData.status.indexOf("BLOCKED") === 0 || modelData.status.indexOf("FAILED") === 0 ? "#d94f4f"
                                           : modelData.status.indexOf("VERIFIED") === 0 ? root.accent : root.textMuted
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                                ProgressBar {
                                    Layout.fillWidth: true
                                    from: 0
                                    to: 1
                                    value: modelData.progress || 0
                                    indeterminate: modelData.status === "DOWNLOADING" && (!modelData.bytes_total || modelData.bytes_total <= 0)
                                }
                                Label { text: modelData.detail || ""; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                            Button {
                                text: "Cancel"
                                visible: modelData.status === "QUEUED" || modelData.status === "DOWNLOADING"
                                onClicked: fa3OpenModelDb.cancelDownload(modelData.id)
                            }
                            Button {
                                text: "Retry"
                                visible: modelData.status === "CANCELLED" || modelData.status.indexOf("FAILED") === 0 || modelData.status.indexOf("BLOCKED_CHECKSUM") === 0
                                onClicked: fa3OpenModelDb.retryDownload(modelData.id)
                            }
                        }
                    }
                }
            }
        }
    }
}
