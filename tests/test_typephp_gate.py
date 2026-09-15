import unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_typephp_gate as t

class TypePHPAOTGateTests(unittest.TestCase):
    def test_baseline_gate_passes(self):
        r=t.gate(ROOT)
        self.assertEqual(r["result"],"PASS",r)
        self.assertEqual((r["regressions"]["passed"],r["regressions"]["total"]),(12,12))
        self.assertEqual(r["authority_scan"]["result"],"PASS")
        self.assertEqual(r["current_host_runtime_evidence"],"NOT_CLAIMED")
    def test_regression_matrix(self): self.assertEqual(t.run_regressions()["result"],"PASS")
    def test_unknown_semantics_fail_closed(self): self.assertFalse(t.semantic_compatibility_valid("UNKNOWN"))
    def test_unpinned_source_rejected(self): self.assertFalse(t.source_toolchain_pin_valid(source_commit="master",php_version="8.5",native_compiler="gcc",cmake_version="3.31",dependency_lock_present=True))
    def test_abi_mismatch_rejected(self): self.assertFalse(t.abi_valid(build_mode="ext",runtime_abi_match=False))
    def test_in_process_extension_needs_authorization(self): self.assertFalse(t.in_process_load_valid(build_mode="ext",explicitly_authorized=False,abi_match=True))
    def test_untrusted_native_needs_sandbox(self): self.assertFalse(t.sandbox_valid(untrusted_native_artifact=True,sandboxed=False))
    def test_network_bootstrap_needs_authorization_and_receipt(self): self.assertFalse(t.network_bootstrap_valid(network_used=True,explicitly_authorized=True,receipt_present=False))
    def test_fallback_requires_semantic_equivalence(self): self.assertFalse(t.fallback_valid(fallback_mode="PHP_INTERPRETER",declared=True,semantic_equivalence_verified=False))

if __name__=="__main__": unittest.main()
