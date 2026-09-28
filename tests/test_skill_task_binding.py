import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_developer_agent_coordination as dac
from fa3_skill_activation import activate_admitted_skill
from fa3_skill_fabric_gate import good_package
from fa3_skill_task_binding import SkillTaskBindingDenied, bind_language_checked_skill


class SkillTaskBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.content = b"---\nname: example\ndescription: Task skill\n---\nReview the code.\n"
        self.p = good_package()
        self.digest = hashlib.sha256(self.content).hexdigest()
        self.p["digests"]["content_sha256"] = self.digest
        self.p["hash_attestation"]["sha256"] = self.digest
        self.p["evaluation"]["bound_content_sha256"] = self.digest
        file = self.root / self.p["entrypoints"][0]["path"]
        file.parent.mkdir(parents=True)
        file.write_bytes(self.content)
        self.admission = {
            "status": "PASS", "package_id": self.p["package_id"],
            "source_commit": self.p["source"]["commit"], "content_sha256": self.digest,
            "manifest_sha256": self.p["digests"]["manifest_sha256"],
            "entrypoint_path": self.p["entrypoints"][0]["path"],
            "skill_version": "1.0.0", "admission_receipt_ref": "admit:test",
        }
        self.selection = {
            "status": "PASS", "task_id": "TASK-1", "package_id": self.p["package_id"],
            "admission_receipt_ref": "admit:test", "selection_receipt_ref": "select:test",
            "eligible_skill_ids": ["example"], "selected_skill_ids": ["example"],
        }
        self.lease = {
            "state": "ACTIVE_FOR_TASK", "task_id": "TASK-1", "skill_id": "example",
            "selection_receipt_ref": "select:test", "admission_receipt_ref": "admit:test",
            "content_sha256": self.digest, "activation_lease_ref": "lease:test",
            "expires_at_epoch": 2000000000,
        }
        self.language = {
            "user_language": "hu-HU", "work_language": "en-US", "output_language": "hu-HU",
        }
        self.evidence = {
            "status": "VALIDATED", "skill_id": "example",
            "source_content_sha256": self.digest, "language": "hu-HU",
            "admission_profile_id": "FA3-LANGUAGE-ADMISSION-001",
            "language_receipt_ref": "lang:test",
        }

    def activate(self):
        return activate_admitted_skill(
            package_root=self.root, package=self.p, admission_receipt=self.admission,
            selection_receipt=self.selection, activation_lease=self.lease,
            skill_id="example", task_id="TASK-1",
            verify_admission=lambda r: r is self.admission,
            verify_selection=lambda r: r is self.selection,
            verify_lease=lambda r: r is self.lease,
            count_tokens=lambda s: len(s.split()), now_epoch=1900000000,
        )

    def bind(self, context, **changes):
        args = {
            "context": context, "task_id": "TASK-1", "skill_id": "example",
            "language_context": self.language, "language_evidence": self.evidence,
            "verify_language_evidence": lambda r: r is self.evidence,
            "now_epoch": 1900000000,
        }
        return bind_language_checked_skill(**(args | changes))

    def test_validated_language_and_cleanup_binding(self):
        with self.activate() as ctx:
            bound = self.bind(ctx)
            self.assertEqual(bound.language_status, "VALIDATED")
            self.assertEqual(bound.language_context["output_language"], "hu-HU")
            self.assertEqual(bound.content_sha256, self.digest)
            self.assertNotIn("content_text", bound.safe_metadata())
            bound.check_live(now_epoch=1900000000)
        with self.assertRaises(SkillTaskBindingDenied):
            bound.check_live(now_epoch=1900000000)

    def test_unverified_or_wrong_language_denied(self):
        with self.activate() as ctx:
            for changes in (
                {"verify_language_evidence": lambda r: False},
                {"language_context": self.language | {"output_language": "de-DE"}},
                {"task_id": "TASK-OTHER"},
                {"language_evidence": dict(self.evidence) | {"status": "UNVERIFIED"}},
                {"language_evidence": dict(self.evidence) | {"source_content_sha256": "0" * 64}},
            ):
                with self.subTest(changes=list(changes)):
                    with self.assertRaises(SkillTaskBindingDenied):
                        self.bind(ctx, **changes)

    def test_bridged_language_requires_exact_verified_source_and_target_bytes(self):
        mediated = "Ellenőrizd a kódot."
        receipt = {
            "bridge_id": "FA3-LANGUAGE-BRIDGE-001",
            "native_or_mediated": "MEDIATED",
            "input_sha256": self.digest,
            "output_sha256": hashlib.sha256(mediated.encode()).hexdigest(),
            "target_language": "hu-HU",
            "protected_token_validation": "PASS",
            "authority_expanded_by_mediation": False,
            "provider_id": "FA3-ADMITTED-TEST-BRIDGE",
        }
        evidence = self.evidence | {"status": "BRIDGED"}
        with self.activate() as ctx:
            bridge = self.bind(
                ctx, language_evidence=evidence,
                verify_language_evidence=lambda r: r is evidence,
                mediated_text=mediated, mediation_receipt=receipt,
                verify_mediation_receipt=lambda r: r is receipt,
            )
            self.assertNotEqual(bridge.content_sha256, bridge.original_content_sha256)
            self.assertEqual(bridge.content_text, mediated)
            bridge.check_live(now_epoch=1900000000)
            with self.assertRaises(SkillTaskBindingDenied):
                self.bind(ctx, language_evidence=evidence,
                          verify_language_evidence=lambda r: r is evidence)
            with self.assertRaises(SkillTaskBindingDenied):
                self.bind(ctx, language_evidence=evidence,
                          verify_language_evidence=lambda r: r is evidence,
                          mediated_text=mediated + "!", mediation_receipt=receipt,
                          verify_mediation_receipt=lambda r: r is receipt)

    def test_coordinator_requires_explicit_skill_aware_adapter(self):
        repo = self.root / "repo"
        dac._init_fixture_repo(repo, {"work/a.txt": "base a\n", "work/b.txt": "base b\n"})
        class CapturingAdapter(dac.BuiltinDeterministicAdapter):
            observed = None
            def spawn_with_skill(self, *, task, workspace, request_path, result_path, skill_context):
                skill_context.check_live()
                self.observed = skill_context.safe_metadata()
                return super().spawn(
                    task=task, workspace=workspace,
                    request_path=request_path, result_path=result_path,
                )

        tasks = [
            dac.AgentTask("TASK-1", "alice", dac.FIXTURE_PROVIDER_ID, "work/a.txt",
                          "change a\n", required_skill_id="example"),
            dac.AgentTask("TASK-2", "bob", dac.FIXTURE_PROVIDER_ID, "work/b.txt", "change b\n"),
        ]
        with self.activate() as ctx:
            bound = self.bind(ctx)
            with self.assertRaises(dac.CoordinationDenied):
                dac.Coordinator(repo, self.root / "control-denied").run(
                    tasks, dac.BuiltinDeterministicAdapter(),
                    skill_contexts={"TASK-1": bound},
                )
            adapter = CapturingAdapter()
            result = dac.Coordinator(repo, self.root / "control-allowed").run(
                tasks, adapter, skill_contexts={"TASK-1": bound}
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(adapter.observed["materialization_receipt_ref"],
                             bound.materialization_receipt_ref)
            self.assertEqual(adapter.observed["language_context"]["output_language"], "hu-HU")

    def test_missing_or_extra_skill_context_denied(self):
        repo = self.root / "repo"
        dac._init_fixture_repo(repo, {"work/a.txt": "base a\n", "work/b.txt": "base b\n"})
        tasks = [
            dac.AgentTask("TASK-1", "alice", dac.FIXTURE_PROVIDER_ID, "work/a.txt",
                          "change a\n", required_skill_id="example"),
            dac.AgentTask("TASK-2", "bob", dac.FIXTURE_PROVIDER_ID, "work/b.txt", "change b\n"),
        ]
        with self.assertRaises(dac.CoordinationDenied):
            dac.Coordinator(repo, self.root / "control-missing").run(
                tasks, dac.BuiltinDeterministicAdapter()
            )


if __name__ == "__main__":
    unittest.main()
