import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from fa3_repository_prepare import PROJECTION, prepare_repository
from fa3_python_namespace_audit import audit


ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> str:
    cp = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)
    return cp.stdout.strip()


class ReproducibilityBootstrapTests(unittest.TestCase):
    def test_repository_has_single_fa3_python_namespace(self):
        report = audit(ROOT)
        self.assertEqual("PASS", report["result"], report["findings"])

    def test_prepare_repository_recovers_required_history_from_shallow_clone(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = base / "source"
            source.mkdir()
            git(source, "init")
            git(source, "config", "user.email", "fa3-test@example.invalid")
            git(source, "config", "user.name", "FA3 Test")
            (source / "canonical").mkdir()
            (source / "canonical/state.txt").write_text("baseline\n")
            git(source, "add", ".")
            git(source, "commit", "-m", "baseline")
            baseline = git(source, "rev-parse", "HEAD")

            (source / "canonical/state.txt").write_text("snapshot\n")
            git(source, "add", ".")
            git(source, "commit", "-m", "snapshot")
            snapshot = git(source, "rev-parse", "HEAD")
            root_tree = git(source, "rev-parse", f"{snapshot}^{{tree}}")
            canonical_tree = git(source, "rev-parse", f"{snapshot}:canonical")

            projection = {
                "base_release_commit": baseline,
                "source_snapshot": {
                    "baseline_commit_sha": baseline,
                    "pre_projection_head_sha": snapshot,
                    "pre_projection_root_tree_sha": root_tree,
                    "pre_projection_canonical_tree_sha": canonical_tree,
                },
            }
            path = source / PROJECTION
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(projection))
            git(source, "add", ".")
            git(source, "commit", "-m", "projection")

            clone = base / "clone"
            subprocess.run(
                ["git", "clone", "--depth=1", f"file://{source}", str(clone)],
                check=True,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(
                0,
                subprocess.run(
                    ["git", "-C", str(clone), "cat-file", "-e", f"{baseline}^{{commit}}"],
                    check=False,
                ).returncode,
            )

            check_only = prepare_repository(clone, check_only=True)
            self.assertEqual("FAIL", check_only["result"])
            self.assertIn(baseline, check_only["remaining_missing"])

            repaired = prepare_repository(clone)
            self.assertEqual("PASS", repaired["result"], repaired)
            self.assertIn(baseline, repaired["fetched"])
            self.assertTrue(repaired["snapshot_identity"]["baseline_is_ancestor"])
            self.assertFalse(repaired["working_tree_mutated"])


if __name__ == "__main__":
    unittest.main()
