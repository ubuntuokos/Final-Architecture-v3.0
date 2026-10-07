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
    property bool compactNavigation: false
    property bool statusStripVisible: true

    signal compactNavigationRequested(bool enabled)
    signal statusStripRequested(bool enabled)
    signal navigateRequested(int pageIndex)

    property int selectedIndex: 0
    property string draftResult: ""
    property string shortcutMessage: ""
    property var sections: [
        {title: "Appearance", badge: "GUI", tone: root.accent, detail: "Színes téma, navigáció és a Control Center felületi beállításai."},
        {title: "Chat Style", badge: "CHAT", tone: root.cyan, detail: "Beszélgetési nézet, tipográfia és message-flow preferenciák."},
        {title: "Reasoning", badge: "CHAT", tone: root.magenta, detail: "Reasoning blokk megjelenítési preferenciák."},
        {title: "Gyorsbillentyűk", badge: "INPUT", tone: root.green, detail: "Perzisztens, konfliktus-ellenőrzött FA3 Control Center billentyűparancsok."},
        {title: "Compute & Accelerators", badge: "GATED", tone: root.orange, detail: "CPU / GPU / NPU / DGX felderítés és brokerelt erőforrás-policy."},
        {title: "Kamera / Print / Scan", badge: "DEVICE", tone: root.cyan, detail: "Webkamera, nyomtató és scanner read-only felderítése és adapter policy."},
        {title: "MIDI & Control Surfaces", badge: "MIDI", tone: root.green, detail: "ALSA MIDI felderítés és GIMP / Ardour control-surface mapping intent."},
        {title: "Hálózat", badge: "POLICY", tone: root.cyan, detail: "Lokális és jóváhagyott távoli provider-hozzáférés."},
        {title: "Biztonság", badge: "FAIL-CLOSED", tone: root.magenta, detail: "Approval, secret-metadata és security policy."},
        {title: "Frissítések", badge: "CONTROLLED", tone: root.green, detail: "Komponens- és provider-frissítési preferenciák."},
        {title: "Naplózás", badge: "JOURNAL", tone: root.accent, detail: "Retention, export és archive-kezelési preferenciák."}
    ]
    property var shortcutDefinitions: [
        {key: "shortcuts/dashboard", label: "Dashboard", fallback: "Ctrl+1"},
        {key: "shortcuts/projects", label: "Projects", fallback: "Ctrl+2"},
        {key: "shortcuts/aiStudio", label: "AI Studio", fallback: "Ctrl+3"},
        {key: "shortcuts/search", label: "Keresés", fallback: "Ctrl+K"},
        {key: "shortcuts/settings", label: "Rendszerbeállítások", fallback: "Ctrl+,"},
        {key: "shortcuts/toggleStatus", label: "Alsó állapotsáv ki/be", fallback: "Ctrl+Shift+S"}
    ]

    function preference(key, fallback) {
        return fa3Preferences.value(key, fallback)
    }

    function savePreference(key, value) {
        fa3Preferences.setValue(key, value)
    }

    function createDraft(scope, action, target, rationale) {
        draftResult = fa3Repository.createDraftChangeSet(scope, action, target, rationale)
    }

    function deviceRows(kind) {
        var generation = fa3Devices.inventory
        return fa3Devices.byKind(kind)
    }

    function statusTone(status) {
        if (status === "DISCOVERED") return root.green
        if (status === "ADAPTER-GATED") return root.orange
        return root.textMuted
    }

    function shortcutValue(definition) {
        return String(preference(definition.key, definition.fallback))
    }

    function saveShortcut(key, sequence) {
        var normalized = fa3Preferences.normalizeShortcut(sequence)
        if (sequence.trim().length > 0 && normalized.length === 0) {
            shortcutMessage = "Érvénytelen billentyűkombináció: " + sequence
            return "__ERROR__"
        }
        if (normalized.length > 0) {
            for (var i = 0; i < shortcutDefinitions.length; ++i) {
                var def = shortcutDefinitions[i]
                if (def.key === key) continue
                var other = fa3Preferences.normalizeShortcut(shortcutValue(def))
                if (other.length > 0 && other === normalized) {
                    shortcutMessage = "Konfliktus: " + normalized + " már a(z) " + def.label + " művelethez van rendelve."
                    return "__ERROR__"
                }
            }
        }
        savePreference(key, normalized)
        shortcutMessage = normalized.length > 0 ? ("Mentve: " + normalized) : "A gyorsbillentyű letiltva."
        return normalized
    }

    component SettingLine: ColumnLayout {
        property string labelText: ""
        property string helpText: ""
        Layout.fillWidth: true
        spacing: 2
        Label {
            text: parent.labelText
            color: root.textPrimary
            font.pixelSize: 11
            font.bold: true
            Layout.fillWidth: true
        }
        Label {
            text: parent.helpText
            color: root.textMuted
            font.pixelSize: 9
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    component DeviceList: ColumnLayout {
        property string kind: ""
        property string titleText: kind
        Layout.fillWidth: true
        spacing: 6
        Label {
            text: parent.titleText
            color: root.textPrimary
            font.pixelSize: 11
            font.bold: true
        }
        Repeater {
            model: root.deviceRows(parent.kind)
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                implicitHeight: 46
                radius: 6
                color: root.panelRaised
                border.color: root.border
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 8
                    Rectangle { width: 7; height: 7; radius: 4; color: root.statusTone(modelData.status) }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: modelData.detail; color: root.textMuted; font.pixelSize: 8; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Label { text: modelData.status; color: root.statusTone(modelData.status); font.pixelSize: 8; font.bold: true }
                }
            }
        }
    }

    component ShortcutEditor: RowLayout {
        property string prefKey: ""
        property string titleText: ""
        property string fallback: ""
        Layout.fillWidth: true
        spacing: 10
        Label { text: parent.titleText; color: root.textPrimary; font.pixelSize: 10; Layout.preferredWidth: 180 }
        TextField {
            id: shortcutField
            Layout.preferredWidth: 180
            text: String(root.preference(parent.prefKey, parent.fallback))
            placeholderText: "pl. Ctrl+K"
        }
        Button {
            text: "Mentés"
            onClicked: {
                var result = root.saveShortcut(parent.prefKey, shortcutField.text)
                if (result !== "__ERROR__") shortcutField.text = result
            }
        }
        Item { Layout.fillWidth: true }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label { text: "Rendszerbeállítások"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
            Label {
                text: "GUI-preferenciák közvetlenül és perzisztensen menthetők; host-, accelerator- és periféria-módosítások továbbra is typed ChangeSet / adapter határon maradnak."
                color: root.textMuted
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            Rectangle {
                id: categoryPane
                Layout.preferredWidth: Math.max(220, Math.min(270, root.width * 0.24))
                Layout.minimumWidth: 220
                Layout.maximumWidth: 270
                Layout.fillHeight: true
                radius: 9
                color: root.panel
                border.color: root.border
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8
                    Label { text: "Kategóriák"; color: root.textMuted; font.pixelSize: 9; font.bold: true }
                    ListView {
                        id: settingsCategoryList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 6
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.sections
                        currentIndex: root.selectedIndex
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: ListView.view.width - 10
                            height: 54
                            radius: 7
                            color: index === root.selectedIndex ? root.panelRaised : (settingsMouse.containsMouse ? "#10233a" : "transparent")
                            border.color: index === root.selectedIndex ? modelData.tone : "transparent"
                            border.width: index === root.selectedIndex ? 1 : 0
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8
                                Rectangle { width: 7; height: 7; radius: 4; color: modelData.tone }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 11; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Label { text: modelData.badge; color: modelData.tone; font.pixelSize: 7; font.bold: true }
                                    }
                                    Label { text: modelData.detail; color: root.textMuted; font.pixelSize: 8; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                            }
                            MouseArea {
                                id: settingsMouse
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
                id: settingsWorkspace
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 520
                radius: 9
                color: root.panel
                border.color: root.sections[root.selectedIndex].tone
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: root.sections[root.selectedIndex].title; color: root.textPrimary; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: root.sections[root.selectedIndex].badge; color: root.sections[root.selectedIndex].tone; font.pixelSize: 9; font.bold: true }
                    }
                    Label { text: root.sections[root.selectedIndex].detail; color: root.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.border }

                    ScrollView {
                        id: settingsDetailScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn; active: true }

                        ColumnLayout {
                            width: settingsDetailScroll.availableWidth
                            spacing: 12

                            StackLayout {
                                id: settingsStack
                                Layout.fillWidth: true
                                Layout.minimumHeight: Math.max(420, settingsDetailScroll.availableHeight - 12)
                                currentIndex: root.selectedIndex

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine { labelText: "Színes téma"; helpText: "Az FA3 accent-színét azonnal módosítja és QSettings-ben perzisztensen menti." }
                                    ComboBox {
                                        id: colorTheme
                                        property var options: ["Blue", "Cyan", "Green", "Magenta", "Amber"]
                                        Layout.preferredWidth: 220
                                        model: options
                                        Component.onCompleted: currentIndex = Math.max(0, options.indexOf(String(root.preference("appearance/colorTheme", "Blue"))))
                                        onActivated: root.savePreference("appearance/colorTheme", currentText)
                                    }
                                    SettingLine { labelText: "Navigation Bar position"; helpText: "A fő navigáció bal vagy jobb oldalra helyezhető." }
                                    ComboBox {
                                        id: navigationPosition
                                        property var options: ["Left", "Right"]
                                        Layout.preferredWidth: 220
                                        model: options
                                        Component.onCompleted: currentIndex = Math.max(0, options.indexOf(String(root.preference("appearance/navigationBarPosition", "Left"))))
                                        onActivated: root.savePreference("appearance/navigationBarPosition", currentText)
                                    }
                                    SettingLine { labelText: "Kompakt navigáció"; helpText: "Keskenyebb oldalsávot és sűrűbb menüt használ." }
                                    Switch {
                                        text: checked ? "Bekapcsolva" : "Kikapcsolva"
                                        checked: root.compactNavigation
                                        onToggled: root.compactNavigationRequested(checked)
                                    }
                                    SettingLine { labelText: "Alsó állapotsáv"; helpText: "CPU / GPU / NPU / RAM / Pressure státuszsáv megjelenítése." }
                                    Switch {
                                        text: checked ? "Látható" : "Rejtett"
                                        checked: root.statusStripVisible
                                        onToggled: root.statusStripRequested(checked)
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 11
                                    SettingLine { labelText: "Nézet mód"; helpText: "A beszélgetési renderer layout-preferenciája." }
                                    ComboBox {
                                        property var options: ["Standard", "Compact", "Reading"]
                                        Layout.preferredWidth: 220
                                        model: options
                                        Component.onCompleted: currentIndex = Math.max(0, options.indexOf(String(root.preference("chat/viewMode", "Standard"))))
                                        onActivated: root.savePreference("chat/viewMode", currentText)
                                    }
                                    Switch { text: "Show tab strip scrollbar"; checked: Boolean(root.preference("chat/showTabStripScrollbar", true)); onToggled: root.savePreference("chat/showTabStripScrollbar", checked) }
                                    RowLayout {
                                        Label { text: "Betűméret"; color: root.textPrimary; Layout.preferredWidth: 180 }
                                        SpinBox { from: 9; to: 28; value: Number(root.preference("chat/fontSize", 14)); onValueModified: root.savePreference("chat/fontSize", value) }
                                    }
                                    RowLayout {
                                        Label { text: "Font Weight"; color: root.textPrimary; Layout.preferredWidth: 180 }
                                        ComboBox {
                                            property var options: ["Normal", "Medium", "Semibold"]
                                            Layout.preferredWidth: 180
                                            model: options
                                            Component.onCompleted: currentIndex = Math.max(0, options.indexOf(String(root.preference("chat/fontWeight", "Normal"))))
                                            onActivated: root.savePreference("chat/fontWeight", currentText)
                                        }
                                    }
                                    Switch { text: "Show Gen Info"; checked: Boolean(root.preference("chat/showGenInfo", false)); onToggled: root.savePreference("chat/showGenInfo", checked) }
                                    Switch { text: "Scroll message to top on send"; checked: Boolean(root.preference("chat/scrollMessageToTopOnSend", true)); onToggled: root.savePreference("chat/scrollMessageToTopOnSend", checked) }
                                    Switch { text: "Auto-latch onto generating message"; checked: Boolean(root.preference("chat/autoLatchGenerating", true)); onToggled: root.savePreference("chat/autoLatchGenerating", checked) }
                                    RowLayout {
                                        Label { text: "Chat messages style"; color: root.textPrimary; Layout.preferredWidth: 180 }
                                        ComboBox {
                                            property var options: ["Cards", "Bubbles", "Plain"]
                                            Layout.preferredWidth: 180
                                            model: options
                                            Component.onCompleted: currentIndex = Math.max(0, options.indexOf(String(root.preference("chat/messageStyle", "Cards"))))
                                            onActivated: root.savePreference("chat/messageStyle", currentText)
                                        }
                                    }
                                    Switch { text: "Expand chat container to window width"; checked: Boolean(root.preference("chat/expandToWindowWidth", false)); onToggled: root.savePreference("chat/expandToWindowWidth", checked) }
                                    Label {
                                        text: "Ezek a preference-ek perzisztensen mentve vannak. Csak olyan chat-renderer állítható át velük, amely ezt a preference namespace-t ténylegesen fogyasztja; a GUI nem állít hamis alkalmazási állapotot."
                                        color: root.orange
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    Switch { text: "Expand reasoning blocks by default"; checked: Boolean(root.preference("reasoning/expandBlocksByDefault", false)); onToggled: root.savePreference("reasoning/expandBlocksByDefault", checked) }
                                    Switch { text: "Show reasoning block vignette"; checked: Boolean(root.preference("reasoning/showBlockVignette", true)); onToggled: root.savePreference("reasoning/showBlockVignette", checked) }
                                    Label {
                                        text: "A reasoning preference kizárólag megjelenítési beállítás. Nem változtatja meg a modellek gondolkodási módját, hozzáférését vagy policy-ját."
                                        color: root.textMuted
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 10
                                    SettingLine { labelText: "FA3 Control Center gyorsbillentyűk"; helpText: "QSettings/XDG-perzisztencia, hordozható Qt key-sequence formátum és ütközésellenőrzés. Üres érték letiltja az adott shortcutot." }
                                    ShortcutEditor { prefKey: "shortcuts/dashboard"; titleText: "Dashboard"; fallback: "Ctrl+1" }
                                    ShortcutEditor { prefKey: "shortcuts/projects"; titleText: "Projects"; fallback: "Ctrl+2" }
                                    ShortcutEditor { prefKey: "shortcuts/aiStudio"; titleText: "AI Studio"; fallback: "Ctrl+3" }
                                    ShortcutEditor { prefKey: "shortcuts/search"; titleText: "Keresés"; fallback: "Ctrl+K" }
                                    ShortcutEditor { prefKey: "shortcuts/settings"; titleText: "Rendszerbeállítások"; fallback: "Ctrl+," }
                                    ShortcutEditor { prefKey: "shortcuts/toggleStatus"; titleText: "Állapotsáv ki/be"; fallback: "Ctrl+Shift+S" }
                                    Label { text: root.shortcutMessage; visible: text.length > 0; color: text.indexOf("Konfliktus") >= 0 || text.indexOf("Érvénytelen") >= 0 ? root.orange : root.green; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Read-only host discovery"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                                        Item { Layout.fillWidth: true }
                                        Label { text: "Frissítve: " + fa3Devices.lastRefresh; color: root.textMuted; font.pixelSize: 8 }
                                        Button { text: "Újraolvasás"; onClicked: fa3Devices.refresh() }
                                    }
                                    DeviceList { kind: "CPU"; titleText: "CPU" }
                                    DeviceList { kind: "GPU"; titleText: "GPU" }
                                    DeviceList { kind: "NPU"; titleText: "NPU" }
                                    DeviceList { kind: "DGX"; titleText: "DGX / NVSwitch fabric" }
                                    RowLayout {
                                        Label { text: "Preferred accelerator"; color: root.textPrimary; Layout.preferredWidth: 180 }
                                        ComboBox {
                                            id: acceleratorPreference
                                            property var options: ["Auto", "CPU", "GPU", "NPU", "DGX"]
                                            Layout.preferredWidth: 180
                                            model: options
                                            Component.onCompleted: currentIndex = Math.max(0, options.indexOf(String(root.preference("compute/preferredAccelerator", "Auto"))))
                                            onActivated: root.savePreference("compute/preferredAccelerator", currentText)
                                        }
                                    }
                                    RowLayout {
                                        Label { text: "Erőforrás-profil"; color: root.textPrimary; Layout.preferredWidth: 180 }
                                        ComboBox { id: resourcePolicy; Layout.preferredWidth: 220; model: ["Balanced", "Interactive", "Throughput"] }
                                    }
                                    Button {
                                        text: "Accelerator policy ChangeSet-tervezet"
                                        onClicked: root.createDraft("resources", "set-accelerator-policy", acceleratorPreference.currentText,
                                                                    "Preferred accelerator: " + acceleratorPreference.currentText + "; resource profile: " + resourcePolicy.currentText + ". Resource Guardian / Accelerator Broker admission required.")
                                    }
                                    Label {
                                        text: "CPU/GPU/NPU/DGX első osztályú erőforrásként kezelendő, de a GUI nem foglal le eszközt és nem ír közvetlenül cgroup/systemd/driver állapotot. A Resource Guardian / Accelerator Broker marad az authority."
                                        color: root.orange
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "Periféria-felderítés"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                                        Item { Layout.fillWidth: true }
                                        Button { text: "Újraolvasás"; onClicked: fa3Devices.refresh() }
                                    }
                                    DeviceList { kind: "WEBCAM"; titleText: "Webkamera / V4L2 capture" }
                                    ComboBox {
                                        id: defaultCamera
                                        Layout.fillWidth: true
                                        model: root.deviceRows("WEBCAM")
                                        textRole: "title"
                                        valueRole: "id"
                                    }
                                    Button { text: "Kamera alapértelmezés mentése"; enabled: defaultCamera.count > 0; onClicked: root.savePreference("peripherals/defaultCamera", defaultCamera.currentValue) }
                                    DeviceList { kind: "PRINTER"; titleText: "Nyomtató / Qt-CUPS" }
                                    ComboBox {
                                        id: defaultPrinter
                                        Layout.fillWidth: true
                                        model: root.deviceRows("PRINTER")
                                        textRole: "title"
                                        valueRole: "id"
                                    }
                                    Button { text: "Nyomtató alapértelmezés mentése"; enabled: defaultPrinter.count > 0; onClicked: root.savePreference("peripherals/defaultPrinter", defaultPrinter.currentValue) }
                                    DeviceList { kind: "SCANNER"; titleText: "Scanner / SANE" }
                                    Button {
                                        text: "Scanner adapter ChangeSet-tervezet"
                                        onClicked: root.createDraft("peripherals", "configure-scanner-adapter", "scanner", "SANE scanner discovery/configuration requested. Read-only discovery first; no root shell or direct device mutation.")
                                    }
                                    Label {
                                        text: "A webkamera és nyomtató listázása read-only. A kiválasztás FA3 preference, nem írja át az operációs rendszer globális alapértelmezését. A scanner részletes képességfelderítése SANE adapterhez kötött."
                                        color: root.textMuted
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { text: "MIDI eszközök"; color: root.textPrimary; font.pixelSize: 12; font.bold: true }
                                        Item { Layout.fillWidth: true }
                                        Button { text: "Újraolvasás"; onClicked: fa3Devices.refresh() }
                                    }
                                    DeviceList { kind: "MIDI"; titleText: "ALSA MIDI / Sequencer" }
                                    RowLayout {
                                        Label { text: "MIDI endpoint"; color: root.textPrimary; Layout.preferredWidth: 160 }
                                        ComboBox {
                                            id: midiDevice
                                            Layout.fillWidth: true
                                            model: root.deviceRows("MIDI")
                                            textRole: "title"
                                            valueRole: "id"
                                        }
                                    }
                                    RowLayout {
                                        Label { text: "Célalkalmazás"; color: root.textPrimary; Layout.preferredWidth: 160 }
                                        ComboBox { id: midiTarget; Layout.preferredWidth: 220; model: ["GIMP", "Ardour", "Generic"] }
                                    }
                                    RowLayout {
                                        Label { text: "Mapping profil"; color: root.textPrimary; Layout.preferredWidth: 160 }
                                        TextField { id: midiProfile; Layout.fillWidth: true; text: String(root.preference("midi/profileName", "FA3 Control Surface")); placeholderText: "pl. FA3 Control Surface" }
                                    }
                                    Button {
                                        text: "MIDI mapping ChangeSet-tervezet"
                                        onClicked: {
                                            root.savePreference("midi/profileName", midiProfile.text)
                                            root.savePreference("midi/defaultDevice", midiDevice.currentValue)
                                            root.createDraft("peripherals", "configure-midi-control-surface", midiTarget.currentText,
                                                             "MIDI device: " + midiDevice.currentValue + "; profile: " + midiProfile.text + "; target: " + midiTarget.currentText + ". App-specific adapter must apply mapping.")
                                        }
                                    }
                                    Label {
                                        text: "GIMP mapping: tool / brush size / opacity / action bindings. Ardour mapping: transport / mixer / plugin parameter bindings. A Control Center csak a mapping intentet és a kiválasztott endpointot kezeli; a GIMP/Ardour adapter végzi az alkalmazásspecifikus konfigurációt."
                                        color: root.green
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: "Közvetlen ALSA-, root-shell- vagy alkalmazásfájl-módosítás nincs ebből a felületből."
                                        color: root.orange
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        Layout.fillWidth: true
                                    }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine { labelText: "Provider-hozzáférés"; helpText: "Lokális-only vagy jóváhagyott távoli provider egress-intent." }
                                    ComboBox { id: networkPolicy; Layout.preferredWidth: 310; model: ["Local only", "Approved remote providers"] }
                                    Button {
                                        text: "Hálózati policy-tervezet"
                                        onClicked: root.createDraft("network", "set-provider-egress-policy", "provider-egress", "Requested network policy: " + networkPolicy.currentText)
                                    }
                                    Label { text: "A beépített Web Workspace nem nyit külső böngészőt; a provider-egress ettől külön policy."; color: root.textMuted; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine { labelText: "Fail-closed védelem"; helpText: "Privilegizált művelet, secret vagy approval megkerülése nem állítható át ebből a GUI-ból." }
                                    CheckBox { text: "Approval required"; checked: true; enabled: false }
                                    CheckBox { text: "Secret values hidden"; checked: true; enabled: false }
                                    Button { text: "Security & Approvals megnyitása"; onClicked: root.navigateRequested(10) }
                                    Label { text: "A biztonsági authority szándékosan nem duplikálható a Rendszerbeállításokban."; color: root.magenta; font.pixelSize: 9; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine { labelText: "Frissítési csatorna"; helpText: "A választás kontrollált update-intentként kerül továbbításra." }
                                    ComboBox { id: updateChannel; Layout.preferredWidth: 240; model: ["Stable", "Preview"] }
                                    Button { text: "Frissítési tervezet"; onClicked: root.createDraft("updates", "set-update-channel", "fa3-components", "Requested update channel: " + updateChannel.currentText) }
                                    Item { Layout.fillHeight: true }
                                }

                                ColumnLayout {
                                    spacing: 12
                                    SettingLine { labelText: "Napló-retention"; helpText: "A retention módosítása Journal policy-tervezet; meglévő archívumot nem töröl közvetlenül." }
                                    RowLayout {
                                        Label { text: "Napok:"; color: root.textMuted }
                                        SpinBox { id: retentionDays; from: 7; to: 3650; value: 90; editable: true }
                                    }
                                    Button { text: "Retention-tervezet"; onClicked: root.createDraft("journal", "set-retention-days", "journal-retention", "Requested retention days: " + retentionDays.value) }
                                    Item { Layout.fillHeight: true }
                                }
                            }

                            Rectangle {
                                visible: root.draftResult.length > 0
                                Layout.fillWidth: true
                                implicitHeight: draftLabel.implicitHeight + 20
                                radius: 6
                                color: "#091624"
                                border.color: root.accent
                                Label {
                                    id: draftLabel
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: root.draftResult
                                    color: root.accent
                                    font.pixelSize: 9
                                    wrapMode: Text.WrapAnywhere
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
