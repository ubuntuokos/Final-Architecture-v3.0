from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_blender_engine_fabric_gate import validate

FILES = [
    "canonical/FA3-BLENDER-ENGINE-FABRIC-001.json",
    "canonical/profiles/FA3-BLENDER-COMPATIBILITY-PROFILE-001.json",
    "canonical/contracts/FA3-BLENDER-COMPATIBILITY-CONTRACTS-001.json",
    "canonical/assessments/FA3-BLENDER-ENGINE-FABRIC-REUSE-ASSESSMENT-001.json",
    "canonical/assessments/FA3-BLENDER-COMPATIBILITY-PROFILE-DECISION-ASSESSMENT-2026-10-01.json",
    "canonical/decisions/FA3-DEC-BLENDER-ENGINE-FABRIC-2026-10-01.json",
    "canonical/intents/FA3-BLENDER-ENGINE-FABRIC-APPLICATION-INTENT-001.json",
    "canonical/FA3-BLENDER-ENGINE-FABRIC-CURRENT-HOST-IMPACT-001.json",
    "canonical/FA3-CAPABILITY-MODEL-175-001.json",
]

def fixture(dst: Path) -> None:
    for rel in FILES:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)

class BlenderEngineFabricTests(unittest.TestCase):
    def test_canonical_passes(self):
        report = validate(ROOT)
        self.assertEqual(report["validation"]["result"], "PASS", report["validation"]["findings"])
        self.assertEqual(report["capability_baseline"], 175)
        self.assertEqual(report["capability_bindings"], 16)
        self.assertFalse(report["runtime_activation"])
        self.assertFalse(report["physical_current_host_pass_claimed"])

    def test_governance_assessments_cover_profile(self):
        reuse = json.loads((ROOT / FILES[3]).read_text())
        self.assertIn("FA3-BLENDER-COMPATIBILITY-PROFILE-001", reuse["covered_ids"])
        decision = json.loads((ROOT / FILES[4]).read_text())
        self.assertEqual(decision["assessment"], "NOT_APPLICABLE")
        self.assertIn("FA3-BLENDER-COMPATIBILITY-PROFILE-001", decision["covered_ids"])

    def test_blender_fork_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            path = root / FILES[0]
            data = json.loads(path.read_text())
            data["architecture"]["blender_core_fork"] = True
            path.write_text(json.dumps(data))
            codes = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("BLENDER_FORK_FORBIDDEN", codes)

    def test_cap_176_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            path = root / FILES[0]
            data = json.loads(path.read_text())
            data["capability_bindings"].append("CAP-176")
            path.write_text(json.dumps(data))
            codes = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("CAPABILITY_BINDING_DRIFT", codes)
            self.assertIn("CAPABILITY_OUT_OF_BASELINE", codes)

    def test_silent_loss_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            path = root / FILES[1]
            data = json.loads(path.read_text())
            data["loss_policy"]["silent_loss_forbidden"] = False
            path.write_text(json.dumps(data))
            codes = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("SILENT_LOSS_FORBIDDEN", codes)

    def test_runtime_activation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            path = root / FILES[0]
            data = json.loads(path.read_text())
            data["runtime_materialization"]["gpu_backend_activation"] = True
            path.write_text(json.dumps(data))
            codes = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("STATIC_RUNTIME_ACTIVATION", codes)

    def test_direct_neural_core_coupling_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            path = root / FILES[0]
            data = json.loads(path.read_text())
            data["render_policy"]["direct_opendlss_nr_blender_core_coupling"] = True
            path.write_text(json.dumps(data))
            codes = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("NEURAL_CORE_COUPLING", codes)

    def test_false_current_host_promotion_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture(root)
            path = root / FILES[7]
            data = json.loads(path.read_text())
            data["physical_current_host_pass_claimed"] = True
            path.write_text(json.dumps(data))
            codes = {x["code"] for x in validate(root)["validation"]["findings"]}
            self.assertIn("CURRENT_HOST_FALSE_PROMOTION", codes)

if __name__ == "__main__":
    unittest.main()
