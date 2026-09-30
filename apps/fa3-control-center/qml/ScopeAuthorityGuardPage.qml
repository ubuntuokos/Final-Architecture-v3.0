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
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"
    signal operatorActionRequested(string eventId, string action)

    function count(name) {
        return Number(fa3ScopeGuard.counters[name] || 0)
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 12
            Item { Layout.preferredHeight: 8 }
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Scope & Authority Guard"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                    Label { text: "FA3 Testőr · 12 canonical layer · 175 capability · default DENY"; color: root.accent; font.pixelSize: 10; font.bold: true }
                    Label { text: "Megfigyelés és draft operátori beavatkozás. A felület nem bővíthet scope-ot és nem ad végrehajtási jogot."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                Button { text: "Refresh"; onClicked: fa3ScopeGuard.refresh() }
            }

            GridLayout {
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
                columns: 6; rowSpacing: 8; columnSpacing: 8
                Repeater {
                    model: [
                        {t:"ALLOW",v:root.count("ALLOW"),c:root.green},
                        {t:"DELEGATE",v:root.count("DELEGATE"),c:root.accent},
                        {t:"SPLIT",v:root.count("SPLIT"),c:root.orange},
                        {t:"ESCALATE",v:root.count("ESCALATE"),c:root.orange},
                        {t:"DENY",v:root.count("DENY"),c:root.magenta},
                        {t:"QUARANTINE",v:root.count("QUARANTINE"),c:root.magenta}
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 72
                        radius: 7; color: root.panel; border.color: root.border
                        ColumnLayout { anchors.centerIn: parent
                            Label { text: modelData.t; color: root.textMuted; font.pixelSize: 8 }
                            Label { text: modelData.v; color: modelData.c; font.pixelSize: 18; font.bold: true }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
                spacing: 10
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 330
                    radius: 8; color: root.panel; border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "Layer Guardians"; color: root.textPrimary; font.bold: true }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            clip: true; model: fa3ScopeGuard.layers
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                            delegate: ItemDelegate {
                                required property var modelData
                                width: ListView.view.width
                                contentItem: Column {
                                    spacing: 2
                                    Label { text: modelData.layer_key + " · " + modelData.name; color: root.textPrimary; font.bold: true; font.pixelSize: 10 }
                                    Label { text: modelData.allowed_capabilities.length + " capability · " + modelData.authority_owners.join(", "); color: root.textMuted; font.pixelSize: 8; elide: Text.ElideRight; width: parent.width }
                                }
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 330
                    radius: 8; color: root.panel; border.color: root.border
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 12
                        Label { text: "Authority / Orchestrator Guards"; color: root.textPrimary; font.bold: true }
                        ListView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            clip: true; model: fa3ScopeGuard.actors
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                            delegate: ItemDelegate {
                                required property var modelData
                                width: ListView.view.width
                                contentItem: Column {
                                    spacing: 2
                                    Label { text: modelData.actor_id; color: root.textPrimary; font.bold: true; font.pixelSize: 10 }
                                    Label { text: modelData.actor_type + " · scope expansion=" + modelData.may_expand_scope; color: root.textMuted; font.pixelSize: 8 }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
                Layout.preferredHeight: 360; radius: 8; color: root.panel; border.color: root.border
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Recent guard events"; color: root.textPrimary; font.bold: true; Layout.fillWidth: true }
                        Label { text: fa3ScopeGuard.state; color: root.green; font.pixelSize: 9 }
                    }
                    ListView {
                        id: eventList
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true
                        model: fa3ScopeGuard.recentEvents.slice().reverse()
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                        delegate: ItemDelegate {
                            required property var modelData
                            width: ListView.view.width
                            contentItem: RowLayout {
                                spacing: 8
                                Label { text: modelData.result || "?"; color: (modelData.result === "ALLOW" || modelData.result === "DELEGATE") ? root.green : (modelData.result === "SPLIT" ? root.orange : root.magenta); font.bold: true; Layout.preferredWidth: 80 }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 1
                                    Label { text: (modelData.actor_id || modelData.target_actor || "layer") + " · " + (modelData.intent || "layer.task"); color: root.textPrimary; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Label { text: (modelData.reason || "") + " · " + (modelData.task_id || ""); color: root.textMuted; font.pixelSize: 8; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                ComboBox { id: actionBox; model: ["ESCALATE","PAUSE","CANCEL","REPLAN","REASSIGN"]; Layout.preferredWidth: 110 }
                                Button {
                                    text: "Draft"
                                    onClicked: root.operatorActionRequested(String(modelData.event_id || modelData.task_id || ""), String(actionBox.currentText))
                                }
                            }
                        }
                    }
                }
            }
            Label {
                visible: fa3ScopeGuard.lastError.length > 0
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
                text: fa3ScopeGuard.lastError; color: root.orange; wrapMode: Text.WordWrap
            }
            Item { Layout.preferredHeight: 10 }
        }
    }
}
