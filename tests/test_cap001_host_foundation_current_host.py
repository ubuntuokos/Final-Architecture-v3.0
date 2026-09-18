import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cap001_host_foundation_current_host import (
    _fixture_snapshot,
    _run_negative,
    _run_positive,
    _run_rollback,
    validate_host_snapshot,
)


class Cap001HostFoundationCurrentHostTests(unittest.TestCase):
    def test_fixture_satisfies_portable_host_foundation(self):
        self.assertEqual(validate_host_snapshot(_fixture_snapshot()), [])

    def test_positive_uses_non_synthetic_portable_discovery_contract(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = _run_positive(ROOT, Path(td), _fixture_snapshot())
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["canonical"]["hardware_portability"], "PASS")
            self.assertEqual(result["canonical"]["hrb_deterministic_locality"], "PASS")
            self.assertEqual(result["canonical"]["page_cache_prefetch"], "PASS")
            self.assertFalse(result["canonical"]["reference_runtime_promotion_claim"])
            self.assertTrue(result["dynamic_cpu_cardinality"])
            self.assertTrue(result["stable_accelerator_identity"])
            self.assertTrue(result["cgroup_v2"])
            self.assertTrue(result["page_cache_observable"])
            self.assertTrue(result["hrb_authority_preserved"])

    def test_negative_injections_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = _run_negative(ROOT, Path(td))
            self.assertEqual(result["status"], "PASS")
            for name, value in result.items():
                if name.endswith("_rejected"):
                    self.assertTrue(value, name)

    def test_rollback_restores_exact_policy_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            result = _run_rollback(ROOT, Path(td))
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["fault_rejected"])
            self.assertTrue(result["rollback_hash_equal"])
            self.assertTrue(result["restored_policy_admitted"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
