from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import fa3_stable_audio_3_gate as s

ROOT = Path(__file__).resolve().parents[1]


class StableAudio3GateTests(unittest.TestCase):
    def _copy(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return td, root

    def _mutate(self, root: Path, rel: str, fn):
        p = root / rel
        d = json.loads(p.read_text(encoding="utf-8"))
        fn(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_baseline_passes_without_current_host_promotion(self):
        r = s.gate(ROOT)
        self.assertEqual("PASS", r["result"], r)
        self.assertEqual(143, r["capability_count"])
        self.assertFalse(r["current_host_runtime_evidence"])
        self.assertFalse(r["production_promotion_claim"])

    def test_music_profile_binding_is_fail_closed(self):
        td, root = self._copy()
        try:
            self._mutate(root, "canonical/profiles/FA3-MUSIC-001.json", lambda d: d.__setitem__("providers", ["FA3-PROVIDER-ACE-STEP-001"]))
            self.assertEqual("FAIL", s.gate(root)["result"])
        finally:
            td.cleanup()

    def test_provider_authority_escalation_fails(self):
        td, root = self._copy()
        try:
            self._mutate(root, "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json", lambda d: d.__setitem__("architectural_authority", True))
            self.assertEqual("FAIL", s.gate(root)["result"])
        finally:
            td.cleanup()

    def test_floating_upstream_reference_fails(self):
        td, root = self._copy()
        try:
            self._mutate(root, "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json", lambda d: d.__setitem__("immutable_reference", "main"))
            self.assertEqual("FAIL", s.gate(root)["result"])
        finally:
            td.cleanup()

    def test_retired_medium_bf16_cannot_be_reenabled(self):
        td, root = self._copy()
        try:
            def mutate(d):
                d["precision_policy"]["allowed_medium"].append("bf16")
            self._mutate(root, "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json", mutate)
            self.assertEqual("FAIL", s.gate(root)["result"])
        finally:
            td.cleanup()

    def test_floating_flash_attention_artifact_policy_fails(self):
        td, root = self._copy()
        try:
            def mutate(d):
                d["supply_chain"]["flash_attention"]["floating_community_wheel_url_for_production_forbidden"] = False
            self._mutate(root, "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json", mutate)
            self.assertEqual("FAIL", s.gate(root)["result"])
        finally:
            td.cleanup()

    def test_missing_runtime_identity_field_fails(self):
        td, root = self._copy()
        try:
            def mutate(d):
                d["runtime_identity"]["required_fields"].remove("pcm_conversion_semantics")
            self._mutate(root, "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json", mutate)
            self.assertEqual("FAIL", s.gate(root)["result"])
        finally:
            td.cleanup()

    def test_current_host_gate_requires_real_receipt(self):
        td, root = self._copy()
        try:
            r = s.current_host_gate(root)
            self.assertEqual("FAIL", r["result"])
            self.assertFalse(r["current_host_runtime_evidence"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
