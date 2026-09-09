import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hrb_systemd_manager_current_host_gate import hardware_floor_valid, manager_violations, validate_receipt


def base_receipt():
    return {
        "schema": "fa3.hrb-systemd-manager-current-host-receipt.v1",
        "status": "PASS",
        "evidence_level": "CURRENT_HOST_HRB_SYSTEMD_MANAGER_NEUTRALITY_PASS",
        "hardware_profile_id": "FA3-HARDWARE-BASELINE-001",
        "hardware_discovery_contract_id": "FA3-HARDWARE-DISCOVERY-CONTRACTS-001",
        "resource_authority_id": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "systemd_provider_id": "FA3-PROVIDER-SYSTEMD-CGROUPV2-001",
        "hardware_discovery": {
            "cardinality_semantics": "DYNAMIC_1_TO_N",
            "host_identity_semantics": "EVIDENCE_ONLY_NOT_CANONICAL_IDENTITY",
            "cpu": {"package_count": 1, "physical_cores_by_package": {"0": 8}},
            "gpu": {"devices": [{"qualifies_portable_floor": True, "device_uuid": "GPU-X", "pci_bdf": "0000:01:00.0"}]},
        },
        "systemd_manager": {"source": "SYSTEMD_ANALYZE_CAT_CONFIG", "returncode": 0, "assignments": []},
        "host_survival_policy": {},
        "cgroup_v2": {"unified": True, "cgroup_path": "/", "controllers": ["cpu", "cpuset", "memory"], "effective_cpus": "0-7", "effective_memory_nodes": "0"},
        "negative_tests": {
            "global_cpu_affinity_denied": True,
            "global_numa_policy_denied": True,
            "global_unbounded_memlock_denied": True,
            "global_oom_continue_denied": True,
            "global_memory_pressure_disable_denied": True,
            "global_1ms_timer_denied": True,
            "guarded_timeout_without_survival_receipt_denied": True,
        },
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }


class HrbSystemdManagerCurrentHostTests(unittest.TestCase):
    def test_minimum_portable_host_passes_without_machine_identity(self):
        receipt = base_receipt()
        self.assertTrue(hardware_floor_valid(receipt["hardware_discovery"]))
        self.assertEqual(validate_receipt(receipt), [])

    def test_larger_dynamic_host_passes(self):
        receipt = base_receipt()
        receipt["hardware_discovery"]["cpu"] = {"package_count": 4, "physical_cores_by_package": {"0": 32, "1": 32, "2": 64, "3": 64}}
        receipt["hardware_discovery"]["gpu"]["devices"] = [{"qualifies_portable_floor": True} for _ in range(8)]
        self.assertEqual(validate_receipt(receipt), [])

    def test_under_floor_cpu_or_no_qualifying_gpu_fails(self):
        receipt = base_receipt()
        receipt["hardware_discovery"]["cpu"]["physical_cores_by_package"]["0"] = 7
        self.assertTrue(validate_receipt(receipt))
        receipt = base_receipt()
        receipt["hardware_discovery"]["gpu"]["devices"] = []
        self.assertTrue(validate_receipt(receipt))

    def test_concrete_machine_pin_fails(self):
        receipt = base_receipt()
        receipt["hardware_discovery"]["expected_machine"] = "some-model"
        self.assertTrue(any(x["code"] == "HRB-SYSD-HOST-003" for x in validate_receipt(receipt)))

    def test_global_manager_affinity_and_unsafe_defaults_fail(self):
        for key, value in (
            ("CPUAffinity", "0-7"),
            ("NUMAPolicy", "preferred"),
            ("NUMAMask", "0"),
            ("DefaultTasksMax", "infinity"),
            ("DefaultLimitMEMLOCK", "infinity"),
            ("DefaultLimitNPROC", "infinity"),
            ("DefaultOOMPolicy", "continue"),
            ("DefaultMemoryPressureWatch", "no"),
            ("DefaultTimerAccuracySec", "1ms"),
        ):
            self.assertTrue(manager_violations([{"source": "/etc/systemd/system.conf.d/90-ai.conf", "key": key, "value": value}]))

    def test_vendor_defaults_are_evidence_not_operator_ai_override(self):
        self.assertEqual(manager_violations([{"source": "/usr/lib/systemd/system.conf", "key": "DefaultTimeoutStartSec", "value": "90s"}]), [])

    def test_guarded_override_requires_expiring_survival_receipt(self):
        assignment = [{"source": "/etc/systemd/system.conf.d/10-host.conf", "key": "DefaultTimeoutStartSec", "value": "45s"}]
        self.assertTrue(manager_violations(assignment, {}))
        policy = {
            "schema": "fa3.host-survival-policy-receipt.v1",
            "status": "PASS",
            "approved": True,
            "hrb_noninterference_verified": True,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "allowed_manager_overrides": [{"key": "DefaultTimeoutStartSec", "value": "45s"}],
        }
        self.assertEqual(manager_violations(assignment, policy), [])


if __name__ == "__main__":
    unittest.main()
