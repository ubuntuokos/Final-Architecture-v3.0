import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {
    "FA3-PROVIDER-KLING-001",
    "FA3-PROVIDER-SEEDANCE-001",
    "FA3-PROVIDER-MINIMAX-H3-001",
}


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class VideoRegistryTests(unittest.TestCase):
    def test_video_profile_is_canonical_free_only_without_new_authority(self):
        profile = load("canonical/profiles/FA3-VIDEO-001.json")
        self.assertEqual(profile["status"], "CANONICAL")
        self.assertEqual(profile["priority"], "P0")
        self.assertEqual(profile["requirement"], "MUST")
        self.assertFalse(profile["new_capability"])
        self.assertFalse(profile["new_architectural_authority"])
        self.assertEqual(profile["capability_count"], 143)
        self.assertEqual(profile["economics_policy"], "FA3-FREE-SELF-HOSTED-ONLY-001")
        self.assertFalse(profile["paid_provider_fallback"])
        self.assertTrue(BLOCKED.isdisjoint(profile["providers"]))

    def test_paid_video_provider_records_are_tombstones_only(self):
        for provider_id in sorted(BLOCKED):
            provider = load(f"canonical/providers/{provider_id}.json")
            self.assertTrue(provider["status"].startswith("REMOVED_"))
            self.assertFalse(provider["active"])
            self.assertFalse(provider["routing_eligible"])
            self.assertEqual(provider["production_admission"], "DENY")
            self.assertEqual(provider["runtime_surface"], "ABSENT")
            self.assertFalse(provider["canonical_root"])
            self.assertFalse(provider["architectural_authority"])
            self.assertEqual(provider["capability_count"], 143)

    def test_remaining_video_providers_are_non_authoritative(self):
        profile = load("canonical/profiles/FA3-VIDEO-001.json")
        for provider_id in profile["providers"]:
            provider = load(f"canonical/providers/{provider_id}.json")
            self.assertFalse(provider["canonical_root"])
            self.assertFalse(provider["architectural_authority"])
            self.assertFalse(provider["new_capability"])
            self.assertEqual(provider["capability_count"], 143)

    def test_context_ir_remains_provider_neutral_after_h3_removal(self):
        profile = load("canonical/profiles/FA3-VIDEO-001.json")
        ctx = profile["multimodal_generation_context_ir"]
        self.assertTrue(ctx["provider_neutral"])
        self.assertFalse(ctx["hosted_provider_context_ir_dependency"])
        self.assertEqual(ctx["canonical_type"], "MultimodalGenerationContextIR")
        self.assertEqual(ctx["embedding"], "TYPED_CHILD_OF_VideoGenerationIR")

    def test_enforcement_is_free_only_and_has_no_h3_service_sections(self):
        gate = load("canonical/video-enforcement.json")
        self.assertTrue(gate["fail_closed"])
        self.assertFalse(gate["paid_provider_fallback"])
        self.assertEqual(gate["economics_policy"], "FA3-FREE-SELF-HOSTED-ONLY-001")
        self.assertTrue(BLOCKED.isdisjoint(gate["provider_ids"]))
        serialized = json.dumps(gate)
        self.assertNotIn("h3_service_access_policy", serialized)
        self.assertNotIn("h3_runtime_admission", serialized)

    def test_provider_specific_h3_runtime_surfaces_are_absent(self):
        removed = [
            "canonical/FA3-MINIMAX-H3-RUNTIME-ADMISSION-001.json",
            "canonical/contracts/FA3-MINIMAX-H3-ADAPTER-CONTRACTS-001.json",
            "src/fa3_minimax_h3_provider_adapter.py",
            "src/fa3_minimax_h3_runtime_admission_gate.py",
            "evidence/collect-minimax-h3-current-host.py",
            ".github/workflows/fa3-minimax-h3-current-host.yml",
        ]
        for rel in removed:
            self.assertFalse((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
