import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property bool adminMode: false
    property string contextLabel: adminMode ? "FA3 GLOBAL" : "APPLICATION CONTEXT"
    property color panel: "#0b1728"
    property color panelRaised: "#10243a"
    property color border: "#1d3850"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8aa0b5"
    property color accent: "#25a7ff"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color red: "#ff6b6b"

    function stateColor(state) {
        if (state === "ADMITTED_BY_SEPARATE_EVIDENCE") return green
        if (state === "DISCOVERED_NOT_ADMITTED") return orange
        return textMuted
    }

    Rectangle {
        anchors.fill: parent
        color: "#07111f"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label {
                    text: "Proxy & Network Security"
                    color: root.textPrimary
                    font.pixelSize: 24
                    font.bold: true
                }
                Label {
                    text: root.adminMode
                          ? "Shared SCP administration projection — policy authority remains outside the GUI"
                          : "Shared SCP application projection — context-limited and inherited"
                    color: root.textMuted
                    font.pixelSize: 11
                }
            }
            Rectangle {
                radius: 5
                color: root.panelRaised
                border.color: root.border
                implicitWidth: stateText.implicitWidth + 24
                implicitHeight: 30
                Label {
                    id: stateText
                    anchors.centerIn: parent
                    text: fa3Scp.fabricState
                    color: root.orange
                    font.pixelSize: 9
                    font.bold: true
                }
            }
            Button {
                text: "Refresh"
                onClicked: fa3Scp.refresh()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 44
            radius: 6
            color: root.panel
            border.color: root.border
            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                Label { text: "Context"; color: root.textMuted; font.pixelSize: 9 }
                Label { text: root.contextLabel; color: root.textPrimary; font.bold: true; Layout.fillWidth: true }
                Label {
                    text: root.adminMode ? "ADMIN PROJECTION" : "EMBEDDED"
                    color: root.accent
                    font.pixelSize: 9
                    font.bold: true
                }
            }
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Overview" }
            TabButton { text: "Applications" }
            TabButton { text: "Internal / Mesh" }
            TabButton { text: "Egress" }
            TabButton { text: "Ingress" }
            TabButton { text: "DNS" }
            TabButton { text: "Identity & Trust" }
            TabButton { text: "Runtime" }
            TabButton { text: "Audit" }
        }

        StackLayout {
            currentIndex: tabs.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Label {
                        text: "Runtime adapters"
                        color: root.textPrimary
                        font.pixelSize: 16
                        font.bold: true
                    }
                    Label {
                        text: "Discovery never equals admission. A discovered binary remains blocked until its separate FA3 admission/evidence path succeeds."
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Repeater {
                        model: fa3Scp.components
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: 58
                            radius: 6
                            color: root.panel
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Label { text: modelData.name; color: root.textPrimary; font.bold: true }
                                    Label { text: modelData.role; color: root.textMuted; font.pixelSize: 9 }
                                }
                                Label {
                                    text: modelData.mandatory ? "BASELINE" : "OPTIONAL"
                                    color: modelData.mandatory ? root.accent : root.textMuted
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                                Label {
                                    text: modelData.state
                                    color: root.stateColor(modelData.state)
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "Application access"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label {
                        text: "The embedded view may only draft changes inside its context. Higher-layer locks cannot be weakened here."
                        color: root.textMuted
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    Repeater {
                        model: fa3Scp.policyLayers
                        delegate: Rectangle {
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: 48
                            radius: 5
                            color: root.panel
                            border.color: root.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                Label { text: modelData.label; color: root.textPrimary; Layout.fillWidth: true }
                                Label {
                                    text: modelData.locked ? "LOCKED / INHERITED" : "DRAFTABLE"
                                    color: modelData.locked ? root.textMuted : root.accent
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                        }
                    }
                    Switch {
                        id: externalAccess
                        text: "Request external network access"
                        checked: false
                        enabled: true
                    }
                    Button {
                        text: "Create draft ChangeSet"
                        onClicked: fa3Scp.createDraftChange(root.contextLabel, "external_network_access", externalAccess.checked)
                    }
                    Label {
                        text: fa3Scp.lastDraftPath.length > 0 ? ("Draft: " + fa3Scp.lastDraftPath) : "No draft created."
                        color: root.textMuted
                        wrapMode: Text.WrapAnywhere
                        Layout.fillWidth: true
                    }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "Internal network / mesh"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "Host membership does not grant service access. Workload identity + mTLS + Layer/Scope + capability policy remain required."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Preferred service addressing: fa3://service-id"; color: root.accent }
                    Label { text: "Node encryption: adapter-dependent (for example WireGuard)"; color: root.textPrimary }
                    Label { text: "Workload encryption: mTLS remains independent from node transport"; color: root.textPrimary }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "External egress"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "Direct Internet access is deny-by-default. Provider traffic must traverse the governed egress path."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "AI OFF => no provider network connection"; color: root.orange; font.bold: true }
                    Label { text: "Credential policy: SecretReference only; no plaintext .env or GUI storage."; color: root.textPrimary }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "Ingress"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "Published FA3 services terminate at a governed ingress boundary. Backend applications do not directly expose arbitrary public listeners."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Authentication · authorization · rate limits · request limits · audit"; color: root.textPrimary }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "DNS"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "Application-controlled arbitrary DNS is not part of the baseline. External resolution follows FA3 destination policy."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Internal fa3:// service identity is resolved by FA3 service discovery, not treated as DNS authority."; color: root.textPrimary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "Identity & Trust"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "Existing FA3 step-ca trust remains authoritative. Workload identity adapters bind short-lived identities without creating a second PKI authority."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Expired, revoked or unknown identity => DENY"; color: root.orange; font.bold: true }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "Runtime protection"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "nftables/network namespaces form the generic-Linux bypass-prevention baseline. eBPF, IDS/IPS and cluster backends remain optional and capability-detected."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "No optional runtime may silently become a mandatory hardware or distribution dependency."; color: root.textPrimary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }

            ScrollView {
                ColumnLayout {
                    width: parent.width
                    spacing: 12
                    Label { text: "Audit"; color: root.textPrimary; font.pixelSize: 16; font.bold: true }
                    Label { text: "Audit records metadata and policy decisions, not raw credentials or arbitrary payload bodies."; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Current implementation: local draft receipts only. Runtime evidence remains PENDING until physical Current Host execution."; color: root.orange; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
            }
        }
    }
}
