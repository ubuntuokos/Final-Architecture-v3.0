from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_acestep_baseline_gate import explicit_steps_valid, export_path_valid, gate, torchcodec_enablement_valid, vram_reserve_valid

class ACEBaseLine20260912Tests(unittest.TestCase):
    def test_canonical_gate_passes(self):
        result = gate(ROOT)
        self.assertEqual(result["result"], "PASS", result)
        self.assertEqual(result["capability_count"], 143)
        self.assertEqual(result["current_host_runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(result["production_promotion_claimed"], False)

    def test_sft_api_steps_are_explicit_and_not_turbo_default(self):
        self.assertTrue(explicit_steps_valid("xl_sft", 50))
        self.assertFalse(explicit_steps_valid("xl_sft", 8))
        self.assertFalse(explicit_steps_valid("sft_2b", None))

    def test_vram_policy_preserves_kv_floor_and_hrb_authority(self):
        self.assertTrue(vram_reserve_valid(model_aware=True, duration_aware=True, batch_aware=True, kv_floor_preserved=True, hrb_lease=True))
        self.assertFalse(vram_reserve_valid(model_aware=True, duration_aware=True, batch_aware=True, kv_floor_preserved=False, hrb_lease=True))
        self.assertFalse(vram_reserve_valid(model_aware=True, duration_aware=True, batch_aware=True, kv_floor_preserved=True, hrb_lease=False))

    def test_lossless_master_and_torchcodec_fail_closed(self):
        self.assertTrue(export_path_valid(fmt="flac", torchcodec_required=False, fallback_verified=True, linux_dependency_smoke=True))
        self.assertFalse(export_path_valid(fmt="mp3", torchcodec_required=False, fallback_verified=True, linux_dependency_smoke=True))
        self.assertTrue(torchcodec_enablement_valid(enabled=True, torch_abi_match=True, torchaudio_abi_match=True, codec_import_smoke=True))
        self.assertFalse(torchcodec_enablement_valid(enabled=True, torch_abi_match=False, torchaudio_abi_match=True, codec_import_smoke=False))

if __name__ == "__main__":
    unittest.main()
