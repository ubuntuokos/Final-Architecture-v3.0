import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color canvas: "#07111f"
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

    component Panel: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    component SectionLabel: Label {
        color: root.textPrimary
        font.pixelSize: 15
        font.weight: Font.DemiBold
    }

    component MutedLabel: Label {
        color: root.textMuted
        font.pixelSize: 11
    }

    component StatusDot: Rectangle {
        property color dotColor: root.green
        implicitWidth: 7
        implicitHeight: 7
        radius: 4
        color: dotColor
    }

    component ProgressMeter: Item {
        property real value: 0.0
        property color meterColor: root.accent
        implicitHeight: 6
        implicitWidth: 160
        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: "#16263a"
        }
        Rectangle {
            width: Math.max(0, Math.min(parent.width, parent.width * parent.value))
            height: parent.height
            radius: height / 2
            color: parent.meterColor
        }
    }

    component StatCard: Panel {
        property string iconText: "◉"
        property string titleText: ""
        property string valueText: "—"
        property string noteText: ""
        property color tone: root.accent
        implicitHeight: 124

        RowLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 13
            Rectangle {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                radius: 8
                color: Qt.rgba(parent.parent.tone.r, parent.parent.tone.g, parent.parent.tone.b, 0.12)
                Label {
                    anchors.centerIn: parent
                    text: parent.parent.iconText
                    color: parent.parent.tone
                    font.pixelSize: 18
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                MutedLabel { text: parent.parent.parent.titleText.toUpperCase(); font.pixelSize: 9; font.bold: true }
                Label { text: parent.parent.parent.valueText; color: root.textPrimary; font.pixelSize: 24; font.bold: true }
                MutedLabel { text: parent.parent.parent.noteText; Layout.fillWidth: true; elide: Text.ElideRight }
            }
        }
    }

    component MiniLineChart: Canvas {
        property color lineColor: root.cyan
        property var samples: [0.22, 0.30, 0.25, 0.38, 0.32, 0.48, 0.40, 0.51, 0.44, 0.62, 0.49, 0.67, 0.58, 0.73, 0.63, 0.70]
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.strokeStyle = "#17314d"
            ctx.lineWidth = 1
            for (var gy = 1; gy < 4; ++gy) {
                var y = height * gy / 4
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
            }
            ctx.strokeStyle = lineColor
            ctx.lineWidth = 2
            ctx.beginPath()
            for (var i = 0; i < samples.length; ++i) {
                var x = samples.length > 1 ? i * width / (samples.length - 1) : 0
                var py = height - (samples[i] * height)
                if (i === 0) ctx.moveTo(x, py); else ctx.lineTo(x, py)
            }
            ctx.stroke()
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 12

        ScrollView {
            id: dashboardScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth

            ColumnLayout {
                width: dashboardScroll.availableWidth
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 4
                    Layout.rightMargin: 4
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Label { text: "Dashboard"; color: root.textPrimary; font.pixelSize: 23; font.bold: true }
                        MutedLabel { text: "Command Center · canonical state, host context and operator focus" }
                    }
                    RowLayout {
                        spacing: 7
                        StatusDot { dotColor: root.green }
                        Label { text: "System Online"; color: root.green; font.pixelSize: 11; font.bold: true }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 225
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            spacing: 10
                            SectionLabel { text: "System Health" }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 18
                                Item {
                                    Layout.preferredWidth: 126
                                    Layout.preferredHeight: 126
                                    Canvas {
                                        anchors.fill: parent
                                        onPaint: {
                                            var ctx = getContext("2d")
                                            ctx.clearRect(0, 0, width, height)
                                            var cx = width / 2, cy = height / 2, r = Math.min(width, height) * 0.38
                                            ctx.lineWidth = 9
                                            ctx.strokeStyle = "#17283b"
                                            ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke()
                                            ctx.strokeStyle = root.green
                                            ctx.lineCap = "round"
                                            ctx.beginPath(); ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI * 1.35); ctx.stroke()
                                        }
                                    }
                                    Column {
                                        anchors.centerIn: parent
                                        spacing: 1
                                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: "143"; color: root.textPrimary; font.pixelSize: 23; font.bold: true }
                                        MutedLabel { anchors.horizontalCenter: parent.horizontalCenter; text: "CAPABILITIES"; font.pixelSize: 8 }
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 9
                                    RowLayout { StatusDot {}; Label { text: "Canonical Registry"; color: root.textPrimary; font.pixelSize: 11 }; Item { Layout.fillWidth: true }; Label { text: fa3Repository.canonicalRecordCount; color: root.textMuted; font.pixelSize: 11 } }
                                    RowLayout { StatusDot {}; Label { text: "Providers"; color: root.textPrimary; font.pixelSize: 11 }; Item { Layout.fillWidth: true }; Label { text: fa3Repository.providerCount; color: root.textMuted; font.pixelSize: 11 } }
                                    RowLayout { StatusDot { dotColor: fa3Repository.pendingCount > 0 ? root.orange : root.green }; Label { text: "Pending"; color: root.textPrimary; font.pixelSize: 11 }; Item { Layout.fillWidth: true }; Label { text: fa3Repository.pendingCount; color: fa3Repository.pendingCount > 0 ? root.orange : root.green; font.pixelSize: 11; font.bold: true } }
                                    RowLayout { StatusDot {}; Label { text: "Evidence"; color: root.textPrimary; font.pixelSize: 11 }; Item { Layout.fillWidth: true }; Label { text: fa3Repository.evidenceCount; color: root.textMuted; font.pixelSize: 11 } }
                                }
                            }
                        }
                    }

                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 225
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            spacing: 10
                            RowLayout { SectionLabel { text: "Active Models" }; Item { Layout.fillWidth: true }; Label { text: "Registry"; color: root.accent; font.pixelSize: 10; font.bold: true } }
                            Repeater {
                                model: [
                                    {name: "Ollama Runtime", role: "LOCAL INFERENCE", color: root.accent, v: 0.72},
                                    {name: "Model Registry", role: "CANONICAL", color: root.green, v: 0.86},
                                    {name: "Provider Fabric", role: "ROUTED", color: root.magenta, v: 0.64}
                                ]
                                delegate: ColumnLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: 4
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Rectangle { width: 8; height: 8; radius: 4; color: modelData.color }
                                        Label { text: modelData.name; color: root.textPrimary; font.pixelSize: 11; font.bold: true }
                                        Item { Layout.fillWidth: true }
                                        Label { text: modelData.role; color: root.textMuted; font.pixelSize: 8; font.bold: true }
                                    }
                                    ProgressMeter { Layout.fillWidth: true; value: modelData.v; meterColor: modelData.color }
                                }
                            }
                        }
                    }

                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 225
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            spacing: 10
                            SectionLabel { text: "Resource Allocation" }
                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                columnSpacing: 16
                                rowSpacing: 12
                                MutedLabel { text: "CPU THREADS" }
                                Label { text: fa3Repository.cpuThreads.toString(); color: root.cyan; font.pixelSize: 18; font.bold: true; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                                MutedLabel { text: "MEMORY" }
                                Label { text: fa3Repository.memoryGiB.toFixed(1) + " GiB"; color: root.accent; font.pixelSize: 18; font.bold: true; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                                MutedLabel { text: "GPU TELEMETRY" }
                                Label { text: "adapter-gated"; color: root.orange; font.pixelSize: 11; font.bold: true; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true }
                                MutedLabel { text: "HOST" }
                                Label { text: fa3Repository.hostName; color: root.textPrimary; font.pixelSize: 11; horizontalAlignment: Text.AlignRight; Layout.fillWidth: true; elide: Text.ElideRight }
                            }
                            Item { Layout.fillHeight: true }
                            MutedLabel { text: "No synthetic utilization values are shown."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    StatCard { Layout.fillWidth: true; iconText: "CPU"; titleText: "Processor"; valueText: fa3Repository.cpuThreads + " threads"; noteText: fa3Repository.kernelVersion; tone: root.cyan }
                    StatCard { Layout.fillWidth: true; iconText: "RAM"; titleText: "Memory"; valueText: fa3Repository.memoryGiB.toFixed(1) + " GiB"; noteText: "physical host memory"; tone: root.accent }
                    StatCard { Layout.fillWidth: true; iconText: "GPU"; titleText: "Accelerator"; valueText: "HRB gated"; noteText: "GPU / NPU admission surface"; tone: root.magenta }
                    StatCard { Layout.fillWidth: true; iconText: "✓"; titleText: "Evidence"; valueText: fa3Repository.evidenceCount.toString(); noteText: "repository evidence records"; tone: root.green }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1.65
                        Layout.preferredHeight: 248
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            spacing: 8
                            RowLayout {
                                SectionLabel { text: "System Resources" }
                                Item { Layout.fillWidth: true }
                                Rectangle { width: 7; height: 7; radius: 4; color: root.cyan }
                                MutedLabel { text: "CPU context" }
                                Rectangle { width: 7; height: 7; radius: 4; color: root.magenta }
                                MutedLabel { text: "accelerator lane" }
                            }
                            MiniLineChart { Layout.fillWidth: true; Layout.fillHeight: true; lineColor: root.cyan }
                            RowLayout {
                                Layout.fillWidth: true
                                MutedLabel { text: "60s" }
                                Item { Layout.fillWidth: true }
                                MutedLabel { text: "30s" }
                                Item { Layout.fillWidth: true }
                                MutedLabel { text: "now" }
                            }
                        }
                    }

                    Panel {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 248
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            spacing: 6
                            SectionLabel { text: "Recent Activity" }
                            Repeater {
                                model: [
                                    {title: "Canonical state refreshed", meta: fa3Repository.lastRefresh, c: root.green},
                                    {title: "Provider registry projected", meta: fa3Repository.providerCount + " providers", c: root.accent},
                                    {title: "Evidence inventory indexed", meta: fa3Repository.evidenceCount + " records", c: root.magenta},
                                    {title: "Host context available", meta: fa3Repository.hostName, c: root.cyan}
                                ]
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 38
                                    Rectangle { width: 8; height: 8; radius: 4; color: modelData.c }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1
                                        Label { text: modelData.title; color: root.textPrimary; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                        MutedLabel { text: modelData.meta; elide: Text.ElideRight; Layout.fillWidth: true; font.pixelSize: 9 }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Panel {
            Layout.preferredWidth: 292
            Layout.fillHeight: true
            color: "#091523"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                RowLayout {
                    spacing: 9
                    Rectangle {
                        width: 30; height: 30; radius: 15
                        color: Qt.rgba(root.magenta.r, root.magenta.g, root.magenta.b, 0.15)
                        Label { anchors.centerIn: parent; text: "✦"; color: root.magenta; font.pixelSize: 16 }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Label { text: "FA3 Assistant"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        RowLayout { spacing: 5; StatusDot {}; MutedLabel { text: "Online"; color: root.green; font.pixelSize: 9 } }
                    }
                    ToolButton { text: "×"; enabled: false }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: root.border }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    ColumnLayout {
                        width: parent.width
                        spacing: 11
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: assistantIntro.implicitHeight + 24
                            radius: 9
                            color: root.panelRaised
                            Label {
                                id: assistantIntro
                                anchors.fill: parent
                                anchors.margins: 12
                                text: "Hello. I can help you inspect FA3 state, providers, evidence and current operator actions from this control surface."
                                color: root.textPrimary
                                wrapMode: Text.WordWrap
                                font.pixelSize: 10
                            }
                        }
                        MutedLabel { text: "QUICK ACTIONS"; font.pixelSize: 8; font.bold: true }
                        Repeater {
                            model: ["Summarize system state", "Inspect pending evidence", "Show provider inventory"]
                            delegate: Rectangle {
                                required property string modelData
                                Layout.fillWidth: true
                                implicitHeight: 38
                                radius: 7
                                color: "#0d1c2f"
                                border.color: root.border
                                Label { anchors.fill: parent; anchors.margins: 10; text: modelData; color: root.textPrimary; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 54
                    radius: 8
                    color: "#0d1c2f"
                    border.color: root.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        TextField {
                            Layout.fillWidth: true
                            placeholderText: "Ask about FA3…"
                            color: root.textPrimary
                            background: Item {}
                            enabled: false
                        }
                        Rectangle {
                            width: 30; height: 30; radius: 6; color: root.accent
                            Label { anchors.centerIn: parent; text: "➤"; color: "white"; font.pixelSize: 12 }
                        }
                    }
                }
                MutedLabel { text: "Assistant execution remains policy-gated."; font.pixelSize: 8; Layout.alignment: Qt.AlignHCenter }
            }
        }
    }
}
