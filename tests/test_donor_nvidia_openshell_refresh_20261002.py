"""NVIDIA OpenShell existing-donor refresh regressions."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-NVIDIA-OPENSHELL-REFRESH-2026-10-02.json"
LINKS = ROOT / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"

KEY = "github:nvidia/openshell"
DONOR_ID = "FA3-DONOR-NVIDIA-OPENSHELL-001"
REQUIRED_HINTS = {
    "policy-proving",
    "executable-identity-binding",
    "filesystem-process-network-enforcement",
    "credential-projection",
    "mcp-l7-inspection",
    "sandbox-lifecycle",
    "structured-security-events",
    "runtime-isolation",
}
DENY_FLAGS = (
    "authority",
    "automatic_selection",
    "automatic_fetch",
    "automatic_install",
    "automatic_activation",
    "automatic_dependency",
    "automatic_code_import",
    "automatic_provider_admission",
    "automatic_model_selection",
)


class NvidiaOpenShellDonorRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))
        cls.links = json.loads(LINKS.read_text(encoding="utf-8"))
        cls.entries = cls.registry["entries"]
        cls.matches = [e for e in cls.entries if e["source"]["normalized_key"] == KEY]
        cls.row = cls.matches[0]

    def test_refresh_preserves_single_identity_and_baseline(self):
        self.assertEqual(len(self.matches), 1)
        self.assertEqual(self.row["donor_id"], DONOR_ID)
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.entries))
        self.assertEqual(len(self.entries), 1354)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertEqual(self.delta["parent_entry_count"], 1354)
        self.assertEqual(self.delta["proposed_entry_count"], 1354)
        self.assertEqual(self.delta["new_entry_count"], 0)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)

    def test_refresh_records_current_reference_delta(self):
        self.assertEqual(self.row["last_seen"], "2026-10-02")
        self.assertTrue(REQUIRED_HINTS.issubset(set(self.row["capability_hints"])))
        self.assertEqual(self.delta["upstream"]["stable_release"], "v0.1.2")
        self.assertEqual(
            self.delta["upstream"]["stable_commit"],
            "6648bd0c290efbc41ba131ee9831ee45cd431f94",
        )
        self.assertEqual(
            self.delta["upstream"]["discovery_main_commit"],
            "ec49209da25be39840742df29b64ec694d159c2f",
        )
        self.assertEqual(self.delta["upstream"]["commits_ahead_of_stable"], 71)
        self.assertFalse(self.delta["upstream"]["discovery_main_is_runtime_baseline"])

    def test_refresh_does_not_promote_or_admit_runtime(self):
        self.assertEqual(self.row["status"], "CANDIDATE")
        self.assertTrue(all(self.row[flag] is False for flag in DENY_FLAGS))
        self.assertTrue(all(v is False for v in self.delta["boundaries"].values()))

    def test_refresh_does_not_create_usage_edge(self):
        serialized = json.dumps(self.links, sort_keys=True)
        self.assertNotIn(DONOR_ID, serialized)
        self.assertFalse(self.delta["boundaries"]["usage_edge_created"])


if __name__ == "__main__":
    unittest.main()
