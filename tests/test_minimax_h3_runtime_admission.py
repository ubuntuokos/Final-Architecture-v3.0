import json
import tempfile
import unittest
from pathlib import Path

from fa3_minimax_h3_provider_adapter import (
    GLOBAL_API_BASE,
    H3AdmissionError,
    H3HostedConfig,
    H3ProviderError,
    MiniMaxH3Adapter,
    admit_local_execution,
    project_video_generation_ir,
    validate_credential_class,
)

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class FakeTransport:
    def __init__(self, fail_status=None):
        self.calls = []
        self.fail_status = fail_status

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body, "timeout": timeout})
        if self.fail_status is not None and "/v2/video_generation" in url and method == "POST":
            return self.fail_status, {"Content-Type": "application/json"}, b'{"error":"denied"}'
        if url.endswith("/v2/video_generation") and method == "POST":
            return 200, {"Content-Type": "application/json", "X-RateLimit-Remaining": "7"}, b'{"task_id":"task-1"}'
        if url.endswith("/v2/h3_context_ir") and method == "POST":
            return 200, {"Content-Type": "application/json"}, b'{"task_id":"context-1"}'
        if "/v2/query/video_generation/" in url and method == "GET":
            return 200, {"Content-Type": "application/json"}, b'{"task":{"status":"succeeded","content":{"url":"https://cdn.example/h3.mp4"},"usage":{"provider_units":1}}}'
        if url == "https://cdn.example/h3.mp4" and method == "GET":
            return 200, {"Content-Type": "video/mp4"}, b"FAKE-MP4-BYTES"
        raise AssertionError(f"unexpected transport call: {method} {url}")


class MiniMaxH3RuntimeAdmissionTests(unittest.TestCase):
    def config(self, **overrides):
        values = dict(
            token="unit-test-secret",
            credential_class="PAYG_API_KEY",
            service_terms_admitted=True,
            api_base=GLOBAL_API_BASE,
            poll_interval_seconds=0,
            poll_timeout_seconds=1,
        )
        values.update(overrides)
        return H3HostedConfig(**values)

    def test_credential_class_must_be_explicit(self):
        for bad in ("", "api-key", "unknown"):
            with self.assertRaises(H3AdmissionError):
                validate_credential_class(bad)

    def test_subscription_key_requires_explicit_production_policy(self):
        with self.assertRaises(H3AdmissionError):
            self.config(credential_class="TOKEN_PLAN_SUBSCRIPTION_KEY").validated()
        admitted = self.config(
            credential_class="TOKEN_PLAN_SUBSCRIPTION_KEY",
            allow_subscription_for_production=True,
        ).validated()
        self.assertEqual(admitted.credential_class, "TOKEN_PLAN_SUBSCRIPTION_KEY")

    def test_service_terms_are_fail_closed(self):
        with self.assertRaises(H3AdmissionError):
            self.config(service_terms_admitted=False).validated()

    def test_local_execution_denied_without_license_evidence(self):
        self.assertEqual(
            admit_local_execution(None)["state"],
            "LOCAL_DENIED_WITHOUT_LICENSE_EVIDENCE",
        )

    def test_local_execution_requires_explicit_allow_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "license.json"
            p.write_text(json.dumps({
                "deployment_authorized": True,
                "territory_evaluation": "ALLOW",
                "decision": "ALLOW",
            }), encoding="utf-8")
            result = admit_local_execution(p)
            self.assertEqual(result["result"], "ALLOW")
            self.assertEqual(result["state"], "LOCAL_LICENSE_ADMISSION_PASS")

    def test_video_generation_ir_projects_without_replacing_canonical_ir(self):
        ir = {
            "prompt": "A quiet cinematic room",
            "duration": 4,
            "resolution": "768P",
            "ratio": "16:9",
            "references": [
                {"media_type": "image", "url": "https://example.invalid/frame.png", "role": "first_frame"}
            ],
        }
        projected = project_video_generation_ir(ir)
        self.assertEqual(projected["model"], "MiniMax-H3")
        self.assertEqual(projected["duration"], 4)
        self.assertEqual(projected["content"][1]["role"], "first_frame")
        self.assertNotIn("provider_id", ir)

    def test_projection_rejects_invalid_duration_and_resolution(self):
        with self.assertRaises(H3AdmissionError):
            project_video_generation_ir({"prompt": "x", "duration": 16, "resolution": "768P"})
        with self.assertRaises(H3AdmissionError):
            project_video_generation_ir({"prompt": "x", "duration": 4, "resolution": "4K"})

    def test_mocked_real_flow_normalizes_task_and_artifact(self):
        transport = FakeTransport()
        adapter = MiniMaxH3Adapter(self.config(), transport=transport)
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "result.mp4"
            result = adapter.run_hosted_video(
                {"prompt": "conformance", "duration": 4, "resolution": "768P", "ratio": "16:9"},
                output,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["task_id"], "task-1")
            self.assertTrue(output.is_file())
            self.assertEqual(result["artifact"]["bytes"], len(b"FAKE-MP4-BYTES"))
            self.assertEqual(result["entitlement_discovery"]["method"], "REAL_REQUEST_ACCEPTED_AND_COMPLETED")
            self.assertFalse(result["cost_evidence"]["static_price_used"])
            cdn = next(call for call in transport.calls if call["url"] == "https://cdn.example/h3.mp4")
            self.assertNotIn("Authorization", cdn["headers"])

    def test_context_ir_uses_provider_projection_endpoint(self):
        transport = FakeTransport()
        adapter = MiniMaxH3Adapter(self.config(), transport=transport)
        result = adapter.create_context_ir({"prompt": "expand", "duration": 4, "resolution": "768P", "ratio": "16:9"})
        self.assertEqual(result["task_id"], "context-1")
        self.assertTrue(any(call["url"].endswith("/v2/h3_context_ir") for call in transport.calls))

    def test_provider_http_denial_is_not_silently_fallbacked(self):
        adapter = MiniMaxH3Adapter(self.config(), transport=FakeTransport(fail_status=403))
        with self.assertRaises(H3ProviderError):
            adapter.create_video({"prompt": "x", "duration": 4, "resolution": "768P", "ratio": "16:9"})

    def test_runtime_materialization_preserves_architecture_invariants(self):
        contract = load("canonical/contracts/FA3-MINIMAX-H3-ADAPTER-CONTRACTS-001.json")
        runtime = load("canonical/FA3-MINIMAX-H3-RUNTIME-ADMISSION-001.json")
        gate = load("canonical/minimax-h3-runtime-admission-enforcement.json")
        self.assertFalse(contract["new_capability"])
        self.assertFalse(contract["new_architectural_authority"])
        self.assertEqual(runtime["capability_count"], 143)
        self.assertEqual(gate["capability_count"], 143)
        self.assertFalse(runtime["runtime_promotion_claim"])
        self.assertFalse(gate["runtime_promotion_claim"])
        self.assertEqual(runtime["missing_secret_or_entitlement_state"], "PENDING_EXTERNAL_ADMISSION")

    def test_integration_index_candidates_are_fail_closed(self):
        provider = load("canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        gate = load("canonical/minimax-h3-runtime-admission-enforcement.json")
        reference = load("canonical/references/FA3-MINIMAX-H3-INTEGRATION-INDEX-REFERENCE-2026-09-12.json")
        self.assertEqual(provider["integration_index_reference"], reference["id"])
        self.assertEqual(reference["upstream"]["commit"], "41872e10b49d112c543775ef2341e2006644cb75")
        self.assertFalse(reference["runtime_promotion_claim"])

        vllm = provider["integration_targets"]["vllm"]
        self.assertEqual(vllm["status"], "RESTRICTED_NOT_END_TO_END_H3_TARGET")
        self.assertFalse(vllm["end_to_end_h3_dit_serving"])
        self.assertFalse(vllm["production_h3_target"])

        vllm_omni = provider["integration_targets"]["vllm_omni"]
        self.assertEqual(vllm_omni["status"], "DISCOVERED_NOT_ADMITTED")
        self.assertFalse(vllm_omni["automatic_promotion"])
        self.assertTrue(vllm_omni["current_host_e2e_required"])

        candidates = provider["discovered_local_execution_candidates"]
        for name in ("diffsynth_studio", "lightx2v", "nvidia_sol_attn", "vdn_h3"):
            self.assertEqual(candidates[name]["status"], "DISCOVERED_NOT_ADMITTED")
            self.assertFalse(candidates[name]["automatic_promotion"])
        self.assertEqual(candidates["nvidia_sol_attn"]["governing_contract"], "FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001")
        self.assertTrue(candidates["vdn_h3"]["separate_model_artifact_admission_required"])

        self.assertEqual(gate["mandatory_rule_count"], 13)
        self.assertIn("DISCOVERED_NOT_ADMITTED", gate["pending_states_are_not_pass"])
        self.assertTrue(gate["integration_index_promotion_barrier"]["discovered_candidate_automatic_promotion_forbidden"])
        self.assertTrue(gate["integration_index_promotion_barrier"]["discovered_candidate_silent_substitution_forbidden"])

    def test_video_enforcement_binds_runtime_admission_fail_closed(self):
        video = load("canonical/video-enforcement.json")
        policy = video["h3_runtime_admission"]
        self.assertEqual(policy["gate_id"], "FA3-MINIMAX-H3-RUNTIME-ADMISSION-GATESET-001")
        self.assertTrue(policy["fail_closed"])
        self.assertFalse(policy["current_host_runtime_promotion_claim"])
        self.assertIn("PENDING_EXTERNAL_ADMISSION", policy["non_pass_states"])

    def test_billable_workflow_is_manual_only(self):
        workflow = (ROOT / ".github/workflows/fa3-minimax-h3-current-host.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("RUN MINIMAX H3 BILLABLE E2E", workflow)
        self.assertIn("I_ACKNOWLEDGE_BILLABLE_MINIMAX_H3_E2E", workflow)
        self.assertIn("fa3-current-host", workflow)


if __name__ == "__main__":
    unittest.main()
