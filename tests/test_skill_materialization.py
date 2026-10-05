import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_skill_fabric_gate import good_package, good_use_receipt
from fa3_skill_materialization import (
    SkillSnapshotDenied, snapshot_digests, task_activation_lease,
    verified_use_receipt, verify_admitted_snapshot,
)


class MaterializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        target = self.root / "skills/example/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"---\nname: example\n---\nOnly task-scoped advice.\n")
        self.package = good_package()
        observed = snapshot_digests(self.root, ["skills/example/SKILL.md"])
        self.package["digests"]["content_sha256"] = observed["files"][0]["sha256"]
        self.package["digests"]["manifest_sha256"] = observed["manifest_sha256"]
        self.package["hash_attestation"]["sha256"] = observed["files"][0]["sha256"]
        self.package["evaluation"]["bound_content_sha256"] = observed["files"][0]["sha256"]
        self.registry = {
            "skill_id": "example", "package_id": self.package["package_id"],
            "version": "1.0.0", "entrypoint": "skills/example/SKILL.md",
            "admission_status": "ADMITTED", "eligibility": {"task_classes": ["task.example"]},
        }
        self.admission = {
            "receipt_ref": "skill-admit:real:1", "result": "PASS",
            "package_id": self.package["package_id"],
            "content_sha256": observed["files"][0]["sha256"],
            "manifest_sha256": observed["manifest_sha256"],
            "dependency_digest_sha256": self.package["dependencies"]["digest_sha256"],
        }
        self.selection = {
            "receipt_ref": "skill-select:real:1", "package_id": self.package["package_id"],
            "skill_id": "example", "task_scope": "task.example",
            "eligible_skill_ids": ["example"],
        }
        self.intent = {k: good_use_receipt()[k] for k in (
            "tool_intent", "model_intent", "resource_intent", "secret_intent"
        )}

    def verified(self):
        return verify_admitted_snapshot(self.root, self.package, self.registry,
                                        self.admission, self.selection, "task.example")

    def test_positive_real_bytes_and_non_authority(self):
        result = self.verified()
        self.assertEqual(result["result"], "PASS")
        self.assertFalse(result["authority"])
        lease = task_activation_lease(result)
        receipt = verified_use_receipt(self.root, self.package, self.registry,
                                       self.admission, self.selection, lease, self.intent)
        self.assertEqual(receipt["snapshot_verification"]["result"], "PASS")
        self.assertFalse(lease["grants_execution_authority"])

    def test_tamper_after_activation_denied_on_use(self):
        lease = task_activation_lease(self.verified())
        (self.root / "skills/example/SKILL.md").write_bytes(b"modified after activation")
        with self.assertRaises(SkillSnapshotDenied):
            verified_use_receipt(self.root, self.package, self.registry, self.admission,
                                 self.selection, lease, self.intent)

    def test_fake_admission_and_selection_denied(self):
        changed = dict(self.admission, content_sha256="f" * 64)
        with self.assertRaises(SkillSnapshotDenied):
            verify_admitted_snapshot(self.root, self.package, self.registry, changed,
                                     self.selection, "task.example")
        changed = dict(self.selection, eligible_skill_ids=[])
        with self.assertRaises(SkillSnapshotDenied):
            verify_admitted_snapshot(self.root, self.package, self.registry, self.admission,
                                     changed, "task.example")

    def test_entrypoint_and_scope_denied(self):
        entry = copy.deepcopy(self.registry)
        entry["entrypoint"] = "skills/example/other.md"
        with self.assertRaises(SkillSnapshotDenied):
            verify_admitted_snapshot(self.root, self.package, entry, self.admission,
                                     self.selection, "task.example")
        with self.assertRaises(SkillSnapshotDenied):
            verify_admitted_snapshot(self.root, self.package, self.registry, self.admission,
                                     self.selection, "task.other")

    def test_symlink_and_escape_denied(self):
        target = self.root / "skills/example/SKILL.md"
        target.unlink()
        outside = self.root / "outside.md"
        outside.write_bytes(b"unsafe")
        target.symlink_to(outside)
        with self.assertRaises(SkillSnapshotDenied):
            self.verified()
        for path in ("../outside.md", "/etc/passwd", "skills//example/SKILL.md",
                     "skills/./example/SKILL.md", "skills\\example\\SKILL.md"):
            with self.subTest(path=path), self.assertRaises(SkillSnapshotDenied):
                snapshot_digests(self.root, [path])

    def test_expiry_and_permission_denied(self):
        now = datetime(2026, 9, 28, tzinfo=timezone.utc)
        lease = task_activation_lease(self.verified(), now=now, ttl_seconds=1)
        with self.assertRaises(SkillSnapshotDenied):
            verified_use_receipt(self.root, self.package, self.registry, self.admission,
                                 self.selection, lease, self.intent, now=now + timedelta(seconds=2))
        lease = task_activation_lease(self.verified(), now=now)
        intent = copy.deepcopy(self.intent)
        intent["tool_intent"]["via_central_mcp"] = False
        with self.assertRaises(SkillSnapshotDenied):
            verified_use_receipt(self.root, self.package, self.registry, self.admission,
                                 self.selection, lease, intent, now=now)

    def test_manifest_is_order_independent_and_duplicate_denied(self):
        second = self.root / "skills/example/readme.md"
        second.write_bytes(b"extra")
        a = snapshot_digests(self.root, ["skills/example/readme.md", "skills/example/SKILL.md"])
        b = snapshot_digests(self.root, ["skills/example/SKILL.md", "skills/example/readme.md"])
        self.assertEqual(a["manifest_sha256"], b["manifest_sha256"])
        with self.assertRaises(SkillSnapshotDenied):
            snapshot_digests(self.root, ["skills/example/SKILL.md"] * 2)

    def test_instance_bound_activation_denies_wrong_task(self):
        now = datetime.now(timezone.utc)
        lease = task_activation_lease(self.verified(), task_id="TASK-A", now=now)
        self.assertEqual(lease["task_id"], "TASK-A")
        verified_use_receipt(self.root, self.package, self.registry, self.admission,
                             self.selection, lease, self.intent, task_id="TASK-A", now=now)
        with self.assertRaises(SkillSnapshotDenied):
            verified_use_receipt(self.root, self.package, self.registry, self.admission,
                                 self.selection, lease, self.intent, task_id="TASK-B", now=now)
        with self.assertRaises(SkillSnapshotDenied):
            task_activation_lease(self.verified(), task_id="../other", now=now)


if __name__ == "__main__":
    unittest.main()
