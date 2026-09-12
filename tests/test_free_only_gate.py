import unittest
from pathlib import Path
from fa3_free_only_gate import BLOCKED, REMOVED_RUNTIME_PATHS, gate

ROOT = Path(__file__).resolve().parents[1]


class FreeOnlyGateTests(unittest.TestCase):
    def test_free_only_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["capability_count"], 143)
        self.assertEqual(report["new_capabilities"], 0)
        self.assertEqual(report["new_architectural_authorities"], 0)

    def test_blocked_paid_provider_set_is_explicit(self):
        self.assertEqual(
            BLOCKED,
            {
                "FA3-PROVIDER-CODEX-001",
                "FA3-PROVIDER-KLING-001",
                "FA3-PROVIDER-SEEDANCE-001",
                "FA3-PROVIDER-MINIMAX-H3-001",
                "FA3-PROVIDER-SD35-NVIDIA-NIM-001",
            },
        )

    def test_removed_runtime_surfaces_are_absent(self):
        returned = [rel for rel in REMOVED_RUNTIME_PATHS if (ROOT / rel).exists()]
        self.assertEqual(returned, [])


if __name__ == "__main__":
    unittest.main()
