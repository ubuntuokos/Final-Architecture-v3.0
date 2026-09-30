import json
import unittest
from pathlib import Path

from fa3_plugin_extension_manager import effective_execution_allowed, shared_binding_state, validate_manifest
from fa3_plugin_extension_gate import gate

ROOT=Path(__file__).resolve().parents[1]

class PluginExtensionManagerTests(unittest.TestCase):
    def test_materialization_gate(self):
        self.assertEqual("PASS", gate(ROOT)["result"])

    def test_installed_is_not_automatically_executable(self):
        state={"trust":"ADMITTED","installation":"INSTALLED","activation":"DISABLED",
               "compatible":True,"permission_allowed":True,"layer_allowed":True,
               "coexistence_pass":True,"resource_admitted":True,
               "required_evidence_valid":True,"host_binding_valid":True,
               "ai_class":"AI_NONE","ai_requested":False}
        decision=effective_execution_allowed(state)
        self.assertFalse(decision.allowed)
        self.assertIn("not-enabled",decision.reasons)

    def test_ai_deny_wins_without_silent_fallback(self):
        state={"trust":"ADMITTED","installation":"INSTALLED","activation":"ENABLED",
               "compatible":True,"permission_allowed":True,"layer_allowed":True,
               "coexistence_pass":True,"resource_admitted":True,
               "required_evidence_valid":True,"host_binding_valid":True,
               "ai_class":"AI_OPTIONAL","ai_requested":True,
               "ai_policy_allowed":False,"model_router_allowed":True,"requested_provider_allowed":True}
        decision=effective_execution_allowed(state)
        self.assertFalse(decision.allowed)
        self.assertIn("ai-policy-denied",decision.reasons)

    def test_shared_package_binding_is_per_application(self):
        pkg={"id":"P","installation":"INSTALLED","consumer_bindings":{"video":{"enabled":True},"story":{"enabled":False}}}
        self.assertTrue(shared_binding_state(pkg,"video")["enabled"])
        self.assertFalse(shared_binding_state(pkg,"story")["enabled"])

    def test_manifest_requires_declared_surface(self):
        self.assertTrue(validate_manifest({"schema":"fa3.plugin-extension.manifest.v1"}))

    def test_ui_binding_is_global_and_standalone(self):
        data=json.loads((ROOT/"canonical/FA3-PLUGIN-EXTENSION-UI-BINDINGS-001.json").read_text())
        self.assertEqual("ALL_FA3_GUI_APPLICATIONS",data["scope"])
        self.assertFalse(data["standalone_entry"]["target_application_must_be_running"])
        self.assertTrue(data["application_binding_contract"]["standalone_manageable_required"])

if __name__=="__main__":
    unittest.main()
