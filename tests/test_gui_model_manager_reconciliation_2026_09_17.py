from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GuiModelManagerReconciliationTests(unittest.TestCase):
    def text(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def data(self, path: str) -> dict:
        return json.loads(self.text(path))

    def test_current_main_shell_is_extended_not_replaced(self) -> None:
        main = self.text("apps/fa3-control-center/qml/Main.qml")
        self.assertIn("Remote AI Hub", main)
        self.assertIn("Models & Providers", main)
        self.assertIn("Model Manager", main)
        self.assertIn("Tolmács", main)
        self.assertNotIn("LegacyMain {", main)

    def test_resource_status_is_real_overlay(self) -> None:
        main_cpp = self.text("apps/fa3-control-center/src/main.cpp")
        qml = self.text("apps/fa3-control-center/qml/ResourceStatusStrip.qml")
        self.assertIn('setContextProperty("fa3ResourceTelemetry"', main_cpp)
        self.assertIn('attachOverlay(QStringLiteral("ResourceStatusStrip.qml"))', main_cpp)
        for token in ["cpuPercent", "gpuPercent", "npuAvailable", "ramPercent", "pressureState"]:
            self.assertIn(token, qml)

    def test_language_policy_and_live_interpreter_are_both_materialized(self) -> None:
        wrapper = self.text("apps/fa3-control-center/qml/LanguageControlPage.qml")
        live = self.text("apps/fa3-control-center/qml/LiveInterpreterPage.qml")
        policy = self.text("apps/fa3-control-center/qml/LanguagePolicyPage.qml")
        main_cpp = self.text("apps/fa3-control-center/src/main.cpp")
        self.assertIn("primaryLanguage !== secondaryLanguage", wrapper)
        self.assertIn("LiveInterpreterPage", wrapper)
        self.assertIn("LanguagePolicyPage", wrapper)
        self.assertIn("fa3Interpreter.startLive", live)
        self.assertIn("FA3-PROVIDER-WHISPER-001", live)
        self.assertIn("property string primaryLanguage", policy)
        self.assertIn('setContextProperty("fa3Interpreter"', main_cpp)

    def test_tools_update_manager_and_model_lab_are_projection_only(self) -> None:
        main_cpp = self.text("apps/fa3-control-center/src/main.cpp")
        overlay = self.text("apps/fa3-control-center/qml/OperationsExtensionsOverlay.qml")
        tools = self.text("apps/fa3-control-center/qml/ToolsOverlay.qml")
        self.assertIn('attachOverlay(QStringLiteral("ToolsOverlay.qml"))', main_cpp)
        self.assertIn('attachOverlay(QStringLiteral("OperationsExtensionsOverlay.qml"))', main_cpp)
        for token in ["ManagerPage", "OpenModelDbPage", "LlmfitPage", "UpdateCenterPage", "DRAFT_NOT_SUBMITTED"]:
            self.assertIn(token, overlay)
        self.assertIn("FA3 Tools", tools)

    def test_llmfit_remains_advisory_and_hrb_owned(self) -> None:
        profile = self.data("canonical/profiles/FA3-MODEL-MANAGER-001.json")
        provider = self.data("canonical/providers/FA3-PROVIDER-LLMFIT-001.json")
        self.assertIn("FA3-PROVIDER-LLMFIT-001", profile["providers"])
        self.assertFalse(profile["llmfit_gui_extension"]["estimate_is_runtime_evidence"])
        self.assertFalse(provider["architectural_authority"])
        self.assertEqual(provider["fa3_usage_policy"]["accelerator_placement"], "DELEGATE_TO_HOST_RESOURCE_BROKER")

    def test_capability_and_authority_baseline_is_unchanged(self) -> None:
        for path in [
            "canonical/profiles/FA3-REMOTE-AI-EXEC-001.json",
            "canonical/providers/FA3-PROVIDER-LLMFIT-001.json",
            "canonical/FA3-TOOLS-FABRIC-001.json",
        ]:
            data = self.data(path)
            serialized = json.dumps(data)
            self.assertIn("143", serialized)
        self.assertFalse(self.data("canonical/providers/FA3-PROVIDER-LLMFIT-001.json")["architectural_authority"])


if __name__ == "__main__":
    unittest.main()
