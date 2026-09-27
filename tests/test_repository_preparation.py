import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from fa3_prepare_repository import inspect, required_git_objects


class RepositoryPreparationTests(unittest.TestCase):
    def test_current_repository_has_required_projection_objects(self):
        report = inspect(ROOT)
        self.assertEqual(report["result"], "PASS", report)

    def test_required_objects_come_from_release_projection(self):
        rows = required_git_objects(ROOT)
        self.assertEqual({x["kind"] for x in rows}, {"baseline_commit", "pre_projection_head"})
        self.assertTrue(all(len(x["sha"]) == 40 for x in rows))

    def test_shallow_fixture_reports_recovery_hint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "canonical/releases").mkdir(parents=True)
            projection = {
                "source_snapshot": {
                    "baseline_commit_sha": "a" * 40,
                    "pre_projection_head_sha": "b" * 40,
                }
            }
            (root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json").write_text(json.dumps(projection))
            report = inspect(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertEqual(report["recovery_hint"], "bash bin/fa3-prepare-repository --fetch")


if __name__ == "__main__":
    unittest.main()
