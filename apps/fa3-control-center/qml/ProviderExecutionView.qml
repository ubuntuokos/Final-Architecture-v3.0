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

    // Read-only backend projection; this surface never accepts secret values.
    property var observabilitySnapshot: ({})
    function obs(name) {
        var value = observabilitySnapshot ? observabilitySnapshot[name] : undefined
        if (value === undefined || value === null || value === "")
            return "not reported"
        if (typeof value === "object")
            return JSON.stringify(value)
        return String(value)
    }

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
            BoundaryCard { titleText: "Health observability"; badgeText: "READ ONLY"; tone: root.accent; bodyText: "Provider: " + root.obs("provider_health") + " · Credential: " + root.obs("credential_health") + " · Model: " + root.obs("model_health") + " · Endpoint: " + root.obs("endpoint_health") }
            BoundaryCard { titleText: "Quota, backoff & circuit"; badgeText: "READ ONLY"; tone: root.green; bodyText: "Quota pressure: " + root.obs("quota_pressure") + " · Backoff/cooldown: " + root.obs("backoff_cooldown") + " · Circuit breaker: " + root.obs("circuit_breaker") }
            BoundaryCard { titleText: "Session & rebind history"; badgeText: "READ ONLY"; tone: root.accent; bodyText: "Session affinity: " + root.obs("session_affinity") + " · Rebind history: " + root.obs("rebind_history") + " · Pool traversal: " + root.obs("credential_pool_traversal") }
            BoundaryCard { titleText: "Protocol, reasoning & context"; badgeText: "READ ONLY"; tone: root.green; bodyText: "Protocol degradation: " + root.obs("protocol_degradation") + " · Reasoning intent: " + root.obs("reasoning_intent") + " · Reasoning result: " + root.obs("reasoning_result") + " · Context budget: " + root.obs("context_budget") }
            BoundaryCard { titleText: "Runtime admission"; badgeText: "READ ONLY"; tone: root.orange; bodyText: "Provider runtime admission: " + root.obs("provider_runtime_admission") + " · Current Host evidence: " + root.obs("current_host_evidence_status") }
            BoundaryCard { titleText: "Credential custody"; badgeText: "SECRETREFERENCE ONLY"; tone: root.accent; bodyText: "Credential values remain under FA3-SECRET-BROKER-001. This GUI exposes no credential-entry field and never displays raw secrets; execution evidence may identify only a SHA-256 of the SecretReference identifier." }
            BoundaryCard { titleText: "Session affinity & recovery"; badgeText: "FAIL CLOSED"; tone: root.green; bodyText: "Eligible sessions may retain the same credential. Rate-limit, quota, authentication or transient failure may rebind only within the already selected provider; otherwise the Model Router must reevaluate." }
            BoundaryCard { titleText: "Protocol compatibility"; badgeText: "EXPLICIT DEGRADATION"; tone: root.accent; bodyText: "FA3-LLM-GATEWAY-001 remains the single LiteLLM data plane. OpenAI, Anthropic and Gemini projection preserves error status, normalizes tool-call IDs and cannot silently strip security-relevant tool-schema semantics." }
            BoundaryCard { titleText: "Pool protection"; badgeText: "BOUNDED"; tone: root.green; bodyText: "Per-request credential traversal and rebind attempts are bounded. Tiered backoff, cooldown and circuit state are visible as execution evidence; pool exhaustion returns control to the Model Router." }
            BoundaryCard { titleText: "Health dimensions"; badgeText: "SEPARATE HEALTH"; tone: root.accent; bodyText: "Provider, credential, model and endpoint health remain distinct. One bad credential or model does not silently poison the complete admitted provider pool." }
            BoundaryCard { titleText: "Reasoning arbitration"; badgeText: "MODEL ROUTER"; tone: root.green; bodyText: "Reasoning class and optional token budget originate from the Agent Workload task. The Model Router checks admitted model capability; OpenAI, Anthropic and Gemini adapters only project the canonical result and cannot raise the budget." }
            BoundaryCard { titleText: "Context lifecycle"; badgeText: "PROVENANCE"; tone: root.accent; bodyText: "Shared Conversation and Knowledge layers own context-budget projection. Protected and active context cannot be silently dropped; compaction preserves provenance, retrieval backreferences and anti-thrashing headroom." }
            BoundaryCard { titleText: "Current-host evidence"; badgeText: "PROVIDER-SPECIFIC"; tone: root.orange; bodyText: "The generic Provider Execution core is statically closed. Real provider execution remains separately Current-Host promotion-gated for each provider or multi-credential deployment selected for runtime promotion." }
            Label { text: "No direct provider execution · No direct credential mutation · No Model Router mutation"; color: root.textMuted; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
    }
}
