from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cpu_numa_threading_current_host_gate import gate, validate_receipt

DIGEST = hashlib.sha256(b"fa3-current-host-fixture").hexdigest()


def fixture() -> dict:
    return {
        "schema": "fa3.cpu-numa-threading-current-host-receipt.v1",
        "status": "PASS",
        "evidence_level": "CURRENT_HOST_CPU_NUMA_THREADING_E2E_PASS",
        "hardware": {
            "source": "LIVE_SYSFS_PROCFS",
            "machine": "Dell Precision Tower 7910",
            "cpu_model_match": True,
            "packages": 2,
            "physical_cores": 44,
            "logical_cpus": 88,
            "numa_domains": 2,
            "smt_width": 2,
            "fingerprint_sha256": DIGEST,
        },
        "hardware_semantics": "REFERENCE_HOST_ASSERTION_NOT_PORTABLE_DEFAULT",
        "placement": {
            "topology_source": "LIVE_OS_AFFINITY_AND_SYSFS",
            "cgroup_v2": True,
            "cgroup_path": "/system.slice/fa3-test.scope",
            "effective_cpus": list(range(88)),
            "effective_memory_nodes": [0, 1],
            "visible_numa_nodes": [0, 1],
            "affinity_matches_effective_cpuset": True,
            "hrb_authority_receipt": "HRB_PLACEMENT_RECEIPT",
        },
        "thread_plan": {
            "status": "ADMITTED",
            "visible_physical_cores": 44,
            "thread_budget": 44,
            "uses_smt_above_physical_budget": False,
            "environment": {
                "OMP_NUM_THREADS": "44", "MKL_NUM_THREADS": "44",
                "OPENBLAS_NUM_THREADS": "44", "NUMEXPR_NUM_THREADS": "8",
                "OMP_PLACES": "cores", "OMP_PROC_BIND": "close",
            },
        },
        "numa_local_plans": [
            {"status": "ADMITTED", "numa_node": 0, "visible_physical_cores": 22, "thread_budget": 22},
            {"status": "ADMITTED", "numa_node": 1, "visible_physical_cores": 22, "thread_budget": 22},
        ],
        "accelerator_locality_source": "LIVE_PCI_SYSFS_NO_STATIC_MAPPING",
        "accelerator_locality": [{"pci_address": "0000:05:00.0", "numa_node": 0}],
        "negative_tests": {
            "missing_hrb_receipt_denied": True,
            "physical_core_oversubscription_denied": True,
            "smt_without_evidence_denied": True,
            "interleave_without_benchmark_denied": True,
            "spread_without_benchmark_denied": True,
        },
        "performance_evidence": {
            "schema": "fa3.cpu-numa-performance-evidence.v1", "status": "PASS",
            "hardware_fingerprint_sha256": DIGEST, "iterations": 5,
            "selected_profile": "NUMA_LOCAL_MULTI_INSTANCE", "benchmark_command_sha256": DIGEST,
        },
        "rollback_evidence": {
            "schema": "fa3.cpu-numa-rollback-evidence.v1", "status": "PASS",
            "failure_injection_denied": True,
            "pre_environment_sha256": DIGEST, "post_environment_sha256": DIGEST,
            "pre_cgroup_sha256": DIGEST, "post_cgroup_sha256": DIGEST,
        },
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }


class CpuNumaCurrentHostGateTests(unittest.TestCase):
    def test_complete_live_receipt_contract_passes(self):
        self.assertEqual(validate_receipt(fixture()), [])

    def test_obsolete_hardware_default_fails_closed(self):
        receipt = fixture()
        receipt["hardware"].update({"cpu_model_match": False, "physical_cores": 36, "logical_cpus": 72})
        self.assertTrue(any(item["code"] == "CPU-NUMA-HOST-002" for item in validate_receipt(receipt)))

    def test_reference_values_cannot_be_portable_defaults(self):
        receipt = fixture()
        receipt["hardware_semantics"] = "GLOBAL_THREAD_DEFAULT"
        self.assertTrue(any(item["code"] == "CPU-NUMA-HOST-003" for item in validate_receipt(receipt)))

    def test_performance_and_rollback_are_mandatory(self):
        receipt = fixture()
        receipt["performance_evidence"] = {}
        receipt["rollback_evidence"] = {}
        codes = {item["code"] for item in validate_receipt(receipt)}
        self.assertTrue({"CPU-NUMA-HOST-010", "CPU-NUMA-HOST-011"} <= codes)

    def test_missing_real_receipt_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            report = gate(Path(temp))
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["findings"][0]["code"], "CPU-NUMA-HOST-000")

    def test_synthetic_fixture_is_test_only(self):
        receipt = copy.deepcopy(fixture())
        receipt["hardware"]["source"] = "SYNTHETIC_REFERENCE_FIXTURE_NOT_CURRENT_HOST"
        self.assertTrue(any(item["code"] == "CPU-NUMA-HOST-002" for item in validate_receipt(receipt)))


if __name__ == "__main__":
    unittest.main()
