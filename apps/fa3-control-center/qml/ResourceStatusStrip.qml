import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    required property var telemetry
    required property color textPrimary
    required property color textMuted
    required property color accent
    height: 38
    color: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.035)
    border.color: Qt.rgba(textPrimary.r, textPrimary.g, textPrimary.b, 0.14)

    function pct(v) { return v < 0 ? "—" : Math.round(v) + "%" }
    function gib(v) { return v < 0 ? "—" : v.toFixed(v >= 100 ? 0 : 1) + "G" }
    function gpuDetail() {
        var p=[]
        if (telemetry.gpuMemoryTotalGiB > 0) p.push(gib(telemetry.gpuMemoryUsedGiB)+"/"+gib(telemetry.gpuMemoryTotalGiB))
        if (telemetry.gpuTemperatureC >= 0) p.push(Math.round(telemetry.gpuTemperatureC)+"°C")
        return p.join(" · ")
    }

    component Cell: RowLayout {
        required property string name
        required property string value
        property string detail: ""
        spacing: 5
        Label { text: parent.name; color: root.textMuted; font.pixelSize: 10; font.bold: true }
        Label { text: parent.value; font.pixelSize: 12; font.bold: true }
        Label { visible: parent.detail.length>0; text: parent.detail; color: root.textMuted; font.pixelSize: 10 }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        spacing: 12
        Label { text: "HOST"; color: root.accent; font.bold: true; font.pixelSize: 10 }
        Cell { name: "CPU"; value: root.pct(root.telemetry.cpuPercent) }
        Rectangle { width: 1; height: 18; color: root.border.color }
        Cell { name: "GPU"; value: root.telemetry.gpuAvailable ? root.pct(root.telemetry.gpuPercent) : "N/A"; detail: root.telemetry.gpuAvailable ? root.gpuDetail() : "" }
        Rectangle { width: 1; height: 18; color: root.border.color }
        Cell { name: "NPU"; value: root.telemetry.npuAvailable ? root.pct(root.telemetry.npuPercent) : "N/A"; detail: root.telemetry.npuAvailable && root.telemetry.npuPercent < 0 ? "detected" : "" }
        Rectangle { width: 1; height: 18; color: root.border.color }
        Cell { name: "RAM"; value: root.pct(root.telemetry.ramPercent); detail: root.telemetry.ramTotalGiB>0 ? root.gib(root.telemetry.ramUsedGiB)+"/"+root.gib(root.telemetry.ramTotalGiB) : "" }
        Item { Layout.fillWidth: true }
        Rectangle { width: 8; height: 8; radius: 4; color: root.telemetry.pressureState === "CRITICAL" ? "#d9534f" : root.telemetry.pressureState === "WARN" ? "#d99b32" : root.accent }
        Label { text: root.telemetry.pressureState; font.bold: true; font.pixelSize: 10; ToolTip.visible: pressureHover.hovered; ToolTip.text: root.telemetry.pressureSummary + " · read-only · HRB admission"; HoverHandler { id: pressureHover } }
    }
}
