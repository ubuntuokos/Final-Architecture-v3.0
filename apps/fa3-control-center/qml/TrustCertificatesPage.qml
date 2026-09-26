import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property color panel: "#0b1728"
    property color panelRaised: "#0f2035"
    property color border: "#1d3550"
    property color textPrimary: "#f5f8fc"
    property color textMuted: "#8fa4bb"
    property color accent: "#25a7ff"
    property color cyan: "#22d3ee"
    property color green: "#35e0a1"
    property color orange: "#f0b14a"
    property color magenta: "#b778ff"

    component Card: Rectangle {
        radius: 10
        color: root.panel
        border.color: root.border
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 14

            Item { Layout.preferredHeight: 4 }
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Trust & Certificates"; color: root.textPrimary; font.pixelSize: 22; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: "FA3-TRUST-PKI-001 · step-ca internal CA provider · offline root / online intermediate"
                        color: root.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap
                    }
                }
                Rectangle {
                    radius: 11
                    implicitWidth: stateLabel.implicitWidth + 20
                    implicitHeight: 24
                    color: "#10281f"
                    border.color: root.green
                    Label {
                        id: stateLabel
                        anchors.centerIn: parent
                        text: "RUNTIME REQUALIFICATION PENDING"
                        color: root.green; font.pixelSize: 8; font.bold: true
                    }
                }
            }

            Card {
                Layout.fillWidth: true
                Layout.preferredHeight: 135
                GridLayout {
                    anchors.fill: parent; anchors.margins: 14
                    columns: 4; columnSpacing: 18; rowSpacing: 8
                    Label { text: "Profile"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "FA3-TRUST-PKI-001"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
                    Label { text: "Provider"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "FA3-PROVIDER-STEP-CA-001"; color: root.textPrimary; font.pixelSize: 9; font.bold: true }
                    Label { text: "Upstream"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "step-ca v0.30.2"; color: root.cyan; font.pixelSize: 9; font.bold: true }
                    Label { text: "Default TLS TTL"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "12h · max 24h"; color: root.green; font.pixelSize: 9; font.bold: true }
                    Label { text: "Root CA"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "OFFLINE ONLY"; color: root.magenta; font.pixelSize: 9; font.bold: true }
                    Label { text: "Online issuer"; color: root.textMuted; font.pixelSize: 8 }
                    Label { text: "INTERMEDIATE ONLY"; color: root.green; font.pixelSize: 9; font.bold: true }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 14
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 235
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 8
                        Label { text: "Trust topology"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label { text: "Offline Root CA"; color: root.magenta; font.pixelSize: 10; font.bold: true }
                        Label { text: "↓ signs"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "Online Intermediate CA · step-ca"; color: root.cyan; font.pixelSize: 10; font.bold: true }
                        Label { text: "↓"; color: root.textMuted; font.pixelSize: 9 }
                        Label { text: "ACME · X.509 · mTLS · SSH certificates"; color: root.green; font.pixelSize: 10; font.bold: true }
                        Label {
                            Layout.fillWidth: true; wrapMode: Text.WordWrap
                            text: "A certificate proves cryptographic identity. Authorization remains an external FA3 policy decision."
                            color: root.textMuted; font.pixelSize: 9
                        }
                    }
                }
                Card {
                    Layout.fillWidth: true; Layout.preferredHeight: 255
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 8
                        Label { text: "Promotion requirements"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                        Label { text: "✓ canonical/reference gate"; color: root.green; font.pixelSize: 9 }
                        Label { text: "✓ verified current-host artifact digest + Sigstore"; color: root.green; font.pixelSize: 9 }
                        Label { text: "✓ offline root ceremony receipt"; color: root.green; font.pixelSize: 9 }
                        Label { text: "✓ ACME issue/reorder + mTLS E2E"; color: root.green; font.pixelSize: 9 }
                        Label { text: "✓ SSH certificate E2E"; color: root.green; font.pixelSize: 9 }
                        Label { text: "✓ backup / restore / post-restore issuance"; color: root.green; font.pixelSize: 9 }
                        Label { text: "Scope: current-host step-ca runtime only · global FA3 promotion: NO"; color: root.cyan; font.pixelSize: 9; font.bold: true }
                        Label {
                            Layout.fillWidth: true; wrapMode: Text.WordWrap
                            text: "A GUI nem állíthat elő PASS-t és nem adhat ki tanúsítványt közvetlen QML-hívással."
                            color: root.magenta; font.pixelSize: 9; font.bold: true
                        }
                    }
                }
            }

            Card {
                Layout.fillWidth: true; Layout.preferredHeight: 145
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 8
                    Label { text: "Default runtime boundary"; color: root.textPrimary; font.pixelSize: 13; font.bold: true }
                    Label { text: "Listener: 127.0.0.1:9443"; color: root.textPrimary; font.pixelSize: 9 }
                    Label { text: "Unlock secret: systemd LoadCredential"; color: root.textPrimary; font.pixelSize: 9 }
                    Label { text: "Service user: fa3-step-ca"; color: root.textPrimary; font.pixelSize: 9 }
                    Label { text: "Remote exposure: explicit network/security admission required"; color: root.orange; font.pixelSize: 9; font.bold: true }
                    Label { text: "Private root key in online runtime: FORBIDDEN"; color: root.magenta; font.pixelSize: 9; font.bold: true }
                }
            }
            Item { Layout.preferredHeight: 14 }
        }
    }
}
