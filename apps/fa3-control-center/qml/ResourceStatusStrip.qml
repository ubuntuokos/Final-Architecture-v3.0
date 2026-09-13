import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    SystemPalette { id: systemPalette }
    x: 0
    y: parent ? parent.height - height : 0
    width: parent ? parent.width : 0
    height: 38
    z: 1000
    color: systemPalette.window
    border.color: Qt.rgba(systemPalette.windowText.r, systemPalette.windowText.g, systemPalette.windowText.b, 0.14)

    function pct(value) {
        return value < 0 ? "—" : Math.round(value) + "%"
    }

    function gib(value) {
        return value < 0 ? "—" : value.toFixed(value >= 100 ? 0 : 1) + "G"
    }

    function gpuDetail() {
        var parts = []
        if (fa3ResourceTelemetry.gpuMemoryTotalGiB > 0)
            parts.push(gib(fa3ResourceTelemetry.gpuMemoryUsedGiB) + "/" + gib(fa3ResourceTelemetry.gpuMemoryTotalGiB))
        if (fa3ResourceTelemetry.gpuTemperatureC >= 0)
            parts.push(Math.round(fa3ResourceTelemetry.gpuTemperatureC) + "°C")
        return parts.join(" · ")
    }

    component ResourceCell: Item {
        required property string resourceName
        required property string valueText
        property string detailText: ""
        implicitWidth: detailText.length > 0 ? 176 : 112
        implicitHeight: 30

        RowLayout {
            anchors.fill: parent
            spacing: 6
            Label {
                text: parent.parent.resourceName
                color: Qt.rgba(systemPalette.windowText.r, systemPalette.windowText.g, systemPalette.windowText.b, 0.62)
                font.pixelSize: 10
                font.bold: true
            }
            Label {
                text: parent.parent.valueText
                font.pixelSize: 12
                font.bold: true
            }
            Label {
                visible: parent.parent.detailText.length > 0
                text: parent.parent.detailText
                color: Qt.rgba(systemPalette.windowText.r, systemPalette.windowText.g, systemPalette.windowText.b, 0.58)
                font.pixelSize: 10
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 14

        Label {
            text: "HOST"
            color: systemPalette.highlight
            font.pixelSize: 10
            font.bold: true
        }

        ResourceCell {
            resourceName: "CPU"
            valueText: root.pct(fa3ResourceTelemetry.cpuPercent)
        }

        Rectangle { width: 1; height: 18; color: root.border.color }

        ResourceCell {
            resourceName: "GPU"
            valueText: fa3ResourceTelemetry.gpuAvailable ? root.pct(fa3ResourceTelemetry.gpuPercent) : "N/A"
            detailText: fa3ResourceTelemetry.gpuAvailable ? root.gpuDetail() : ""
        }

        Rectangle { width: 1; height: 18; color: root.border.color }

        ResourceCell {
            resourceName: "NPU"
            valueText: fa3ResourceTelemetry.npuAvailable ? root.pct(fa3ResourceTelemetry.npuPercent) : "N/A"
            detailText: fa3ResourceTelemetry.npuAvailable && fa3ResourceTelemetry.npuPercent < 0 ? "detected" : ""
        }

        Rectangle { width: 1; height: 18; color: root.border.color }

        ResourceCell {
            resourceName: "RAM"
            valueText: root.pct(fa3ResourceTelemetry.ramPercent)
            detailText: fa3ResourceTelemetry.ramTotalGiB > 0
                        ? root.gib(fa3ResourceTelemetry.ramUsedGiB) + "/" + root.gib(fa3ResourceTelemetry.ramTotalGiB)
                        : ""
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            width: 8
            height: 8
            radius: 4
            color: fa3ResourceTelemetry.pressureState === "CRITICAL"
                   ? "#d9534f"
                   : (fa3ResourceTelemetry.pressureState === "WARN" ? "#d99b32" : systemPalette.highlight)
        }
        Label {
            text: fa3ResourceTelemetry.pressureState
            font.pixelSize: 10
            font.bold: true
            ToolTip.visible: pressureHover.hovered
            ToolTip.text: fa3ResourceTelemetry.pressureSummary + " — read-only projection; admission authority remains Host Resource Broker"
            HoverHandler { id: pressureHover }
        }
        Label {
            text: "read-only"
            color: Qt.rgba(systemPalette.windowText.r, systemPalette.windowText.g, systemPalette.windowText.b, 0.50)
            font.pixelSize: 9
        }
    }
}
