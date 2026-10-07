import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cap054_external_asset_inventory_current_host import (
    LOCK_REGISTRY,
    _run_negative,
    _run_positive,
    _run_rollback,
    validate_inventory,
)


class Cap054ExternalAssetInventoryCurrentHostTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        target = root / LOCK_REGISTRY
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / LOCK_REGISTRY, target)
        scope = root / ".fa3-current-host/qualification-source-artifacts/cap054"
        scope.mkdir(parents=True)
        return td, root, scope

    def test_positive_validates_real_canonical_lock_inventory(self):
        scope = ROOT / ".fa3-current-host/test-fixtures/cap054-positive"
        result = _run_positive(ROOT, scope)
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(result["lock_count"], 0)
        self.assertEqual(result["lock_count"], result["provider_count"])
        self.assertTrue(result["immutable_identity_required"])
        self.assertFalse(result["floating_runtime_refs_allowed"])

    def test_validator_rejects_floating_and_duplicate_identity(self):
        baseline = json.loads((ROOT / LOCK_REGISTRY).read_text(encoding="utf-8"))
        keys = sorted(baseline["locks"])

        duplicate = json.loads(json.dumps(baseline))
        duplicate["locks"][keys[1]]["provider_id"] = duplicate["locks"][keys[0]]["provider_id"]
        findings = validate_inventory(duplicate)
        self.assertTrue(any("duplicate provider_id" in item for item in findings))

        floating = json.loads(json.dumps(baseline))
        floating["locks"][keys[0]]["revision"] = "main"
        findings = validate_inventory(floating)
        self.assertTrue(any("floating revision forbidden" in item for item in findings))

    def test_negative_drill_rejects_both_fault_classes(self):
        td, root, scope = self._root()
        try:
            result = _run_negative(root, scope)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["duplicate_provider_rejected"])
            self.assertTrue(result["floating_revision_rejected"])
        finally:
            td.cleanup()

    def test_rollback_restores_exact_inventory_bytes(self):
        td, root, scope = self._root()
        try:
            result = _run_rollback(root, scope)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["fault_detected"])
            self.assertTrue(result["rollback_hash_equal"])
            self.assertTrue(result["restored_inventory_valid"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
