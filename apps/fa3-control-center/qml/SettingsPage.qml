import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var settings
    required property color surface1
    required property color surface2
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property real uiScale
    required property real fontScale
    required property string language

    property int sectionIndex: 0
    property var sections: [
        ["appearance", t("Megjelenés", "Appearance")],
        ["locale", t("Nyelv & régió", "Language & Region")],
        ["paths", t("Könyvtárak", "Paths & Libraries")],
        ["workspace", "Workspace"],
        ["dashboard", "Dashboard"],
        ["notifications", t("Értesítések", "Notifications")],
        ["integrations", t("Integrációk", "Integrations")],
        ["mentor", "AI Mentor"],
        ["coach", "AI Coach"],
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
        implicitHeight: Math.round(116 * root.uiScale)

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
                             + " · " + Number(pathEditor.status.freeGiB).toFixed(1) + " GiB free")
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

                Label {
                    text: root.t("Beállítások", "Settings")
                    font.pixelSize: root.px(18)
                    font.bold: true
                    Layout.bottomMargin: 8
                }

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
                        subtitle: root.t("A Control Center méretezése, betűi és vizuális sűrűsége.", "Control Center scaling, typography and visual density.")
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
                            columnSpacing: 24
                            rowSpacing: 12

                            Label { text: root.t("UI méretezés", "UI scale") }
                            RowLayout {
                                Slider {
                                    id: scaleSlider
                                    from: 0.8
                                    to: 2.0
                                    stepSize: 0.05
                                    value: root.settings.uiScale
                                    Layout.preferredWidth: 260
                                    onMoved: root.settings.uiScale = value
                                }
                                Label {
                                    text: Math.round(scaleSlider.value * 100) + "%"
                                    Layout.preferredWidth: 60
                                }
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
                                currentIndex: ["system", "light", "dark"].indexOf(root.settings.themeMode)
                                onActivated: root.settings.themeMode = currentText
                            }

                            Label { text: root.t("Sűrűség", "Density") }
                            ComboBox {
                                model: ["compact", "normal", "spacious"]
                                currentIndex: ["compact", "normal", "spacious"].indexOf(root.settings.value("appearance/density", "normal"))
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

                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(130 * root.uiScale)
                        Column {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8
                            Label {
                                text: root.t("Élő előnézet", "Live preview")
                                font.bold: true
                                font.pixelSize: root.px(16)
                            }
                            Label {
                                text: root.t("A betűméret, UI-scale és téma azonnal alkalmazódik erre az ablakra.", "Font size, UI scale and theme are applied immediately.")
                                color: root.textMuted
                            }
                            ProgressBar {
                                width: parent.width
                                value: 0.68
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
                        Layout.preferredHeight: Math.round(220 * root.uiScale)
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            columnSpacing: 24
                            rowSpacing: 12
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
                            Label { text: root.t("Megjegyzés", "Note") }
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                color: root.textMuted
                                text: "FA3 IDs, ChangeSet, Evidence, Provider, Gate and canonical identifiers are never translated."
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
                        subtitle: root.t("Felhasználói path role-ok. Ez a felület nem módosít fstab-ot vagy mount policy-t.", "User path roles. This surface never edits fstab or mount policy.")
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
                        subtitle: root.t("Indulás, session restore és autosave viselkedés.", "Startup, session restore and autosave behavior.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(230 * root.uiScale)
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24
                            Label { text: root.t("Induló oldal", "Start page") }
                            ComboBox {
                                model: ["Command Center", "Projects", "AI Studio", "AI Mentor", "AI Coach", "Evidence"]
                                currentIndex: ["Command Center", "Projects", "AI Studio", "AI Mentor", "AI Coach", "Evidence"].indexOf(root.settings.value("workspace/startPage", "Command Center"))
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
                        subtitle: root.t("Operátori nézetprofil és dashboard prioritás.", "Operator view profile and dashboard priority.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(210 * root.uiScale)
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24
                            Label { text: root.t("Profil", "Profile") }
                            ComboBox {
                                model: ["Studio", "Operations", "Development", "Presentation", "Custom"]
                                currentIndex: ["Studio", "Operations", "Development", "Presentation", "Custom"].indexOf(root.settings.value("dashboard/profile", "Studio"))
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
                        subtitle: root.t("A GUI saját értesítési preferenciái.", "Notification preferences owned by the GUI.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(190 * root.uiScale)
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
                            Label {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: root.t("Mentor és Coach saját intervenciós/quiet-hours szabályt is használ.", "Mentor and Coach also use their own intervention and quiet-hours rules.")
                                color: root.textMuted
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: integrationsView
                contentWidth: availableWidth
                ColumnLayout {
                    width: integrationsView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Integrációk", "Integrations")
                        subtitle: root.t("Alapértelmezett desktop alkalmazások asset-típusonként.", "Default desktop applications by asset type.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(280 * root.uiScale)
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24
                            Label { text: "Image" }
                            TextField { Layout.fillWidth: true; text: root.settings.value("integrations/imageEditor", "Krita"); onEditingFinished: root.settings.setValue("integrations/imageEditor", text) }
                            Label { text: "Video" }
                            TextField { Layout.fillWidth: true; text: root.settings.value("integrations/videoEditor", "Kdenlive"); onEditingFinished: root.settings.setValue("integrations/videoEditor", text) }
                            Label { text: "Audio" }
                            TextField { Layout.fillWidth: true; text: root.settings.value("integrations/audioEditor", "Ardour"); onEditingFinished: root.settings.setValue("integrations/audioEditor", text) }
                            Label { text: "3D" }
                            TextField { Layout.fillWidth: true; text: root.settings.value("integrations/threeDEditor", "Bforartists"); onEditingFinished: root.settings.setValue("integrations/threeDEditor", text) }
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
                        subtitle: root.t("A Mentor felhasználói preferenciái; ezek nem authority-k.", "Mentor user preferences; these are not authorities.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(340 * root.uiScale)
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 24
                            Label { text: root.t("Engedélyezve", "Enabled") }
                            Switch { checked: root.settings.value("mentor/enabled", true); onToggled: root.settings.setValue("mentor/enabled", checked) }
                            Label { text: root.t("Profil", "Profile") }
                            ComboBox {
                                model: ["Teacher", "Coach-style Tutor", "Expert Assistant", "Study", "Custom"]
                                currentIndex: ["Teacher", "Coach-style Tutor", "Expert Assistant", "Study", "Custom"].indexOf(root.settings.value("mentor/profile", "Expert Assistant"))
                                onActivated: root.settings.setValue("mentor/profile", currentText)
                            }
                            Label { text: root.t("Kezdeményezés", "Initiative") }
                            ComboBox {
                                model: ["Silent", "Conservative", "Balanced", "Proactive"]
                                currentIndex: ["Silent", "Conservative", "Balanced", "Proactive"].indexOf(root.settings.value("mentor/initiative", "Balanced"))
                                onActivated: root.settings.setValue("mentor/initiative", currentText)
                            }
                            Label { text: "Memory policy" }
                            ComboBox {
                                model: ["Ask every time", "Ask for new categories", "Allow approved categories", "Never write memory"]
                                currentIndex: ["Ask every time", "Ask for new categories", "Allow approved categories", "Never write memory"].indexOf(root.settings.value("mentor/memoryPolicy", "Ask for new categories"))
                                onActivated: root.settings.setValue("mentor/memoryPolicy", currentText)
                            }
                            Label { text: "Mastery tracking" }
                            Switch { checked: root.settings.value("mentor/masteryTracking", true); onToggled: root.settings.setValue("mentor/masteryTracking", checked) }
                            Label { text: "Practice Lab" }
                            Switch { checked: root.settings.value("mentor/practiceLab", true); onToggled: root.settings.setValue("mentor/practiceLab", checked) }
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
                        subtitle: root.t("A Coach külön szerep: cél- és végrehajtási támogatás, nem Mentor profil.", "Coach is a separate role: goal and execution guidance, not a Mentor profile.")
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
                            Label { text: root.t("Engedélyezve", "Enabled") }
                            Switch { checked: root.settings.value("coach/enabled", true); onToggled: root.settings.setValue("coach/enabled", checked) }
                            Label { text: root.t("Profil", "Profile") }
                            ComboBox {
                                model: ["Supportive", "Structured", "Performance", "Critical Reviewer", "Executive", "Custom"]
                                currentIndex: ["Supportive", "Structured", "Performance", "Critical Reviewer", "Executive", "Custom"].indexOf(root.settings.value("coach/profile", "Executive"))
                                onActivated: root.settings.setValue("coach/profile", currentText)
                            }
                            Label { text: root.t("Proaktivitás", "Proactivity") }
                            ComboBox {
                                model: ["Silent", "Advisory", "Balanced", "Proactive", "Strict"]
                                currentIndex: ["Silent", "Advisory", "Balanced", "Proactive", "Strict"].indexOf(root.settings.value("coach/proactivity", "Balanced"))
                                onActivated: root.settings.setValue("coach/proactivity", currentText)
                            }
                            Label { text: root.t("Check-in", "Check-ins") }
                            Switch { checked: root.settings.value("coach/checkIns", true); onToggled: root.settings.setValue("coach/checkIns", checked) }
                            Label { text: root.t("Projekt awareness", "Project awareness") }
                            Switch { checked: root.settings.value("coach/projectAwareness", true); onToggled: root.settings.setValue("coach/projectAwareness", checked) }
                            Label { text: root.t("Mentor referral", "Mentor referrals") }
                            Switch { checked: root.settings.value("coach/mentorReferrals", true); onToggled: root.settings.setValue("coach/mentorReferrals", checked) }
                            Label { text: "Quiet hours" }
                            TextField { text: root.settings.value("coach/quietHours", "20:00-08:00"); onEditingFinished: root.settings.setValue("coach/quietHours", text) }
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
                        subtitle: root.t("Lokális GUI state és diagnosztikai beállítások. Canonical state-et nem töröl.", "Local GUI state and diagnostics. This never deletes canonical state.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: Math.round(250 * root.uiScale)
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            spacing: 10
                            Label { text: root.settings.configFilePath; color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideMiddle }
                            Button { text: root.t("Megjelenés alaphelyzetbe", "Reset appearance"); onClicked: root.settings.resetGroup("appearance") }
                            Button { text: root.t("Mentor preferenciák alaphelyzetbe", "Reset Mentor preferences"); onClicked: root.settings.resetGroup("mentor") }
                            Button { text: root.t("Coach preferenciák alaphelyzetbe", "Reset Coach preferences"); onClicked: root.settings.resetGroup("coach") }
                            Button { text: root.t("Minden GUI-beállítás alaphelyzetbe…", "Reset all GUI settings…"); onClicked: resetDialog.open() }
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
