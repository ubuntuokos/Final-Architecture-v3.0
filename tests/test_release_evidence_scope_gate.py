from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_release_evidence_scope_gate import BASELINE_ID, PATHS, SCOPE_ID, gate
from fa3_release_baseline import load_active_release_baseline


class ReleaseEvidenceScopeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]

    def make_fixture(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="fa3-release-evidence-scope-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in PATHS.values():
            src = self.repo_root / rel
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return tmp

    def mutate_json(self, root: Path, key: str, fn) -> None:
        path = root / PATHS[key]
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_repository_materialization_passes(self) -> None:
        result = gate(self.repo_root)
        self.assertEqual(result["result"], "PASS", result)
        self.assertEqual(result["checks_passed"], 18)
        self.assertEqual(result["active_release_capability_count"], load_active_release_baseline(self.repo_root).capability_count)
        self.assertEqual(result["authority_delta"], 0)
        baseline = json.loads((self.repo_root / PATHS["baseline"]).read_text(encoding="utf-8"))
        self.assertEqual(result["capability_delta"], baseline["capability_delta"])

    def test_capability_count_cannot_be_reclassified_as_timeless(self) -> None:
        root = self.make_fixture()

        def mutate(baseline: dict) -> None:
            baseline["interpretation"]["capability_count_is_not_timeless_global_constant"] = False

        self.mutate_json(root, "baseline", mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-004", {f["code"] for f in result["findings"]})

    def test_current_release_count_mismatch_fails_closed(self) -> None:
        root = self.make_fixture()
        self.mutate_json(root, "baseline", lambda b: b.__setitem__("current_release_capability_count", 144))
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        codes = {f["code"] for f in result["findings"]}
        self.assertTrue({"RESCOPE-003", "RESCOPE-005", "RESCOPE-006", "RESCOPE-007"} & codes)

    def test_negative_assurance_cannot_promote_runtime(self) -> None:
        root = self.make_fixture()

        def mutate(scope: dict) -> None:
            scope["evidence_classes"]["NEGATIVE_HOST_ASSURANCE"]["may_prove_positive_runtime"] = True

        self.mutate_json(root, "scope", mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-011", {f["code"] for f in result["findings"]})

    def test_enabled_runtime_cannot_use_negative_assurance(self) -> None:
        root = self.make_fixture()

        def mutate(scope: dict) -> None:
            for rule in scope["scope_rules"]:
                if rule["id"] == "EVID-SCOPE-ENABLED-OR-ACTIVE":
                    rule["required_evidence"] = "NEGATIVE_HOST_ASSURANCE"

        self.mutate_json(root, "scope", mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-013", {f["code"] for f in result["findings"]})

    def test_production_promotion_always_requires_positive_current_host(self) -> None:
        root = self.make_fixture()

        def mutate(scope: dict) -> None:
            scope["observation_model"]["PRODUCTION_PROMOTED"]["positive_current_host_required"] = False

        self.mutate_json(root, "scope", mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-010", {f["code"] for f in result["findings"]})

    def test_missing_negative_assurance_check_fails_closed(self) -> None:
        root = self.make_fixture()

        def mutate(scope: dict) -> None:
            scope["negative_assurance"]["required_checks"].remove("NO_UNEXPECTED_NETWORK_EGRESS")

        self.mutate_json(root, "scope", mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-012", {f["code"] for f in result["findings"]})

    def test_policy_records_do_not_become_capabilities(self) -> None:
        root = self.make_fixture()

        def mutate(registry: dict) -> None:
            registry["records"][0]["subject_id"] = BASELINE_ID

        self.mutate_json(root, "registry", mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-008", {f["code"] for f in result["findings"]})

        root = self.make_fixture()

        def mutate_scope(registry: dict) -> None:
            registry["records"][0]["subject_id"] = SCOPE_ID

        self.mutate_json(root, "registry", mutate_scope)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("RESCOPE-008", {f["code"] for f in result["findings"]})

    def test_missing_authoritative_input_fails_closed(self) -> None:
        root = self.make_fixture()
        (root / PATHS["registry"]).unlink()
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["findings"][0]["code"], "RESCOPE-000")


if __name__ == "__main__":
    unittest.main()
