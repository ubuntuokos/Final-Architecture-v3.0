import tempfile
import unittest
from pathlib import Path

import fa3_developer_agent_coordination as dac

class WorkspacePathHardeningTests(unittest.TestCase):
    def test_reject_existing_and_dangling_symlinks_before_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "safe").mkdir()
            (root / "link").symlink_to(root / "safe", target_is_directory=True)
            (root / "dangling").symlink_to(root / "missing")
            for name in ("link/file.txt", "dangling", "safe/../outside", ".git/config"):
                with self.subTest(name=name), self.assertRaises(dac.CoordinationDenied):
                    dac._resolve_within(root, name)
            self.assertEqual(dac._resolve_within(root, "safe/file.txt"),
                             root / "safe" / "file.txt")

    def test_hostile_agent_identity_never_reaches_git_branch_or_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "repo"
            dac._init_fixture_repo(repo, {"work/a.txt": "start\n"})
            control = root / "control"
            coordinator = dac.Coordinator(repo, control)
            for name in ("../escape", "agent/child", ".git", "bad name", "", "a"*65):
                with self.subTest(name=name), self.assertRaises(dac.CoordinationDenied):
                    coordinator.allocate_worktree(dac.AgentTask(
                        task_id="T-01", agent_id=name, provider_id="fixture",
                        relative_path="work/a.txt", content="safe\n"))
            self.assertEqual(list((control / "worktrees").glob("*"))
                             if (control / "worktrees").exists() else [], [])

    def test_canonical_repo_cannot_be_workspace_control_root(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder) / "repo"
            dac._init_fixture_repo(repo, {"work/a.txt": "start\n"})
            coordinator = dac.Coordinator(repo, repo / "agent-control")
            with self.assertRaises(dac.CoordinationDenied):
                coordinator.allocate_worktree(dac.AgentTask(
                    task_id="T-01", agent_id="worker", provider_id="fixture",
                    relative_path="work/a.txt", content="safe\n"))

    def test_normal_reference_e2e_still_works(self):
        report = dac.run_reference_e2e()
        self.assertEqual(report["result"], "PASS", report)
        self.assertFalse(report["current_host_production_claim"])

if __name__ == "__main__":
    unittest.main()
