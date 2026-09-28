import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_skill_activation import (
    SkillActivationDenied, activate_admitted_skill, read_snapshot_file, reference_regressions,
)
from fa3_skill_fabric_gate import good_package


class SkillActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = b"---\nname: example\ndescription: Example\n---\nRead and review the task.\n"
        self.package = good_package()
        digest = hashlib.sha256(self.content).hexdigest()
        self.package["digests"]["content_sha256"] = digest
        self.package["hash_attestation"]["sha256"] = digest
        self.package["evaluation"]["bound_content_sha256"] = digest
        self.path = self.package["entrypoints"][0]["path"]
        file = self.root / self.path
        file.parent.mkdir(parents=True)
        file.write_bytes(self.content)
        self.admission = {
            "status": "PASS", "package_id": self.package["package_id"],
            "source_commit": self.package["source"]["commit"], "content_sha256": digest,
            "manifest_sha256": self.package["digests"]["manifest_sha256"],
            "entrypoint_path": self.path, "skill_version": "1.0.0",
            "admission_receipt_ref": "admission:test",
        }
        self.selection = {
            "status": "PASS", "task_id": "task:test",
            "package_id": self.package["package_id"],
            "admission_receipt_ref": "admission:test",
            "selection_receipt_ref": "selection:test",
            "eligible_skill_ids": ["example"],
            "selected_skill_ids": ["example"],
        }
        self.lease = {
            "state": "ACTIVE_FOR_TASK", "task_id": "task:test", "skill_id": "example",
            "selection_receipt_ref": "selection:test", "admission_receipt_ref": "admission:test",
            "content_sha256": digest, "activation_lease_ref": "lease:test",
            "expires_at_epoch": 2000000000,
        }

    def args(self):
        return {
            "package_root": self.root, "package": self.package,
            "admission_receipt": self.admission, "selection_receipt": self.selection,
            "activation_lease": self.lease, "skill_id": "example", "task_id": "task:test",
            "verify_admission": lambda r: r is self.admission,
            "verify_selection": lambda r: r is self.selection,
            "verify_lease": lambda r: r is self.lease,
            "count_tokens": lambda s: len(s.split()),
            "now_epoch": 1900000000,
        }

    def test_positive_exact_byte_task_scope_cleanup_and_non_authority(self):
        with activate_admitted_skill(**self.args()) as context:
            self.assertEqual(context.read_text().encode(), self.content)
            self.assertEqual(context.receipt["content_sha256"], hashlib.sha256(self.content).hexdigest())
            self.assertFalse(context.receipt["authority"])
            self.assertFalse(context.receipt["current_host_production_claim"])
        self.assertEqual(context.close_receipt["state"], "CLOSED")
        with self.assertRaises(SkillActivationDenied):
            context.read_text()

    def test_changes_symlinks_traversal_and_foreign_task_denied(self):
        base = self.args()
        (self.root / self.path).write_bytes(self.content + b"TAMPERED")
        with self.assertRaisesRegex(SkillActivationDenied, "DIGEST"):
            with activate_admitted_skill(**base):
                pass
        target = self.root / self.path
        target.unlink()
        target.symlink_to(self.root / "other")
        with self.assertRaises(SkillActivationDenied):
            with activate_admitted_skill(**base):
                pass
        target.unlink()
        target.write_bytes(self.content)
        with self.assertRaises(SkillActivationDenied):
            with activate_admitted_skill(**(base | {"task_id": "foreign"})):
                pass
        for path in ("../escape", "skills/../escape", "skills//escape", "/absolute", r"skills\escape"):
            with self.subTest(path=path):
                with self.assertRaises(SkillActivationDenied):
                    read_snapshot_file(self.root, path)

    def test_no_receipt_self_attestation_or_lease_expiry_bypass(self):
        base = self.args()
        for changes in (
            {"verify_admission": lambda r: False},
            {"verify_selection": lambda r: False},
            {"verify_lease": lambda r: False},
            {"count_tokens": lambda s: 999999},
            {"now_epoch": 2000000000},
            {"admission_receipt": dict(self.admission)},
            {"selection_receipt": dict(self.selection)},
        ):
            with self.subTest(change=list(changes)):
                with self.assertRaises(SkillActivationDenied):
                    with activate_admitted_skill(**(base | changes)):
                        pass

    def test_malformed_selection_members_fail_closed(self):
        base = self.args()
        for members in (["example", {"not": "hashable"}], [{"id": "example"}], [None]):
            corrupted = dict(self.selection)
            corrupted["selected_skill_ids"] = members
            with self.subTest(members=repr(members)):
                with self.assertRaises(SkillActivationDenied):
                    with activate_admitted_skill(
                        **(base | {
                            "selection_receipt": corrupted,
                            "verify_selection": lambda r: r is corrupted,
                        })
                    ):
                        pass

    def test_snapshot_single_file_and_no_hidden_dependencies(self):
        package = copy.deepcopy(self.package)
        package["files"].append("scripts/evil.sh")
        with self.assertRaisesRegex(SkillActivationDenied, "WHOLE_MANIFEST"):
            with activate_admitted_skill(**(self.args() | {"package": package})):
                pass

    def test_reference_regressions(self):
        result = reference_regressions()
        self.assertEqual(result["result"], "PASS", result["cases"])
        self.assertFalse(result["current_host_production_claim"])


if __name__ == "__main__":
    unittest.main()
