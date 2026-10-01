from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_sttif import STTIFDenied, plan_inference
from fa3_sttif_gate import gate


class STTIFPlannerTests(unittest.TestCase):
    def constraints(self):
        return {
            "schema": "fa3.model-window-descriptor.v1",
            "max_tile_width": 1024,
            "max_tile_height": 1024,
            "spatial_alignment": 32,
            "minimum_overlap_fraction": 0.5,
            "temporal_window_frames": 97,
            "temporal_overlap_frames": 49,
            "temporal_modulus": 8,
            "temporal_offset": 1,
            "supported_samplers": ["euler", "heun", "dpm_2"],
        }

    def request(self):
        return {
            "schema": "fa3.tiled-inference-request.v1",
            "request_id": "test-4k",
            "target_width": 3840,
            "target_height": 2160,
            "frame_count": 241,
            "sampler": "euler",
            "seed": 42,
            "spatial_overlap_fraction": 0.5,
        }

    def test_high_resolution_and_temporal_plan_is_complete_and_provider_neutral(self):
        result = plan_inference(self.request(), self.constraints(), {"schema": "fa3.resource-budget.v1", "max_pixels_per_tile": 1024 * 1024})
        self.assertTrue(result["spatial"]["coverage_complete"])
        self.assertTrue(result["temporal"]["coverage_complete"])
        self.assertGreater(len(result["spatial"]["tiles"]), 1)
        self.assertGreater(len(result["temporal"]["windows"]), 1)
        self.assertTrue(result["latent_canvas"]["shared_across_spatial_tiles"])
        self.assertTrue(result["noise_trajectory"]["shared_across_spatial_tiles"])
        self.assertFalse(result["physical_device_selected"])
        self.assertFalse(result["provider_selected"])
        self.assertFalse(result["model_selected"])
        self.assertFalse(result["silent_fallback_used"])
        self.assertEqual(64, len(result["plan_sha256"]))

    def test_resource_budget_shrinks_tiles_without_selecting_device(self):
        result = plan_inference(self.request(), self.constraints(), {"schema": "fa3.resource-budget.v1", "max_pixels_per_tile": 512 * 512})
        self.assertLessEqual(result["spatial"]["tile_width"] * result["spatial"]["tile_height"], 512 * 512)
        self.assertTrue(result["resource_budget"]["hrb_authority_preserved"])
        self.assertFalse(result["resource_budget"]["physical_device_authorized"])

    def test_overlap_below_model_constraint_fails_closed(self):
        request = self.request()
        request["spatial_overlap_fraction"] = 0.25
        with self.assertRaises(STTIFDenied):
            plan_inference(request, self.constraints())

    def test_unsupported_sampler_is_not_silently_substituted(self):
        request = self.request()
        request["sampler"] = "ancestral-example"
        with self.assertRaises(STTIFDenied):
            plan_inference(request, self.constraints())

    def test_invalid_temporal_shape_rule_fails_closed(self):
        request = self.request()
        request["temporal_window_frames"] = 96
        with self.assertRaises(STTIFDenied):
            plan_inference(request, self.constraints())

    def test_static_canonical_gate(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report["findings"])
        self.assertEqual(175, report["capability_count"])
        self.assertEqual(0, report["capability_delta"])
        self.assertEqual(0, report["authority_delta"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])


if __name__ == "__main__":
    unittest.main()
