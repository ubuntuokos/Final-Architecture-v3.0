import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Item {
    id: root

    property string role: "Mentor"
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    property string viewMode: String(fa3Preferences.value("chat/viewMode", "Standard"))
    property int chatFontSize: Number(fa3Preferences.value("chat/fontSize", 14))
    property string chatFontWeight: String(fa3Preferences.value("chat/fontWeight", "Normal"))
    property bool showGenInfo: Boolean(fa3Preferences.value("chat/showGenInfo", false))
    property bool scrollMessageToTopOnSend: Boolean(fa3Preferences.value("chat/scrollMessageToTopOnSend", true))
    property bool autoLatchGenerating: Boolean(fa3Preferences.value("chat/autoLatchGenerating", true))
    property string messageStyle: String(fa3Preferences.value("chat/messageStyle", "Cards"))
    property bool expandToWindowWidth: Boolean(fa3Preferences.value("chat/expandToWindowWidth", false))
    property string adapterState: "ADAPTER-GATED"
    property string exportText: ""
    property url pendingCopySource: ""
    property string operationStatus: ""
    property bool operationFailed: false
    property string workspaceMode: "ASSISTANT"
    property string requestedMcpTarget: "AUTO"
    property string mcpTarget: requestedMcpTarget
    property string mcpRiskHint: "AUTO"
    property var mcpTargets: fa3McpControl.targets()
    property var mcpAuthority: fa3McpControl.authoritySnapshot(mcpTarget)

    signal closeRequested()
    signal navigateRequested(int pageIndex)
    signal modeChangeRequested(string mode)

    function roleDescription(name) {
        if (name === "Mentor") return "Tanulási, szakmai és megvalósítási iránymutatás."
        if (name === "Coach") return "Célok, fókusz, következő lépések és visszacsatolás."
        if (name === "Manager") return "Feladat-, prioritás-, erőforrás- és projektkoordináció."
        if (name === "Ellenőr") return "Ellenőrzés, bizonyíték, eltérés, kockázat és megfelelőség."
        if (name === "Ötletelő") return "Alternatívák, új ötletek és kreatív irányok generálása."
        if (name === "Tanácsadó") return "Opciók, trade-offok és döntéstámogató elemzés."
        return "FA3 szerepalapú beszélgetési munkatér."
    }


    function isMcpMode() {
        return workspaceMode === "MCP CONTROL" || workspaceMode === "WORKFLOW"
    }

    function workspaceTitle() {
        if (workspaceMode === "MCP CONTROL") return "MCP Control Chat"
        if (workspaceMode === "WORKFLOW") return "MCP Workflow Chat"
        return "Kérdezd: " + role
    }

    function workspaceDescription() {
        if (workspaceMode === "MCP CONTROL") return "Természetes nyelvű, policy-gated alkalmazásvezérlés a központi MCP authority-láncon keresztül."
        if (workspaceMode === "WORKFLOW") return "Több alkalmazáson átívelő terv és artifact-handoff előkészítése; végrehajtás csak admission után."
        return roleDescription(role)
    }

    function indexForTarget(id) {
        for (var i = 0; i < mcpTargets.length; ++i) {
            if (String(mcpTargets[i].id) === id) return i
        }
        return 0
    }

    function showOperationStatus(text, failed) {
        operationStatus = text
        operationFailed = failed
        statusTimer.restart()
    }

    function parseAttachments(value) {
        if (!value || value.length === 0) return []
        try {
            var parsed = JSON.parse(value)
            return Array.isArray(parsed) ? parsed : []
        } catch (e) {
            return []
        }
    }

    function hasAttachment(urlText) {
        for (var i = 0; i < attachmentModel.count; ++i) {
            if (attachmentModel.get(i).url === urlText) return true
        }
        return false
    }

    function addAttachmentUrls(urls) {
        for (var i = 0; i < urls.length; ++i) {
            var meta = fa3ChatFiles.inspectLocalFile(urls[i])
            if (!meta.valid) {
                root.showOperationStatus(meta.error || "A fájl nem csatolható.", true)
                continue
            }
            if (root.hasAttachment(meta.url)) continue
            attachmentModel.append({
                url: String(meta.url),
                path: String(meta.path),
                name: String(meta.name),
                mime: String(meta.mime),
                sizeLabel: String(meta.sizeLabel),
                analysisClass: String(meta.analysisClass),
                adapterValidationRequired: Boolean(meta.adapterValidationRequired)
            })
        }
    }

    function pendingAttachmentsJson() {
        var items = []
        for (var i = 0; i < attachmentModel.count; ++i) {
            var item = attachmentModel.get(i)
            items.push({
                url: item.url,
                path: item.path,
                name: item.name,
                mime: item.mime,
                sizeLabel: item.sizeLabel,
                analysisClass: item.analysisClass,
                adapterValidationRequired: item.adapterValidationRequired
            })
        }
        return JSON.stringify(items)
    }

    function resetSession() {
        attachmentModel.clear()
        composer.clear()
        chatModel.clear()
        if (root.isMcpMode()) {
            chatModel.append({
                kind: "SYSTEM",
                author: "FA3 MCP Control",
                body: root.workspaceTitle() + " megnyitva. Target: " + root.mcpTarget + ". A GUI intent-capture felület; nem execution authority.",
                state: "READY",
                attachmentsJson: "[]"
            })
            chatModel.append({
                kind: "SYSTEM",
                author: "MCP Authority",
                body: "CAPTURE → PLANNER → POLICY → APPROVAL → MCP GATEWAY → TARGET ADAPTER → EVIDENCE. Planner/gateway/app adapter runtime jelenleg nincs hitelesítetten bekötve, ezért végrehajtás fail-closed.",
                state: "ADAPTER-GATED",
                attachmentsJson: "[]"
            })
        } else {
            chatModel.append({
                kind: "SYSTEM",
                author: "FA3",
                body: role + " chat munkatér megnyitva. " + roleDescription(role),
                state: "READY",
                attachmentsJson: "[]"
            })
            chatModel.append({
                kind: "SYSTEM",
                author: "Runtime",
                body: "Nincs hitelesített role-chat provider adapter hozzárendelve. A felület ezért nem állít elő mesterséges választ és nem jelöl hamisan ONLINE állapotot.",
                state: "ADAPTER-GATED",
                attachmentsJson: "[]"
            })
        }
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

    function draftMcpRequest() {
        var text = composer.text.trim()
        if (text.length === 0 && attachmentModel.count === 0) return
        var attachmentJson = root.pendingAttachmentsJson()
        chatModel.append({
            kind: "USER",
            author: "Te",
            body: text.length > 0 ? text : "Csatolmány(ok) hozzáadva az MCP intenthez.",
            state: "MCP-INTENT",
            attachmentsJson: attachmentJson
        })
        var result = fa3McpControl.createDraftRequest(root.workspaceMode, root.mcpTarget, text, attachmentJson, root.mcpRiskHint)
        composer.clear()
        attachmentModel.clear()
        if (result.ok) {
            chatModel.append({
                kind: "SYSTEM",
                author: "MCP Authority",
                body: "Request " + result.requestId + " · target " + result.target + " · " + result.summary + " A vázlat helyben rögzítve; nincs elküldve és nincs target alkalmazás meghívva.",
                state: result.state,
                attachmentsJson: "[]"
            })
        } else {
            chatModel.append({
                kind: "SYSTEM",
                author: "MCP Authority",
                body: result.error || "Az MCP request-vázlat nem hozható létre.",
                state: "REJECTED",
                attachmentsJson: "[]"
            })
        }
        root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

    function draftPrompt() {
        if (root.isMcpMode()) { root.draftMcpRequest(); return }
        var text = composer.text.trim()
        if (text.length === 0 && attachmentModel.count === 0) return
        var attachmentJson = root.pendingAttachmentsJson()
        chatModel.append({
            kind: "USER",
            author: "Te",
            body: text.length > 0 ? text : "Csatolmány(ok) hozzáadva.",
            state: "LOCAL-DRAFT",
            attachmentsJson: attachmentJson
        })
        composer.clear()
        attachmentModel.clear()
        chatModel.append({
            kind: "SYSTEM",
            author: "Runtime",
            body: "Az üzenet helyi vázlatként látható, de nincs elküldve: előbb aktív provider/runtime adapter szükséges.",
            state: "NOT-SENT",
            attachmentsJson: "[]"
        })
        Qt.callLater(function() { messageList.positionViewAtEnd() })
    }

    function requestMessageExport(author, body, state) {
        exportText = "# " + role + " — " + author + "\n\n" + body + "\n\n---\nState: " + state + "\n"
        exportDialog.open()
    }

    onRoleChanged: { if (!root.isMcpMode()) resetSession() }
    onWorkspaceModeChanged: resetSession()
    onRequestedMcpTargetChanged: {
        root.mcpTarget = requestedMcpTarget && requestedMcpTarget.length > 0 ? requestedMcpTarget : "AUTO"
        root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
    }
    onMcpTargetChanged: root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
    Component.onCompleted: {
        root.mcpTarget = requestedMcpTarget && requestedMcpTarget.length > 0 ? requestedMcpTarget : "AUTO"
        root.mcpAuthority = fa3McpControl.authoritySnapshot(root.mcpTarget)
        resetSession()
    }

    Connections {
        target: fa3Preferences
        function onPreferenceChanged(key, value) {
            if (key === "chat/viewMode") root.viewMode = String(value)
            else if (key === "chat/fontSize") root.chatFontSize = Number(value)
            else if (key === "chat/fontWeight") root.chatFontWeight = String(value)
            else if (key === "chat/showGenInfo") root.showGenInfo = Boolean(value)
            else if (key === "chat/scrollMessageToTopOnSend") root.scrollMessageToTopOnSend = Boolean(value)
            else if (key === "chat/autoLatchGenerating") root.autoLatchGenerating = Boolean(value)
            else if (key === "chat/messageStyle") root.messageStyle = String(value)
            else if (key === "chat/expandToWindowWidth") root.expandToWindowWidth = Boolean(value)
        }
    }

    ListModel { id: chatModel }
    ListModel { id: attachmentModel }

    Timer {
        id: statusTimer
        interval: 5000
        repeat: false
        onTriggered: root.operationStatus = ""
    }

    FileDialog {
        id: attachmentDialog
        title: "Fájlok csatolása az üzenethez"
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "AI-értelmezhető fájlok (*.txt *.md *.json *.yaml *.yml *.csv *.tsv *.xml *.html *.pdf *.doc *.docx *.odt *.rtf *.xls *.xlsx *.ods *.ppt *.pptx *.odp *.svg *.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff *.wav *.mp3 *.flac *.ogg *.mp4 *.mkv *.webm *.mov)",
            "Minden fájl (*)"
        ]
        onAccepted: root.addAttachmentUrls(selectedFiles)
    }

    FileDialog {
        id: exportDialog
        title: "Válasz mentése"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Markdown (*.md)", "Szöveg (*.txt)", "Minden fájl (*)"]
        onAccepted: {
            var result = fa3ChatFiles.saveTextFile(selectedFile, root.exportText)
            root.showOperationStatus(result.ok ? "Az üzenet mentve." : (result.error || "A mentés sikertelen."), !result.ok)
        }
    }

    FileDialog {
        id: responseAttachmentSaveDialog
        title: "Válasz-csatolmány mentése"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Minden fájl (*)"]
        onAccepted: {
            var result = fa3ChatFiles.copyLocalFile(root.pendingCopySource, selectedFile)
            root.showOperationStatus(result.ok ? "A csatolmány mentve." : (result.error || "A mentés sikertelen."), !result.ok)
        }
    }

    component Surface: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Surface {
            Layout.fillWidth: true
            Layout.preferredHeight: root.isMcpMode() ? 126 : 104

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 7

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label { text: root.workspaceTitle(); color: root.textPrimary; font.pixelSize: 19; font.bold: true }
                        Label { text: root.workspaceDescription(); color: root.textMuted; font.pixelSize: 9; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Rectangle {
                        radius: 12
                        implicitWidth: modeState.implicitWidth + 20
                        implicitHeight: 24
                        color: "#2a2113"
                        border.color: root.orange
                        Label { id: modeState; anchors.centerIn: parent; text: root.isMcpMode() ? "MCP · ADAPTER-GATED" : root.adapterState; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                    HelpBubble {
                        helpText: root.isMcpMode()
                                  ? "Authority: GUI capture → planner → policy → approval → central MCP gateway → app adapter → evidence. A GUI nem hagyhat jóvá és nem hívhat közvetlenül MCP toolt."
                                  : "A chatfelület használható vázlatokhoz és csatolmányok előkészítéséhez. Valódi AI-válasz csak hitelesített role-chat provider/runtime adapterrel engedélyezhető."
                        bubbleText: root.textPrimary
                        bubbleBorder: root.border
                    }
                    ToolButton { text: "✕"; onClicked: root.closeRequested() }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 7
                    Button { text: "Asszisztens"; checkable: true; checked: root.workspaceMode === "ASSISTANT"; onClicked: root.modeChangeRequested("ASSISTANT") }
                    Button { text: "MCP Control"; checkable: true; checked: root.workspaceMode === "MCP CONTROL"; onClicked: root.modeChangeRequested("MCP CONTROL") }
                    Button { text: "Workflow"; checkable: true; checked: root.workspaceMode === "WORKFLOW"; onClicked: root.modeChangeRequested("WORKFLOW") }
                    Rectangle { width: 1; height: 28; color: root.border; visible: root.isMcpMode() }
                    Label { visible: root.isMcpMode(); text: "Target"; color: root.textMuted; font.pixelSize: 9 }
                    ComboBox {
                        visible: root.isMcpMode()
                        Layout.preferredWidth: 190
                        model: root.mcpTargets
                        textRole: "name"
                        valueRole: "id"
                        currentIndex: root.indexForTarget(root.mcpTarget)
                        onActivated: root.mcpTarget = String(currentValue)
                    }
                    Label { visible: root.isMcpMode(); text: "Risk"; color: root.textMuted; font.pixelSize: 9 }
                    ComboBox {
                        visible: root.isMcpMode()
                        Layout.preferredWidth: 160
                        model: ["AUTO", "READ_ONLY", "MUTATING", "DESTRUCTIVE", "EXTERNAL_SIDE_EFFECT"]
                        currentIndex: Math.max(0, model.indexOf(root.mcpRiskHint))
                        onActivated: root.mcpRiskHint = currentText
                    }
                    Item { Layout.fillWidth: true }
                    Button { text: "Models & Providers"; onClicked: root.navigateRequested(5) }
                    Button { text: "Integrations"; onClicked: root.navigateRequested(14) }
                }
            }
        }

        Surface {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: root.viewMode === "Compact" ? 10 : 14
                spacing: root.viewMode === "Compact" ? 7 : 10

                Rectangle {
                    visible: root.isMcpMode()
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? 66 : 0
                    radius: 7
                    color: root.panelRaised
                    border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "MCP Authority"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Label { text: root.mcpAuthority.state || "ADAPTER-GATED"; color: root.orange; font.pixelSize: 8; font.bold: true }
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 5
                            Repeater {
                                model: root.mcpAuthority && root.mcpAuthority.stages ? root.mcpAuthority.stages : []
                                delegate: Rectangle {
                                    required property var modelData
                                    width: stageText.implicitWidth + 16
                                    height: 23
                                    radius: 10
                                    color: modelData.state === "READY" ? "#103528" : "#2a2113"
                                    border.color: modelData.state === "READY" ? root.green : root.orange
                                    Label {
                                        id: stageText
                                        anchors.centerIn: parent
                                        text: modelData.id + " · " + modelData.state
                                        color: modelData.state === "READY" ? root.green : root.orange
                                        font.pixelSize: 7
                                        font.bold: true
                                    }
                                    ToolTip.visible: stageMouse.containsMouse
                                    ToolTip.text: modelData.detail
                                    MouseArea { id: stageMouse; anchors.fill: parent; hoverEnabled: true }
                                }
                            }
                        }
                    }
                }

                ListView {
                    id: messageList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: root.viewMode === "Compact" ? 6 : 10
                    boundsBehavior: Flickable.StopAtBounds
                    model: chatModel
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                    delegate: Item {
                        id: messageItem
                        required property string kind
                        required property string author
                        required property string body
                        required property string state
                        required property string attachmentsJson
                        property var attachments: root.parseAttachments(attachmentsJson)
                        width: ListView.view.width
                        height: messageCard.implicitHeight

                        Rectangle {
                            id: messageCard
                            width: root.messageStyle === "Bubbles"
                                ? Math.min(parent.width * 0.82, Math.max(320, messageColumn.implicitWidth + 28))
                                : (root.expandToWindowWidth ? parent.width - 10 : Math.min(parent.width - 10, 1180))
                            anchors.horizontalCenter: root.messageStyle !== "Bubbles" && !root.expandToWindowWidth ? parent.horizontalCenter : undefined
                            anchors.right: messageItem.kind === "USER" && root.messageStyle === "Bubbles" ? parent.right : undefined
                            anchors.left: messageItem.kind !== "USER" && root.messageStyle === "Bubbles" ? parent.left : undefined
                            implicitHeight: messageColumn.implicitHeight + (root.messageStyle === "Plain" ? 8 : 20)
                            radius: root.messageStyle === "Plain" ? 0 : 8
                            color: root.messageStyle === "Plain" ? "transparent" : (messageItem.kind === "USER" ? "#102a43" : root.panelRaised)
                            border.color: root.messageStyle === "Plain" ? "transparent" : (messageItem.state === "ADAPTER-GATED" || messageItem.state === "NOT-SENT" ? root.orange : root.border)

                            ColumnLayout {
                                id: messageColumn
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: root.messageStyle === "Plain" ? 4 : 10
                                spacing: 5
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: messageItem.author
                                        color: messageItem.kind === "USER" ? root.accent : root.textPrimary
                                        font.pixelSize: Math.max(9, root.chatFontSize - 3)
                                        font.bold: true
                                    }
                                    Item { Layout.fillWidth: true }
                                    Label {
                                        visible: root.showGenInfo
                                        text: messageItem.state
                                        color: messageItem.state === "ADAPTER-GATED" || messageItem.state === "NOT-SENT" ? root.orange : root.textMuted
                                        font.pixelSize: 8
                                    }
                                    ToolButton {
                                        visible: messageItem.kind !== "USER"
                                        text: "⇩"
                                        implicitWidth: 28
                                        implicitHeight: 24
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Üzenet mentése Markdown vagy szöveg fájlba"
                                        onClicked: root.requestMessageExport(messageItem.author, messageItem.body, messageItem.state)
                                    }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: messageItem.body
                                    color: root.textPrimary
                                    wrapMode: Text.WordWrap
                                    font.pixelSize: root.chatFontSize
                                    font.weight: root.chatFontWeight === "Semibold" ? Font.DemiBold : (root.chatFontWeight === "Medium" ? Font.Medium : Font.Normal)
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    visible: messageItem.attachments.length > 0
                                    spacing: 6
                                    Repeater {
                                        model: messageItem.attachments
                                        delegate: Rectangle {
                                            required property var modelData
                                            height: 30
                                            width: Math.min(messageCard.width - 20, Math.max(150, attachmentName.implicitWidth + 74))
                                            radius: 6
                                            color: "#0a1b2d"
                                            border.color: modelData.adapterValidationRequired ? root.orange : root.border
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 8
                                                anchors.rightMargin: 4
                                                spacing: 6
                                                Label {
                                                    id: attachmentName
                                                    text: modelData.name + " · " + modelData.analysisClass + " · " + modelData.sizeLabel
                                                    color: root.textPrimary
                                                    font.pixelSize: 8
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideMiddle
                                                }
                                                ToolButton {
                                                    visible: messageItem.kind !== "USER"
                                                    text: "⇩"
                                                    implicitWidth: 24
                                                    implicitHeight: 24
                                                    ToolTip.visible: hovered
                                                    ToolTip.text: "Válasz-csatolmány mentése"
                                                    onClicked: {
                                                        root.pendingCopySource = modelData.url
                                                        responseAttachmentSaveDialog.open()
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.border }

                ListView {
                    id: pendingAttachmentList
                    visible: attachmentModel.count > 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? 42 : 0
                    orientation: ListView.Horizontal
                    spacing: 6
                    clip: true
                    model: attachmentModel
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded; active: true }

                    delegate: Rectangle {
                        required property string name
                        required property string sizeLabel
                        required property string analysisClass
                        required property bool adapterValidationRequired
                        required property int index
                        height: 34
                        width: Math.min(310, Math.max(175, pendingLabel.implicitWidth + 44))
                        radius: 6
                        color: "#0a1b2d"
                        border.color: adapterValidationRequired ? root.orange : root.border
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 4
                            spacing: 6
                            Label {
                                id: pendingLabel
                                text: name + " · " + analysisClass + " · " + sizeLabel
                                color: root.textPrimary
                                font.pixelSize: 8
                                Layout.fillWidth: true
                                elide: Text.ElideMiddle
                            }
                            ToolButton {
                                text: "✕"
                                implicitWidth: 24
                                implicitHeight: 24
                                onClicked: attachmentModel.remove(index)
                            }
                        }
                    }
                }

                Rectangle {
                    id: composerFrame
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.viewMode === "Compact" ? 116 : 154
                    Layout.minimumHeight: 104
                    Layout.maximumHeight: Math.max(140, root.height * 0.34)
                    radius: 8
                    color: dropArea.containsDrag ? "#0d2841" : "#091624"
                    border.color: dropArea.containsDrag ? root.accent : root.border
                    border.width: dropArea.containsDrag ? 2 : 1

                    TextArea {
                        id: composer
                        anchors.fill: parent
                        anchors.margins: 10
                        placeholderText: root.isMcpMode() ? ("Írj MCP utasítást · target: " + root.mcpTarget + "… Fájlt ide is húzhatsz.") : ("Írj a(z) " + root.role + " szerepnek… Fájlt ide is húzhatsz.")
                        wrapMode: TextEdit.Wrap
                        color: root.textPrimary
                        font.pixelSize: root.chatFontSize
                        background: null
                        selectByMouse: true
                    }

                    DropArea {
                        id: dropArea
                        anchors.fill: parent
                        onDropped: function(drop) {
                            if (drop.hasUrls) {
                                root.addAttachmentUrls(drop.urls)
                                drop.acceptProposedAction()
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Button {
                        text: "＋ Fájl hozzáadása"
                        onClicked: attachmentDialog.open()
                    }
                    HelpBubble {
                        helpText: "Szöveg, PDF, Office-dokumentum, táblázat, prezentáció, SVG, pixelkép/fotó, hang, videó és egyéb helyi fájl csatolható. A fájl nem kerül automatikusan hálózatra: a kiválasztott provider adapter a küldéskor ellenőrzi, hogy az adott modell valóban tudja-e elemezni."
                        bubbleText: root.textPrimary
                        bubbleBorder: root.border
                    }
                    Label {
                        visible: root.operationStatus.length > 0
                        text: root.operationStatus
                        color: root.operationFailed ? root.orange : root.green
                        font.pixelSize: 9
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                    Item { Layout.fillWidth: root.operationStatus.length === 0 }
                    Button {
                        text: root.isMcpMode() ? "MCP request vázlat" : "Vázlat"
                        enabled: composer.text.trim().length > 0 || attachmentModel.count > 0
                        onClicked: root.draftPrompt()
                    }
                    Button {
                        text: root.isMcpMode() ? "Végrehajtás" : "Küldés"
                        enabled: false
                    }
                    HelpBubble {
                        helpText: root.isMcpMode()
                                  ? "Végrehajtás csak akkor engedélyezhető, ha a planner typed tool-call tervet ad, a policy outcome PASS, a szükséges approval megvan, a központi MCP gateway és a target adapter hitelesítetten elérhető, majd evidence receipt készül. Jelenleg fail-closed."
                                  : "A Küldés csak aktív és hitelesített role-chat provider/runtime adapter után lesz engedélyezve. Addig a szöveg és a csatolmányok helyi vázlatként készíthetők elő."
                        bubbleText: root.textPrimary
                        bubbleBorder: root.border
                    }
                }
            }
        }
    }
}
