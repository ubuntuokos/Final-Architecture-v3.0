import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import fa3_hrb_lease_lifecycle_current_host_gate as gate_mod


def good_receipt():
    name = "fa3-hrb-ttl-test-a1b2c3d4e5f6"
    unit = name + ".scope"
    binding = {
        "lease_id": "lease-" + name,
        "generation": 1,
        "workload_identity": name,
        "runtime_instance_identity": "pid:123:start:456:cgroup:789",
        "host_attestation_digest": "a" * 64,
        "cgroup_v2_identity": {"path": "/user.slice/test.scope", "st_dev": 1, "st_ino": 789, "owner_uid": 1000, "owner_gid": 1000},
        "pidfd_subject_reference": {"pid": 123, "start_time_ticks": 456},
        "systemd_unit_scope": unit,
        "runtime_backend": "SYSTEMD_CGROUPV2_SCOPE",
        "backend_instance_id": unit,
        "accelerator_assignments": [],
        "execution_path": {"cgroup_version": 2, "pidfd_required": True},
        "issued_at_utc": "2026-09-24T00:00:00Z",
        "expires_at_utc": "2026-09-24T00:00:02Z",
        "ttl_seconds": 2.0,
    }
    return {
        "schema": "fa3.hrb-lease-lifecycle-current-host-receipt.v1",
        "status": "PASS",
        "evidence_level": gate_mod.EVIDENCE_LEVEL,
        "resource_authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "secret_authority_id": "FA3-AUTH-SECRETS-001",
        "durable_evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
        "trust_profile_id": "FA3-TRUST-PKI-001",
        "capability_count_after": gate_mod.CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "workload": {
            "name": name,
            "unit_scope": unit,
            "dedicated": True,
            "existing_fa3_workload_targeted": False,
            "ttl_seconds": 2.0,
            "cpu_only": True,
            "accelerator_assignments": [],
        },
        "crypto": {
            "algorithm": "HMAC-SHA256",
            "scope": "HRB_INTERNAL_EPHEMERAL_LEASE_AUTH",
            "key_id": "current-host-test-a1b2c3d4e5f6",
            "test_only_ephemeral_key": True,
            "production_hmac_master_key_read": False,
            "provider_agent_master_key_access": False,
            "hmac_used_for_durable_evidence_signature": False,
        },
        "runtime_binding": binding,
        "runtime": {
            "systemd_user_transient_scope": True,
            "cgroup_v2": True,
            "cgroup_path": "/user.slice/test.scope",
            "pidfd": True,
            "group_kill_method": "SYSTEMD_KILL_ALL_CGROUP_SCOPE",
            "final_state": "EVICTED",
            "state_history": ["ISSUED", "ACTIVE", "REVOKING", "EVICTING", "VERIFYING", "EVICTED"],
            "lease_record_deleted": False,
            "cleanup_verified": True,
            "gpu_global_reset_used": False,
            "cuda_device_reset_used": False,
        },
        "secret_projection": {
            "test_projection_only": True,
            "live_secret_broker_store_touched": False,
            "zeroized": True,
            "revoked": True,
        },
        "evidence_handoff": {
            "typed_hash_chain_valid": True,
            "event_count": 1,
            "final_event_sha256": "b" * 64,
            "external_asymmetric_signature_required": True,
            "durable_signing_authority": "FA3-AUTH-OBS-EVIDENCE-001",
            "trust_profile": "FA3-TRUST-PKI-001",
        },
        "safety": {
            "target_derivation_from_client_identity": False,
            "target_derivation_from_generated_container_name": False,
            "test_prefix_enforced": True,
            "preexisting_workload_kill_allowed": False,
            "container_id_used": False,
        },
    }


class HrbLeaseLifecycleCurrentHostGateTests(unittest.TestCase):
    def test_valid_synthetic_receipt_shape(self):
        self.assertEqual(gate_mod.validate_receipt(good_receipt()), [])

    def test_rejects_non_dedicated_workload(self):
        receipt = good_receipt()
        receipt["workload"]["name"] = "fa3-existing-service"
        self.assertTrue(gate_mod.validate_receipt(receipt))

    def test_rejects_hmac_as_durable_evidence_signature(self):
        receipt = good_receipt()
        receipt["crypto"]["hmac_used_for_durable_evidence_signature"] = True
        self.assertTrue(gate_mod.validate_receipt(receipt))

    def test_rejects_missing_pidfd_or_group_kill(self):
        receipt = good_receipt()
        receipt["runtime"]["pidfd"] = False
        receipt["runtime"]["group_kill_method"] = "PROCESS_ONLY"
        self.assertTrue(gate_mod.validate_receipt(receipt))

    def test_rejects_deleted_failed_record_semantics(self):
        receipt = good_receipt()
        receipt["runtime"]["lease_record_deleted"] = True
        self.assertTrue(gate_mod.validate_receipt(receipt))


if __name__ == "__main__":
    unittest.main()
