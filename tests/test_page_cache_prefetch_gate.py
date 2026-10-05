import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_page_cache_prefetch_gate import evaluate


class PageCachePrefetchGateTests(unittest.TestCase):
    def test_reference_gate_passes(self):
        result = evaluate(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["summary"], {"passed": 23, "total": 23})
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_hrb_authority_and_capability_count_preserved(self):
        result = evaluate(ROOT)
        by_name = {item["name"]: item for item in result["checks"]}
        for name in (
            "capability-count-stable",
            "no-new-authority",
            "hrb-parent-authority",
            "provider-optional-non-authority",
            "provider-projection-linked",
        ):
            self.assertEqual(by_name[name]["status"], "PASS")

    def test_dangerous_legacy_prefetch_patterns_are_rejected(self):
        result = evaluate(ROOT)
        by_name = {item["name"]: item for item in result["checks"]}
        for name in (
            "no-global-magic-constants",
            "virtual-filesystems-denied",
            "home-tree-not-default",
            "large-model-blind-prefetch-forbidden",
            "drop-caches-optimization-forbidden",
            "cannot-override-placement",
        ):
            self.assertEqual(by_name[name]["status"], "PASS")

    def test_promotion_semantics_require_measurement_and_rollback(self):
        result = evaluate(ROOT)
        by_name = {item["name"]: item for item in result["checks"]}
        for name in (
            "cold-warm-benchmark-separation",
            "io-memory-pressure-evidence",
            "adaptive-readahead-benchmarked",
            "rollback-required",
            "disabled-provider-near-zero-cost",
            "current-host-claim-honest",
        ):
            self.assertEqual(by_name[name]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
