import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_shared_plugin_extension_current_host_gate import gate as current_host_gate

from fa3_shared_plugin_extension_fabric import (
    HRB,
    MODEL_ROUTER,
    SECURITY,
    SharedComponentError,
    ai_access_decision,
    binding_decision,
    derive_bindings,
    runtime_request,
    validate_manifest,
)


def manifest(kind="PLUGIN", uses_ai=True):
    return {
        "schema": "fa3.shared-plugin-extension-manifest.v1",
        "component_id": "FA3-COMPONENT-TEST-001",
        "kind": kind,
        "scope": "SHARED",
        "authority": False,
        "automatic_activation": False,
        "capabilities": {
            "provides": ["fa3.image.super-resolution", "fa3.image.denoise"],
            "requires_host": ["fa3.image.buffer"],
        },
        "host_contracts": ["fa3.image.host.v1"],
        "provenance": {
            "source": "https://example.invalid/component",
            "immutable_revision": "abc123",
            "content_sha256": "a" * 64,
            "license": "MIT",
        },
        "ai": {
            "uses_ai": uses_ai,
            "capabilities": ["fa3.ai.super-resolution"] if uses_ai else [],
            "default_access": "DISABLED",
            "direct_provider_access": False,
            "silent_fallback": False,
            "route_authority": MODEL_ROUTER,
        },
        "runtime": {"hardware_authority": HRB},
        "security": {"admission_authority": SECURITY},
    }


class SharedPluginExtensionFabricTests(unittest.TestCase):
    def test_plugin_and_extension_are_shared(self):
        validate_manifest(manifest("PLUGIN"))
        validate_manifest(manifest("EXTENSION"))

    def test_single_app_hard_binding_is_not_part_of_manifest(self):
        m = manifest()
        self.assertNotIn("application_id", m)
        self.assertEqual(m["scope"], "SHARED")

    def test_binding_is_capability_and_contract_based(self):
        app = {
            "application_id": "fa3.photo",
            "host_capabilities": ["fa3.image.buffer"],
            "host_contracts": ["fa3.image.host.v1"],
            "capabilities": ["fa3.image.denoise"],
            "accepted_component_kinds": ["PLUGIN", "EXTENSION"],
            "denied_components": [],
        }
        d = binding_decision(manifest(), app)
        self.assertTrue(d.eligible)
        self.assertEqual(d.added_capabilities, ("fa3.image.super-resolution",))

    def test_binding_rejects_incompatible_app(self):
        app = {
            "application_id": "fa3.story",
            "host_capabilities": [],
            "host_contracts": [],
            "capabilities": [],
            "accepted_component_kinds": ["PLUGIN", "EXTENSION"],
            "denied_components": [],
        }
        d = binding_decision(manifest(), app)
        self.assertFalse(d.eligible)
        self.assertTrue(any(x.startswith("MISSING_HOST_CAPABILITIES") for x in d.reasons))

    def test_same_component_can_bind_to_multiple_apps(self):
        base = {
            "host_capabilities": ["fa3.image.buffer"],
            "host_contracts": ["fa3.image.host.v1"],
            "capabilities": [],
            "accepted_component_kinds": ["PLUGIN", "EXTENSION"],
            "denied_components": [],
        }
        rows = derive_bindings(manifest(), [
            {**base, "application_id": "fa3.photo"},
            {**base, "application_id": "fa3.video"},
        ])
        self.assertEqual([r["eligible"] for r in rows], [True, True])

    def test_global_ai_off_is_absolute(self):
        d = ai_access_decision(
            manifest(),
            capability="fa3.ai.super-resolution",
            global_policy={"state": "DISABLED", "local_allowed": True, "remote_allowed": True},
            application_policy={"state": "ENABLED", "remote_allowed": True},
            component_policy={"state": "ENABLED", "remote_allowed": True},
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "GLOBAL_AI_DISABLED")

    def test_app_module_component_and_capability_can_disable_ai(self):
        for slot in ("application_policy", "module_policy", "component_policy", "capability_policy"):
            kwargs = dict(
                capability="fa3.ai.super-resolution",
                global_policy={"state": "ENABLED", "local_allowed": True, "remote_allowed": True},
            )
            kwargs[slot] = {"state": "DISABLED"}
            self.assertFalse(ai_access_decision(manifest(), **kwargs).allowed)

    def test_external_component_ai_defaults_disabled(self):
        d = ai_access_decision(
            manifest(),
            capability="fa3.ai.super-resolution",
            global_policy={"state": "INHERIT", "local_allowed": True, "remote_allowed": False},
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "AI_NOT_EXPLICITLY_ENABLED")

    def test_local_ai_can_be_enabled(self):
        d = ai_access_decision(
            manifest(),
            capability="fa3.ai.super-resolution",
            global_policy={"state": "ENABLED", "local_allowed": True, "remote_allowed": False},
            requested_route="LOCAL",
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.route_authority, MODEL_ROUTER)
        self.assertFalse(d.silent_fallback_allowed)

    def test_remote_child_policy_cannot_expand_global_egress(self):
        d = ai_access_decision(
            manifest(),
            capability="fa3.ai.super-resolution",
            global_policy={"state": "ENABLED", "local_allowed": True, "remote_allowed": False},
            application_policy={"state": "ENABLED", "remote_allowed": True},
            requested_route="REMOTE",
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "REMOTE_AI_ROUTE_DISABLED")

    def test_runtime_request_never_selects_provider_or_model(self):
        decision = ai_access_decision(
            manifest(),
            capability="fa3.ai.super-resolution",
            global_policy={"state": "ENABLED", "local_allowed": True, "remote_allowed": False},
        )
        req = runtime_request(
            manifest(),
            capability="fa3.ai.super-resolution",
            ai_decision=decision,
            application_id="fa3.photo",
        )
        self.assertEqual(req["model_route_authority"], MODEL_ROUTER)
        self.assertIsNone(req["provider_id"])
        self.assertIsNone(req["model_id"])
        self.assertFalse(req["direct_provider_access"])
        self.assertFalse(req["silent_fallback"])

    def test_direct_provider_access_manifest_rejected(self):
        m = manifest()
        m["ai"]["direct_provider_access"] = True
        with self.assertRaises(SharedComponentError):
            validate_manifest(m)

    def test_automatic_activation_rejected(self):
        m = manifest()
        m["automatic_activation"] = True
        with self.assertRaises(SharedComponentError):
            validate_manifest(m)

    def test_current_host_gate_blocks_without_physical_receipt(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "canonical").mkdir()
            src = ROOT / "canonical/FA3-SHARED-PLUGIN-EXTENSION-CURRENT-HOST-CONFORMANCE-001.json"
            (base / "canonical/FA3-SHARED-PLUGIN-EXTENSION-CURRENT-HOST-CONFORMANCE-001.json").write_text(src.read_text())
            r = current_host_gate(base)
            self.assertEqual(r["result"], "BLOCKED")
            self.assertFalse(r["production_promotion"])

    def test_current_host_gate_requires_all_physical_proofs(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "canonical").mkdir()
            (base / "evidence/receipts").mkdir(parents=True)
            src = ROOT / "canonical/FA3-SHARED-PLUGIN-EXTENSION-CURRENT-HOST-CONFORMANCE-001.json"
            (base / "canonical/FA3-SHARED-PLUGIN-EXTENSION-CURRENT-HOST-CONFORMANCE-001.json").write_text(src.read_text())
            receipt = {
                "schema": "fa3.shared-plugin-extension-current-host-receipt.v1",
                "physical_host": True,
                "same_component_two_apps": True,
                "ai_toggle_proof": {"global": True, "application": True, "module": True, "component": True, "capability": True},
                "negative_proof": {"direct_provider_rejected": True, "silent_fallback_rejected": True, "automatic_activation_rejected": True},
                "software_coexistence_pass": True,
                "hardware_safety_envelope_pass": True,
                "rollback_pass": True,
                "result": "PASS",
            }
            rp = base / "evidence/receipts/shared-plugin-extension-current-host.json"
            rp.write_text(json.dumps(receipt))
            r = current_host_gate(base)
            self.assertEqual(r["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
