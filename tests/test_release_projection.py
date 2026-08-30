from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_release_projection_gate import PROJECTION_PATH, gate

ROOT = Path(__file__).resolve().parents[1]


class ReleaseProjectionGateTests(unittest.TestCase):
    def test_current_projection_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)

    def _copy_repo(self):
        td = tempfile.TemporaryDirectory()
        dst = Path(td.name) / "repo"
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "reports"))
        return td, dst

    def test_capability_drift_fails_closed(self):
        td, dst = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["invariants"]["canonical_capability_count"] = 144
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-003" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_manifest_tamper_fails_closed(self):
        td, dst = self._copy_repo()
        try:
            projection = json.loads((dst / PROJECTION_PATH).read_text(encoding="utf-8"))
            victim = next(x["path"] for x in projection["manifest"] if x["path"].startswith("canonical/providers/"))
            path = dst / victim
            path.write_bytes(path.read_bytes() + b"\n")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-010" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_policy_unbind_fails_closed(self):
        td, dst = self._copy_repo()
        try:
            path = dst / "canonical/enforcement-policy.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["canonical_release_projection"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = gate(dst)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-004" for x in report["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
