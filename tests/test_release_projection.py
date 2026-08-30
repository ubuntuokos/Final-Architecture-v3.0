from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fa3_release_projection_gate import (
    PROJECTION_PATH,
    collect_git_snapshot_facts,
    gate,
)

ROOT = Path(__file__).resolve().parents[1]


class ReleaseProjectionGateTests(unittest.TestCase):
    def test_current_projection_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], report)

    def _copy_repo(self):
        projection = json.loads((ROOT / PROJECTION_PATH).read_text(encoding="utf-8"))
        snapshot_head = projection["source_snapshot"]["pre_projection_head_sha"]
        facts = collect_git_snapshot_facts(ROOT, snapshot_head)

        td = tempfile.TemporaryDirectory()
        dst = Path(td.name) / "repo"
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "reports"))
        return td, dst, facts

    def _gate_copy(self, dst: Path, facts):
        with patch(
            "fa3_release_projection_gate.collect_git_snapshot_facts",
            return_value=facts,
        ):
            return gate(dst)

    def test_capability_drift_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["invariants"]["canonical_capability_count"] = 144
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-003" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_manifest_tamper_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            projection = json.loads((dst / PROJECTION_PATH).read_text(encoding="utf-8"))
            victim = next(x["path"] for x in projection["manifest"] if x["path"].startswith("canonical/providers/"))
            path = dst / victim
            path.write_bytes(path.read_bytes() + b"\n")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-010" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_policy_unbind_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "canonical/enforcement-policy.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["canonical_release_projection"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-004" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_unmanifested_release_surface_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "canonical/providers/FA3-PROVIDER-UNMANIFESTED-TEST.json"
            path.write_text("{}\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-014" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_stale_snapshot_commit_count_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["source_snapshot"]["total_post_baseline_commits"] -= 1
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-018" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_stale_snapshot_delta_file_count_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["source_snapshot"]["delta_file_count"] += 1
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-018" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_stale_overlay_count_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["overlay_inventory"]["canonical_files_in_post_baseline_delta"] += 1
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-019" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_missing_inventory_record_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            providers = obj["overlay_inventory"]["provider_records"]
            mentor = "canonical/providers/FA3-PROVIDER-MENTOR-LOCAL-001.json"
            if mentor in providers:
                providers.remove(mentor)
            else:
                providers.pop()
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-020" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_wrong_snapshot_tree_sha_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["source_snapshot"]["pre_projection_root_tree_sha"] = "0" * 40
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-017" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_kanboard_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["kanboard_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-021" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_kanboard_overlay_inventory_membership_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["overlay_inventory"]["provider_records"].remove("canonical/providers/FA3-PROVIDER-KANBOARD-001.json")
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-021" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_presenton_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["presenton_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-022" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_presenton_current_host_pass_cannot_be_claimed_by_ci_reference(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["presenton_reconciliation"]["current_host_production_e2e"] = "CURRENT_HOST_PRODUCTION_E2E_PASS"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-022" for x in report["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
