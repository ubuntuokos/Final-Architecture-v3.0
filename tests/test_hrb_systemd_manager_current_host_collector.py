import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "evidence/collect-hrb-systemd-manager-current-host.py"

spec = importlib.util.spec_from_file_location("fa3_collect_hrb_systemd_current_host", COLLECTOR)
collector = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(collector)


class HrbSystemdManagerCollectorTests(unittest.TestCase):
    def test_provider_enrichment_does_not_create_a_global_cuda_floor(self):
        rows = collector.parse_gpu_rows(
            "GPU-A, 00000000:A1:00.0, NVIDIA Fixture Accelerator X, 610.57.04, 8188, 8.6\n"
            "GPU-B, 00000000:B1:00.0, NVIDIA GeForce RTX 5090, 610.57.04, 24564, 8.0\n"
        )
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["eligible_for_workload_admission"])
        self.assertEqual(rows[0]["cuda_compute_capability"], 8.6)
        self.assertEqual(rows[0]["admission_semantics"], "PROVIDER_CAPABILITIES_ARE_WORKLOAD_SCOPED_NOT_GLOBAL_FLOOR")
        self.assertTrue(rows[1]["eligible_for_workload_admission"])

    def test_missing_cuda_capability_remains_workload_scoped(self):
        rows = collector.parse_gpu_rows(
            "GPU-A, 00000000:A1:00.0, NVIDIA Fixture Accelerator X, 610.57.04, 8188, N/A\n"
        )
        self.assertEqual(rows[0]["cuda_compute_capability"], None)
        self.assertTrue(rows[0]["eligible_for_workload_admission"])

    def test_effective_cpuset_walks_to_nearest_nonempty_ancestor(self):
        with tempfile.TemporaryDirectory() as td:
            mount = Path(td)
            parent = mount / "user.slice"
            leaf = parent / "runner.scope"
            leaf.mkdir(parents=True)
            (mount / "cpuset.cpus.effective").write_text("0-87\n", encoding="utf-8")
            (parent / "cpuset.cpus.effective").write_text("22-43,66-87\n", encoding="utf-8")
            (leaf / "cpuset.cpus.effective").write_text("\n", encoding="utf-8")
            value, source = collector.nearest_nonempty_cgroup_value(
                leaf, mount, "cpuset.cpus.effective"
            )
            self.assertEqual(value, "22-43,66-87")
            self.assertEqual(source, "/user.slice")

    def test_effective_memory_nodes_can_fall_back_to_root(self):
        with tempfile.TemporaryDirectory() as td:
            mount = Path(td)
            leaf = mount / "user.slice" / "runner.scope"
            leaf.mkdir(parents=True)
            (mount / "cpuset.mems.effective").write_text("0-1\n", encoding="utf-8")
            (leaf / "cpuset.mems.effective").write_text("\n", encoding="utf-8")
            value, source = collector.nearest_nonempty_cgroup_value(
                leaf, mount, "cpuset.mems.effective"
            )
            self.assertEqual(value, "0-1")
            self.assertEqual(source, "/")

    def test_cgroup_lookup_rejects_escape(self):
        with tempfile.TemporaryDirectory() as td:
            mount = Path(td) / "mount"
            mount.mkdir()
            outside = Path(td) / "outside"
            outside.mkdir()
            with self.assertRaises(RuntimeError):
                collector.nearest_nonempty_cgroup_value(
                    outside, mount, "cpuset.cpus.effective"
                )


if __name__ == "__main__":
    unittest.main()
