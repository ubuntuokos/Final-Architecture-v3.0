from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class GenerativeMediaStudioGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]

    def load(self, rel: str) -> dict:
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def test_static_gate_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.root / "src/fa3_generative_media_studio_gate.py"), "--root", str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "PASS")
        self.assertEqual(payload["gate_id"], "FA3-GENERATIVE-MEDIA-STUDIO-GATESET-001")
        self.assertIn("CURRENT_HOST_BUILD_PASS", payload["non_claims"])
        self.assertFalse(payload["current_host_runtime_promotion_claim"])

    def test_contract_keeps_authorities_external(self) -> None:
        contract = self.load("canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json")
        self.assertEqual(contract["capability_count"], 175)
        self.assertFalse(contract["new_capability"])
        self.assertFalse(contract["new_architectural_authority"])
        self.assertEqual(contract["authority_boundaries"]["provider_routing"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(contract["authority_boundaries"]["host_resources"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertEqual(contract["authority_boundaries"]["action_execution"], "FA3-UNIFIED-ACTION-FABRIC-001")
        self.assertFalse(contract["request_compilation"]["physical_provider_pin_allowed"])
        self.assertFalse(contract["request_compilation"]["physical_model_pin_allowed"])
        self.assertEqual(contract["request_compilation"]["initial_state"], "PENDING_ADMISSION")

    def test_request_schema_denies_physical_pins_and_runtime_claim(self) -> None:
        schema = self.load("canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-REQUEST-001.schema.json")
        route = schema["properties"]["route"]["properties"]
        self.assertFalse(route["physical_provider_pin"]["const"])
        self.assertFalse(route["physical_model_pin"]["const"])
        self.assertEqual(route["authority"]["const"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertFalse(schema["properties"]["runtime_success_claim"]["const"])
        self.assertEqual(schema["properties"]["state"]["const"], "PENDING_ADMISSION")

    def test_ui_duration_is_application_scoped(self) -> None:
        contract = self.load("canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json")
        duration = contract["studio_ui_policy"]["self_contained_video_duration_seconds"]
        self.assertEqual(duration["minimum"], 6)
        self.assertEqual(duration["maximum"], 20)
        self.assertEqual(duration["scope"], "STUDIO_SHOT_CONTROL_ONLY")
        self.assertTrue(duration["provider_capability_may_be_narrower"])
        self.assertTrue(duration["provider_capability_may_be_broader"])
        qml = (self.root / "apps/fa3-generative-media-studio/qml/Main.qml").read_text(encoding="utf-8")
        self.assertIn("from: 6", qml)
        self.assertIn("to: 20", qml)

    def test_hardware_audit_is_vendor_neutral(self) -> None:
        contract = self.load("canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json")
        hardware = contract["hardware_audit"]
        self.assertTrue(hardware["vendor_neutral"])
        self.assertTrue(hardware["cpu_only_architecture_supported"])
        self.assertEqual(hardware["accelerator_cardinality"], "0..N")
        self.assertEqual(hardware["fixed_gpu_vendor_model_ordinal_or_count"], "FORBIDDEN")
        self.assertEqual(hardware["display_accelerator_implicit_compute_fallback"], "FORBIDDEN")

    def test_autom8ai_is_discovery_not_authority(self) -> None:
        ref = self.load("canonical/references/FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28.json")
        self.assertFalse(ref["policy"]["autom8ai_fork_is_canonical_source"])
        self.assertTrue(ref["policy"]["original_upstream_is_canonical_donor_source"])
        self.assertFalse(ref["policy"]["code_imported_by_this_change"])

    def test_reuse_governance_has_no_capability_or_authority_delta(self) -> None:
        intent = self.load("canonical/intents/FA3-GENERATIVE-MEDIA-STUDIO-APPLICATION-INTENT-001.json")
        assessment = self.load("canonical/assessments/FA3-GENERATIVE-MEDIA-STUDIO-REUSE-ASSESSMENT-001.json")
        self.assertEqual(intent["declared_new_capabilities"], [])
        self.assertEqual(intent["proposed_authority_roles"], [])
        self.assertFalse(intent["namespace_claims"]["requires_upstream_uninstall"])
        self.assertFalse(intent["namespace_claims"]["global_environment_mutation"])
        self.assertEqual(assessment["result"], "PASS")
        self.assertEqual(assessment["capability_count_after"], 175)
        self.assertEqual(assessment["new_architectural_authorities"], 0)
        self.assertFalse(assessment["current_host_runtime_promotion_claim"])
        self.assertFalse(assessment["global_promotion_claim"])

    def test_backend_has_no_direct_provider_execution_surface(self) -> None:
        backend = (self.root / "apps/fa3-generative-media-studio/src/StudioBackend.cpp").read_text(encoding="utf-8")
        for forbidden in ("QProcess", "QNetworkAccessManager", "QTcpSocket", "curl ", "wget ", "system("):
            self.assertNotIn(forbidden, backend)
        self.assertIn("FA3-AUTH-MODEL-ROUTER-001", backend)
        self.assertIn("FA3-AUTH-HOST-RESOURCE-BROKER-001", backend)
        self.assertIn("PENDING_ADMISSION", backend)

    def test_global_mandatory_gate_binding(self) -> None:
        registry = self.load("canonical/FA3-GATE-REGISTRY-001.json")
        policy = self.load("canonical/enforcement-policy.json")
        self.assertIn("FA3-GENERATIVE-MEDIA-STUDIO-GATESET-001", registry["mandatory_reference_gates"])
        self.assertEqual(registry["mandatory_reference_gates"], policy["mandatory_reference_gates"])
        self.assertEqual(policy["generative_media_studio_profile_id"], "FA3-GENERATIVE-MEDIA-STUDIO-001")
        self.assertEqual(policy["generative_media_studio_contract_id"], "FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001")
        self.assertEqual(policy["generative_media_studio_gate_id"], "FA3-GENERATIVE-MEDIA-STUDIO-GATESET-001")
        self.assertFalse(policy["generative_media_studio_current_host_runtime_promotion_claim"])

    def test_gate_record_never_promotes_runtime(self) -> None:
        gate = self.load("canonical/FA3-GATE-GENERATIVE-MEDIA-STUDIO-001.json")
        enforcement = self.load("canonical/generative-media-studio-enforcement.json")
        self.assertTrue(gate["fail_closed"])
        self.assertFalse(gate["static_pass_promotes_runtime"])
        self.assertFalse(gate["current_host_runtime_promotion_claim"])
        self.assertTrue(enforcement["fail_closed"])
        self.assertFalse(enforcement["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
