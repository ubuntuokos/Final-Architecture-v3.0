import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_inference_cache_hardening_gate import (
    CACHE_IDENTITY_FIELDS,
    CAPABILITY_COUNT,
    PARENT_GATE_ID,
    PROVIDER_ID,
    RULES,
    SUBGATE_ID,
    benchmark_receipt_valid,
    cache_identity_valid,
    cache_use_receipt_valid,
    gate,
    reference_check,
    run_regressions,
    runtime_cache_compatible,
)


class InferenceCacheHardeningGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        for name in ("canonical", "evidence"):
            shutil.copytree(ROOT / name, root / name)
        return td, root

    def _write(self, path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["parent_gate_id"], PARENT_GATE_ID)
        self.assertEqual(report["subgate_id"], SUBGATE_ID)
        self.assertEqual(report["provider_id"], PROVIDER_ID)
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_exact_five_regressions_pass(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 5)
        self.assertEqual(report["total"], 5)
        self.assertEqual([row["invariant"] for row in report["cases"]], list(RULES))

    def test_cache_identity_requires_gpu_version_cig_and_origin_driver(self):
        good = {
            "gpu_sku": "NVIDIA-GeForce-RTX-3090",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "cache_origin_driver_version": "610.43.02",
        }
        self.assertTrue(cache_identity_valid(good))
        for field in CACHE_IDENTITY_FIELDS:
            with self.subTest(field=field):
                bad = dict(good)
                bad.pop(field)
                self.assertFalse(cache_identity_valid(bad))

    def test_older_driver_rejects_cache_reuse(self):
        cache = {
            "gpu_sku": "NVIDIA-GeForce-RTX-3090",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "cache_origin_driver_version": "610.43.02",
        }
        runtime = {
            "gpu_sku": "NVIDIA-GeForce-RTX-3090",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "runtime_driver_version": "609.99.00",
        }
        self.assertFalse(runtime_cache_compatible(cache, runtime))

    def test_cig_or_version_drift_rejects_cache_reuse(self):
        cache = {
            "gpu_sku": "NVIDIA-GeForce-RTX-3090",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "cache_origin_driver_version": "610.43.02",
        }
        runtime = {
            "gpu_sku": "NVIDIA-GeForce-RTX-3090",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "runtime_driver_version": "610.57.04",
        }
        self.assertFalse(runtime_cache_compatible(cache, {**runtime, "cuda_context_cig_state": "ENABLED"}))
        self.assertFalse(runtime_cache_compatible(cache, {**runtime, "tensorrt_rtx_version": "1.6.2"}))

    def test_gpu_sku_drift_requires_explicit_equivalence_evidence(self):
        cache = {
            "gpu_sku": "GPU-SKU-A",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "cache_origin_driver_version": "610.43.02",
        }
        runtime = {
            "gpu_sku": "GPU-SKU-B",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "runtime_driver_version": "610.57.04",
        }
        self.assertFalse(runtime_cache_compatible(cache, runtime))
        self.assertTrue(runtime_cache_compatible(cache, {**runtime, "gpu_sku_equivalence_evidence": "PASS"}))

    def test_transparent_jit_rebuild_requires_observable_receipt(self):
        receipt = {
            "provider_id": PROVIDER_ID,
            "cache_artifact_hash": "sha256:cache",
            "cache_compatibility_result": "FAIL",
            "cache_used": False,
            "jit_rebuild_detected": True,
            "observability_source": "APPLICATION_LOG",
            "runtime_driver_version": "610.57.04",
            "cache_origin_driver_version": "610.43.02",
            "gpu_sku": "NVIDIA-GeForce-RTX-3090",
            "tensorrt_rtx_version": "1.6.1.120",
            "cuda_context_cig_state": "DISABLED",
            "first_inference_latency_ms": 2200.0,
        }
        self.assertTrue(cache_use_receipt_valid(receipt))
        self.assertFalse(cache_use_receipt_valid({**receipt, "jit_rebuild_detected": False}))
        self.assertFalse(cache_use_receipt_valid({**receipt, "observability_source": "NONE"}))

    def test_steady_state_benchmark_must_separate_jit_warmup(self):
        good = {
            "warmup_jit_phase_recorded": True,
            "steady_state_cache_hit_confirmed": True,
            "first_inference_latency_ms": 2200.0,
            "steady_state_latency_ms": 38.0,
            "steady_state_sample_count": 10,
            "benchmark_phase_separation": "WARMUP_JIT_THEN_STEADY_STATE",
        }
        self.assertTrue(benchmark_receipt_valid(good))
        self.assertFalse(benchmark_receipt_valid({**good, "warmup_jit_phase_recorded": False}))
        self.assertFalse(benchmark_receipt_valid({**good, "steady_state_sample_count": 1}))

    def test_timing_cache_cannot_be_reclassified_as_canonical_runtime_cache(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["timing_cache_api"]["status"] = "CANONICAL_RUNTIME_CACHE"
            self._write(p, obj)
            report = reference_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-CACHE-REF-012" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_contract_cache_identity_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/contracts/FA3-INFERENCE-PORTABILITY-CONTRACTS-001.json"
            obj = json.loads(p.read_text(encoding="utf-8"))
            obj["tensorrt_rtx_runtime_cache_fingerprint_required_fields"] = obj["tensorrt_rtx_runtime_cache_fingerprint_required_fields"][:-1]
            self._write(p, obj)
            report = reference_check(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "INFER-CACHE-REF-011" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_runtime_promotion_remains_not_claimed(self):
        provider = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-TENSORRT-RTX-001.json").read_text(encoding="utf-8"))
        self.assertEqual(provider["runtime_activation_status"], "NOT_ADMITTED_REFERENCE_ONLY")
        self.assertEqual(provider["current_host_production_evidence"], "NOT_CLAIMED")


if __name__ == "__main__":
    unittest.main()
