import unittest
from pathlib import Path

from src import fa3_gui_gate


ROOT = Path(__file__).resolve().parents[1]


class Fa3GuiGateTests(unittest.TestCase):
    def test_gui_materialization_is_fail_closed_and_authority_neutral(self):
        self.assertEqual([], fa3_gui_gate.validate())

    def test_checkpoint_manager_is_operational_shared_model_library(self):
        qml = (ROOT / "apps/fa3-control-center/qml/CheckpointManagerPage.qml").read_text(encoding="utf-8")
        service = (ROOT / "apps/fa3-control-center/src/ModelLibraryService.cpp").read_text(encoding="utf-8")
        main_cpp = (ROOT / "apps/fa3-control-center/src/main.cpp").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")

        for token in [
            "SHARED STORAGE", "Checkpoints", "LoRA", "VAE", "Diffusion / Video",
            "CivitAI böngészés", "Hugging Face böngészés", "Built-in Model Downloader",
            "ComfyUI", "Automatic1111", "Forge", "Fooocus", "DropArea", "Metadata & Preview",
        ]:
            self.assertIn(token, qml)

        for token in [
            "importFiles", "moveModel", "saveMetadata", "setPreview", "linkClient",
            "create_directory_symlink", "startDownload", "NoLessSafeRedirectPolicy",
            "Credential/token nem kerülhet URL-be",
        ]:
            self.assertIn(token, service)

        self.assertIn('setContextProperty("fa3ModelLibrary"', main_cpp)
        self.assertIn("ModelLibraryService.cpp", cmake)
        self.assertIn("Qt6::Network", cmake)

    def test_application_search_uses_canonical_catalog_and_navigation_uses_routes(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        catalog = (ROOT / "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json").read_text(encoding="utf-8")

        self.assertNotIn("property var fa3ApplicationIndex", main)
        self.assertIn("function searchFa3Applications", main)
        self.assertIn("fa3AppCatalog.applications", main)
        self.assertIn("var apps = searchFa3Applications(needle)", main)
        self.assertNotIn("fa3Repository.searchInstalledApplications(needle)", main)
        self.assertIn('{label: "FA3 alkalmazások", value: "APPLICATION"}', main)
        for app in ["ComfyUI", "InvokeAI", "Kdenlive", "Bforartists", "Natron", "Gaffer", "Demucs", "DeepFilterNet", "Mautic", "Twenty", "listmonk"]:
            self.assertIn('"name": "' + app + '"', catalog)

        self.assertIn('property var routeTable', main)
        self.assertIn('function navigate(routeId)', main)
        self.assertIn('routeId: "create.ai-studio"', main)
        self.assertIn('routeId: "integrations.root"', main)
        self.assertNotIn('property int pageIndex: 0', main[main.index("component NavButton"):main.index("component ModuleCard")])

    def test_language_control_is_restored_as_global_drawer(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        page = (ROOT / "apps/fa3-control-center/qml/LanguageControlPage.qml").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")

        for token in ["id: languageDrawer", "id: languageButton", "Ctrl+Shift+L", "Tolmács / Nyelvi híd", "LanguageControlPage"]:
            self.assertIn(token, main)
        for token in ["FA3-GUI-LANGUAGE-CONTROL-001", "FA3-LANGUAGE-BRIDGE-001", "ADAPTER-GATED", "PENDING_BACKEND", "SECRET", "derived projection"]:
            self.assertIn(token, page)
        self.assertIn("qml/LanguageControlPage.qml", cmake)

    def test_translator_is_permanent_and_assistant_toolbar_is_responsive(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        self.assertIn('id: assistantToolbar', main)
        self.assertIn('Layout.preferredHeight: 104', main)
        self.assertIn('text: "ASSZISZTENS"', main)
        self.assertIn('Layout.minimumWidth: 180', main)
        self.assertIn('text: "文/A  Tolmács"', main)
        self.assertIn('Layout.minimumWidth: 118', main)
        self.assertIn('function openLanguageControl()', main)
        self.assertIn('function openLanguageControl()', main)
        self.assertIn('navigate("global.language")', main)
        self.assertGreaterEqual(main.count('LanguageControlPage {'), 2)
        self.assertIn('onActivated: window.openLanguageControl()', main)
        self.assertIn('onClicked: window.openLanguageControl()', main)

    def test_chat_workspace_is_responsive_and_keeps_controls_in_bounds(self):
        chat = (ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml").read_text(encoding="utf-8")

        for token in [
            'property bool narrowLayout: width < 980',
            'property bool veryNarrowLayout: width < 760',
            'id: modeFlow',
            'id: actionFlow',
            'Layout.minimumWidth: 0',
            'var available = Math.max(0, messageItem.width - 10)',
            'Math.max(0, pendingAttachmentList.width - 8)',
            'Layout.preferredHeight: childrenRect.height',
        ]:
            self.assertIn(token, chat)

        self.assertNotIn('Layout.preferredHeight: root.isMcpMode() ? 126 : 104', chat)
        self.assertNotIn('Layout.preferredHeight: root.viewMode === "Compact" ? 116 : 154', chat)

    def test_installer_tracks_semantic_routes_not_removed_search_nav_item(self):
        installer = (ROOT / "deployment/fa3-gui/install.sh").read_text(encoding="utf-8")
        for token in [
            'property var routeTable',
            'function navigate(routeId)',
            'routeId: "agents.action-center"',
            'routeId: "decision.fabric"',
            'routeId: "home.work-management"',
            'routeId: "system.accelerator-guard"',
            'routeId: "integrations.fa3-os"',
            'text: "⌕  Keresés"',
            'Generic Linux · Wayland primary / X11 supported',
        ]:
            self.assertIn(token, installer)
        self.assertNotIn('label: "Keresés"', installer)
        self.assertIn("NavButton is still coupled to pageIndex", installer)

    def test_agent_native_decision_fabric_and_dead_signal_reconciliation(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        action = (ROOT / "apps/fa3-control-center/qml/AgentActionCenterPage.qml").read_text(encoding="utf-8")
        model = (ROOT / "apps/fa3-control-center/src/Fa3RepositoryModel.cpp").read_text(encoding="utf-8")
        registry = (ROOT / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json").read_text(encoding="utf-8")

        for group in ["HOME", "CREATE", "AGENTS", "MODELS & DATA", "DECISION & CONTEXT", "INTEGRATIONS", "GOVERNANCE", "SYSTEM"]:
            self.assertIn('text: "' + group + '"', main)
        for route in ["agents.action-center", "decision.fabric", "decision.inspector", "decision.context-inspector", "decision.project-radar"]:
            self.assertIn('"' + route + '"', main)
            self.assertIn('"route_id": "' + route + '"', registry)

        for token in ["Agent Action Center", "Stage DRAFT action intent", "Ez nem UAF execution", "Decision Fabric advisory"]:
            self.assertIn(token, action)
        self.assertIn("searchActions", model)
        self.assertIn("canonical/actions", model)
        for token in ["onCreateWorkItemRequested", "onTransitionRequested", "onProviderConfigureRequested", "onDecisionRequested"]:
            self.assertIn(token, main)
        self.assertIn("accelerators: window.acceleratorProjection(fa3Devices.inventory)", main)
        self.assertIn("Generic Linux · Wayland primary / X11 supported", main)

    def test_mcp_control_chat_is_authority_gated_and_integrated(self):
        main = (ROOT / "apps/fa3-control-center/qml/Main.qml").read_text(encoding="utf-8")
        chat = (ROOT / "apps/fa3-control-center/qml/ChatWorkspace.qml").read_text(encoding="utf-8")
        integrations = (ROOT / "apps/fa3-control-center/qml/IntegrationsPage.qml").read_text(encoding="utf-8")
        service = (ROOT / "apps/fa3-control-center/src/McpControlService.cpp").read_text(encoding="utf-8")
        contract = (ROOT / "canonical/FA3-MCP-CONTROL-CHAT-001.json").read_text(encoding="utf-8")
        cmake = (ROOT / "apps/fa3-control-center/CMakeLists.txt").read_text(encoding="utf-8")

        for token in ["function openMcpChat", "MCP Control Chat", "IntegrationsPage", "workspaceMode: window.chatWorkspaceMode"]:
            self.assertIn(token, main)
        for token in ["MCP CONTROL", "WORKFLOW", "MCP Authority", "MCP request vázlat", "Végrehajtás", "createDraftRequest"]:
            self.assertIn(token, chat)
        for token in ["GIMP", "Krita", "Blender", "Kdenlive", "OpenShot", "Inkscape", "Ardour", "No fabricated CONNECTED state"]:
            self.assertIn(token, integrations)
        for token in ["DRAFT_NOT_SUBMITTED", "direct_tool_invocation_allowed", "gui_self_approval_allowed", "execution_without_policy_allowed", "execution_without_evidence_allowed"]:
            self.assertIn(token, service)
        self.assertIn('"new_architectural_authority": false', contract)
        self.assertIn('"capability_count_delta": 0', contract)
        self.assertIn("McpControlService.cpp", cmake)
        self.assertIn("IntegrationsPage.qml", cmake)


if __name__ == "__main__":
    unittest.main()
