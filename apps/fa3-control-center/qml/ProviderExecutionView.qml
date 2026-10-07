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

    component BoundaryCard: Rectangle {
        property string titleText: ""
        property string bodyText: ""
        property string badgeText: ""
        property color tone: root.accent
        Layout.fillWidth: true
        implicitHeight: 116
        radius: 9
        color: root.panel
        border.color: root.border
        border.width: 1
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Label { text: parent.parent.parent.titleText; color: root.textPrimary; font.bold: true; Layout.fillWidth: true }
                Label { text: parent.parent.parent.badgeText; color: parent.parent.parent.tone; font.pixelSize: 9; font.bold: true }
            }
            Label { text: parent.parent.bodyText; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.fillHeight: true }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight + 32
        clip: true
        ColumnLayout {
            id: content
            width: parent.width
            spacing: 12
            Label { text: "Provider Execution"; color: root.textPrimary; font.pixelSize: 20; font.bold: true }
            Label { text: "Read-only Model Router execution, credential-state and protocol-compatibility projection"; color: root.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            BoundaryCard { titleText: "Routing authority"; badgeText: "SINGLE AUTHORITY"; tone: root.green; bodyText: "FA3-AUTH-MODEL-ROUTER-001 remains the only provider/model routing authority. Cross-provider transition is never performed by this surface or by the credential pool." }
            BoundaryCard { titleText: "Credential custody"; badgeText: "SECRETREFERENCE ONLY"; tone: root.accent; bodyText: "Credential values remain under FA3-SECRET-BROKER-001. This GUI exposes no credential-entry field and never displays raw secrets; execution evidence may identify only a SHA-256 of the SecretReference identifier." }
            BoundaryCard { titleText: "Session affinity & recovery"; badgeText: "FAIL CLOSED"; tone: root.green; bodyText: "Eligible sessions may retain the same credential. Rate-limit, quota, authentication or transient failure may rebind only within the already selected provider; otherwise the Model Router must reevaluate." }
            BoundaryCard { titleText: "Protocol compatibility"; badgeText: "EXPLICIT DEGRADATION"; tone: root.accent; bodyText: "FA3-LLM-GATEWAY-001 remains the single LiteLLM data plane. OpenAI, Anthropic and Gemini projection cannot silently strip security-relevant tool-schema semantics." }
            BoundaryCard { titleText: "Current-host evidence"; badgeText: "PENDING"; tone: root.orange; bodyText: "Repository/reference regressions do not prove real provider execution. Current-host execution, rollback and secret-projection evidence remain separately promotion-gated." }
            Label { text: "No direct provider execution · No direct credential mutation · No Model Router mutation"; color: root.textMuted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
}
