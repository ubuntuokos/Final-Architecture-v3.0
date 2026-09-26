from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_governance_tiering_gate import PATHS, PROJECTION_ID, gate
from fa3_release_baseline import load_active_release_baseline


class GovernanceTieringGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]

    def make_fixture(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="fa3-governance-tiering-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel in PATHS.values():
            src = self.repo_root / rel
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return tmp

    def mutate_projection(self, root: Path, fn) -> None:
        path = root / PATHS["projection"]
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_repository_projection_passes(self) -> None:
        result = gate(self.repo_root)
        self.assertEqual(result["result"], "PASS", result)
        self.assertEqual(result["checks_passed"], 16)
        self.assertEqual(result["authority_delta"], 0)
        projection = json.loads((self.repo_root / PATHS["projection"]).read_text(encoding="utf-8"))
        self.assertEqual(result["capability_delta"], projection["capability_delta"])
        self.assertEqual(result["canonical_capability_count"], load_active_release_baseline(self.repo_root).capability_count)

    def test_projection_cannot_gain_authority(self) -> None:
        root = self.make_fixture()
        self.mutate_projection(root, lambda p: p.__setitem__("authority_delta", 1))
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("GOVT-002", {f["code"] for f in result["findings"]})

    def test_projection_cannot_add_capability(self) -> None:
        root = self.make_fixture()
        self.mutate_projection(root, lambda p: p.__setitem__("capability_delta", 1))
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("GOVT-002", {f["code"] for f in result["findings"]})

    def test_assurance_cannot_collapse_into_production(self) -> None:
        root = self.make_fixture()

        def mutate(projection: dict) -> None:
            projection["derivation_rules"]["staging_with_not_promoted_is_valid"] = False

        self.mutate_projection(root, mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("GOVT-011", {f["code"] for f in result["findings"]})

    def test_unknown_state_must_fail_closed(self) -> None:
        root = self.make_fixture()

        def mutate(projection: dict) -> None:
            projection["derivation_rules"]["missing_or_ambiguous_authoritative_state"] = "PROMOTED"

        self.mutate_projection(root, mutate)
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("GOVT-012", {f["code"] for f in result["findings"]})

    def test_projection_must_not_register_as_capability(self) -> None:
        root = self.make_fixture()
        registry_path = root / PATHS["registry"]
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["records"][0]["subject_id"] = PROJECTION_ID
        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("GOVT-015", {f["code"] for f in result["findings"]})

    def test_missing_authoritative_source_fails_closed(self) -> None:
        root = self.make_fixture()
        (root / PATHS["policy"]).unlink()
        result = gate(root)
        self.assertEqual(result["result"], "FAIL")
        self.assertTrue(result["findings"])
        self.assertEqual(result["findings"][0]["code"], "GOVT-000")


if __name__ == "__main__":
    unittest.main()
