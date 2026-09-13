import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var journal
    required property color textPrimary
    required property color textMuted
    required property color surface1
    required property color accent
    property string filterText: ""

    function rows() {
        const q=filterText.trim().toLowerCase(); if(q.length===0) return journal.entries
        const out=[]; for(let i=0;i<journal.entries.length;++i){const r=journal.entries[i];const h=(r.timestamp+" "+r.unit+" "+r.identifier+" "+r.message).toLowerCase();if(h.indexOf(q)>=0)out.push(r)} return out
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { text: "Naplók / Logs"; font.pixelSize: 22; font.bold: true; Layout.fillWidth: true }
            Label { text: root.journal.statusText; color: root.textMuted }
            Button { text: "Frissítés"; onClicked: root.journal.refresh(400) }
        }
        Label { Layout.fillWidth: true; text: "Read-only journald nézet. Evidence nem napló és itt nem törölhető."; color: root.textMuted; wrapMode: Text.WordWrap }
        TextField { Layout.fillWidth: true; placeholderText: "Szűrés egységre, folyamatra vagy üzenetre…"; onTextChanged: root.filterText=text }
        Rectangle {
            Layout.fillWidth: true; Layout.fillHeight: true; color: root.surface1; radius: 8
            ListView {
                anchors.fill: parent; anchors.margins: 8; clip: true; spacing: 2; model: root.rows()
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width; height: Math.max(44, msg.implicitHeight+12)
                    contentItem: RowLayout {
                        spacing: 8
                        Label { text: modelData.timestamp; color: root.textMuted; font.family: "monospace"; Layout.preferredWidth: 165; font.pixelSize: 10 }
                        Label { text: modelData.unit || modelData.identifier || "—"; color: root.accent; Layout.preferredWidth: 175; elide: Text.ElideRight }
                        Label { id: msg; text: modelData.message; Layout.fillWidth: true; wrapMode: Text.Wrap; font.family: "monospace"; font.pixelSize: 11 }
                    }
                }
            }
        }
    }
}
