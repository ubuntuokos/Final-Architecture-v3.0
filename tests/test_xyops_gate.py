from __future__ import annotations

from pathlib import Path
import unittest

from fa3_xyops_gate import (
    CAPABILITY_COUNT,
    P0_RULES,
    capacity_pool_valid,
    credential_transport_valid,
    execution_receipt_valid,
    gate,
    hardware_discovery_valid,
    hrb_admission_valid,
    http_execution_valid,
    least_privilege_valid,
    local_enforcement_valid,
    production_policy_admission_valid,
    resource_projection_valid,
    resume_valid,
    retry_valid,
    rollback_valid,
    secret_projection_valid,
    shell_execution_valid,
    supply_chain_valid,
    terminal_control_evidence_valid,
    typed_execution_request_valid,
)

ROOT = Path(__file__).resolve().parents[1]


class XyOpsGateTests(unittest.TestCase):
    def test_rule_inventory_is_fail_closed_p0_30(self):
        self.assertEqual(CAPABILITY_COUNT, 143)
        self.assertEqual(len(P0_RULES), 30)
        self.assertEqual(len(P0_RULES), len(set(P0_RULES)))

    def test_reference_gate_passes_repository_materialization(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["blocking_findings"], 0)
        self.assertEqual(report["rule_count"], 30)
        self.assertFalse(report["current_host_runtime_promotion_claimed"])

    def test_typed_request_gate(self):
        cases = [
            ({"typed": True, "versioned": True, "request_id": "req-1"}, True),
            ({"typed": False, "versioned": True, "request_id": "req-1"}, False),
            ({"typed": True, "versioned": False, "request_id": "req-1"}, False),
            ({"typed": True, "versioned": True, "request_id": ""}, False),
        ]
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                self.assertIs(typed_execution_request_valid(**kwargs), expected)

    def test_production_policy_and_hrb_are_mandatory(self):
        self.assertTrue(
            production_policy_admission_valid(production=True, policy_decision="ALLOW")
        )
        self.assertFalse(
            production_policy_admission_valid(production=True, policy_decision=None)
        )
        self.assertTrue(
            hrb_admission_valid(
                host_workload=True,
                admitted=True,
                placement_owner="FA3-AUTH-HOST-RESOURCE-BROKER-001",
            )
        )
        self.assertFalse(
            hrb_admission_valid(
                host_workload=True,
                admitted=True,
                placement_owner="FA3-PROVIDER-XYOPS-001",
            )
        )
        self.assertFalse(
            hrb_admission_valid(
                host_workload=True,
                admitted=False,
                placement_owner="FA3-AUTH-HOST-RESOURCE-BROKER-001",
            )
        )

    def test_resource_limits_and_hardware_are_projection_only(self):
        self.assertTrue(
            resource_projection_valid(
                provider_native_limit=True,
                canonicalized=True,
                provider_is_authority=False,
            )
        )
        self.assertFalse(
            resource_projection_valid(
                provider_native_limit=True,
                canonicalized=False,
                provider_is_authority=False,
            )
        )
        self.assertFalse(
            resource_projection_valid(
                provider_native_limit=True,
                canonicalized=True,
                provider_is_authority=True,
            )
        )
        self.assertTrue(
            hardware_discovery_valid(
                host_workload=True,
                live_discovery=True,
                static_accelerator_placement=False,
            )
        )
        self.assertFalse(
            hardware_discovery_valid(
                host_workload=True,
                live_discovery=False,
                static_accelerator_placement=False,
            )
        )
        self.assertFalse(
            hardware_discovery_valid(
                host_workload=True,
                live_discovery=True,
                static_accelerator_placement=True,
            )
        )

    def test_local_host_enforcement_requires_systemd_cgroup_v2(self):
        self.assertTrue(local_enforcement_valid(local_host=True, systemd_cgroup_v2=True))
        self.assertFalse(local_enforcement_valid(local_host=True, systemd_cgroup_v2=False))

    def test_secret_and_credential_boundaries(self):
        self.assertTrue(
            secret_projection_valid(
                secret_refs=["secret-ref:ops/api"],
                raw_secret_values=[],
                provider_persisted_raw=False,
            )
        )
        self.assertFalse(
            secret_projection_valid(
                secret_refs=["secret-ref:ops/api"],
                raw_secret_values=["plaintext"],
                provider_persisted_raw=False,
            )
        )
        self.assertFalse(
            secret_projection_valid(
                secret_refs=["api-token"],
                raw_secret_values=[],
                provider_persisted_raw=False,
            )
        )
        self.assertTrue(
            credential_transport_valid(
                production=True,
                location="HEADER",
                short_lived=True,
                rotatable=True,
                identity_bound=True,
            )
        )
        self.assertFalse(
            credential_transport_valid(
                production=True,
                location="QUERY",
                short_lived=True,
                rotatable=True,
                identity_bound=True,
            )
        )
        self.assertFalse(
            credential_transport_valid(
                production=True,
                location="HEADER",
                short_lived=False,
                rotatable=True,
                identity_bound=True,
            )
        )

    def test_least_privilege_is_exact_scope(self):
        self.assertTrue(least_privilege_valid(granted={"run"}, required={"run"}))
        self.assertFalse(
            least_privilege_valid(granted={"run", "admin"}, required={"run"})
        )
        self.assertFalse(least_privilege_valid(granted=set(), required={"run"}))

    def test_arbitrary_shell_and_http_require_policy(self):
        self.assertTrue(
            shell_execution_valid(
                arbitrary_shell=True,
                explicit_policy=True,
                bounded_executor=True,
            )
        )
        self.assertFalse(
            shell_execution_valid(
                arbitrary_shell=True,
                explicit_policy=False,
                bounded_executor=True,
            )
        )
        self.assertFalse(
            shell_execution_valid(
                arbitrary_shell=True,
                explicit_policy=True,
                bounded_executor=False,
            )
        )
        self.assertTrue(
            http_execution_valid(
                arbitrary_http=True,
                egress_policy=True,
                destination_admitted=True,
            )
        )
        self.assertFalse(
            http_execution_valid(
                arbitrary_http=True,
                egress_policy=False,
                destination_admitted=True,
            )
        )
        self.assertFalse(
            http_execution_valid(
                arbitrary_http=True,
                egress_policy=True,
                destination_admitted=False,
            )
        )

    def test_execution_receipt_schema_is_required(self):
        required = {
            "request_id",
            "workflow_id",
            "job_id",
            "provider",
            "provider_version",
            "executor",
            "target",
            "started_at",
            "finished_at",
            "exit_status",
            "resource_admission",
            "policy_decision",
            "artifacts",
            "logs",
            "metrics",
            "alerts",
            "snapshots",
            "incident_ids",
            "provenance",
            "evidence_hash",
        }
        receipt = {key: None for key in required}
        self.assertTrue(execution_receipt_valid(receipt))
        receipt.pop("evidence_hash")
        self.assertFalse(execution_receipt_valid(receipt))

    def test_retry_resume_terminal_control_evidence(self):
        self.assertTrue(
            retry_valid(
                retry=True,
                idempotency_classified=True,
                idempotency_key="idem-1",
            )
        )
        self.assertFalse(
            retry_valid(
                retry=True,
                idempotency_classified=False,
                idempotency_key="idem-1",
            )
        )
        self.assertFalse(
            retry_valid(
                retry=True,
                idempotency_classified=True,
                idempotency_key=None,
            )
        )
        self.assertTrue(
            resume_valid(
                resume=True,
                committed_checkpoint=True,
                provider_resume_receipt=False,
            )
        )
        self.assertTrue(
            resume_valid(
                resume=True,
                committed_checkpoint=False,
                provider_resume_receipt=True,
            )
        )
        self.assertFalse(
            resume_valid(
                resume=True,
                committed_checkpoint=False,
                provider_resume_receipt=False,
            )
        )
        self.assertTrue(
            terminal_control_evidence_valid(
                cancelled=True,
                timed_out=False,
                aborted=False,
                evidence_written=True,
            )
        )
        self.assertFalse(
            terminal_control_evidence_valid(
                cancelled=True,
                timed_out=False,
                aborted=False,
                evidence_written=False,
            )
        )

    def test_supply_chain_rollback_and_capacity_pool_boundaries(self):
        self.assertTrue(
            supply_chain_valid(
                runtime_promotion=True,
                sbom=True,
                provenance=True,
                license_gate=True,
            )
        )
        self.assertFalse(
            supply_chain_valid(
                runtime_promotion=True,
                sbom=False,
                provenance=True,
                license_gate=True,
            )
        )
        self.assertTrue(rollback_valid(mutating_production=True, rollback_path=True))
        self.assertFalse(rollback_valid(mutating_production=True, rollback_path=False))
        self.assertTrue(
            capacity_pool_valid(
                declarative_policy=True,
                provider_is_resource_authority=False,
            )
        )
        self.assertFalse(
            capacity_pool_valid(
                declarative_policy=True,
                provider_is_resource_authority=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
