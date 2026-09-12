import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var settings
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
    property string updateMessage: ""
    property var sections: [
        ["appearance", t("Megjelenés", "Appearance")],
        ["locale", t("Nyelv & régió", "Language & Region")],
        ["paths", t("Könyvtárak", "Paths & Libraries")],
        ["workspace", "Workspace"],
        ["dashboard", "Dashboard"],
        ["notifications", t("Értesítések", "Notifications")],
        ["shortcuts", t("Gyorsbillentyűk", "Shortcuts")],
        ["integrations", t("Integrációk", "Integrations")],
        ["publishing", t("Publikálás", "Publishing")],
        ["hdr", "HDR"],
        ["mentor", "AI Mentor"],
        ["coach", "AI Coach"],
        ["updates", t("Frissítés", "Updates")],
        ["about", t("Névjegy", "About")],
        ["advanced", t("Haladó", "Advanced")]
    ]

    function t(hu, en) {
        return language === "en" ? en : hu
    }

    function px(value) {
        return Math.max(9, Math.round(value * fontScale))
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

    component PathEditor: Card {
        id: pathEditor
        property string settingKey: ""
        property string label: ""
        property var status: root.settings.pathStatus(pathField.text)
        implicitHeight: Math.round(108 * root.uiScale)

        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 10

            ColumnLayout {
                Layout.preferredWidth: Math.round(190 * root.uiScale)

                Label {
                    text: pathEditor.label
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    font.pixelSize: root.px(10)
                    color: pathEditor.status.exists ? root.textMuted : "#d99b32"
                    text: pathEditor.status.exists
                          ? ((pathEditor.status.writable ? root.t("írható", "writable") : root.t("csak olvasható", "read-only"))
                             + " · " + (pathEditor.status.filesystem || "fs")
                             + " · " + Number(pathEditor.status.freeGiB).toFixed(1) + " GiB")
                          : root.t("nem létezik / nincs felcsatolva", "missing / not mounted")
                }
            }

            TextField {
                id: pathField
                Layout.fillWidth: true
                text: root.settings.value(pathEditor.settingKey, "")
                onEditingFinished: root.settings.setValue(pathEditor.settingKey, text)
            }

            Button {
                text: root.t("Tallózás", "Browse")
                onClicked: {
                    const chosen = root.settings.chooseDirectory(pathEditor.label, pathField.text)
                    if (chosen.length > 0) {
                        pathField.text = chosen
                        root.settings.setValue(pathEditor.settingKey, chosen)
                    }
                }
            }
        }
    }

    component ShortcutEditor: Card {
        id: shortcutEditor
        property string actionLabel: ""
        property string settingKey: ""
        property string defaultSequence: ""
        implicitHeight: Math.round(82 * root.uiScale)

        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 12

            Label {
                text: shortcutEditor.actionLabel
                Layout.preferredWidth: Math.round(220 * root.uiScale)
                font.bold: true
            }

            TextField {
                id: shortcutField
                Layout.fillWidth: true
                text: root.settings.value(shortcutEditor.settingKey, shortcutEditor.defaultSequence)
                placeholderText: "Ctrl+Alt+K"
                onEditingFinished: {
                    if (root.settings.validShortcut(text)
                            && root.settings.shortcutConflict(shortcutEditor.settingKey, text).length === 0) {
                        root.settings.setValue(shortcutEditor.settingKey, text)
                    }
                }
            }

            Label {
                Layout.preferredWidth: Math.round(180 * root.uiScale)
                color: "#d99b32"
                text: {
                    if (!root.settings.validShortcut(shortcutField.text))
                        return root.t("Érvénytelen", "Invalid")
                    const conflict = root.settings.shortcutConflict(shortcutEditor.settingKey, shortcutField.text)
                    return conflict.length > 0 ? root.t("Ütközés: ", "Conflict: ") + conflict : ""
                }
            }

            Button {
                text: root.t("Alap", "Default")
                onClicked: {
                    shortcutField.text = shortcutEditor.defaultSequence
                    root.settings.setValue(shortcutEditor.settingKey, shortcutEditor.defaultSequence)
                }
            }
        }
    }

    component IntegrationGroup: Card {
        id: integrationGroup
        property string groupTitle: ""
        property string primaryApp: ""
        property string secondaryApp: ""
        property string primaryEnabledKey: ""
        property string secondaryEnabledKey: ""
        property string defaultKey: ""
        property string defaultValue: ""
        implicitHeight: Math.round(178 * root.uiScale)

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true

                Label {
                    text: integrationGroup.groupTitle
                    font.pixelSize: root.px(17)
                    font.bold: true
                    Layout.fillWidth: true
                }

                Label {
                    text: root.t("Alapértelmezett", "Default")
                    color: root.textMuted
                }

                ComboBox {
                    model: [integrationGroup.primaryApp, integrationGroup.secondaryApp]
                    currentIndex: root.settings.value(integrationGroup.defaultKey, integrationGroup.defaultValue) === integrationGroup.secondaryApp ? 1 : 0
                    onActivated: root.settings.setValue(integrationGroup.defaultKey, currentText)
                }
            }

            CheckBox {
                text: integrationGroup.primaryApp
                checked: root.settings.value(integrationGroup.primaryEnabledKey, true)
                onToggled: root.settings.setValue(integrationGroup.primaryEnabledKey, checked)
            }

            CheckBox {
                text: integrationGroup.secondaryApp
                checked: root.settings.value(integrationGroup.secondaryEnabledKey, true)
                onToggled: root.settings.setValue(integrationGroup.secondaryEnabledKey, checked)
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: Math.round(240 * root.uiScale)
            Layout.fillHeight: true
            color: root.surface1
            border.color: Qt.rgba(root.textPrimary.r, root.textPrimary.g, root.textPrimary.b, 0.08)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                Label {
                    text: root.t("Beállítások", "Settings")
                    font.pixelSize: root.px(18)
                    font.bold: true
                    Layout.bottomMargin: 8
                }

                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
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

                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: root.settings.configFilePath
                    color: root.textMuted
                    font.pixelSize: root.px(9)
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.sectionIndex

            ScrollView {
                id: appearanceView
                contentWidth: availableWidth

                ColumnLayout {
                    width: appearanceView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Megjelenés", "Appearance")
                        subtitle: root.t("A Control Center méretezése és vizuális viselkedése.", "Control Center scaling and visual behavior.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(300 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("UI méretezés", "UI scale") }
                            Slider {
                                from: 0.8
                                to: 2.0
                                stepSize: 0.05
                                value: root.settings.uiScale
                                onMoved: root.settings.uiScale = value
                            }

                            Label { text: root.t("Alap betűméret", "Base font size") }
                            SpinBox {
                                from: 10
                                to: 28
                                value: root.settings.baseFontSize
                                editable: true
                                onValueModified: root.settings.baseFontSize = value
                            }

                            Label { text: root.t("Téma", "Theme") }
                            ComboBox {
                                model: ["system", "light", "dark"]
                                currentIndex: root.settings.themeMode === "light" ? 1 : root.settings.themeMode === "dark" ? 2 : 0
                                onActivated: root.settings.themeMode = currentText
                            }

                            Label { text: root.t("Sűrűség", "Density") }
                            ComboBox {
                                model: ["compact", "normal", "spacious"]
                                currentIndex: root.settings.value("appearance/density", "normal") === "compact" ? 0 : root.settings.value("appearance/density", "normal") === "spacious" ? 2 : 1
                                onActivated: root.settings.setValue("appearance/density", currentText)
                            }

                            Label { text: root.t("Kisebb animáció", "Reduced motion") }
                            Switch {
                                checked: root.settings.value("appearance/reducedMotion", false)
                                onToggled: root.settings.setValue("appearance/reducedMotion", checked)
                            }

                            Label { text: root.t("Magas kontraszt", "High contrast") }
                            Switch {
                                checked: root.settings.value("appearance/highContrast", false)
                                onToggled: root.settings.setValue("appearance/highContrast", checked)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: localeView
                contentWidth: availableWidth

                ColumnLayout {
                    width: localeView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Nyelv & régió", "Language & Region")
                        subtitle: root.t("A GUI nyelve különválik a canonical technikai azonosítóktól.", "UI language remains separate from canonical technical identifiers.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(190 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("GUI nyelve", "UI language") }
                            ComboBox {
                                model: ["Magyar", "English"]
                                currentIndex: root.settings.language === "en" ? 1 : 0
                                onActivated: root.settings.language = currentIndex === 1 ? "en" : "hu"
                            }

                            Label { text: root.t("Technikai kifejezések angolul", "Keep technical terms in English") }
                            Switch {
                                checked: root.settings.value("locale/technicalTermsEnglish", true)
                                onToggled: root.settings.setValue("locale/technicalTermsEnglish", checked)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: pathsView
                contentWidth: availableWidth

                ColumnLayout {
                    width: pathsView.availableWidth
                    spacing: 12
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Könyvtárak", "Paths & Libraries")
                        subtitle: root.t("Felhasználói path role-ok; fstab vagy mount policy nem módosul.", "User path roles; fstab and mount policy are never modified here.")
                    }

                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Projects"; settingKey: "paths/projects" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Workspaces"; settingKey: "paths/workspaces" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Models"; settingKey: "paths/models" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Model Cache"; settingKey: "paths/modelCache" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Datasets"; settingKey: "paths/datasets" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Outputs"; settingKey: "paths/outputs" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Evidence Export"; settingKey: "paths/evidenceExport" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Image Assets"; settingKey: "paths/imageAssets" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Video Assets"; settingKey: "paths/videoAssets" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "Audio Assets"; settingKey: "paths/audioAssets" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "3D Assets"; settingKey: "paths/threeDAssets" }
                    PathEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; label: "LUT Library"; settingKey: "paths/lutLibrary" }
                    Item { Layout.preferredHeight: 20 }
                }
            }

            ScrollView {
                id: workspaceView
                contentWidth: availableWidth

                ColumnLayout {
                    width: workspaceView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "Workspace"
                        subtitle: root.t("Indulás, session restore és autosave.", "Startup, session restore and autosave.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(220 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Induló oldal", "Start page") }
                            ComboBox {
                                model: ["Command Center", "Projects", "AI Studio", "AI Mentor", "AI Coach", "Evidence"]
                                currentIndex: 0
                                onActivated: root.settings.setValue("workspace/startPage", currentText)
                            }

                            Label { text: root.t("Session visszaállítása", "Restore session") }
                            Switch {
                                checked: root.settings.value("workspace/restoreSession", true)
                                onToggled: root.settings.setValue("workspace/restoreSession", checked)
                            }

                            Label { text: root.t("Autosave perc", "Autosave minutes") }
                            SpinBox {
                                from: 1
                                to: 60
                                value: root.settings.value("workspace/autosaveMinutes", 5)
                                onValueModified: root.settings.setValue("workspace/autosaveMinutes", value)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: dashboardView
                contentWidth: availableWidth

                ColumnLayout {
                    width: dashboardView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "Dashboard"
                        subtitle: root.t("Operátori nézetprofil és telemetry frissítés.", "Operator view profile and telemetry refresh.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(180 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Profil", "Profile") }
                            ComboBox {
                                model: ["Studio", "Operations", "Development", "Presentation", "Custom"]
                                currentIndex: 0
                                onActivated: root.settings.setValue("dashboard/profile", currentText)
                            }

                            Label { text: "Telemetry refresh" }
                            SpinBox {
                                from: 1
                                to: 60
                                value: root.settings.value("performance/telemetryRefreshSeconds", 5)
                                onValueModified: root.settings.setValue("performance/telemetryRefreshSeconds", value)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: notificationsView
                contentWidth: availableWidth

                ColumnLayout {
                    width: notificationsView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Értesítések", "Notifications")
                        subtitle: root.t("A GUI saját értesítési preferenciái.", "GUI-owned notification preferences.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(170 * root.uiScale)

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18

                            CheckBox {
                                text: root.t("Desktop értesítések", "Desktop notifications")
                                checked: root.settings.value("notifications/enabled", true)
                                onToggled: root.settings.setValue("notifications/enabled", checked)
                            }

                            CheckBox {
                                text: root.t("Csak hiba és kritikus esemény", "Errors and critical events only")
                                checked: root.settings.value("notifications/errorsOnly", false)
                                onToggled: root.settings.setValue("notifications/errorsOnly", checked)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: shortcutsView
                contentWidth: availableWidth

                ColumnLayout {
                    width: shortcutsView.availableWidth
                    spacing: 10
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Gyorsbillentyűk", "Shortcuts")
                        subtitle: root.t("A Control Center fő nézeteinek és műveleteinek billentyűkombinációi. Ütközés esetén a módosítás nem mentődik.", "Keyboard sequences for main Control Center views and actions. Conflicting sequences are not saved.")
                    }

                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "Command Center"; settingKey: "shortcuts/commandCenter"; defaultSequence: "Ctrl+1" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "Projects"; settingKey: "shortcuts/projects"; defaultSequence: "Ctrl+2" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "AI Studio"; settingKey: "shortcuts/studio"; defaultSequence: "Ctrl+3" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "AI Mentor"; settingKey: "shortcuts/mentor"; defaultSequence: "Ctrl+4" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "AI Coach"; settingKey: "shortcuts/coach"; defaultSequence: "Ctrl+5" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "Manager"; settingKey: "shortcuts/manager"; defaultSequence: "Ctrl+6" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: "Model Manager"; settingKey: "shortcuts/modelManager"; defaultSequence: "Ctrl+7" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: root.t("Rendszer", "System"); settingKey: "shortcuts/system"; defaultSequence: "Ctrl+8" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: root.t("Beállítások", "Settings"); settingKey: "shortcuts/settings"; defaultSequence: "Ctrl+," }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: root.t("Asszisztens", "Assistant"); settingKey: "shortcuts/assistant"; defaultSequence: "Ctrl+Space" }
                    ShortcutEditor { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; actionLabel: root.t("Frissítés / újraolvasás", "Refresh"); settingKey: "shortcuts/refresh"; defaultSequence: "Ctrl+R" }
                    Item { Layout.preferredHeight: 20 }
                }
            }

            ScrollView {
                id: integrationsView
                contentWidth: availableWidth

                ColumnLayout {
                    width: integrationsView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Integrációk", "Integrations")
                        subtitle: root.t("Kreatív, irodai és knowledge alkalmazások. Ezek felhasználói preferenciák, nem authority-k.", "Creative, office and knowledge applications. These are user preferences, not authorities.")
                    }

                    IntegrationGroup {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        groupTitle: root.t("Grafika", "Graphics")
                        primaryApp: "GIMP"
                        secondaryApp: "Krita"
                        primaryEnabledKey: "integrations/gimpEnabled"
                        secondaryEnabledKey: "integrations/kritaEnabled"
                        defaultKey: "integrations/imageEditor"
                        defaultValue: "Krita"
                    }

                    IntegrationGroup {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        groupTitle: "Video"
                        primaryApp: "Kdenlive"
                        secondaryApp: "OpenShot"
                        primaryEnabledKey: "integrations/kdenliveEnabled"
                        secondaryEnabledKey: "integrations/openshotEnabled"
                        defaultKey: "integrations/videoEditor"
                        defaultValue: "Kdenlive"
                    }

                    IntegrationGroup {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        groupTitle: "Audio"
                        primaryApp: "Ardour"
                        secondaryApp: "Audacity"
                        primaryEnabledKey: "integrations/ardourEnabled"
                        secondaryEnabledKey: "integrations/audacityEnabled"
                        defaultKey: "integrations/audioEditor"
                        defaultValue: "Ardour"
                    }

                    IntegrationGroup {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        groupTitle: "3D"
                        primaryApp: "Blender"
                        secondaryApp: "Bforartist"
                        primaryEnabledKey: "integrations/blenderEnabled"
                        secondaryEnabledKey: "integrations/bforartistEnabled"
                        defaultKey: "integrations/threeDEditor"
                        defaultValue: "Bforartist"
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(220 * root.uiScale)

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10

                            Label {
                                text: root.t("Office & Knowledge", "Office & Knowledge")
                                font.pixelSize: root.px(17)
                                font.bold: true
                            }

                            CheckBox {
                                text: "LibreOffice — " + root.t("dokumentum / iroda", "documents / office")
                                checked: root.settings.value("integrations/libreOfficeEnabled", true)
                                onToggled: root.settings.setValue("integrations/libreOfficeEnabled", checked)
                            }

                            CheckBox {
                                text: "Obsidian — " + root.t("knowledge / jegyzetek", "knowledge / notes")
                                checked: root.settings.value("integrations/obsidianEnabled", true)
                                onToggled: root.settings.setValue("integrations/obsidianEnabled", checked)
                            }

                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                color: root.textMuted
                                text: root.t("Alap szerepek: LibreOffice = dokumentumszerkesztő, Obsidian = knowledge/notes workspace. A canonical Knowledge/Memory authority nem változik.", "Default roles: LibreOffice = document editor, Obsidian = knowledge/notes workspace. Canonical Knowledge/Memory authority is unchanged.")
                            }
                        }
                    }

                    Item { Layout.preferredHeight: 20 }
                }
            }

            ScrollView {
                id: publishingView
                contentWidth: availableWidth

                ColumnLayout {
                    width: publishingView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Publikálás", "Publishing")
                        subtitle: root.t("Publikálási célok és preferenciák. Token, jelszó, cookie vagy API secret nem tárolható QSettings-ben.", "Publishing targets and preferences. Tokens, passwords, cookies and API secrets are never stored in QSettings.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(370 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Alap cél", "Default target") }
                            ComboBox {
                                model: ["None", "YouTube", "Facebook", "TikTok", "Website"]
                                currentIndex: 0
                                onActivated: root.settings.setValue("publishing/defaultTarget", currentText)
                            }

                            Label { text: "YouTube" }
                            Switch {
                                checked: root.settings.value("publishing/youtubeEnabled", false)
                                onToggled: root.settings.setValue("publishing/youtubeEnabled", checked)
                            }

                            Label { text: "Facebook" }
                            Switch {
                                checked: root.settings.value("publishing/facebookEnabled", false)
                                onToggled: root.settings.setValue("publishing/facebookEnabled", checked)
                            }

                            Label { text: "TikTok" }
                            Switch {
                                checked: root.settings.value("publishing/tiktokEnabled", false)
                                onToggled: root.settings.setValue("publishing/tiktokEnabled", checked)
                            }

                            Label { text: root.t("Saját weboldal", "Own website") }
                            Switch {
                                checked: root.settings.value("publishing/websiteEnabled", false)
                                onToggled: root.settings.setValue("publishing/websiteEnabled", checked)
                            }

                            Label { text: root.t("Weboldal URL", "Website URL") }
                            TextField {
                                Layout.fillWidth: true
                                text: root.settings.value("publishing/websiteUrl", "")
                                placeholderText: "https://example.com"
                                onEditingFinished: root.settings.setValue("publishing/websiteUrl", text)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: hdrView
                contentWidth: availableWidth

                ColumnLayout {
                    width: hdrView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "HDR"
                        subtitle: root.t("Fenntartott beállítási pont a később meghatározandó HDR workflow-hoz.", "Reserved settings surface for the HDR workflow to be specified later.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(190 * root.uiScale)

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18

                            Label {
                                text: "RESERVED"
                                color: root.accent
                                font.bold: true
                            }

                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                color: root.textMuted
                                text: root.t("Itt egyelőre nincs automatikus funkció vagy policy. A HDR követelményeit külön fogjuk rögzíteni.", "No automatic function or policy is assigned here yet. HDR requirements will be defined separately.")
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: mentorSettingsView
                contentWidth: availableWidth

                ColumnLayout {
                    width: mentorSettingsView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "AI Mentor"
                        subtitle: root.t("Tanulási és magyarázati preferenciák.", "Teaching and explanation preferences.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(300 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Engedélyezve", "Enabled") }
                            Switch {
                                checked: root.settings.value("mentor/enabled", true)
                                onToggled: root.settings.setValue("mentor/enabled", checked)
                            }

                            Label { text: root.t("Profil", "Profile") }
                            ComboBox {
                                model: ["Teacher", "Guided Learning", "Expert Assistant", "Study", "Custom"]
                                currentIndex: 2
                                onActivated: root.settings.setValue("mentor/profile", currentText)
                            }

                            Label { text: root.t("Kezdeményezés", "Initiative") }
                            ComboBox {
                                model: ["Silent", "Conservative", "Balanced", "Proactive"]
                                currentIndex: 2
                                onActivated: root.settings.setValue("mentor/initiative", currentText)
                            }

                            Label { text: "Practice Lab" }
                            Switch {
                                checked: root.settings.value("mentor/practiceLab", true)
                                onToggled: root.settings.setValue("mentor/practiceLab", checked)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: coachSettingsView
                contentWidth: availableWidth

                ColumnLayout {
                    width: coachSettingsView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "AI Coach"
                        subtitle: root.t("Cél-, haladás- és végrehajtási támogatás; nem Mentor profil.", "Goal, progress and execution guidance; not a Mentor profile.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(300 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Engedélyezve", "Enabled") }
                            Switch {
                                checked: root.settings.value("coach/enabled", true)
                                onToggled: root.settings.setValue("coach/enabled", checked)
                            }

                            Label { text: root.t("Profil", "Profile") }
                            ComboBox {
                                model: ["Supportive", "Structured", "Performance", "Critical Reviewer", "Executive", "Custom"]
                                currentIndex: 4
                                onActivated: root.settings.setValue("coach/profile", currentText)
                            }

                            Label { text: root.t("Proaktivitás", "Proactivity") }
                            ComboBox {
                                model: ["Silent", "Advisory", "Balanced", "Proactive", "Strict"]
                                currentIndex: 2
                                onActivated: root.settings.setValue("coach/proactivity", currentText)
                            }

                            Label { text: root.t("Mentor referral", "Mentor referrals") }
                            Switch {
                                checked: root.settings.value("coach/mentorReferrals", true)
                                onToggled: root.settings.setValue("coach/mentorReferrals", checked)
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: updatesView
                contentWidth: availableWidth

                ColumnLayout {
                    width: updatesView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Frissítés", "Updates")
                        subtitle: root.t("A Control Center frissítési preferenciái. A GUI nem kap automatikus root jogot.", "Control Center update preferences. The GUI never receives automatic root privileges.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(300 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Telepített verzió", "Installed version") }
                            Label { text: Qt.application.version }

                            Label { text: root.t("Csatorna", "Channel") }
                            ComboBox {
                                model: ["Stable", "Preview"]
                                currentIndex: root.settings.value("updates/channel", "Stable") === "Preview" ? 1 : 0
                                onActivated: root.settings.setValue("updates/channel", currentText)
                            }

                            Label { text: root.t("Automatikus ellenőrzés", "Automatic check") }
                            Switch {
                                checked: root.settings.value("updates/autoCheck", true)
                                onToggled: root.settings.setValue("updates/autoCheck", checked)
                            }

                            Label { text: root.t("Preview GUI build-ek", "Preview GUI builds") }
                            Switch {
                                checked: root.settings.value("updates/includeGuiPreviews", false)
                                onToggled: root.settings.setValue("updates/includeGuiPreviews", checked)
                            }

                            Button {
                                text: root.t("Frissítés keresése", "Check for updates")
                                onClicked: root.updateMessage = root.t("Az update adapter még nincs runtime-promotálva; automatikus root telepítés nincs.", "The update adapter is not runtime-promoted yet; there is no automatic root installation.")
                            }

                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                color: root.textMuted
                                text: root.updateMessage
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: aboutView
                contentWidth: availableWidth

                ColumnLayout {
                    width: aboutView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Névjegy", "About")
                        subtitle: "FINAL ARCHITECTURE v3.0 — Control Center"
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(360 * root.uiScale)

                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24

                            Label { text: root.t("Alkalmazás", "Application") }
                            Label { text: "FA3 Control Center" }

                            Label { text: root.t("Verzió", "Version") }
                            Label { text: Qt.application.version }

                            Label { text: "Canonical capabilities" }
                            Label { text: "143" }

                            Label { text: root.t("Új authority", "New authority") }
                            Label { text: "0" }

                            Label { text: root.t("Repository", "Repository") }
                            Label {
                                Layout.fillWidth: true
                                text: root.repository.repoRoot
                                elide: Text.ElideMiddle
                            }

                            Label { text: root.t("Host", "Host") }
                            Label { text: root.repository.hostName }

                            Label { text: root.t("Runtime státusz", "Runtime status") }
                            Label { text: "PENDING_CURRENT_HOST"; color: "#d99b32" }

                            Label { text: root.t("Konfiguráció", "Configuration") }
                            Label {
                                Layout.fillWidth: true
                                text: root.settings.configFilePath
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: advancedView
                contentWidth: availableWidth

                ColumnLayout {
                    width: advancedView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }

                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Haladó", "Advanced")
                        subtitle: root.t("Lokális GUI state visszaállítása. Canonical/Evidence/Memory/project adat nem törlődik.", "Local GUI state reset. Canonical/Evidence/Memory/project data is never deleted.")
                    }

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(360 * root.uiScale)

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10

                            Button {
                                text: root.t("Gyorsbillentyűk alaphelyzetbe", "Reset shortcuts")
                                onClicked: root.settings.resetGroup("shortcuts")
                            }

                            Button {
                                text: root.t("Integrációk alaphelyzetbe", "Reset integrations")
                                onClicked: root.settings.resetGroup("integrations")
                            }

                            Button {
                                text: root.t("Publikálás alaphelyzetbe", "Reset publishing")
                                onClicked: root.settings.resetGroup("publishing")
                            }

                            Button {
                                text: root.t("Mentor preferenciák alaphelyzetbe", "Reset Mentor preferences")
                                onClicked: root.settings.resetGroup("mentor")
                            }

                            Button {
                                text: root.t("Coach preferenciák alaphelyzetbe", "Reset Coach preferences")
                                onClicked: root.settings.resetGroup("coach")
                            }

                            Button {
                                text: root.t("Minden GUI-beállítás alaphelyzetbe…", "Reset all GUI settings…")
                                onClicked: resetDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: resetDialog
        title: root.t("GUI-beállítások visszaállítása", "Reset GUI settings")
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel

        Label {
            width: 440
            wrapMode: Text.WordWrap
            text: root.t("Ez csak a Control Center lokális felhasználói preferenciáit törli. Canonical, Evidence, Memory vagy projektadatot nem módosít.", "This clears only local Control Center preferences. Canonical, Evidence, Memory and project data are not modified.")
        }

        onAccepted: root.settings.resetAll()
    }
}
