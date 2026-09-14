import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: root

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    property string selectedCategory: "all"
    property var selectedItem: ({})
    property string draggedModelUrl: ""
    property string pendingClientKey: ""
    property string statusText: ""
    property bool statusFailed: false

    signal openWebRequested(url targetUrl, string titleText)

    property var categories: [
        {key: "all", title: "All Models"},
        {key: "checkpoints", title: "Checkpoints"},
        {key: "loras", title: "LoRA"},
        {key: "vae", title: "VAE"},
        {key: "embeddings", title: "Embeddings"},
        {key: "controlnet", title: "ControlNet"},
        {key: "clip", title: "CLIP"},
        {key: "unet", title: "UNet"},
        {key: "diffusion_models", title: "Diffusion / Video"},
        {key: "upscale_models", title: "Upscalers"},
        {key: "other", title: "Other"}
    ]

    function showStatus(message, failed) {
        statusText = message
        statusFailed = failed
        statusTimer.restart()
    }

    function countFor(category) {
        var rows = fa3ModelLibrary.items
        if (category === "all") return rows.length
        var count = 0
        for (var i = 0; i < rows.length; ++i)
            if (rows[i].category === category) ++count
        return count
    }

    function filteredModels() {
        var rows = fa3ModelLibrary.items
        var needle = modelSearch.text.trim().toLowerCase()
        var out = []
        for (var i = 0; i < rows.length; ++i) {
            var item = rows[i]
            if (root.selectedCategory !== "all" && item.category !== root.selectedCategory) continue
            var haystack = (item.name + " " + item.fileName + " " + item.categoryLabel + " " + item.baseModel + " " + item.triggerWords).toLowerCase()
            if (needle.length === 0 || haystack.indexOf(needle) >= 0) out.push(item)
        }
        return out
    }

    function selectItem(item) {
        selectedItem = item
        metadataName.text = item.name || ""
        metadataBaseModel.text = item.baseModel || ""
        metadataTriggerWords.text = item.triggerWords || ""
        metadataSource.text = item.sourceUrl || ""
        metadataNotes.text = item.notes || ""
    }

    function categoryIndex(category) {
        for (var i = 0; i < categories.length; ++i)
            if (categories[i].key === category) return i
        return 1
    }

    Timer {
        id: statusTimer
        interval: 6500
        repeat: false
        onTriggered: root.statusText = ""
    }

    FolderDialog {
        id: sharedRootDialog
        title: "Shared Storage mappa kiválasztása"
        onAccepted: {
            var r = fa3ModelLibrary.setSharedRoot(selectedFolder)
            root.showStatus(r.message, !r.ok)
        }
    }

    FolderDialog {
        id: clientRootDialog
        title: "AI felület model mappájának kiválasztása"
        onAccepted: {
            var r = fa3ModelLibrary.setClientRoot(root.pendingClientKey, selectedFolder)
            root.showStatus(r.message, !r.ok)
        }
    }

    FileDialog {
        id: importDialog
        title: "Modellek importálása a Shared Storage-ba"
        fileMode: FileDialog.OpenFiles
        nameFilters: ["AI modellek (*.safetensors *.ckpt *.pt *.pth *.bin *.gguf *.onnx)", "Minden fájl (*)"]
        onAccepted: {
            var category = root.selectedCategory === "all" ? "checkpoints" : root.selectedCategory
            var r = fa3ModelLibrary.importFiles(selectedFiles, category)
            root.showStatus(r.message, !r.ok)
        }
    }

    FileDialog {
        id: previewDialog
        title: "Előnézeti kép kiválasztása"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Képek (*.png *.jpg *.jpeg *.webp)"]
        onAccepted: {
            if (!root.selectedItem.fileUrl) return
            var r = fa3ModelLibrary.setPreview(root.selectedItem.fileUrl, selectedFile)
            root.showStatus(r.message, !r.ok)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "Checkpoint Manager"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    text: "Központi checkpoint / LoRA / VAE / diffusion-model könyvtár, megosztva a képi és videós AI felületek között."
                    color: root.textMuted
                    font.pixelSize: 10
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
            }
            Rectangle {
                radius: 12
                color: "#102a43"
                border.color: root.border
                implicitWidth: 126
                implicitHeight: 26
                Label { anchors.centerIn: parent; text: "SHARED STORAGE"; color: root.accent; font.pixelSize: 8; font.bold: true }
            }
            HelpBubble {
                helpText: "A Shared Storage egyetlen fizikai példányban tartja a modelleket. Az egyes AI felületek saját model mappái szimbolikus linkekkel mutathatnak ide, ezért ugyanazt a több GB-os modellt nem kell minden alkalmazáshoz külön lemásolni."
                bubbleText: root.textPrimary
                bubbleBorder: root.border
            }
            Button { text: "Frissítés"; onClicked: fa3ModelLibrary.refresh() }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: 7
            color: root.panel
            border.color: root.border
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8
                Label { text: "Shared Storage"; color: root.textMuted; font.pixelSize: 9 }
                Label { text: fa3ModelLibrary.sharedRoot; color: root.textPrimary; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideMiddle }
                Button { text: "Mappa…"; onClicked: sharedRootDialog.open() }
                Button { text: "Megnyitás"; onClicked: fa3ModelLibrary.openLocalPath("file://" + fa3ModelLibrary.sharedRoot) }
                Button { text: "＋ Import"; onClicked: importDialog.open() }
            }
        }

        TabBar {
            id: checkpointTabs
            Layout.fillWidth: true
            TabButton { text: "Library" }
            TabButton { text: "Download" }
            TabButton { text: "Shared Apps" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: checkpointTabs.currentIndex

            Item {
                RowLayout {
                    anchors.fill: parent
                    spacing: 10

                    Rectangle {
                        Layout.preferredWidth: 214
                        Layout.fillHeight: true
                        radius: 8
                        color: root.panel
                        border.color: root.border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 4
                            Label { text: "Folders"; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.leftMargin: 6; Layout.bottomMargin: 4 }
                            Repeater {
                                model: root.categories
                                delegate: Item {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 38

                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 6
                                        color: root.selectedCategory === modelData.key ? "#12304d" : (categoryMouse.containsMouse ? root.panelRaised : "transparent")
                                        border.color: categoryDrop.containsDrag ? root.accent : "transparent"
                                        border.width: categoryDrop.containsDrag ? 1 : 0
                                    }
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 8
                                        Label { text: modelData.key === "all" ? "◫" : "▰"; color: root.selectedCategory === modelData.key ? root.accent : root.textMuted }
                                        Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 10; Layout.fillWidth: true }
                                        Label { text: root.countFor(modelData.key); color: root.textMuted; font.pixelSize: 9 }
                                    }
                                    MouseArea {
                                        id: categoryMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.selectedCategory = modelData.key
                                    }
                                    DropArea {
                                        id: categoryDrop
                                        anchors.fill: parent
                                        enabled: modelData.key !== "all"
                                        keys: ["fa3-model"]
                                        onDropped: function(drop) {
                                            if (root.draggedModelUrl.length > 0) {
                                                var r = fa3ModelLibrary.moveModel(root.draggedModelUrl, modelData.key)
                                                root.showStatus(r.message, !r.ok)
                                                root.draggedModelUrl = ""
                                            }
                                            drop.acceptProposedAction()
                                        }
                                    }
                                }
                            }
                            Item { Layout.fillHeight: true }
                            Label {
                                Layout.fillWidth: true
                                text: "Húzd a model kártyát egy másik mappára az átrendezéshez. Külső fájlt a Library területére dobva importálhatsz."
                                color: root.textMuted
                                font.pixelSize: 8
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: root.panel
                        border.color: libraryDrop.containsDrag ? root.accent : root.border
                        border.width: libraryDrop.containsDrag ? 2 : 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                TextField {
                                    id: modelSearch
                                    Layout.fillWidth: true
                                    placeholderText: "Search models…"
                                }
                                Label { text: root.filteredModels().length + " model"; color: root.textMuted; font.pixelSize: 9 }
                            }

                            GridView {
                                id: modelGrid
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                cellWidth: 226
                                cellHeight: 224
                                model: root.filteredModels()
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                                delegate: Item {
                                    id: modelDelegate
                                    required property var modelData
                                    width: modelGrid.cellWidth - 10
                                    height: modelGrid.cellHeight - 10
                                    Drag.active: dragArea.drag.active
                                    Drag.keys: ["fa3-model"]
                                    Drag.hotSpot.x: width / 2
                                    Drag.hotSpot.y: 18
                                    Drag.onActiveChanged: {
                                        if (Drag.active) root.draggedModelUrl = String(modelData.fileUrl)
                                        else if (!dragArea.drag.active) root.draggedModelUrl = ""
                                    }

                                    Rectangle {
                                        anchors.fill: parent
                                        radius: 8
                                        color: root.selectedItem.path === modelData.path ? "#112d49" : root.panelRaised
                                        border.color: root.selectedItem.path === modelData.path ? root.accent : root.border

                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 7
                                            spacing: 5

                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 137
                                                radius: 5
                                                color: "#091624"
                                                clip: true
                                                Image {
                                                    anchors.fill: parent
                                                    anchors.margins: 2
                                                    source: modelData.previewUrl
                                                    fillMode: Image.PreserveAspectCrop
                                                    visible: status === Image.Ready
                                                    asynchronous: true
                                                    cache: false
                                                }
                                                Label {
                                                    anchors.centerIn: parent
                                                    text: modelData.categoryLabel.toUpperCase()
                                                    color: root.textMuted
                                                    font.pixelSize: 11
                                                    font.bold: true
                                                    visible: parent.children[0].status !== Image.Ready
                                                }
                                                Rectangle {
                                                    anchors.left: parent.left
                                                    anchors.bottom: parent.bottom
                                                    anchors.margins: 6
                                                    height: 22
                                                    width: typeLabel.implicitWidth + 14
                                                    radius: 5
                                                    color: "#c0101d2b"
                                                    Label { id: typeLabel; anchors.centerIn: parent; text: modelData.categoryLabel; color: root.textPrimary; font.pixelSize: 8; font.bold: true }
                                                }
                                            }

                                            Label { text: modelData.name; color: root.textPrimary; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                            Label { text: modelData.sizeLabel + " · ." + modelData.extension; color: root.textMuted; font.pixelSize: 8; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                    }

                                    MouseArea {
                                        id: dragArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        drag.target: modelDelegate
                                        drag.axis: Drag.XAndYAxis
                                        onClicked: root.selectItem(modelData)
                                        onReleased: {
                                            modelDelegate.x = 0
                                            modelDelegate.y = 0
                                        }
                                    }
                                }
                            }
                        }

                        DropArea {
                            id: libraryDrop
                            anchors.fill: parent
                            onDropped: function(drop) {
                                if (drop.hasUrls && root.draggedModelUrl.length === 0) {
                                    var category = root.selectedCategory === "all" ? "checkpoints" : root.selectedCategory
                                    var r = fa3ModelLibrary.importFiles(drop.urls, category)
                                    root.showStatus(r.message, !r.ok)
                                    drop.acceptProposedAction()
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: root.selectedItem.path !== undefined && root.selectedItem.path !== ""
                        Layout.preferredWidth: visible ? 310 : 0
                        Layout.fillHeight: true
                        radius: 8
                        color: root.panel
                        border.color: root.border

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 9
                            contentWidth: availableWidth
                            clip: true
                            ColumnLayout {
                                width: parent.width
                                spacing: 8
                                Label { text: "Metadata & Preview"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 150
                                    radius: 6
                                    color: "#091624"
                                    Image { anchors.fill: parent; anchors.margins: 2; source: root.selectedItem.previewUrl || ""; fillMode: Image.PreserveAspectFit; asynchronous: true; cache: false }
                                }
                                Button { text: "Előnézeti kép…"; Layout.fillWidth: true; onClicked: previewDialog.open() }
                                Label { text: "Név"; color: root.textMuted; font.pixelSize: 8 }
                                TextField { id: metadataName; Layout.fillWidth: true }
                                Label { text: "Base model"; color: root.textMuted; font.pixelSize: 8 }
                                TextField { id: metadataBaseModel; Layout.fillWidth: true; placeholderText: "SDXL / Flux / Wan / Hunyuan…" }
                                Label { text: "Trigger words"; color: root.textMuted; font.pixelSize: 8 }
                                TextField { id: metadataTriggerWords; Layout.fillWidth: true }
                                Label { text: "Source URL"; color: root.textMuted; font.pixelSize: 8 }
                                TextField { id: metadataSource; Layout.fillWidth: true; placeholderText: "https://civitai.com/... vagy https://huggingface.co/..." }
                                Label { text: "Jegyzet"; color: root.textMuted; font.pixelSize: 8 }
                                TextArea {
                                    id: metadataNotes
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 90
                                    wrapMode: TextEdit.Wrap
                                    background: Rectangle { radius: 5; color: "#091624"; border.color: root.border }
                                    color: root.textPrimary
                                }
                                Button {
                                    text: "Metaadat mentése"
                                    Layout.fillWidth: true
                                    onClicked: {
                                        var r = fa3ModelLibrary.saveMetadata(root.selectedItem.fileUrl, {
                                            displayName: metadataName.text,
                                            baseModel: metadataBaseModel.text,
                                            triggerWords: metadataTriggerWords.text,
                                            sourceUrl: metadataSource.text,
                                            notes: metadataNotes.text
                                        })
                                        root.showStatus(r.message, !r.ok)
                                    }
                                }
                                Button { text: "Fájl megnyitása"; Layout.fillWidth: true; onClicked: fa3ModelLibrary.openLocalPath(root.selectedItem.fileUrl) }
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Button { text: "CivitAI böngészés"; onClicked: root.openWebRequested("https://civitai.com/models", "CivitAI — Model Browser") }
                        Button { text: "Hugging Face böngészés"; onClicked: root.openWebRequested("https://huggingface.co/models", "Hugging Face — Model Browser") }
                        HelpBubble {
                            helpText: "A böngészés az FA3 izolált beépített webfelületén nyílik meg. Nyilvános közvetlen letöltési URL az alábbi mezőből tölthető a Shared Storage-ba. Token/API key URL-be írása tiltott; hitelesített letöltéshez később SecretRef broker kapcsolódik."
                            bubbleText: root.textPrimary
                            bubbleBorder: root.border
                        }
                        Item { Layout.fillWidth: true }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 330
                        radius: 8
                        color: root.panel
                        border.color: root.border
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            Label { text: "Built-in Model Downloader"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                            Label { text: "CivitAI / Hugging Face / más HTTPS forrás közvetlen modellfájljának letöltése a közös tárhelyre."; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Label { text: "Download URL"; color: root.textMuted; font.pixelSize: 8 }
                            TextField { id: downloadUrl; Layout.fillWidth: true; placeholderText: "https://.../model.safetensors" }
                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Category"; color: root.textMuted; font.pixelSize: 8 }
                                    ComboBox {
                                        id: downloadCategory
                                        Layout.fillWidth: true
                                        model: root.categories.slice(1)
                                        textRole: "title"
                                        valueRole: "key"
                                        currentIndex: 0
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Filename (optional)"; color: root.textMuted; font.pixelSize: 8 }
                                    TextField { id: downloadFileName; Layout.fillWidth: true; placeholderText: "model.safetensors" }
                                }
                            }
                            ProgressBar { Layout.fillWidth: true; from: 0; to: 100; value: fa3ModelLibrary.downloadProgress }
                            Label { text: fa3ModelLibrary.downloadStatus || "Nincs aktív letöltés."; color: fa3ModelLibrary.downloadActive ? root.accent : root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                            RowLayout {
                                Layout.fillWidth: true
                                Button {
                                    text: "Letöltés indítása"
                                    enabled: !fa3ModelLibrary.downloadActive && downloadUrl.text.trim().length > 0
                                    onClicked: {
                                        var r = fa3ModelLibrary.startDownload(downloadUrl.text.trim(), downloadCategory.currentValue, downloadFileName.text.trim())
                                        root.showStatus(r.message, !r.ok)
                                    }
                                }
                                Button { text: "Megszakítás"; enabled: fa3ModelLibrary.downloadActive; onClicked: fa3ModelLibrary.cancelDownload() }
                                Item { Layout.fillWidth: true }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Shared Applications"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                        HelpBubble {
                            helpText: "A Link model folders művelet csak hiányzó vagy üres célmappát alakít szimbolikus linkké. Nem ír felül nem üres alkalmazásmappát. Ha NEEDS MIGRATION látszik, előbb importáld a meglévő modelleket a Shared Storage-ba."
                            bubbleText: root.textPrimary
                            bubbleBorder: root.border
                        }
                        Item { Layout.fillWidth: true }
                        Button { text: "Frissítés"; onClicked: fa3ModelLibrary.refresh() }
                    }
                    Repeater {
                        model: fa3ModelLibrary.clients
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 104
                            radius: 8
                            color: root.panel
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12
                                Rectangle {
                                    width: 42; height: 42; radius: 8
                                    color: "#102a43"
                                    Label { anchors.centerIn: parent; text: "AI"; color: root.accent; font.bold: true }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Label { text: modelData.name; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                                    Label { text: modelData.path.length ? modelData.path : "Nincs beállított model mappa"; color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                    Label { text: modelData.state; color: modelData.state === "LINKED" ? root.green : (modelData.state === "NEEDS MIGRATION" ? root.orange : root.accent); font.pixelSize: 8; font.bold: true }
                                }
                                Button {
                                    text: "Útvonal…"
                                    onClicked: {
                                        root.pendingClientKey = modelData.key
                                        clientRootDialog.open()
                                    }
                                }
                                Button {
                                    text: "Link model folders"
                                    enabled: modelData.path.length > 0
                                    onClicked: {
                                        var r = fa3ModelLibrary.linkClient(modelData.key)
                                        root.showStatus(r.message, !r.ok)
                                    }
                                }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }

        Label {
            visible: root.statusText.length > 0
            Layout.fillWidth: true
            text: root.statusText
            color: root.statusFailed ? root.orange : root.green
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
