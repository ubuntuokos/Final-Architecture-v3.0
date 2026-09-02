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

    def test_stability_sgm_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["stability_sgm_reconciliation"]["contract_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-030" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_stability_sgm_reference_cannot_claim_current_host_runtime(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["stability_sgm_reconciliation"]["current_host_provider_runtime_evidence"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-030" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_opencut_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["opencut_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-031" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_opencut_reference_cannot_claim_current_host_runtime(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["opencut_reconciliation"]["current_host_runtime_evidence"] = "CURRENT_HOST_PRODUCTION_E2E_PASS"
            obj["opencut_reconciliation"]["runtime_activation_status"] = "ADMITTED"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-031" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_squash_lineage_requires_release_surface_equivalence(self):
        td, dst, facts = self._copy_repo()
        try:
            broken = dict(facts)
            broken["snapshot_is_ancestor_of_current_head"] = False
            broken["snapshot_release_surface_equivalent_except_projection"] = False
            report = self._gate_copy(dst, broken)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-016" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_squash_lineage_accepts_content_equivalent_snapshot(self):
        td, dst, facts = self._copy_repo()
        try:
            equivalent = dict(facts)
            equivalent["snapshot_is_ancestor_of_current_head"] = False
            equivalent["snapshot_release_surface_equivalent_except_projection"] = True
            report = self._gate_copy(dst, equivalent)
            self.assertEqual("PASS", report["result"], report)
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


    def test_autogpt_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["autogpt_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-023" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_autogpt_evidence_registry_binding_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "evidence/evidence-registry.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            cap028 = next(x for x in obj["records"] if x["subject_id"] == "CAP-028")
            cap028["evidence_artifacts"].remove("evidence/reference/autogpt-ci-2026-08-30.json")
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-023" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_autogpt_runtime_promotion_claim_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["autogpt_reconciliation"]["runtime_activation_status"] = "CURRENT_HOST_PRODUCTION_E2E_PASS"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-023" for x in report["findings"]))
        finally:
            td.cleanup()


    def test_developer_agent_coordination_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["developer_agent_coordination_reconciliation"]["contract_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-024" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_developer_agent_coordination_ci_e2e_cannot_claim_current_host_production(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["developer_agent_coordination_reconciliation"]["current_host_production_claim"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-024" for x in report["findings"]))
        finally:
            td.cleanup()


    def test_codex_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["codex_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-025" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_codex_current_host_pass_cannot_be_claimed_by_static_projection(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["codex_reconciliation"]["current_host_production_e2e"] = "CURRENT_HOST_PRODUCTION_E2E_PASS"
            obj["codex_reconciliation"]["runtime_activation_status"] = "ADMITTED"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-025" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_codex_cap028_binding_is_required(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "evidence/evidence-registry.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            cap028 = next(x for x in obj["records"] if x["subject_id"] == "CAP-028")
            cap028["source_decision_ids"].remove("FA3-DEC-CODEX-ADAPTER-2026-08-31")
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-025" for x in report["findings"]))
        finally:
            td.cleanup()


    def test_ai_infra_guard_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["ai_infra_guard_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-026" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_ai_infra_guard_evidence_registry_binding_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "evidence/evidence-registry.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            cap011 = next(x for x in obj["records"] if x["subject_id"] == "CAP-011")
            cap011["evidence_artifacts"].remove("evidence/reference/ai-infra-guard-ci-2026-08-31.json")
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-026" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_ai_infra_guard_runtime_promotion_claim_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["ai_infra_guard_reconciliation"]["current_host_runtime_promotion_claim"] = True
            obj["ai_infra_guard_reconciliation"]["runtime_activation_status"] = "CURRENT_HOST_PRODUCTION_E2E_PASS"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-026" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_ai_infra_guard_admission_cannot_be_admitted_without_current_host_evidence(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "canonical/ai-infra-guard-runtime-admission.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["status"] = "ADMITTED"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-026" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_ai_infra_guard_current_host_tooling_must_be_manifested(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["manifest"] = [
                x for x in obj["manifest"]
                if x["path"] != "src/fa3_ai_infra_guard_adapter.py"
            ]
            obj["manifest_entry_count"] = len(obj["manifest"])
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "FA3-RELEASE-PROJECTION-026" for x in report["findings"]))
        finally:
            td.cleanup()


    def test_marketing_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["marketing_reconciliation"]["primary_locale"] = "en"
            path.write_text(
                json.dumps(obj, indent=2) + "\n",
                encoding="utf-8",
            )
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-028"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()

    def test_marketing_current_host_pass_cannot_be_claimed_by_ci_reference(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["marketing_reconciliation"][
                "current_host_runtime_promotion_claim"
            ] = True
            path.write_text(
                json.dumps(obj, indent=2) + "\n",
                encoding="utf-8",
            )
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-028"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()

    def test_marketing_evidence_registry_binding_is_required(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "evidence/evidence-registry.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            record = next(
                item
                for item in obj["records"]
                if item["subject_id"] == "CAP-040"
            )
            record["evidence_artifacts"].remove(
                "evidence/reference/marketing-ci-2026-08-31.json"
            )
            path.write_text(
                json.dumps(obj, indent=2) + "\n",
                encoding="utf-8",
            )
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-028"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()

    def test_voice_synthesis_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["voice_synthesis_reconciliation"]["provider_ids"] = []
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "FA3-RELEASE-PROJECTION-033" for item in report["findings"]))
        finally:
            td.cleanup()

    def test_voice_synthesis_ci_cannot_claim_current_host_or_hu_quality(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / "evidence/reference/voice-synthesis-ci-2026-09-01.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["current_host_production_claim"] = True
            obj["hungarian_quality_claim"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(item["code"] == "FA3-RELEASE-PROJECTION-033" for item in report["findings"]))
        finally:
            td.cleanup()


    def test_openhands_projection_reconciliation_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["openhands_reconciliation"]["provider_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-032"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()

    def test_openhands_reference_cannot_claim_current_host_runtime(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["openhands_reconciliation"]["current_host_runtime_evidence"] = (
                "CURRENT_HOST_PRODUCTION_E2E_PASS"
            )
            obj["openhands_reconciliation"]["runtime_activation_status"] = "ADMITTED"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-032"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()


    def test_openhands_current_host_materialization_binding_fails_closed(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["openhands_reconciliation"]["current_host_decision_id"] = "INVALID"
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-032"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()

    def test_openhands_materialized_pending_cannot_claim_production_admission(self):
        td, dst, facts = self._copy_repo()
        try:
            path = dst / PROJECTION_PATH
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["openhands_reconciliation"]["production_provider_admission"] = True
            obj["openhands_reconciliation"]["current_host_runtime_evidence"] = (
                "CURRENT_HOST_OPENHANDS_PRODUCTION_E2E_PASS"
            )
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            report = self._gate_copy(dst, facts)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(
                any(
                    item["code"] == "FA3-RELEASE-PROJECTION-032"
                    for item in report["findings"]
                )
            )
        finally:
            td.cleanup()



if __name__ == "__main__":
    unittest.main()
