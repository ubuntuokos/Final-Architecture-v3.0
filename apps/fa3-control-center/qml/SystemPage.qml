import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var repository
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
    property string lastDraft: ""
    property var sections: [
        ["overview", t("Áttekintés", "Overview")],
        ["cpu", "CPU / NUMA"],
        ["gpu", "GPU / Accelerators"],
        ["memory", t("Memória", "Memory")],
        ["storage", "Storage"],
        ["services", t("Szolgáltatások", "Services")],
        ["thermal", "Thermal & Power"],
        ["software", "Software"],
        ["maintenance", t("Karbantartás", "Maintenance")],
        ["peripherals", t("Perifériák", "Peripherals")]
    ]

    function t(hu, en) {
        return language === "en" ? en : hu
    }

    function px(value) {
        return Math.max(9, Math.round(value * fontScale))
    }

    function draft(scope, action, target, rationale) {
        lastDraft = repository.createDraftChangeSet(scope, action, target, rationale)
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

    component Metric: Card {
        property string label: ""
        property string value: ""
        property string note: ""
        implicitWidth: Math.round(210 * root.uiScale)
        implicitHeight: Math.round(106 * root.uiScale)
        Column {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 5
            Label {
                text: parent.parent.label
                color: root.textMuted
                font.pixelSize: root.px(11)
            }
            Label {
                text: parent.parent.value
                font.pixelSize: root.px(22)
                font.bold: true
                elide: Text.ElideRight
                width: parent.width
            }
            Label {
                text: parent.parent.note
                color: root.textMuted
                font.pixelSize: root.px(10)
                elide: Text.ElideRight
                width: parent.width
            }
        }
    }

    component ActionCard: Card {
        property string title: ""
        property string description: ""
        property string actionText: root.t("Javaslat készítése", "Create proposal")
        property string scope: "system-maintenance"
        property string action: "REVIEW"
        property string target: ""
        property bool actionEnabled: true
        implicitWidth: Math.round(300 * root.uiScale)
        implicitHeight: Math.round(170 * root.uiScale)
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8
            Label {
                Layout.fillWidth: true
                text: parent.parent.title
                font.bold: true
                font.pixelSize: root.px(15)
            }
            Label {
                Layout.fillWidth: true
                Layout.fillHeight: true
                text: parent.parent.description
                wrapMode: Text.WordWrap
                color: root.textMuted
                font.pixelSize: root.px(11)
            }
            Button {
                text: parent.parent.actionText
                enabled: parent.parent.actionEnabled
                onClicked: root.draft(parent.parent.scope, parent.parent.action, parent.parent.target, parent.parent.description)
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
                    text: "System"
                    font.pixelSize: root.px(18)
                    font.bold: true
                    Layout.bottomMargin: 6
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

                Button {
                    Layout.fillWidth: true
                    text: root.t("Frissítés", "Refresh")
                    onClicked: root.repository.refresh()
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.sectionIndex

            ScrollView {
                id: overviewView
                contentWidth: availableWidth
                ColumnLayout {
                    width: overviewView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Rendszer áttekintés", "System Overview")
                        subtitle: root.t("Read-only host discovery. A Control Center nem válik host-resource authority-vé.", "Read-only host discovery. The Control Center does not become host-resource authority.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        Metric { label: "Host"; value: root.repository.hostName; note: root.repository.osName }
                        Metric { label: "Kernel"; value: root.repository.kernelVersion; note: root.repository.architecture }
                        Metric { label: "CPU"; value: root.repository.cpuThreads + " threads"; note: root.repository.cpuSockets + " socket / " + root.repository.cpuCores + " cores" }
                        Metric { label: "Memory"; value: root.repository.memoryGiB.toFixed(1) + " GiB"; note: root.repository.memoryAvailableGiB.toFixed(1) + " GiB available" }
                        Metric { label: "GPU"; value: root.repository.gpuDevices.length.toString(); note: "discovered devices" }
                        Metric { label: "Uptime"; value: root.repository.uptime; note: "read-only" }
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        text: root.lastDraft.length > 0 ? root.t("Utolsó draft: ", "Last draft: ") + root.lastDraft : ""
                        color: root.accent
                        elide: Text.ElideMiddle
                    }
                }
            }

            ScrollView {
                id: cpuView
                contentWidth: availableWidth
                ColumnLayout {
                    width: cpuView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "CPU / NUMA"
                        subtitle: root.t("A fizikai CPU-topológia host discovery nézete; placement és admission továbbra is a Host Resource Broker feladata.", "Physical CPU topology discovery; placement and admission remain Host Resource Broker responsibilities.")
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: 210
                        GridLayout {
                            anchors.fill: parent
                            anchors.margins: 18
                            columns: 2
                            rowSpacing: 12
                            columnSpacing: 20
                            Label { text: root.t("Modell", "Model") }
                            Label { text: root.repository.cpuModel; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            Label { text: root.t("Socket", "Sockets") }
                            Label { text: root.repository.cpuSockets.toString() }
                            Label { text: root.t("Fizikai mag", "Physical cores") }
                            Label { text: root.repository.cpuCores.toString() }
                            Label { text: "Threads" }
                            Label { text: root.repository.cpuThreads.toString() }
                            Label { text: "NUMA" }
                            Label { text: root.t("Topology adapter következő discovery-lépés", "Topology adapter is the next discovery layer"); color: root.textMuted }
                        }
                    }
                }
            }

            ScrollView {
                id: gpuView
                contentWidth: availableWidth
                ColumnLayout {
                    width: gpuView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "GPU / Accelerators"
                        subtitle: root.t("GPU discovery közvetlenül a Linux /proc és /sys read-only rétegeiből.", "GPU discovery directly from read-only Linux /proc and /sys layers.")
                    }
                    Repeater {
                        model: root.repository.gpuDevices
                        delegate: Card {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 24
                            Layout.rightMargin: 24
                            Layout.preferredHeight: 120
                            GridLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                columns: 2
                                rowSpacing: 7
                                Label { text: modelData.name; font.bold: true; Layout.columnSpan: 2 }
                                Label { text: "Driver"; color: root.textMuted }
                                Label { text: modelData.driver || "unknown" }
                                Label { text: "Bus"; color: root.textMuted }
                                Label { text: modelData.bus || "unknown" }
                                Label { text: "Source"; color: root.textMuted }
                                Label { text: modelData.source || "read-only" }
                            }
                        }
                    }
                    Label {
                        visible: root.repository.gpuDevices.length === 0
                        Layout.leftMargin: 24
                        text: root.t("Nem találtam GPU-t a read-only discovery rétegekben.", "No GPU found in the read-only discovery layers.")
                        color: root.textMuted
                    }
                }
            }

            ScrollView {
                id: memoryView
                contentWidth: availableWidth
                ColumnLayout {
                    width: memoryView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Memória", "Memory")
                        subtitle: root.t("RAM read-only állapot; HugePages/THP/KSM mutáció továbbra is governance-gated.", "Read-only RAM state; HugePages/THP/KSM mutation remains governance-gated.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        Metric { label: "Physical RAM"; value: root.repository.memoryGiB.toFixed(1) + " GiB"; note: "/proc/meminfo" }
                        Metric { label: "Available"; value: root.repository.memoryAvailableGiB.toFixed(1) + " GiB"; note: "MemAvailable" }
                    }
                    ActionCard {
                        Layout.leftMargin: 24
                        title: "HugePages / THP / KSM"
                        description: root.t("Elemzés és módosítás csak a canonical memory-governance útvonalon.", "Analysis and changes only through the canonical memory-governance path.")
                        action: "REVIEW_MEMORY_GOVERNANCE"
                        target: "host-memory"
                    }
                }
            }

            ScrollView {
                id: storageView
                contentWidth: availableWidth
                ColumnLayout {
                    width: storageView.availableWidth
                    spacing: 12
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "Storage"
                        subtitle: root.t("Felcsatolt filesystemek QStorageInfo read-only discoveryből.", "Mounted filesystems from read-only QStorageInfo discovery.")
                    }
                    Repeater {
                        model: root.repository.storageDevices
                        delegate: Card {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 24
                            Layout.rightMargin: 24
                            Layout.preferredHeight: 105
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 14
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.name; font.bold: true }
                                    Label { text: modelData.root + " · " + modelData.filesystem; color: root.textMuted }
                                }
                                Label { text: Number(modelData.freeGiB).toFixed(1) + " / " + Number(modelData.totalGiB).toFixed(1) + " GiB free" }
                                Label { text: modelData.readOnly ? "RO" : "RW"; color: modelData.readOnly ? "#d99b32" : root.accent; font.bold: true }
                            }
                        }
                    }
                }
            }

            ScrollView {
                id: servicesView
                contentWidth: availableWidth
                ColumnLayout {
                    width: servicesView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Szolgáltatások", "Services")
                        subtitle: root.t("A lifecycle állapotot külön systemd/provider adapternek kell szolgáltatnia; a GUI nem futtat systemctl-t.", "Lifecycle state must come from a dedicated systemd/provider adapter; the GUI does not run systemctl.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        ActionCard { title: "Ollama"; description: "Runtime lifecycle projection"; action: "REQUEST_SERVICE_HEALTH"; target: "ollama" }
                        ActionCard { title: "ComfyUI"; description: "Runtime lifecycle projection"; action: "REQUEST_SERVICE_HEALTH"; target: "comfyui" }
                        ActionCard { title: "InvokeAI"; description: "Runtime lifecycle projection"; action: "REQUEST_SERVICE_HEALTH"; target: "invokeai" }
                        ActionCard { title: "Central MCP"; description: "Tool-mediation service projection"; action: "REQUEST_SERVICE_HEALTH"; target: "mcp-gateway" }
                    }
                }
            }

            ScrollView {
                id: thermalView
                contentWidth: availableWidth
                ColumnLayout {
                    width: thermalView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "Thermal & Power"
                        subtitle: root.t("A hőmérséklet/power adatok provider-neutral telemetry adapterből kerülnek ide. Nincs hardcoded GPU ordinal vagy host-specifikus policy.", "Temperature/power data belongs here via a provider-neutral telemetry adapter. No hardcoded GPU ordinal or host-specific policy.")
                    }
                    ActionCard {
                        Layout.leftMargin: 24
                        title: root.t("Thermal telemetry adapter", "Thermal telemetry adapter")
                        description: root.t("CPU package, GPU hotspot, throttling és power-limit read projection bekötése.", "Wire CPU package, GPU hotspot, throttling and power-limit read projection.")
                        action: "REQUEST_THERMAL_TELEMETRY_ADAPTER"
                        target: "host-thermal"
                    }
                }
            }

            ScrollView {
                id: softwareView
                contentWidth: availableWidth
                ColumnLayout {
                    width: softwareView.availableWidth
                    spacing: 16
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: "Software"
                        subtitle: root.t("Host és GUI software projection.", "Host and GUI software projection.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        Metric { label: "FA3 Control Center"; value: "0.3.0"; note: "Qt 6 / QML" }
                        Metric { label: "OS"; value: root.repository.osName; note: root.repository.architecture }
                        Metric { label: "Kernel"; value: root.repository.kernelVersion; note: "running" }
                        Metric { label: "Repository"; value: "LOCAL"; note: root.repository.repoRoot }
                    }
                }
            }

            ScrollView {
                id: maintenanceView
                contentWidth: availableWidth
                ColumnLayout {
                    width: maintenanceView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Karbantartás", "Maintenance")
                        subtitle: root.t("Analyze → review → typed ChangeSet. Nincs vak törlés, nincs közvetlen root végrehajtás.", "Analyze → review → typed ChangeSet. No blind deletion and no direct root execution.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        ActionCard {
                            title: "Temporary files"
                            description: root.t("/tmp, alkalmazás-temp, félbemaradt exportok és stale session maradványok elemzése.", "Analyze /tmp, application temp, incomplete exports and stale session remnants.")
                            action: "ANALYZE_TEMP_CLEANUP"
                            target: "temporary-storage"
                        }
                        ActionCard {
                            title: "Cache Manager"
                            description: root.t("CUDA/PyTorch/HF/thumbnail/QML/build cache-ek külön kategóriákban; újragenerálási költséggel.", "CUDA/PyTorch/HF/thumbnail/QML/build caches as separate categories, including regeneration cost.")
                            action: "ANALYZE_CACHE_CLEANUP"
                            target: "cache-inventory"
                        }
                        ActionCard {
                            title: "Model Runtime Cleanup"
                            description: root.t("Idle model unload, stale worker és runtime-residency ellenőrzés. A runtime authority végzi a tényleges műveletet.", "Review idle model unload, stale workers and runtime residency. Runtime authority performs any actual action.")
                            action: "REVIEW_IDLE_MODEL_UNLOAD"
                            target: "model-runtimes"
                        }
                        ActionCard {
                            title: "GPU memory"
                            description: root.t("Idle workload/model unload és graceful runtime release. Normál VRAM-takarítás nem használ GPU resetet.", "Idle workload/model unload and graceful runtime release. Routine VRAM cleanup never uses GPU reset.")
                            action: "REVIEW_GPU_MEMORY_RELEASE"
                            target: "gpu-runtime-memory"
                        }
                        ActionCard {
                            title: "Logs & journals"
                            description: root.t("Retention és méret elemzés. Evidence nem log és nem része a generic cleanupnak.", "Retention and size analysis. Evidence is not a log and is excluded from generic cleanup.")
                            action: "ANALYZE_LOG_RETENTION"
                            target: "logs"
                        }
                        ActionCard {
                            title: "Orphan workloads"
                            description: root.t("Stale Python/render/inference worker gyanúk felderítése; graceful terminate javaslat elsőként.", "Detect suspected stale Python/render/inference workers; graceful termination is proposed first.")
                            action: "ANALYZE_ORPHAN_WORKLOADS"
                            target: "workloads"
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.preferredHeight: 132
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            ColumnLayout {
                                Layout.fillWidth: true
                                Label { text: "GPU hard reset"; font.bold: true; font.pixelSize: root.px(15) }
                                Label {
                                    Layout.fillWidth: true
                                    text: root.t("LOCKED — csak végső recovery esetben, root-only bounded executorral, display/workload preflight után. Nem routine maintenance.", "LOCKED — last-resort recovery only, through a root-only bounded executor after display/workload preflight. Not routine maintenance.")
                                    color: root.textMuted
                                    wrapMode: Text.WordWrap
                                }
                            }
                            Label { text: "ROOT ONLY · LOCKED"; color: "#d99b32"; font.bold: true }
                        }
                    }
                }
            }

            ScrollView {
                id: peripheralsView
                contentWidth: availableWidth
                ColumnLayout {
                    width: peripheralsView.availableWidth
                    spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        title: root.t("Perifériák", "Peripherals")
                        subtitle: root.t("Keyboard/HID, MIDI, rajztábla, scanner/USB imaging és kamera discovery. Beállítás csak adapteren vagy ChangeSeten keresztül.", "Keyboard/HID, MIDI, drawing tablet, scanner/USB imaging and camera discovery. Configuration only through adapters or ChangeSets.")
                    }
                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        spacing: 12
                        ActionCard {
                            title: root.t("Billentyűzet & gyorsbillentyűk", "Keyboard & Hotkeys")
                            description: root.t("Programozható gombok, alkalmazás-shortcutok és input mapping. GUI-preferencia közvetlenül, rendszer mapping csak ChangeSettel.", "Programmable keys, app shortcuts and input mapping. GUI preferences direct; system mapping via ChangeSet.")
                            scope: "peripherals"
                            action: "CONFIGURE_HOTKEY_MAPPING"
                            target: "keyboard-hid"
                        }
                        ActionCard {
                            title: "MIDI"
                            description: root.t("MIDI input/output, controller mapping és DAW/AI Studio routing proposal.", "MIDI input/output, controller mapping and DAW/AI Studio routing proposal.")
                            scope: "peripherals"
                            action: "CONFIGURE_MIDI_ROUTING"
                            target: "midi"
                        }
                        ActionCard {
                            title: root.t("Rajztábla", "Drawing Tablet")
                            description: root.t("Tablet/stylus mapping, pressure/area és alkalmazásprofilok. KDE/libinput adapter szükséges a rendszer-szintű módosításhoz.", "Tablet/stylus mapping, pressure/area and application profiles. KDE/libinput adapter required for system-level changes.")
                            scope: "peripherals"
                            action: "CONFIGURE_TABLET_PROFILE"
                            target: "tablet"
                        }
                        ActionCard {
                            title: root.t("Scanner", "Scanner")
                            description: root.t("USB imaging discovery, scanner provider kiválasztás és default output/workspace beállítási javaslat.", "USB imaging discovery, scanner provider selection and default output/workspace proposal.")
                            scope: "peripherals"
                            action: "CONFIGURE_SCANNER"
                            target: "scanner"
                        }
                        ActionCard {
                            title: root.t("Webkamera / Kamera", "Webcam / Camera")
                            description: root.t("V4L2 eszköz, default kamera, felbontás/FPS/exposure profile adapteren keresztül.", "V4L2 device, default camera and resolution/FPS/exposure profile through an adapter.")
                            scope: "peripherals"
                            action: "CONFIGURE_CAMERA_PROFILE"
                            target: "camera"
                        }
                    }
                    Label {
                        Layout.leftMargin: 24
                        text: root.t("Felfedezett eszközök", "Discovered devices") + ": " + root.repository.peripheralDevices.length
                        font.bold: true
                        font.pixelSize: root.px(15)
                    }
                    Repeater {
                        model: root.repository.peripheralDevices
                        delegate: Card {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 24
                            Layout.rightMargin: 24
                            Layout.preferredHeight: 86
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12
                                Label { text: modelData.category; color: root.accent; Layout.preferredWidth: 125 }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.name; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.path + (modelData.detail ? " · " + modelData.detail : ""); color: root.textMuted; Layout.fillWidth: true; elide: Text.ElideMiddle }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
