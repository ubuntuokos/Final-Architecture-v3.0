from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class GenerativeMediaStudioGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]

    def test_static_gate_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.root / "src/fa3_generative_media_studio_gate.py"), "--root", str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "PASS")
        self.assertIn("CURRENT_HOST_BUILD_PASS", payload["non_claims"])

    def test_contract_keeps_authorities_external(self) -> None:
        contract = json.loads(
            (self.root / "canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["capability_count"], 175)
        self.assertFalse(contract["new_capability"])
        self.assertFalse(contract["new_architectural_authority"])
        self.assertEqual(contract["authority_boundaries"]["provider_routing"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertEqual(contract["authority_boundaries"]["host_resources"], "FA3-AUTH-HOST-RESOURCE-BROKER-001")
        self.assertFalse(contract["request_compilation"]["physical_provider_pin_allowed"])
        self.assertFalse(contract["request_compilation"]["physical_model_pin_allowed"])

    def test_ui_duration_is_application_scoped(self) -> None:
        contract = json.loads(
            (self.root / "canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json").read_text(encoding="utf-8")
        )
        duration = contract["studio_ui_policy"]["self_contained_video_duration_seconds"]
        self.assertEqual(duration["minimum"], 6)
        self.assertEqual(duration["maximum"], 20)
        self.assertEqual(duration["scope"], "STUDIO_SHOT_CONTROL_ONLY")
        self.assertTrue(duration["provider_capability_may_be_narrower"])
        self.assertTrue(duration["provider_capability_may_be_broader"])

    def test_autom8ai_is_discovery_not_authority(self) -> None:
        ref = json.loads(
            (self.root / "canonical/references/FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28.json").read_text(encoding="utf-8")
        )
        self.assertFalse(ref["policy"]["autom8ai_fork_is_canonical_source"])
        self.assertTrue(ref["policy"]["original_upstream_is_canonical_donor_source"])
        self.assertFalse(ref["policy"]["code_imported_by_this_change"])


if __name__ == "__main__":
    unittest.main()
