import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Item {
 id: root
 property color panel: "#20242a"; property color panelRaised: "#292f38"; property color border: "#3a424e"; property color textPrimary: "#f1f3f7"; property color textMuted: "#a9b0bc"; property color accent: "#c594ff"; property color green: "#76c893"; property color orange: "#f2b05e"
 ColumnLayout {
  anchors.fill: parent; anchors.margins: 18; spacing: 12
  RowLayout {
   Layout.fillWidth: true
   ColumnLayout { Label { text: "Narration Studio"; color: root.textPrimary; font.pixelSize: 22; font.bold: true } Label { text: "Subtitle → narration / voice-over / dubbing · delegates synthesis to FA3-VOICE-001"; color: root.accent; font.pixelSize: 10; font.bold: true } }
   Item { Layout.fillWidth: true } ComboBox { model: ["NARRATION","VOICE_OVER","DUBBING","AUDIO_DESCRIPTION_READY"] }
  }
  SplitView {
   Layout.fillWidth: true; Layout.fillHeight: true
   Rectangle {
    SplitView.preferredWidth: 520; color: root.panel; border.color: root.border; radius: 8
    ColumnLayout {
     anchors.fill: parent; anchors.margins: 12; spacing: 8
     Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 235; color: "#111318"; radius: 6; Label { anchors.centerIn: parent; text: "VIDEO PREVIEW"; color: root.textMuted } }
     Label { text: "Original audio"; color: root.textMuted } ProgressBar { Layout.fillWidth: true; value: 0.72 }
     Label { text: "Generated narration"; color: root.textMuted } ProgressBar { Layout.fillWidth: true; value: 0.56 }
     RowLayout { Button { text: "Import captions" } Button { text: "Speaker map" } Button { text: "Build plan" } Button { text: "Send to Voice Fabric" } }
     Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; font.pixelSize: 10; text: "Provider/model selection stays with Model Router + FA3-VOICE-001. Voice cloning requires existing consent proof. No application-owned TTS authority." }
    }
   }
   Rectangle {
    SplitView.fillWidth: true; color: root.panel; border.color: root.border; radius: 8
    ColumnLayout {
     anchors.fill: parent; anchors.margins: 12; spacing: 8
     RowLayout { Label { text: "Narration timing"; color: root.textPrimary; font.bold: true } Item { Layout.fillWidth: true } Label { text: "bounded repair only"; color: root.orange } }
     ListView {
      Layout.fillWidth: true; Layout.fillHeight: true; clip: true
      model: ListModel { ListElement { who: "Narrator"; target: "1.80 s"; actual: "1.74 s"; state: "FIT" } ListElement { who: "Speaker 1"; target: "2.70 s"; actual: "3.05 s"; state: "RATE" } ListElement { who: "Speaker 2"; target: "1.40 s"; actual: "2.20 s"; state: "REVIEW" } }
      delegate: Rectangle { width: ListView.view.width; height: 58; color: index % 2 ? root.panelRaised : root.panel
       RowLayout { anchors.fill: parent; anchors.margins: 8; Label { text: who; color: root.accent; Layout.preferredWidth: 110 } Label { text: "target "+target; color: root.textMuted; Layout.preferredWidth: 110 } Label { text: "actual "+actual; color: root.textPrimary; Layout.preferredWidth: 110 } Label { text: state; color: state==="FIT" ? root.green : root.orange; font.bold: true } Item { Layout.fillWidth: true } Button { text: "Review" } }
      }
     }
     Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; font.pixelSize: 10; text: "Timing order: fit → silence padding → bounded rate adjustment → HUMAN REVIEW. The timing engine never rewrites caption text silently." }
    }
   }
  }
 }
}
