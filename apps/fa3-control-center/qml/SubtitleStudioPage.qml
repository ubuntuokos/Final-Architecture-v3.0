import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Item {
 id: root
 property color panel: "#20242a"; property color panelRaised: "#292f38"; property color border: "#3a424e"; property color textPrimary: "#f1f3f7"; property color textMuted: "#a9b0bc"; property color accent: "#70a7ff"; property color green: "#76c893"
 ColumnLayout {
  anchors.fill: parent; anchors.margins: 18; spacing: 12
  RowLayout {
   Layout.fillWidth: true
   ColumnLayout { Label { text: "Subtitle Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true } Label { text: "FA3-CAPTION-SUBTITLE-001 · focused caption authoring workspace"; color: root.accent; font.pixelSize: 10; font.bold: true } }
   Item { Layout.fillWidth: true } Label { text: "STANDALONE + EMBEDDED"; color: root.green; font.bold: true }
  }
  SplitView {
   Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Horizontal
   Rectangle {
    SplitView.preferredWidth: 560; color: root.panel; border.color: root.border; radius: 8
    ColumnLayout {
     anchors.fill: parent; anchors.margins: 12; spacing: 8
     Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 250; color: "#111318"; radius: 6; Label { anchors.centerIn: parent; text: "VIDEO / IMAGE PREVIEW"; color: root.textMuted; font.pixelSize: 14 } }
     Label { text: "Waveform / caption timeline"; color: root.textMuted }
     Rectangle {
      Layout.fillWidth: true; Layout.preferredHeight: 72; color: "#14171c"; radius: 6
      Row { anchors.fill: parent; anchors.margins: 8; spacing: 6
       Repeater { model: ["00:01–00:03","00:03–00:05","00:06–00:08"]; Rectangle { width: 130; height: 44; radius: 5; color: root.panelRaised; border.color: root.accent; Label { anchors.centerIn: parent; text: modelData; color: root.textPrimary; font.pixelSize: 10 } } }
      }
     }
     RowLayout { Button { text: "Import" } Button { text: "Auto subtitle" } Button { text: "Sync" } Button { text: "Translate" } Button { text: "QC" } Button { text: "Style" } Button { text: "Export" } }
    }
   }
   Rectangle {
    SplitView.fillWidth: true; color: root.panel; border.color: root.border; radius: 8
    ColumnLayout {
     anchors.fill: parent; anchors.margins: 12; spacing: 8
     Label { text: "Caption grid"; color: root.textPrimary; font.bold: true }
     ListView {
      Layout.fillWidth: true; Layout.fillHeight: true; clip: true
      model: ListModel { ListElement { start: "00:01.000"; end: "00:02.500"; speaker: "Narrator"; caption: "Árvíztűrő tükörfúrógép." } ListElement { start: "00:03.000"; end: "00:04.250"; speaker: "Speaker 1"; caption: "Második mondat." } }
      delegate: Rectangle { width: ListView.view.width; height: 64; color: index % 2 ? root.panelRaised : root.panel
       RowLayout { anchors.fill: parent; anchors.margins: 8; Label { text: start+" → "+end; color: root.textMuted; Layout.preferredWidth: 145 } Label { text: speaker; color: root.accent; Layout.preferredWidth: 90 } TextField { text: caption; color: root.textPrimary; Layout.fillWidth: true } }
      }
     }
     Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; font.pixelSize: 10; text: "Canonical state: FA3 Caption IR. SRT/VTT/ASS/SSA/SBV/TTML are adapters, not authority. AI edits create a new revision; silent text mutation is forbidden." }
    }
   }
  }
 }
}
