import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_animation_production_gate import (
    accelerator_identity_valid,
    cpu_topology_admission_valid,
    dcc_route_valid,
    display_fallback_valid,
    gate,
    hrb_execution_valid,
    interchange_valid,
    license_admission_valid,
    lipsync_request_valid,
    oom_policy_valid,
    run_regressions,
    stage_transition_valid,
    vram_admission_valid,
)


class AnimationProductionGateTests(unittest.TestCase):
    def test_reference_and_26_regressions_pass(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["regressions"]["total"], 26)
        self.assertEqual(report["regressions"]["passed"], 26)
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_hardware_defaults_are_current_fa3_reference(self):
        hardware = json.loads((ROOT / "canonical/references/FA3-T7910-ANIMATION-HARDWARE-REFERENCE-2026-09-02.json").read_text())
        roles = hardware["declared_accelerator_roles"]
        self.assertEqual(roles["primary_ai_render_compute"]["model"], "NVIDIA GeForce RTX 3090")
        self.assertEqual(roles["primary_ai_render_compute"]["vram_gib"], 24)
        self.assertEqual(roles["display_ui_media_io"]["model"], "NVIDIA RTX A1000")
        self.assertFalse(roles["display_ui_media_io"]["implicit_heavy_ai_fallback"])
        self.assertIn("RTX 3080 or Quadro RTX 4000 is the current FA3 animation default", hardware["prohibited_interpretation"])

    def test_cpu_reference_is_e5_2696_live_discovered(self):
        cpu = json.loads((ROOT / "canonical/references/FA3-T7910-CPU-NUMA-REFERENCE-2026-09-02.json").read_text())
        self.assertEqual(cpu["declared_cpu_configuration"]["model"], "Intel Xeon E5-2696 v4")
        self.assertEqual(cpu["declared_cpu_configuration"]["physical_cores_total"], 44)
        self.assertEqual(cpu["declared_cpu_configuration"]["logical_cpus_total"], 88)
        self.assertTrue(cpu_topology_admission_valid(live_discovered=True, lscpu_or_sysfs=True, static_cpu_ids=False, global_threads=8))
        self.assertFalse(cpu_topology_admission_valid(live_discovered=False, lscpu_or_sysfs=False, static_cpu_ids=True, global_threads=88))

    def test_gpu_identity_hrb_vram_and_display_isolation_fail_closed(self):
        self.assertTrue(accelerator_identity_valid(device_uuid="GPU-1", pci_bdf="0000:05:00.0", runtime_index_only=False))
        self.assertFalse(accelerator_identity_valid(device_uuid="", pci_bdf="GPU0", runtime_index_only=True))
        self.assertTrue(hrb_execution_valid(accelerator=True, lease_valid=True, provider_self_placed=False))
        self.assertFalse(hrb_execution_valid(accelerator=True, lease_valid=False, provider_self_placed=False))
        self.assertFalse(display_fallback_valid(selected_role="DISPLAY_UI_MEDIA_IO", heavy_job=True, explicit_policy=False))
        self.assertTrue(vram_admission_valid(requested_gib=18, capacity_gib=24, reserve_gib=4, concurrent_heavy=1, max_heavy=1))
        self.assertFalse(vram_admission_valid(requested_gib=23, capacity_gib=24, reserve_gib=4, concurrent_heavy=2, max_heavy=1))

    def test_dcc_and_interchange_roles_are_preserved(self):
        self.assertTrue(dcc_route_valid(primary="Bforartists", fallback="Blender", explicit=True, compatibility_evidence=True))
        self.assertFalse(dcc_route_valid(primary="Blender", fallback="Bforartists", explicit=False, compatibility_evidence=False))
        self.assertTrue(interchange_valid(timeline="OpenTimelineIO", color="OpenColorIO", hdr="OpenEXR", provider_local_root=False))
        self.assertFalse(interchange_valid(timeline=".kdenlive", color="provider LUT", hdr="JPEG", provider_local_root=True))

    def test_stage_lineage_and_lipsync_consent_are_required(self):
        stage = {key: "x" for key in ("source_artifact_ids", "source_content_hashes", "provider_id", "operation_or_intent", "frame_rate_and_timebase", "color_space_and_alpha_mode", "result_artifact_id", "result_content_hash", "policy_and_license_decisions", "review_or_qc_evidence")}
        lipsync = {key: "x" for key in ("video_artifact", "audio_artifact", "character_identity", "frame_rate", "timebase", "consent", "synthetic_disclosure")}
        self.assertTrue(stage_transition_valid(stage))
        self.assertFalse(stage_transition_valid({**stage, "review_or_qc_evidence": ""}))
        self.assertTrue(lipsync_request_valid(lipsync))
        self.assertFalse(lipsync_request_valid({**lipsync, "consent": ""}))

    def test_noncommercial_component_cannot_enter_commercial_route(self):
        dims = {key: True for key in ("code", "runtime_dependencies", "model_weights", "training_datasets", "input_assets_and_likeness", "output_usage_rights")}
        self.assertTrue(license_admission_valid(dims, commercial=True, noncommercial_component=False))
        self.assertFalse(license_admission_valid(dims, commercial=True, noncommercial_component=True))
        self.assertFalse(license_admission_valid({**dims, "model_weights": False}, commercial=False, noncommercial_component=False))

    def test_oom_fallback_must_be_explicit(self):
        self.assertTrue(oom_policy_valid(action="QUEUE", explicit=True, silent_device_or_provider_fallback=False))
        self.assertFalse(oom_policy_valid(action="FALLBACK_OTHER_GPU", explicit=False, silent_device_or_provider_fallback=True))

    def test_regression_suite_has_unique_complete_rule_set(self):
        report = run_regressions()
        ids = [case["rule_id"] for case in report["cases"]]
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(len(ids), 26)
        self.assertEqual(len(set(ids)), 26)


if __name__ == "__main__":
    unittest.main()
