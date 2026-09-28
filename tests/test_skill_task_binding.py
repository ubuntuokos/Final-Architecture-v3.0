import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_developer_agent_coordination import AgentTask, CoordinationDenied
from fa3_skill_fabric_gate import good_package, good_use_receipt
from fa3_skill_materialization import snapshot_digests, task_activation_lease, verify_admitted_snapshot
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
                                    task_activation_lease(verified), intent)
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


if __name__ == "__main__":
    unittest.main()
