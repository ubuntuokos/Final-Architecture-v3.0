from pathlib import Path
import unittest

from fa3_ai_guardrail_runtime_gate import (
    capability_task_valid,
    concurrency_valid,
    evaluate,
    fail_mode_valid,
    readiness_valid,
    unit_projection_valid,
)

ROOT = Path(__file__).resolve().parents[1]


class AIGuardrailRuntimeGateTests(unittest.TestCase):
    def test_canonical_reference_gate_passes(self):
        result = evaluate(ROOT)
        failures = [c for c in result.get("checks", []) if c.get("status") != "PASS"]
        self.assertEqual(result.get("status"), "PASS", failures)

    def test_out_of_scope_capability_cannot_issue_allow(self):
        mapping = {"PROMPT_INJECTION": ["prompt_injection_detection"]}
        self.assertFalse(capability_task_valid(
            capability="PROMPT_INJECTION", task="generic_harm_moderation",
            validated_mapping=mapping, verdict="ALLOW"))
        self.assertTrue(capability_task_valid(
            capability="PROMPT_INJECTION", task="prompt_injection_detection",
            validated_mapping=mapping, verdict="ALLOW"))

    def test_privileged_tool_failure_is_fail_closed_or_approval(self):
        self.assertFalse(fail_mode_valid(
            risk_tier="PRIVILEGED", fail_mode="FAIL_OPEN",
            privileged_or_destructive_tool=True))
        self.assertTrue(fail_mode_valid(
            risk_tier="PRIVILEGED", fail_mode="FAIL_CLOSED",
            privileged_or_destructive_tool=True))
        self.assertTrue(fail_mode_valid(
            risk_tier="PRIVILEGED", fail_mode="HUMAN_APPROVAL",
            privileged_or_destructive_tool=True))

    def test_health_without_model_readiness_fails(self):
        self.assertFalse(readiness_valid(
            dependency_ok=True, model_identity_ok=False, auth_ok=True,
            cache_ok=True, capability_smoke_ok=True))
        self.assertTrue(readiness_valid(
            dependency_ok=True, model_identity_ok=True, auth_ok=True,
            cache_ok=True, capability_smoke_ok=True))

    def test_model_backed_multiworker_requires_evidence(self):
        self.assertTrue(concurrency_valid(
            worker_count=1, model_backed=True, shared_model_proven=False,
            benchmark_pass=False, memory_budget_pass=False))
        self.assertFalse(concurrency_valid(
            worker_count=8, model_backed=True, shared_model_proven=False,
            benchmark_pass=False, memory_budget_pass=False))
        self.assertTrue(concurrency_valid(
            worker_count=2, model_backed=True, shared_model_proven=True,
            benchmark_pass=True, memory_budget_pass=True))

    def test_systemd_conflicting_memorymax_fails(self):
        ok, findings = unit_projection_valid("[Service]\nMemoryMax=32G\nMemoryMax=2G\n")
        self.assertFalse(ok)
        self.assertTrue(any("conflicting duplicate MemoryMax" in x for x in findings))

    def test_systemd_startlimit_in_service_fails(self):
        ok, findings = unit_projection_valid("[Service]\nStartLimitIntervalSec=60\nStartLimitBurst=10\n")
        self.assertFalse(ok)
        self.assertTrue(any("must be in [Unit]" in x for x in findings))

    def test_plaintext_hf_token_in_unit_fails(self):
        ok, findings = unit_projection_valid("[Service]\nEnvironment=HF_TOKEN=hf_exampleSecret123\n")
        self.assertFalse(ok)
        self.assertIn("plaintext provider credential in unit", findings)

    def test_valid_resource_projection_passes_semantic_lint(self):
        unit = """[Unit]
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
EnvironmentFile=/run/credentials/fa3-guardrail.env
MemoryHigh=4G
MemoryMax=6G
MemorySwapMax=0
OOMPolicy=stop
TimeoutStopSec=30s
KillMode=control-group
"""
        ok, findings = unit_projection_valid(unit)
        self.assertTrue(ok, findings)


if __name__ == "__main__":
    unittest.main()
