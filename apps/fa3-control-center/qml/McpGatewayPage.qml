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
    property int sectionIndex: 0
    property var snapshot: fa3McpGateway.canonicalSnapshot()
    property var sectionNames: fa3McpGateway.sections()

    component Card: Rectangle {
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 196
            Layout.fillHeight: true
            color: "#081421"
            border.color: root.border
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6
                Label { text: "MCP GATEWAY"; color: root.textPrimary; font.pixelSize: 14; font.bold: true }
                Label { text: "FA3-MCP-GATEWAY-001"; color: root.accent; font.pixelSize: 8 }
                Repeater {
                    model: root.sectionNames
                    delegate: Button {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        text: String(modelData)
                        checkable: true
                        checked: root.sectionIndex === index
                        onClicked: root.sectionIndex = index
                    }
                }
                Item { Layout.fillHeight: true }
                Button {
                    Layout.fillWidth: true
                    text: "Állapot frissítése"
                    onClicked: fa3McpGateway.refresh()
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn

            ColumnLayout {
                width: parent.width
                spacing: 14
                anchors.margins: 18

                Item { Layout.preferredHeight: 4 }
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label { text: "Central MCP Gateway"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                        Label {
                            Layout.fillWidth: true
                            text: "Egyetlen canonical tool/capability boundary · MCP 2026-07-28 stateless · provider-neutral · fail-closed"
                            color: root.textMuted
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                    }
                    Rectangle {
                        radius: 11
                        implicitWidth: stateLabel.implicitWidth + 20
                        implicitHeight: 24
                        color: "#2a2113"
                        border.color: root.orange
                        Label { id: stateLabel; anchors.centerIn: parent; text: fa3McpGateway.state; color: root.orange; font.pixelSize: 8; font.bold: true }
                    }
                }

                Card {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 92
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 18
                        ColumnLayout {
                            Label { text: "Authority"; color: root.textMuted; font.pixelSize: 8 }
                            Label { text: snapshot.authority; color: root.textPrimary; font.pixelSize: 10; font.bold: true }
                        }
                        ColumnLayout {
                            Label { text: "Transport"; color: root.textMuted; font.pixelSize: 8 }
                            Label { text: snapshot.protocol + " · " + snapshot.transport; color: root.green; font.pixelSize: 10; font.bold: true }
                        }
                        ColumnLayout {
                            Label { text: "Current host"; color: root.textMuted; font.pixelSize: 8 }
                            Label { text: snapshot.runtimePromotion; color: root.orange; font.pixelSize: 10; font.bold: true }
                        }
                        Item { Layout.fillWidth: true }
                        Label { text: "No fabricated CONNECTED/PASS"; color: root.magenta; font.pixelSize: 8; font.bold: true }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: root.sectionNames[root.sectionIndex]
                    color: root.textPrimary
                    font.pixelSize: 16
                    font.bold: true
                }

                Card {
                    visible: root.sectionIndex === 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: 230
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        Label { text: "Overview"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label { text: "Data Plane · Control Plane · Policy Plane · Governance Plane"; color: root.accent; font.pixelSize: 10 }
                        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; font.pixelSize: 9; text: "A gateway registryt, routingot és mediationt biztosít. Policy, identity, secret, HRB, Temporal, model routing, Journal és evidence authority nem kerül át a gatewayhez." }
                        Label { text: "health: " + JSON.stringify(fa3McpGateway.health); color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "readiness: " + JSON.stringify(fa3McpGateway.readiness); color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "endpoint: " + snapshot.endpoint; color: root.textMuted; font.pixelSize: 9 }
                    }
                }

                Card {
                    visible: root.sectionIndex === 4
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.max(220, capabilityColumn.implicitHeight + 28)
                    ColumnLayout {
                        id: capabilityColumn
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 7
                        Label { text: "Capabilities"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Repeater {
                            model: fa3McpGateway.capabilities
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Label { Layout.fillWidth: true; text: modelData.capability_id || "unknown"; color: root.textPrimary; font.pixelSize: 9 }
                                Label { text: modelData.risk_class || "N/A"; color: root.textMuted; font.pixelSize: 8 }
                                Label { text: modelData.available ? "AVAILABLE" : "NOT CONNECTED"; color: modelData.available ? root.green : root.orange; font.pixelSize: 8; font.bold: true }
                            }
                        }
                        Label { visible: fa3McpGateway.capabilities.length === 0; text: "Nincs élő capability projection; ez nem jelent üres canonical registryt."; color: root.orange; font.pixelSize: 9 }
                    }
                }

                Card {
                    visible: root.sectionIndex === 10
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        Label { text: "MCP Inspector"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Read-only inspector. QML direct tool execution tiltott; az Inspector csak canonical modern request mintát és live health/registry projectiont mutat."; color: root.textMuted; font.pixelSize: 9 }
                        TextArea {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            readOnly: true
                            text: 'POST /mcp\nMCP-Protocol-Version: 2026-07-28\nMcp-Method: server/discover\nMcp-Name: server/discover\n\n{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}'
                            color: root.textPrimary
                            background: Rectangle { color: root.panelRaised; border.color: root.border; radius: 6 }
                        }
                    }
                }

                Card {
                    visible: root.sectionIndex !== 0 && root.sectionIndex !== 4 && root.sectionIndex !== 10
                    Layout.fillWidth: true
                    Layout.preferredHeight: 245
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        Label { text: root.sectionNames[root.sectionIndex]; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            color: root.textMuted
                            font.pixelSize: 9
                            text: root.sectionIndex === 1 ? "Servers: local/remote MCP endpoint lifecycle projection; activation evidence-gated." :
                                  root.sectionIndex === 2 ? "Tools: typed tool definitions are projected through FA3 capability contracts; no raw provider authority." :
                                  root.sectionIndex === 3 ? "Providers: provider bindings remain ADMISSION/EVIDENCE-GATED. PageIndex MCP is one optional provider." :
                                  root.sectionIndex === 5 ? "Routes: capability → admitted provider binding. No automatic fallback across authority boundaries." :
                                  root.sectionIndex === 6 ? "Requests: application/workflow context is explicit; MCP transport session state is forbidden on the modern path." :
                                  root.sectionIndex === 7 ? "Permissions: identity + external policy decision + risk/provider approval; least privilege and revocation enforced." :
                                  root.sectionIndex === 8 ? "Security: supply-chain pin/hash/scan/sign, prompt-injection/tool-call firewall, sandbox and secret-reference isolation." :
                                  root.sectionIndex === 9 ? "Logs: evidence/observability projection only; GUI cannot fabricate PASS or mutate canonical evidence." :
                                  "Settings: local-first lifecycle driver, loopback default bind, modern protocol canonical; remote exposure needs a separate admitted profile."
                        }
                        Label { text: "Direct QML tool invocation: FORBIDDEN"; color: root.magenta; font.pixelSize: 9; font.bold: true }
                        Label { text: "GUI self-approval: FORBIDDEN"; color: root.magenta; font.pixelSize: 9; font.bold: true }
                        Label { text: "Production admission: current-host E2E evidence required"; color: root.orange; font.pixelSize: 9; font.bold: true }
                    }
                }

                Label {
                    visible: fa3McpGateway.lastError.length > 0
                    Layout.fillWidth: true
                    text: "Live gateway: " + fa3McpGateway.lastError
                    color: root.orange
                    wrapMode: Text.WordWrap
                    font.pixelSize: 9
                }
                Item { Layout.preferredHeight: 14 }
            }
        }
    }

    Component.onCompleted: fa3McpGateway.refresh()
}
