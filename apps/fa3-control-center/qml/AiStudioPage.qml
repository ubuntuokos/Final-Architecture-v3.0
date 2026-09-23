import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8397ad"
    property color accent: "#25a7ff"
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    property color red: "#ff6b7a"

    property int selectedIndex: 7
    property int pageMode: 0
    property int selectedAppIndex: 0
    property string pendingInstallId: ""
    property string pendingInstallName: ""
    property string noticeText: ""
    property var selectedApp: fa3AppCatalog.applications.length > selectedAppIndex
                              ? fa3AppCatalog.applications[selectedAppIndex] : ({})

    property var modules: [
        {title: "Image", badge: "READY", tone: root.magenta, summary: "ComfyUI / InvokeAI / editor bridge projection.", actions: ["Generate és edit pipeline", "Krita / GIMP bridge", "Model- és workflow-választás", "Artifact provenance"]},
        {title: "Video", badge: "READY", tone: root.accent, summary: "Generation, compositing és editorial workflow.", actions: ["Video generation", "Kdenlive editorial", "OpenFX / LUT pipeline", "Render és export handoff"]},
        {title: "Animation", badge: "READY", tone: root.cyan, summary: "Motion, character és timeline workflow-k.", actions: ["Character motion", "Timeline workflow", "Asset handoff", "Preview és render"]},
        {title: "3D / VFX", badge: "READY", tone: root.orange, summary: "Geometry, Bforartist/Blender, Natron/Gaffer kapcsolatok.", actions: ["Geometry / mesh", "DCC bridge", "Compositing", "Scene és artifact provenance"]},
        {title: "Audio", badge: "READY", tone: root.green, summary: "STT, TTS, restoration, separation és voice fabric.", actions: ["Speech-to-text", "Text-to-speech", "Restoration / separation", "Voice workflow"]},
        {title: "Music", badge: "READY", tone: root.magenta, summary: "Music generation, stems, DAW és mastering workflow-k.", actions: ["Generation", "Stem separation", "DAW handoff", "Mastering"]},
        {title: "Story / Screenplay", badge: "READY", tone: root.accent, summary: "FA3 Story profile és production-context projection.", actions: ["Story planning", "Screenplay structure", "Scene breakdown", "Production handoff"]},
        {title: "Office", badge: "UNO", tone: root.cyan, summary: "Writer, Calc és Impress AI-réteg Preview → explicit Apply / Undo folyamattal.", actions: ["Writer · Rewrite · Summarize · Translate · Explain · Continue text · Review", "Calc · Formula · Table analysis · Formula explanation · Data-cleaning plan", "Impress · Slide outline · Slide rewrite · Speaker notes", "Selection/context → proposal → Preview → explicit Apply/UNO mutation → Undo"]},
        {title: "Marketing", badge: "E2E PENDING", tone: root.orange, summary: "Agent Native UAF-folyamatok; a provider runtime csak current-host E2E után éles.", actions: ["Twenty CRM contact projection", "Mautic campaign draft / validate / approve", "listmonk prepare / dispatch", "Consent + suppression fail-closed", "DecisionReceipt + evidence", "CURRENT_HOST_PRODUCTION_E2E_PASS szükséges"]},
        {title: "Weboldal", badge: "PUBLISH", tone: root.cyan, summary: "Webes publikáció, preview és deployment workflow-k.", actions: ["Page/content planning", "Preview", "Asset handoff", "Controlled deployment"]},
        {title: "Prezentáció", badge: "PUBLISH", tone: root.green, summary: "Prezentációk készítése, exportja és publikációs átadása.", actions: ["Deck outline", "Slide generation", "Speaker notes", "Export és handoff"]}
    ]

    function stateLabel(state) {
        if (state === "INSTALLED") return "TELEPÍTVE"
        if (state === "READY_TO_INSTALL") return "TELEPÍTÉSRE KÉSZ"
        if (state === "INSTALLING") return "TELEPÍTÉS…"
        if (state === "RECIPE_REQUIRED") return "PROVIDER RECEPT SZÜKSÉGES"
        if (state === "INCOMPATIBLE") return "NEM KOMPATIBILIS"
        if (state === "ERROR") return "HIBA"
        return "ELÉRHETŐ"
    }

    function stateColor(state) {
        if (state === "INSTALLED") return root.green
        if (state === "READY_TO_INSTALL") return root.accent
        if (state === "INSTALLING") return root.orange
        if (state === "RECIPE_REQUIRED") return root.orange
        if (state === "INCOMPATIBLE" || state === "ERROR") return root.red
        return root.textMuted
    }

    function primaryActionLabel(state) {
        if (state === "INSTALLED") return "Megnyitás"
        if (state === "READY_TO_INSTALL") return "Telepítés első használatkor"
        if (state === "INSTALLING") return "Telepítés folyamatban…"
        if (state === "RECIPE_REQUIRED") return "Provider recept szükséges"
        return "Nem elérhető"
    }

    Connections {
        target: fa3AppCatalog

        function onInstallationConfirmationRequired(appId, name) {
            root.pendingInstallId = appId
            root.pendingInstallName = name
            installDialog.open()
        }

        function onOperationFinished(appId, operation, success, message) {
            root.noticeText = (success ? "✓ " : "⚠ ") + message
        }

        function onApplicationRequestQueued(requestId, filePath) {
            root.noticeText = "✓ Igény review-sorba helyezve: " + requestId
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 13

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label { text: "AI Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                Label {
                    text: root.pageMode === 0
                          ? "Kreatív, Office és publikációs munkaterületek"
                          : "Jóváhagyott katalógus · first-use telepítés · review-köteles új app igény"
                    color: root.textMuted
                    font.pixelSize: 11
                }
            }

            Button {
                text: "Munkaterületek"
                checkable: true
                checked: root.pageMode === 0
                onClicked: root.pageMode = 0
            }
            Button {
                text: "Alkalmazások"
                checkable: true
                checked: root.pageMode === 1
                onClicked: root.pageMode = 1
            }
            Button {
                visible: root.pageMode === 1
                text: "+ Alkalmazás javaslata"
                onClicked: requestDialog.open()
            }
        }

        Rectangle {
            visible: root.pageMode === 1
            Layout.fillWidth: true
            implicitHeight: policyText.implicitHeight + 20
            radius: 7
            color: "#091624"
            border.color: root.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10
                Label { text: "🛡"; color: root.cyan; font.pixelSize: 14 }
                Label {
                    id: policyText
                    Layout.fillWidth: true
                    text: "Az FA3 alaptelepítő nem telepíti ezeket az appokat. Csak a canonical katalógus tagjai materializálhatók, első használatkor vagy explicit telepítéssel. Saját URL-ről közvetlen telepítés nincs."
                    color: root.textMuted
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }
                Label {
                    text: "REVIEW SOR: " + fa3AppCatalog.pendingRequestCount
                    color: root.cyan
                    font.pixelSize: 8
                    font.bold: true
                }
            }
        }

        Label {
            visible: root.noticeText.length > 0 || fa3AppCatalog.lastError.length > 0
            Layout.fillWidth: true
            text: fa3AppCatalog.lastError.length > 0 ? fa3AppCatalog.lastError : root.noticeText
            color: fa3AppCatalog.lastError.length > 0 ? root.orange : root.green
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.pageMode

            Item {
                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    ScrollView {
                        id: moduleScroll
                        Layout.preferredWidth: Math.min(590, root.width * 0.52)
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

                        Flow {
                            width: moduleScroll.availableWidth - 8
                            spacing: 10

                            Repeater {
                                model: root.modules
                                delegate: Rectangle {
                                    required property var modelData
                                    required property int index
                                    width: Math.max(220, (moduleScroll.availableWidth - 30) / 2)
                                    height: 112
                                    radius: 9
                                    color: index === root.selectedIndex ? root.panelRaised : (cardMouse.containsMouse ? "#10233a" : root.panel)
                                    border.color: index === root.selectedIndex ? modelData.tone : root.border
                                    border.width: index === root.selectedIndex ? 2 : 1

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 13
                                        spacing: 7
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Rectangle { width: 8; height: 8; radius: 4; color: modelData.tone }
                                            Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 13; font.bold: true; Layout.fillWidth: true }
                                            Label { text: modelData.badge; color: modelData.tone; font.pixelSize: 8; font.bold: true }
                                        }
                                        Label { text: modelData.summary; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.fillHeight: true }
                                        Label { text: index === root.selectedIndex ? "RÉSZLETEK MEGNYITVA" : "Kattints a részletekhez"; color: index === root.selectedIndex ? modelData.tone : root.textMuted; font.pixelSize: 8; font.bold: true }
                                    }

                                    MouseArea {
                                        id: cardMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectedIndex = index
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 390
                        radius: 9
                        color: root.panel
                        border.color: root.modules[root.selectedIndex].tone
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle { width: 10; height: 10; radius: 5; color: root.modules[root.selectedIndex].tone }
                                Label { text: root.modules[root.selectedIndex].title; color: root.textPrimary; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true }
                                Label { text: root.modules[root.selectedIndex].badge; color: root.modules[root.selectedIndex].tone; font.pixelSize: 9; font.bold: true }
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.modules[root.selectedIndex].summary
                                color: root.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }
                            Label { text: "Elérhető felületek / műveletek"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }

                            Repeater {
                                model: root.modules[root.selectedIndex].actions
                                delegate: Rectangle {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: actionText.implicitHeight + 20
                                    radius: 6
                                    color: root.panelRaised
                                    border.color: root.border
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 12
                                        anchors.rightMargin: 12
                                        Label { text: "›"; color: root.modules[root.selectedIndex].tone; font.pixelSize: 14; font.bold: true }
                                        Label { id: actionText; text: modelData; color: root.textPrimary; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    }
                                }
                            }

                            Item { Layout.fillHeight: true }

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: noteText.implicitHeight + 22
                                radius: 6
                                color: "#091624"
                                border.color: root.border
                                Label {
                                    id: noteText
                                    anchors.fill: parent
                                    anchors.margins: 11
                                    text: root.modules[root.selectedIndex].title === "Office"
                                        ? "Office authority: a LibreOffice/UNO módosítás csak Preview után, explicit Apply lépéssel történhet; közvetlen dokumentummódosítás nincs."
                                        : "Ez a panel az FA3 munkafelületét választja ki; végrehajtás csak a megfelelő provider/adapter és approval-határ szerint történhet."
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }

            Item {
                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    Rectangle {
                        Layout.preferredWidth: Math.min(560, root.width * 0.51)
                        Layout.fillHeight: true
                        radius: 9
                        color: root.panel
                        border.color: root.border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: "Jóváhagyott alkalmazások"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                                    Label { text: "Csak canonical allowlist — nincs webes vagy saját repository telepítés"; color: root.textMuted; font.pixelSize: 9 }
                                }
                                Button { text: "Frissítés"; onClicked: fa3AppCatalog.refresh() }
                            }

                            ScrollView {
                                id: appScroll
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                contentWidth: availableWidth
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                                Column {
                                    width: appScroll.availableWidth - 6
                                    spacing: 8

                                    Repeater {
                                        model: fa3AppCatalog.applications
                                        delegate: Rectangle {
                                            required property var modelData
                                            required property int index
                                            width: parent ? parent.width : 0
                                            height: 88
                                            radius: 7
                                            color: index === root.selectedAppIndex ? root.panelRaised : (appMouse.containsMouse ? "#10233a" : "#091624")
                                            border.color: index === root.selectedAppIndex ? root.stateColor(modelData.runtime_state) : root.border
                                            border.width: index === root.selectedAppIndex ? 2 : 1

                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 12
                                                spacing: 10
                                                Rectangle { width: 9; height: 9; radius: 5; color: root.stateColor(modelData.runtime_state) }
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 3
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        Label { text: modelData.name; color: root.textPrimary; font.pixelSize: 12; font.bold: true; Layout.fillWidth: true }
                                                        Label { text: modelData.category; color: root.textMuted; font.pixelSize: 8 }
                                                    }
                                                    Label { text: modelData.description; color: root.textMuted; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                                                    Label { text: root.stateLabel(modelData.runtime_state); color: root.stateColor(modelData.runtime_state); font.pixelSize: 8; font.bold: true }
                                                }
                                            }

                                            MouseArea {
                                                id: appMouse
                                                anchors.fill: parent
                                                hoverEnabled: true
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: root.selectedAppIndex = index
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 390
                        radius: 9
                        color: root.panel
                        border.color: root.selectedApp.runtime_state ? root.stateColor(root.selectedApp.runtime_state) : root.border

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Rectangle {
                                    width: 10; height: 10; radius: 5
                                    color: root.selectedApp.runtime_state ? root.stateColor(root.selectedApp.runtime_state) : root.textMuted
                                }
                                Label {
                                    text: root.selectedApp.name || "Nincs alkalmazás"
                                    color: root.textPrimary
                                    font.pixelSize: 20
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                Label {
                                    text: root.selectedApp.runtime_state ? root.stateLabel(root.selectedApp.runtime_state) : ""
                                    color: root.selectedApp.runtime_state ? root.stateColor(root.selectedApp.runtime_state) : root.textMuted
                                    font.pixelSize: 8
                                    font.bold: true
                                }
                            }

                            Label {
                                Layout.fillWidth: true
                                text: root.selectedApp.description || ""
                                color: root.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }

                            Rectangle { Layout.fillWidth: true; height: 1; color: root.border }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                columnSpacing: 18
                                rowSpacing: 8
                                Label { text: "Kategória"; color: root.textMuted; font.pixelSize: 9 }
                                Label { text: root.selectedApp.category || "—"; color: root.textPrimary; font.pixelSize: 9 }
                                Label { text: "Telepítési mód"; color: root.textMuted; font.pixelSize: 9 }
                                Label { text: root.selectedApp.install_mode === "FIRST_USE" ? "Első használatkor" : "—"; color: root.textPrimary; font.pixelSize: 9 }
                                Label { text: "Admission"; color: root.textMuted; font.pixelSize: 9 }
                                Label { text: root.selectedApp.admission || "—"; color: root.green; font.pixelSize: 9; font.bold: true }
                                Label { text: "Provider recipe"; color: root.textMuted; font.pixelSize: 9 }
                                Label {
                                    text: root.selectedApp.recipe_available ? "Materializálva" : "Még nincs materializálva"
                                    color: root.selectedApp.recipe_available ? root.green : root.orange
                                    font.pixelSize: 9
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: appPolicyText.implicitHeight + 22
                                radius: 6
                                color: "#091624"
                                border.color: root.border
                                Label {
                                    id: appPolicyText
                                    anchors.fill: parent
                                    anchors.margins: 11
                                    text: root.selectedApp.runtime_state === "RECIPE_REQUIRED"
                                          ? "Az app jóváhagyott, de a provider telepítési receptje még nincs materializálva. Az FA3 nem próbál helyette internetről vagy felhasználói URL-ről telepíteni."
                                          : "First-use policy: telepítés csak explicit jóváhagyás után, a canonical app ID-hoz kötött repository-controlled provider recepten keresztül történhet."
                                    color: root.textMuted
                                    font.pixelSize: 9
                                    wrapMode: Text.WordWrap
                                }
                            }

                            Button {
                                Layout.fillWidth: true
                                text: root.selectedApp.runtime_state ? root.primaryActionLabel(root.selectedApp.runtime_state) : "Nincs alkalmazás"
                                enabled: root.selectedApp.runtime_state === "INSTALLED" || root.selectedApp.runtime_state === "READY_TO_INSTALL"
                                onClicked: fa3AppCatalog.requestFirstUse(root.selectedApp.id)
                            }

                            Item { Layout.fillHeight: true }

                            Button {
                                Layout.fillWidth: true
                                text: "+ Másik alkalmazás javaslata review-ra"
                                onClicked: requestDialog.open()
                            }
                            Label {
                                Layout.fillWidth: true
                                text: "A javaslat nem ad telepítési jogosultságot és nem kerül automatikusan a katalógusba."
                                color: root.textMuted
                                font.pixelSize: 8
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: installDialog
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, root.width - 60)
        title: "Első használat — telepítés"
        standardButtons: Dialog.Ok | Dialog.Cancel

        onAccepted: {
            if (root.pendingInstallId.length > 0)
                fa3AppCatalog.installApproved(root.pendingInstallId)
        }

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                Layout.fillWidth: true
                text: "A(z) “" + root.pendingInstallName + "” még nincs telepítve. Telepítsem a jóváhagyott FA3 provider recepten keresztül?"
                color: root.textPrimary
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            Label {
                Layout.fillWidth: true
                text: "A művelet nem használ felhasználói URL-t és nem kerülheti meg az admission/preflight ellenőrzéseket."
                color: root.textMuted
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }

    Dialog {
        id: requestDialog
        modal: true
        anchors.centerIn: parent
        width: Math.min(640, root.width - 60)
        title: "Alkalmazás javaslata"
        standardButtons: Dialog.Ok | Dialog.Cancel

        onOpened: {
            sourceField.forceActiveFocus()
        }

        onAccepted: {
            const requestId = fa3AppCatalog.submitApplicationRequest(sourceField.text,
                                                                     categoryBox.currentText,
                                                                     rationaleField.text)
            if (requestId.length > 0) {
                sourceField.clear()
                rationaleField.clear()
                categoryBox.currentIndex = 0
            }
        }

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: "Küldj be egy publikus HTTPS projektlinket (például GitHub repository). Ez review-kérés, nem telepítési forrás."
                color: root.textMuted
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }

            Label { text: "Forrás URL *"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
            TextField {
                id: sourceField
                Layout.fillWidth: true
                placeholderText: "https://github.com/szervezet/projekt"
                selectByMouse: true
            }

            Label { text: "Terület"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
            ComboBox {
                id: categoryBox
                Layout.fillWidth: true
                model: ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay", "Office", "Marketing", "Weboldal", "Prezentáció", "Other"]
            }

            Label { text: "Miért lenne hasznos az FA3-ban?"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                TextArea {
                    id: rationaleField
                    placeholderText: "Opcionális indoklás, kívánt workflow vagy kiváltandó funkció…"
                    wrapMode: TextEdit.Wrap
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: requestPolicyText.implicitHeight + 20
                radius: 6
                color: "#091624"
                border.color: root.border
                Label {
                    id: requestPolicyText
                    anchors.fill: parent
                    anchors.margins: 10
                    text: "Beküldés után: source/licence/supply-chain/dependency/network/telemetry/hardver/átfedés review → canonical döntés → provider manifest → conformance → PASS evidence → csak ezután jelenhet meg telepíthető appként."
                    color: root.textMuted
                    font.pixelSize: 8
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
