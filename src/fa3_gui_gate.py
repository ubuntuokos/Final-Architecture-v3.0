#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "profile": ROOT / "canonical/profiles/FA3-DESKTOP-001.json",
    "contract": ROOT / "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-GUI-2026-09-12.json",
    "gate": ROOT / "canonical/FA3-GATE-GUI-001.json",
    "runtime": ROOT / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
    "application_intent": ROOT / "canonical/intents/FA3-GUI-CURRENT-HOST-APPLICATION-INTENT-001.json",
    "reuse_assessment": ROOT / "canonical/assessments/FA3-GUI-CURRENT-HOST-REUSE-ASSESSMENT-001.json",
    "reconciliation_decision": ROOT / "canonical/decisions/FA3-DEC-GUI-RECONCILIATION-JEV-AGENT-NATIVE-2026-09-23.json",
    "surface_registry": ROOT / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json",
    "uaf_contract": ROOT / "canonical/contracts/FA3-UNIFIED-ACTION-FABRIC-CONTRACTS-001.json",
    "decision_fabric_profile": ROOT / "canonical/profiles/FA3-DECISION-FABRIC-001.json",
    "ui_component_profile": ROOT / "canonical/profiles/FA3-UI-COMPONENT-FABRIC-001.json",
    "action_center_qml": ROOT / "apps/fa3-control-center/qml/AgentActionCenterPage.qml",
    "work_management_qml": ROOT / "apps/fa3-control-center/qml/WorkManagementPage.qml",
    "accelerator_guard_qml": ROOT / "apps/fa3-control-center/qml/AcceleratorGuardPage.qml",
    "update_center_qml": ROOT / "apps/fa3-control-center/qml/UpdateCenterPage.qml",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
    "cmake": ROOT / "apps/fa3-control-center/CMakeLists.txt",
    "main_cpp": ROOT / "apps/fa3-control-center/src/main.cpp",
    "model_cpp": ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp",
    "qml": ROOT / "apps/fa3-control-center/qml/Main.qml",
    "models_providers_qml": ROOT / "apps/fa3-control-center/qml/ModelsProvidersPage.qml",
    "studio_qml": ROOT / "apps/fa3-control-center/qml/AiStudioPage.qml",
    "subtitle_studio_qml": ROOT / "apps/fa3-control-center/qml/SubtitleStudioPage.qml",
    "narration_studio_qml": ROOT / "apps/fa3-control-center/qml/NarrationStudioPage.qml",
    "settings_qml": ROOT / "apps/fa3-control-center/qml/SystemSettingsPage.qml",
    "rtd_qml": ROOT / "apps/fa3-control-center/qml/RtdProvidersPage.qml",
    "chat_qml": ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml",
    "help_bubble_qml": ROOT / "apps/fa3-control-center/qml/HelpBubble.qml",
    "checkpoint_qml": ROOT / "apps/fa3-control-center/qml/CheckpointManagerPage.qml",
    "external_providers_qml": ROOT / "apps/fa3-control-center/qml/ExternalProvidersSetupPage.qml",
    "token_control_qml": ROOT / "apps/fa3-control-center/qml/TokenControlCenterPage.qml",
    "language_control_qml": ROOT / "apps/fa3-control-center/qml/LanguageControlPage.qml",
    "integrations_qml": ROOT / "apps/fa3-control-center/qml/IntegrationsPage.qml",
    "mcp_control_service": ROOT / "apps/fa3-control-center/src/McpControlService.cpp",
    "mcp_control_contract": ROOT / "canonical/FA3-MCP-CONTROL-CHAT-001.json",
    "mcp_gateway_qml": ROOT / "apps/fa3-control-center/qml/McpGatewayPage.qml",
    "mcp_gateway_service": ROOT / "apps/fa3-control-center/src/McpGatewayService.cpp",
    "mcp_gateway_contract": ROOT / "canonical/FA3-MCP-GATEWAY-GUI-001.json",
    "knowledge_qml": ROOT / "apps/fa3-control-center/qml/KnowledgePage.qml",
    "preference_store": ROOT / "apps/fa3-control-center/src/PreferenceStore.cpp",
    "device_model": ROOT / "apps/fa3-control-center/src/SystemDeviceModel.cpp",
    "chat_file_service": ROOT / "apps/fa3-control-center/src/ChatFileService.cpp",
    "desktop": ROOT / "apps/fa3-control-center/packaging/org.fa3.ControlCenter.desktop",
    "installer": ROOT / "deployment/fa3-gui/install.sh",
}

NAVIGATION = ["Dashboard", "Projects", "Work Management", "AI Studio", "Subtitle Studio", "Narration Studio", "Knowledge & Retrieval", "Agent Action Center", "Agents & Workflows", "Models & Providers", "Model Manager", "Checkpoint Manager", "Remote AI Hub", "RTD Providers", "External Providers Setup", "Decision Fabric", "Decision Inspector", "Context Inspector", "External Project Radar", "Integrations", "MCP Gateway", "FA3 OS", "Security & Approvals", "Token Control Center", "Trust & Certificates", "Session Vault / Kulcsvault", "Evidence", "Observability", "Architecture", "Napló / Journal", "Resources", "Accelerator Guard", "Update Center", "Rendszerbeállítások", "System"]
NAVIGATION_GROUPS = ["HOME", "CREATE", "AGENTS", "MODELS & DATA", "DECISION & CONTEXT", "INTEGRATIONS", "GOVERNANCE", "SYSTEM"]
FORBIDDEN_BACKEND_TOKENS = ["QProcess", "std::system(", "popen(", "/bin/sh", "/bin/bash", "pkexec", "setuid("]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    for name, path in REQUIRED.items():
        if not path.exists(): failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures: return failures

    profile = load_json(REQUIRED["profile"])
    contract = load_json(REQUIRED["contract"])
    decision = load_json(REQUIRED["decision"])
    gate = load_json(REQUIRED["gate"])
    runtime = load_json(REQUIRED["runtime"])
    application_intent = load_json(REQUIRED["application_intent"])
    reuse_assessment = load_json(REQUIRED["reuse_assessment"])
    reconciliation = load_json(REQUIRED["reconciliation_decision"])
    surface_registry = load_json(REQUIRED["surface_registry"])
    uaf_contract = load_json(REQUIRED["uaf_contract"])
    decision_fabric = load_json(REQUIRED["decision_fabric_profile"])
    ui_component = load_json(REQUIRED["ui_component_profile"])

    checks = [
        (profile.get("id") == "FA3-DESKTOP-001", "profile-id"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        (contract.get("provider_neutral") is True, "contract-provider-neutral"),
        (contract.get("mutation_model", {}).get("direct_canonical_write") == "FORBIDDEN", "no-direct-canonical-write"),
        (contract.get("mutation_model", {}).get("direct_systemd_or_cgroup_mutation") == "FORBIDDEN", "no-direct-host-enforcement"),
        (contract.get("mutation_model", {}).get("sudo_su_pkexec") == "FORBIDDEN", "no-privilege-bypass"),
        (decision.get("new_capabilities") == 0, "decision-no-new-capability"),
        (decision.get("new_architectural_authorities") == 0, "decision-no-new-authority"),
        (decision.get("capability_count_after") == 143, "decision-capability-count"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
        (application_intent.get("schema") == "fa3.application-intent.v1", "reuse-application-intent-schema"),
        (application_intent.get("project_id") == "FA3-DESKTOP-001", "reuse-application-intent-project"),
        (application_intent.get("declared_new_capabilities") == [], "reuse-application-intent-no-new-capability"),
        (application_intent.get("proposed_authority_roles") == [], "reuse-application-intent-no-new-authority"),
        (application_intent.get("hardware_audit", {}).get("vendor_neutral") is True, "reuse-application-intent-hardware-vendor-neutral"),
        (application_intent.get("hardware_audit", {}).get("cpu_only_viable") is True, "reuse-application-intent-cpu-only"),
        (application_intent.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N", "reuse-application-intent-accelerator-cardinality"),
        (application_intent.get("namespace_claims", {}).get("requires_upstream_uninstall") is False, "reuse-application-intent-no-upstream-uninstall"),
        (application_intent.get("namespace_claims", {}).get("global_environment_mutation") is False, "reuse-application-intent-no-global-mutation"),
        (reuse_assessment.get("schema") == "fa3.reuse-assessment.v1", "reuse-assessment-schema"),
        (reuse_assessment.get("project_id") == "FA3-DESKTOP-001", "reuse-assessment-project"),
        (reuse_assessment.get("intent_id") == "FA3-GUI-CURRENT-HOST-APPLICATION-INTENT-001", "reuse-assessment-intent-binding"),
        (reuse_assessment.get("result") == "PASS", "reuse-assessment-pass"),
        (reuse_assessment.get("coexistence", {}).get("result") == "PASS", "reuse-assessment-coexistence-pass"),
        (reuse_assessment.get("coexistence", {}).get("upstream_uninstall_required") is False, "reuse-assessment-no-upstream-uninstall"),
        (reuse_assessment.get("coexistence", {}).get("global_mutation") is False, "reuse-assessment-no-global-mutation"),
        (reuse_assessment.get("hardware_audit", {}).get("cpu_only_viable") is True, "reuse-assessment-cpu-only"),
        (reuse_assessment.get("current_host_runtime_promotion_claim") is False, "reuse-assessment-no-current-host-overclaim"),
        (reuse_assessment.get("global_promotion_claim") is False, "reuse-assessment-no-global-overclaim"),
        (reuse_assessment.get("capability_count_after") == 143, "reuse-assessment-capability-count"),
        (reuse_assessment.get("new_architectural_authorities") == 0, "reuse-assessment-no-new-authority"),
        (runtime.get("current_host_gate_id") == "FA3-GUI-CURRENT-HOST-GATESET-001", "runtime-current-host-gate-binding"),
        (
            (
                runtime.get("status") in {"PENDING_CURRENT_HOST", "EXECUTABLE_CURRENT_HOST_CLOSURE_MATERIALIZED_PENDING_RUN"}
                and runtime.get("production_admitted") is False
                and runtime.get("current_host_receipt_present") is False
            )
            or (
                runtime.get("status") == "CURRENT_HOST_PASS"
                and runtime.get("production_admitted") is True
                and runtime.get("current_host_receipt_present") is True
                and runtime.get("admission_scope") == "GUI_CONTROL_CENTER_PROCESS_RUNTIME_ONLY"
                and runtime.get("secret_backend_admission") == "FAIL_SEPARATE_AUTHORITY_NOT_PROMOTED"
                and (ROOT / str(runtime.get("current_host_receipt", ""))).is_file()
            ),
            "runtime-evidence-state-invalid",
        ),
        (reconciliation.get("new_capabilities") == 0, "reconciliation-no-new-capability"),
        (reconciliation.get("new_architectural_authorities") == 0, "reconciliation-no-new-authority"),
        (reconciliation.get("capability_count_after") == 143, "reconciliation-capability-count"),
        (reconciliation.get("agent_native", {}).get("gui_may_execute_provider_directly") is False, "reconciliation-no-direct-agent-provider"),
        (reconciliation.get("decision_fabric", {}).get("authorization_authority") is False, "reconciliation-decision-no-authorization"),
        (reconciliation.get("decision_fabric", {}).get("candidate_expansion") is False, "reconciliation-decision-no-candidate-expansion"),
        (reconciliation.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N", "reconciliation-hardware-cardinality"),
        (surface_registry.get("new_architectural_authority") is False, "surface-registry-no-authority"),
        (surface_registry.get("capability_count") == 143, "surface-registry-capability-count"),
        (uaf_contract.get("new_architectural_authority") is False, "uaf-no-new-authority"),
        (decision_fabric.get("new_architectural_authority") is False, "decision-fabric-no-new-authority"),
        (ui_component.get("parent_profile") == "FA3-DESKTOP-001", "ui-component-parent"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    qml = REQUIRED["qml"].read_text(encoding="utf-8")
    for label in NAVIGATION:
        if label not in qml: failures.append(f"qml-navigation-missing:{label}")
    for group in NAVIGATION_GROUPS:
        if f'text: "{group}"' not in qml: failures.append(f"qml-navigation-group-missing:{group}")
    route_ids = [surface.get("route_id") for surface in surface_registry.get("surfaces", [])]
    if len(route_ids) != len(set(route_ids)): failures.append("surface-registry-duplicate-route-id")
    for route_id in route_ids:
        if route_id and f'"{route_id}"' not in qml: failures.append(f"qml-route-missing:{route_id}")
    if "property int pageIndex" in qml[qml.find("component NavButton"):qml.find("component ModuleCard")]:
        failures.append("qml-navbutton-still-index-coupled")
    if "function navigate(routeId)" not in qml or "property var routeTable" not in qml:
        failures.append("qml-stable-route-dispatch-missing")
    studio_qml = REQUIRED["studio_qml"].read_text(encoding="utf-8")
    for module in ["Image", "Video", "Animation", "3D / VFX", "Audio", "Music", "Story / Screenplay", "Office", "Marketing", "Weboldal", "Prezentáció"]:
        if module not in studio_qml: failures.append(f"qml-studio-module-missing:{module}")
    for office_surface in ["Writer", "Calc", "Impress", "Preview", "Apply/UNO", "Undo"]:
        if office_surface not in studio_qml: failures.append(f"qml-office-surface-missing:{office_surface}")
    if "createDraftChangeSet" not in qml: failures.append("qml-changeset-intent-missing")
    if "id: askButton" not in qml or "id: askMenu" not in qml or "y: parent.height" not in qml: failures.append("qml-ask-menu-anchor-missing")
    if "id: modulePage" not in qml or "model: modulePage.cards" not in qml or "width: modulePage.availableWidth" not in qml: failures.append("qml-module-page-render-contract-missing")
    if "id: modelRegistryList" not in qml or "modelManagerView.availableHeight - 250" not in qml or "ScrollBar.AlwaysOn" not in qml: failures.append("qml-model-registry-responsive-scrollbar-missing")
    if "id: llmFitButton" not in qml or "property bool llmFitExpanded" not in qml or "nincs terminálindítás" not in qml: failures.append("qml-model-manager-llmfit-surface-missing")
    if "id: searchScope" not in qml or "FA3 alkalmazások" not in qml or "FA3 funkciók" not in qml or "Beállítások" not in qml or "unifiedSearchResults" not in qml:
        failures.append("qml-unified-search-scopes-missing")
    if "function searchFa3Applications" not in qml or "fa3AppCatalog.applications" not in qml or "var apps = searchFa3Applications(needle)" not in qml:
        failures.append("qml-fa3-application-search-missing")
    if "property var fa3ApplicationIndex" in qml:
        failures.append("qml-stale-independent-application-index-present")
    if "fa3Repository.searchInstalledApplications(needle)" in qml:
        failures.append("qml-host-application-search-leak")
    if "id: architectureScope" not in qml or "Canonical Core" not in qml or "Execution Fabric" not in qml or "Evidence & Release" not in qml or "architectureResults" not in qml: failures.append("qml-architecture-semantic-view-missing")
    models_qml = REQUIRED["models_providers_qml"].read_text(encoding="utf-8")
    if "id: providerList" not in models_qml or "Layout.fillHeight: true" not in models_qml or "ScrollBar.AlwaysOn" not in models_qml: failures.append("qml-models-providers-responsive-scrollbar-missing")
    settings_qml = REQUIRED["settings_qml"].read_text(encoding="utf-8")
    if "compactNavigationRequested" not in settings_qml or "statusStripRequested" not in settings_qml or "ChangeSet-tervezet" not in settings_qml or "Security & Approvals megnyitása" not in settings_qml: failures.append("qml-system-settings-interaction-missing")
    for token in ["Appearance", "Chat Style", "Reasoning", "Gyorsbillentyűk", "CPU", "GPU", "NPU", "DGX", "Webkamera", "Nyomtató", "Scanner", "MIDI", "GIMP", "Ardour", "Auto-latch onto generating message"]:
        if token not in settings_qml: failures.append(f"qml-system-settings-surface-missing:{token}")
    preference_cpp = REQUIRED["preference_store"].read_text(encoding="utf-8")
    if "m_settings" not in preference_cpp or "normalizeShortcut" not in preference_cpp or "preferenceChanged" not in preference_cpp: failures.append("settings-preference-store-missing")
    device_cpp = REQUIRED["device_model"].read_text(encoding="utf-8")
    for token in ["QPrinterInfo", "/sys/class/accel", "video*", "/dev/snd", "DGX", "ADAPTER-GATED"]:
        if token not in device_cpp: failures.append(f"settings-device-discovery-missing:{token}")
    for token in ["accentForTheme", "navigationBarPosition", "Shortcut {", "fa3Preferences.setValue"]:
        if token not in qml: failures.append(f"qml-persistent-settings-shell-missing:{token}")
    if "ModelsProvidersPage" not in qml or "AiStudioPage" not in qml or "SystemSettingsPage" not in qml: failures.append("qml-dedicated-page-wiring-missing")
    for token in ['routeId: "create.subtitle-studio"', 'routeId: "create.narration-studio"', "SubtitleStudioPage", "NarrationStudioPage"]:
        if token not in qml: failures.append(f"qml-caption-narration-route-wiring-missing:{token}")
    subtitle_qml = REQUIRED["subtitle_studio_qml"].read_text(encoding="utf-8")
    narration_qml = REQUIRED["narration_studio_qml"].read_text(encoding="utf-8")
    for token in ["FA3-CAPTION-SUBTITLE-001", "Canonical state: FA3 Caption IR", "silent text mutation is forbidden"]:
        if token not in subtitle_qml: failures.append(f"qml-subtitle-studio-boundary-missing:{token}")
    for token in ["delegates synthesis to FA3-VOICE-001", "Model Router + FA3-VOICE-001", "HUMAN REVIEW"]:
        if token not in narration_qml: failures.append(f"qml-narration-studio-boundary-missing:{token}")

    rtd_qml = REQUIRED["rtd_qml"].read_text(encoding="utf-8")
    integrations_qml = REQUIRED["integrations_qml"].read_text(encoding="utf-8")
    for token in ["Real-Time Data", "ADAPTER-GATED", "Freshness SLA", "Provenance", "FAIL-CLOSED", "Adapter ChangeSet-tervezet"]:
        if token not in rtd_qml: failures.append(f"qml-rtd-provider-surface-missing:{token}")
    if "RtdProvidersPage" not in qml or "RTD Data Sources" not in qml or "RTD Adapters" not in integrations_qml or '{label: "Real-Time Data", value: "RTD"}' not in qml:
        failures.append("qml-rtd-cross-surface-projection-missing")

    chat_qml = REQUIRED["chat_qml"].read_text(encoding="utf-8")
    for token in ["Kérdezd: ", "ADAPTER-GATED", "Models & Providers", "Integrations", "LOCAL-DRAFT", "NOT-SENT", "Fájl hozzáadása", "DropArea", "FileDialog", "responseAttachmentSaveDialog", "saveTextFile", "HelpBubble"]:
        if token not in chat_qml: failures.append(f"qml-role-chat-surface-missing:{token}")
    help_qml = REQUIRED["help_bubble_qml"].read_text(encoding="utf-8")
    for token in ["ToolTip.visible", "helpText", "hovered || pressed"]:
        if token not in help_qml: failures.append(f"qml-help-bubble-missing:{token}")
    for role in ["Mentor", "Coach", "Manager", "Ellenőr", "Ötletelő", "Tanácsadó"]:
        if f'window.openRoleChat("{role}")' not in qml: failures.append(f"qml-role-chat-menu-wiring-missing:{role}")
    if "property bool chatWorkspaceOpen" not in qml or "ChatWorkspace" not in qml or "window.chatWorkspaceOpen ? 19" not in qml:
        failures.append("qml-role-chat-workspace-wiring-missing")

    checkpoint_qml = REQUIRED["checkpoint_qml"].read_text(encoding="utf-8")
    for token in ["Checkpoint Manager", "SHA-256", "serialization/security", "lineage", "runtime compatibility", "EVIDENCE-GATED", "MODEL_CHECKPOINT_GOVERNANCE"]:
        if token not in checkpoint_qml: failures.append(f"qml-checkpoint-manager-surface-missing:{token}")
    external_qml = REQUIRED["external_providers_qml"].read_text(encoding="utf-8")
    for token in ["External Providers Setup", "externalProviders/enabled", "BROKER / SECRETREF ONLY", "FORBIDDEN IN GUI STORAGE", "FAIL-CLOSED", "monthlyBudget"]:
        if token not in external_qml: failures.append(f"qml-external-provider-setup-missing:{token}")
    language_qml = REQUIRED["language_control_qml"].read_text(encoding="utf-8")
    for token in ["Tolmács / Nyelvi híd", "FA3-GUI-LANGUAGE-CONTROL-001", "FA3-LANGUAGE-BRIDGE-001", "Natív modellnyelv előnyben", "Közvetített nyelv engedélyezése", "ADAPTER-GATED", "PENDING_BACKEND", "SECRET", "derived projection"]:
        if token not in language_qml: failures.append(f"qml-language-control-surface-missing:{token}")
    for token in ["id: languageDrawer", "id: languageButton", "Ctrl+Shift+L", "LanguageControlPage"]:
        if token not in qml: failures.append(f"qml-language-control-wiring-missing:{token}")

    for token in ["MCP Control Chat", "fa3McpControl.targets()", "openMcpControlRequested", "ADAPTER-GATED", "No fabricated CONNECTED state"]:
        if token not in integrations_qml: failures.append(f"qml-mcp-integrations-surface-missing:{token}")
    for token in ["Central MCP Gateway", "FA3-MCP-GATEWAY-001", "openMcpGatewayRequested", "MCP Gateway megnyitása"]:
        if token not in integrations_qml: failures.append(f"qml-mcp-gateway-integrations-link-missing:{token}")
    mcp_contract = load_json(REQUIRED["mcp_control_contract"])
    if mcp_contract.get("id") != "FA3-MCP-CONTROL-CHAT-001" or mcp_contract.get("new_architectural_authority") is not False or mcp_contract.get("capability_count_delta") != 0:
        failures.append("mcp-control-authority-contract-invalid")
    for token in ["MCP CONTROL", "WORKFLOW", "MCP Authority", "createDraftRequest", "MCP request vázlat", "Végrehajtás"]:
        if token not in chat_qml: failures.append(f"qml-mcp-control-chat-missing:{token}")
    for token in ["function openMcpChat", "MCP Control Chat", "IntegrationsPage", "workspaceMode: window.chatWorkspaceMode", "requestedMcpTarget: window.mcpChatTarget"]:
        if token not in qml: failures.append(f"qml-mcp-control-wiring-missing:{token}")

    mcp_gateway_qml = REQUIRED["mcp_gateway_qml"].read_text(encoding="utf-8")
    mcp_gateway_service = REQUIRED["mcp_gateway_service"].read_text(encoding="utf-8")
    mcp_gateway_contract = load_json(REQUIRED["mcp_gateway_contract"])
    for token in ["Central MCP Gateway", "Overview", "Servers", "Tools", "Providers", "Capabilities", "Routes", "Requests", "Permissions", "Security", "Logs", "MCP Inspector", "Settings", "No fabricated CONNECTED/PASS"]:
        if token not in mcp_gateway_qml: failures.append(f"qml-mcp-gateway-surface-missing:{token}")
    if mcp_gateway_contract.get("id") != "FA3-MCP-GATEWAY-GUI-001" or mcp_gateway_contract.get("direct_qml_tool_invocation") is not False:
        failures.append("mcp-gateway-page-contract-invalid")
    for token in ["QNetworkAccessManager", "/healthz", "/readyz", "/capabilities", "directQmlExecutionAllowed"]:
        if token not in mcp_gateway_service: failures.append(f"mcp-gateway-readonly-service-missing:{token}")
    if "McpGatewayPage" not in qml or 'routeId: "integrations.mcp-gateway"' not in qml:
        failures.append("qml-mcp-gateway-page-wiring-missing")
    knowledge_qml = REQUIRED["knowledge_qml"].read_text(encoding="utf-8")
    for token in ["Knowledge & Retrieval", "FA3-KNOWLEDGE-001", "Hierarchical + Hybrid", "PageIndex Local", "OpenKB", "ConDB", "RetrievalPlan", "RetrievalTrace", "ContextPassport", "No fabricated CONNECTED/PASS"]:
        if token not in knowledge_qml: failures.append(f"qml-knowledge-surface-missing:{token}")
    if "KnowledgePage" not in qml or 'routeId: "create.knowledge"' not in qml:
        failures.append("qml-knowledge-page-wiring-missing")
    if 'setContextProperty("fa3McpGateway"' not in REQUIRED["main_cpp"].read_text(encoding="utf-8"):
        failures.append("mcp-gateway-service-qml-wiring-missing")

    token_qml = REQUIRED["token_control_qml"].read_text(encoding="utf-8")
    for token in ["Token Control Center", "FA3-TOKEN-GOVERNANCE-001", "Credentialek", "AI tokenhasználat", "Budgetek", "Költségek", "Audit", "Riasztások", "Házirendek", "VAULT / BROKER", "Plaintext secret storage forbidden"]:
        if token not in token_qml: failures.append(f"qml-token-control-center-missing:{token}")
    for token in ["CheckpointManagerPage", "ExternalProvidersSetupPage", "TokenControlCenterPage", 'routeId: "models.checkpoints"', 'routeId: "models.external-providers"', 'routeId: "governance.tokens"']:
        if token not in qml: failures.append(f"qml-management-center-wiring-missing:{token}")

    action_qml = REQUIRED["action_center_qml"].read_text(encoding="utf-8")
    for token in ["Agent Action Center", "Unified Action Fabric", "Stage DRAFT action intent", "Decision Fabric advisory", "fa3Repository.searchActions", "Ez nem UAF execution"]:
        if token not in action_qml: failures.append(f"qml-agent-action-center-missing:{token}")
    work_qml = REQUIRED["work_management_qml"].read_text(encoding="utf-8")
    accel_qml = REQUIRED["accelerator_guard_qml"].read_text(encoding="utf-8")
    for token in ["onRefreshRequested", "onCreateWorkItemRequested", "onTransitionRequested", "onProviderConfigureRequested"]:
        if token not in qml: failures.append(f"qml-work-management-handler-missing:{token}")
    for token in ["accelerators: window.acceleratorProjection(fa3Devices.inventory)", "onRefreshRequested", "onDecisionRequested"]:
        if token not in qml: failures.append(f"qml-accelerator-guard-handler-missing:{token}")
    if "operationNotice" not in work_qml or "operationNotice" not in accel_qml:
        failures.append("qml-draft-intent-feedback-missing")
    update_qml = REQUIRED["update_center_qml"].read_text(encoding="utf-8")
    for token in ["FA3 Update Center", "UAF DRAFT ONLY", "DRAFT_NOT_SUBMITTED", "stageActionIntentRequested", "update.check", "update.apply-selected", "update.security", "update.restart-choice"]:
        if token not in update_qml: failures.append(f"qml-update-center-missing:{token}")
    if 'routeId: "system.updates"' not in qml or "UpdateCenterPage" not in qml:
        failures.append("qml-update-center-route-wiring-missing")
    agency_surface = next((item for item in surface_registry.get("surfaces", []) if item.get("route_id") == "agents.workflows"), {})
    agency_children = {item.get("surface_id"): item for item in agency_surface.get("children", [])}
    agency_pack = agency_children.get("agency-agents.imported-pack", {})
    if not (
        agency_pack.get("provider_id") == "FA3-PROVIDER-AGENCY-AGENTS-001"
        and agency_pack.get("candidate_catalog_id") == "FA3-AGENCY-AGENTS-CURATED-CANDIDATES-001"
        and agency_pack.get("agent_definition_registry_id") == "FA3-AGENT-DEFINITION-REGISTRY-001"
        and agency_pack.get("mode") == "READ_ONLY_CANONICAL_DEFINITIONS"
        and agency_pack.get("activation_status") == "DEFINITION_AVAILABLE_RUNTIME_PROVIDER_SEPARATE"
        and agency_pack.get("execution_intent_route") == "agents.action-center"
        and agency_pack.get("direct_provider_execution") is False
        and agency_pack.get("authority") is False
    ):
        failures.append("gui-agency-agents-imported-pack-boundary-invalid")
    for token in ["Imported Packs · Agency Agents", "12 canonical FA3 role + 5 canonical template", "runtime/provider külön admission", "nincs közvetlen provider execution"]:
        if token not in qml:
            failures.append(f"qml-agency-agents-imported-pack-missing:{token}")
    if "Generic Linux · Wayland primary / X11 supported" not in qml:
        failures.append("qml-desktop-portability-label-missing")

    installer = REQUIRED["installer"].read_text(encoding="utf-8")
    for token in [
        'property var routeTable',
        'function navigate(routeId)',
        'routeId: "agents.action-center"',
        'routeId: "decision.fabric"',
        'routeId: "home.work-management"',
        'routeId: "system.accelerator-guard"',
        'routeId: "system.updates"',
        'routeId: "integrations.fa3-os"',
        'text: "⌕  Keresés"',
        'Generic Linux · Wayland primary / X11 supported',
    ]:
        if token not in installer:
            failures.append(f"installer-semantic-route-contract-missing:{token}")
    if 'label: "Keresés"' in installer:
        failures.append("installer-stale-search-navigation-marker-present")
    if "NavButton is still coupled to pageIndex" not in installer:
        failures.append("installer-pageindex-drift-guard-missing")
    if "--check-source-contract" not in installer or "CHECK_SOURCE_CONTRACT_ONLY" not in installer:
        failures.append("installer-source-contract-check-mode-missing")

    model_cpp = REQUIRED["model_cpp"].read_text(encoding="utf-8")
    if "searchActions" not in model_cpp or "canonical/actions" not in model_cpp:
        failures.append("backend-uaf-action-catalog-search-missing")
    if "DRAFT_NOT_SUBMITTED" not in model_cpp: failures.append("backend-draft-status-missing")
    if '"direct_execution_allowed", false' not in model_cpp: failures.append("backend-direct-execution-denial-missing")
    if '"canonical_write_allowed", false' not in model_cpp: failures.append("backend-canonical-write-denial-missing")
    if "searchInstalledApplications" not in model_cpp or "scanApplications" not in model_cpp or "QSettings" not in model_cpp: failures.append("backend-installed-app-search-missing")
    mcp_cpp = REQUIRED["mcp_control_service"].read_text(encoding="utf-8")
    for token in ["DRAFT_NOT_SUBMITTED", "direct_tool_invocation_allowed", "gui_self_approval_allowed", "ADAPTER-GATED", "authoritySnapshot"]:
        if token not in mcp_cpp: failures.append(f"mcp-control-service-missing:{token}")
    chat_file_cpp = REQUIRED["chat_file_service"].read_text(encoding="utf-8")
    for token in ["inspectLocalFile", "QMimeDatabase", "QSaveFile", "copyLocalFile", "GENERIC_BINARY"]:
        if token not in chat_file_cpp: failures.append(f"chat-file-service-missing:{token}")
    main_cpp = REQUIRED["main_cpp"].read_text(encoding="utf-8")
    if "ChatFileService" not in main_cpp or 'setContextProperty("fa3ChatFiles"' not in main_cpp:
        failures.append("chat-file-service-qml-wiring-missing")
    if "McpControlService" not in main_cpp or 'setContextProperty("fa3McpControl"' not in main_cpp:
        failures.append("mcp-control-service-qml-wiring-missing")
    for token in FORBIDDEN_BACKEND_TOKENS:
        if token in model_cpp or token in device_cpp or token in preference_cpp or token in chat_file_cpp or token in mcp_cpp: failures.append(f"backend-forbidden-token:{token}")

    cmake = REQUIRED["cmake"].read_text(encoding="utf-8")
    if "Qt6" not in cmake or "qt_add_qml_module" not in cmake: failures.append("qt6-qml-build-contract-missing")
    if "PrintSupport" not in cmake or "PreferenceStore.cpp" not in cmake or "SystemDeviceModel.cpp" not in cmake: failures.append("settings-device-build-wiring-missing")
    for token in ["QuickDialogs2", "ChatFileService.cpp", "HelpBubble.qml", "McpControlService.cpp", "IntegrationsPage.qml", "McpGatewayService.cpp", "McpGatewayPage.qml", "KnowledgePage.qml", "AgentActionCenterPage.qml", "UpdateCenterPage.qml", "SubtitleStudioPage.qml", "NarrationStudioPage.qml"]:
        if token not in cmake: failures.append(f"chat-file-build-wiring-missing:{token}")
    installer = REQUIRED["installer"].read_text(encoding="utf-8")
    if "qml6-module-qtquick-dialogs" not in installer: failures.append("chat-file-installer-dialogs-missing")
    desktop = REQUIRED["desktop"].read_text(encoding="utf-8")
    if "Exec=fa3-control-center" not in desktop: failures.append("desktop-entry-exec-missing")
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 GUI gate: FAIL")
        for failure in failures: print(f" - {failure}")
        return 1
    print("FA3 GUI gate: PASS")
    runtime = load_json(REQUIRED["runtime"])
    print(f"profile=FA3-DESKTOP-001 capabilities=143 new_authorities=0 runtime={runtime.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
