import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_developer_agent_coordination as dac
from fa3_developer_agent_coordination import AgentTask, CoordinationDenied
from fa3_skill_fabric_gate import good_package, good_use_receipt
from fa3_skill_materialization import snapshot_digests, task_activation_lease, verify_admitted_snapshot
from fa3_skill_task_projection import SkillTaskPreflight, SkillProjectionDenied
from fa3_skill_task_binding import (
    SkillTaskBinding, SkillTaskBindingDenied, task_skill_preflight,
    validate_language_context,
)


class AgentSkillBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / "skills/example"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_bytes(b"---\nname: example\n---\nDeveloper skill.\n")
        package = good_package()
        pkg_id = package["package_id"]
        package["compatibility"]["task_classes"] = ["developer"]
        d = snapshot_digests(self.root, ["skills/example/SKILL.md"])
        package["digests"].update(content_sha256=d["files"][0]["sha256"],
                                  manifest_sha256=d["manifest_sha256"])
        package["hash_attestation"]["sha256"] = d["files"][0]["sha256"]
        package["evaluation"]["bound_content_sha256"] = d["files"][0]["sha256"]
        registry = {
            "skill_id": "example", "package_id": pkg_id, "version": "1.0.0",
            "entrypoint": "skills/example/SKILL.md", "admission_status": "ADMITTED",
            "eligibility": {"task_classes": ["developer"]},
        }
        admission = {"receipt_ref": "skill-admit:1", "result": "PASS", "package_id": pkg_id,
                     "content_sha256": d["files"][0]["sha256"],
                     "manifest_sha256": d["manifest_sha256"],
                     "dependency_digest_sha256": package["dependencies"]["digest_sha256"]}
        selection = {"receipt_ref": "skill-select:1", "package_id": pkg_id,
                     "skill_id": "example", "task_scope": "developer",
                     "eligible_skill_ids": ["example"]}
        verified = verify_admitted_snapshot(self.root, package, registry,
                                             admission, selection, "developer")
        intent = {k: good_use_receipt()[k] for k in (
            "tool_intent", "model_intent", "resource_intent", "secret_intent")}
        self.row = SkillTaskBinding(self.root, package, registry, admission, selection,
                                    task_activation_lease(verified, task_id="TASK-1"), intent)
        self.task = AgentTask("TASK-1", "agent-1", "provider-1", "x.txt", "x",
                              required_skill_ids=("example",))
        self.lang = {
            "primary_language": "hu-HU", "secondary_language": "en-US",
            "user_language": "hu-HU", "work_language": "en-US",
            "output_language": "hu-HU",
            "admitted_language_status": {"hu-HU": "BRIDGED", "en-US": "NATIVE"},
        }

    def test_real_snapshot_preflight_and_language(self):
        result = task_skill_preflight(self.task, {"example": self.row}, self.lang)
        self.assertEqual(result[0]["snapshot_verification"]["skill_id"], "example")
        self.assertEqual(validate_language_context(self.lang)["output_language"], "hu-HU")

    def test_not_admitted_language_fails_closed(self):
        lang = copy.deepcopy(self.lang)
        lang["admitted_language_status"]["hu-HU"] = "UNVERIFIED"
        with self.assertRaises(SkillTaskBindingDenied):
            task_skill_preflight(self.task, {"example": self.row}, lang)

    def test_tamper_or_undisclosed_skill_fails_closed(self):
        (self.root / "skills/example/SKILL.md").write_text("changed")
        with self.assertRaises(SkillTaskBindingDenied):
            task_skill_preflight(self.task, {"example": self.row}, self.lang)
        with self.assertRaises(SkillTaskBindingDenied):
            task_skill_preflight(self.task, {}, self.lang)

    def _reference_preflight(self):
        canonical = self.root / "canonical"
        canonical.mkdir(exist_ok=True)
        (canonical / "skill-registry.json").write_text(
            json.dumps({"id": "FA3-SKILL-REGISTRY-001",
                        "entries": [self.row.registry_entry]}), encoding="utf-8")
        return SkillTaskPreflight({"example": self.row}, self.lang, self.root,
                                  reference_only=True)

    def _fixture_coordinator(self):
        repo = self.root / "repo"
        dac._init_fixture_repo(repo, {
            "work/a.txt": "baseline\n",
            "work/b.txt": "baseline\n",
        })
        return dac.Coordinator(repo, self.root / "control")

    @staticmethod
    def _workers():
        return [
            AgentTask("TASK-1", "agent-1", dac.FIXTURE_PROVIDER_ID,
                      "work/a.txt", "skill-verified\n", required_skill_ids=("example",)),
            AgentTask("TASK-2", "agent-2", dac.FIXTURE_PROVIDER_ID,
                      "work/b.txt", "ordinary\n"),
        ]

    def test_reference_e2e_delivers_real_checked_skill_bytes(self):
        preflight = self._reference_preflight()
        coordinator = self._fixture_coordinator()
        result = coordinator.run(self._workers(), dac.BuiltinDeterministicAdapter(),
                                 skill_preflight=preflight)
        self.assertEqual(result["status"], "PASS", result)
        events = [json.loads(row) for row in
                  (self.root / "control/events.jsonl").read_text().splitlines()]
        staged = [e for e in events if e["event_type"] == "SKILL_CONTEXT_STAGED"]
        self.assertEqual(len(staged), 1)
        self.assertEqual(staged[0]["skill_ids"], ["example"])
        self.assertEqual(staged[0]["evidence_scope"], "CI_REFERENCE_ONLY")
        self.assertEqual(list((self.root / "control/ephemeral-skill-context").glob("*.json")), [])
        worker = json.loads((self.root / "control/results/TASK-1.json").read_text())
        self.assertEqual(worker["verified_skill_ids"], ["example"])
        self.assertTrue(worker["skill_context_sha256"])

    def test_fake_pass_callback_cannot_authorize_worker(self):
        coordinator = self._fixture_coordinator()
        forged = lambda task: [{
            "task_scope": "developer", "content_sha256": "a" * 64,
            "snapshot_verification": {"result": "PASS", "task_scope": "developer",
                                      "skill_id": "example"},
        }]
        with self.assertRaises(CoordinationDenied):
            coordinator.run(self._workers(), dac.BuiltinDeterministicAdapter(),
                            skill_preflight=forged)
        self.assertFalse((self.root / "control/results/TASK-1.json").exists())

    def test_unregistered_or_modified_file_denied(self):
        preflight = self._reference_preflight()
        (self.root / "canonical/skill-registry.json").write_text(
            json.dumps({"id": "FA3-SKILL-REGISTRY-001", "entries": []}))
        with self.assertRaises(SkillProjectionDenied):
            preflight.prepare_task(self._workers()[0])
        preflight = self._reference_preflight()
        (self.root / "skills/example/SKILL.md").write_bytes(b"tampered")
        with self.assertRaises(SkillProjectionDenied):
            preflight.prepare_task(self._workers()[0])

    def test_unapproved_adapter_and_missing_authority_fail_closed(self):
        with self.assertRaises(SkillProjectionDenied):
            SkillTaskPreflight({"example": self.row}, self.lang, self.root)
        preflight = self._reference_preflight()
        class NoProjectionAdapter(dac.BuiltinDeterministicAdapter):
            supports_verified_skill_context = False
        coordinator = self._fixture_coordinator()
        with self.assertRaises(CoordinationDenied):
            coordinator.run(self._workers(), NoProjectionAdapter(),
                            skill_preflight=preflight)
        self.assertFalse((self.root / "control/results/TASK-1.json").exists())

    def test_authority_adapter_must_validate_all_claims(self):
        preflight = self._reference_preflight()
        preflight.reference_only = False
        seen = []
        def verifier(kind, record, task_id):
            seen.append(kind)
            return kind != "task_selection"
        preflight.authority_verifier = verifier
        with self.assertRaises(SkillProjectionDenied):
            preflight.prepare_task(self._workers()[0])
        self.assertEqual(seen, ["language_admission", "package_admission", "task_selection"])

    def test_lease_cannot_be_replayed_for_another_task(self):
        preflight = self._reference_preflight()
        wrong = AgentTask("TASK-OTHER", "agent-other", dac.FIXTURE_PROVIDER_ID,
                          "work/a.txt", "x", required_skill_ids=("example",))
        with self.assertRaises(SkillProjectionDenied):
            preflight.prepare_task(wrong)
        context = preflight.prepare_task(self._workers()[0])
        self.assertEqual(context["skills"][0]["bound_task_id"], "TASK-1")
        self.assertTrue(context["skills"][0]["activation_lease_id"].startswith("skill-lease:"))

    def test_fixture_worker_rejects_expired_projected_lease(self):
        from datetime import datetime, timedelta, timezone
        preflight = self._reference_preflight()
        context = preflight.prepare_task(self._workers()[0])
        context["skills"][0]["lease_expires_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        workspace = self.root / "worker-workspace"
        (workspace / "work").mkdir(parents=True)
        target = workspace / "work/a.txt"
        target.write_text("original", encoding="utf-8")
        context_path = self.root / "expired-skill-context.json"
        request_path = self.root / "expired-skill-request.json"
        result_path = self.root / "expired-skill-result.json"
        context_path.write_text(json.dumps(context), encoding="utf-8")
        request_path.write_text(json.dumps({
            "task_id": "TASK-1", "agent_id": "agent-1",
            "provider_id": dac.FIXTURE_PROVIDER_ID,
            "workspace": str(workspace), "relative_path": "work/a.txt",
            "content": "should-not-run", "required_skill_ids": ["example"],
            "skill_context_path": str(context_path),
        }), encoding="utf-8")
        with self.assertRaises(CoordinationDenied):
            dac.worker_main(request_path, result_path)
        self.assertEqual(target.read_text(), "original")
        self.assertFalse(result_path.exists())


if __name__ == "__main__":
    unittest.main()
