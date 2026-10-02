"""Owner-marked Motion/Video execution donor intake regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-MOTION-VIDEO-EXECUTION-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

EXPECTED = {
    "github:huggingface/diffusers": "FA3-DONOR-HUGGINGFACE-DIFFUSERS-001",
    "github:xdit-project/xdit": "FA3-DONOR-XDIT-001",
    "github:tencent-hunyuan/hunyuanvideo-1.5": "FA3-DONOR-HUNYUANVIDEO-1-5-001",
    "github:skyworkai/skyreels-v3": "FA3-DONOR-SKYREELS-V3-001",
    "github:nus-hpc-ai-lab/videosys": "FA3-DONOR-VIDEOSYS-001",
}
FLAGS = (
    "authority","automatic_selection","automatic_fetch","automatic_install",
    "automatic_activation","automatic_dependency","automatic_code_import",
    "automatic_provider_admission","automatic_model_selection",
)

class MotionVideoDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta=json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links=json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries=cls.registry["entries"]
        cls.by_key={e["source"]["normalized_key"]:e for e in cls.entries}

    def test_registry_integrity_and_delta(self):
        self.assertEqual(len(self.entries),len(self.by_key))
        self.assertGreaterEqual(len(self.entries),1349)
        self.assertEqual(self.registry["backfill"]["entry_count"],len(self.entries))
        self.assertEqual(self.registry["capability_count"],175)
        self.assertEqual(self.delta["parent_entry_count"],1344)
        self.assertEqual(self.delta["proposed_entry_count"],1349)
        self.assertEqual(self.delta["source_count"],5)
        self.assertEqual(self.delta["capability_delta"],0)
        self.assertEqual(self.delta["authority_delta"],0)

    def test_exact_sources_are_reference_only(self):
        self.assertEqual(set(EXPECTED),{x["normalized_key"] for x in self.delta["sources"]})
        for key, donor_id in EXPECTED.items():
            row=self.by_key[key]
            self.assertEqual(row["donor_id"],donor_id)
            self.assertEqual(row["status"],"ACCEPTED_REFERENCE")
            self.assertEqual(row["submission_review"]["basis"],"OWNER_EXPLICIT_DONORNAK_MARKER")
            self.assertEqual(row["submission_review"]["scope"],"REFERENCE_REGISTRATION_ONLY")
            self.assertTrue(row["discoverable_for_planning"])
            self.assertTrue(all(row[flag] is False for flag in FLAGS))

    def test_no_automatic_usage_or_runtime_admission(self):
        # The intake itself remains reference-only forever. Later explicitly
        # approved pattern adoption may create usage edges, but those edges
        # must not retroactively imply code/runtime/provider/model admission.
        self.assertTrue(all(v is False for v in self.delta["boundaries"].values()))
        expected_ids=set(EXPECTED.values())
        for usage in self.links.get("donor_usage_records",[]):
            if usage.get("donor_id") not in expected_ids:
                continue
            self.assertFalse(usage.get("automatic_activation",False))
            self.assertFalse(usage.get("code_imported",False))
            self.assertFalse(usage.get("provider_admission",False))
            self.assertFalse(usage.get("model_admission",False))
            self.assertFalse(usage.get("runtime_dependency",False))
            self.assertIn(usage.get("usage_kind"),{
                "CAPABILITY_PATTERN","ALGORITHM_PATTERN","WORKFLOW_PATTERN",
                "ARCHITECTURE_PATTERN","UI_UX_PATTERN","REFERENCE_BINDING"
            })

if __name__ == "__main__":
    unittest.main()
