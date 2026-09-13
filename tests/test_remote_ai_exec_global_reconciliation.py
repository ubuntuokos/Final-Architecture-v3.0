from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "FA3-REMOTE-AI-EXEC-001"
GATESET_ID = "FA3-REMOTE-AI-EXEC-GATESET-001"
RELEASE_PATH = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY_PATH = ROOT / "canonical/enforcement-policy.json"
REQUIRED_MANIFEST_PATHS = {
    ".github/workflows/fa3-remote-ai-exec-gate.yml",
    ".github/workflows/fa3-remote-ai-exec-reconcile.yml",
    "apps/fa3-control-center/qml/Main.qml",
    "canonical/FA3-GATE-REMOTE-AI-EXEC-001.json",
    "canonical/contracts/FA3-REMOTE-AI-EXEC-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-REMOTE-AI-HF-SPACES-2026-09-13.json",
    "canonical/profiles/FA3-REMOTE-AI-EXEC-001.json",
    "canonical/providers/FA3-PROVIDER-HF-SPACES-001.json",
    "evidence/reference/remote-ai-hf-spaces-ci-2026-09-13.json",
    "src/fa3_remote_ai_exec_gate.py",
    "tests/test_remote_ai_exec_gate.py",
    "tests/test_remote_ai_exec_global_reconciliation.py",
    "tools/fa3_remote_ai_exec_global_reconcile.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RemoteAIGlobalReconciliationTests(unittest.TestCase):
    def test_remote_ai_gate_is_globally_mandatory(self) -> None:
        policy = load(POLICY_PATH)
        release = load(RELEASE_PATH)
        self.assertIn(GATESET_ID, policy["mandatory_reference_gates"])
        self.assertIn(GATESET_ID, release["mandatory_reference_gates"])
        self.assertEqual(
            set(policy["mandatory_reference_gates"]),
            set(release["mandatory_reference_gates"]),
        )

    def test_release_semantics_remain_non_authoritative_and_non_promoted(self) -> None:
        release = load(RELEASE_PATH)
        remote_ai = release["remote_ai_execution_reconciliation"]
        self.assertEqual(remote_ai["profile_id"], PROFILE_ID)
        self.assertEqual(remote_ai["capability_projection"], ["CAP-005", "CAP-011"])
        self.assertEqual(remote_ai["gui_entry"], "Remote AI Hub")
        self.assertEqual(remote_ai["silent_local_to_remote_fallback"], "FORBIDDEN")
        self.assertIs(remote_ai["discovery_metadata_is_trust_authority"], False)
        self.assertIs(remote_ai["credential_reference_only"], True)
        self.assertEqual(remote_ai["direct_gui_remote_provider_bypass"], "FORBIDDEN")
        self.assertIs(remote_ai["hf_model_store_separate_projection"], True)
        self.assertEqual(remote_ai["live_remote_execution_status"], "NOT_CLAIMED")
        self.assertEqual(remote_ai["runtime_status"], "PENDING_CURRENT_HOST")
        self.assertIs(remote_ai["production_admitted"], False)
        self.assertIs(remote_ai["current_host_runtime_promotion_claimed"], False)
        self.assertIs(remote_ai["provider_is_architectural_authority"], False)
        self.assertEqual(remote_ai["new_capabilities"], 0)
        self.assertEqual(remote_ai["new_architectural_authorities"], 0)
        self.assertEqual(remote_ai["capability_count_after"], 143)

    def test_all_remote_ai_release_surface_files_are_manifested(self) -> None:
        release = load(RELEASE_PATH)
        manifest_paths = {entry["path"] for entry in release["manifest"]}
        self.assertFalse(REQUIRED_MANIFEST_PATHS - manifest_paths)


if __name__ == "__main__":
    unittest.main()
