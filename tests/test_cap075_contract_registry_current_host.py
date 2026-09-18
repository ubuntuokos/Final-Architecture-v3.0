import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cap075_contract_registry_current_host import (
    ROLLBACK_TARGET,
    run_mode,
    validate_contract_files,
)


class Cap075ContractRegistryCurrentHostTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical").mkdir(parents=True)
        shutil.copytree(ROOT / "canonical/contracts", root / "canonical/contracts")
        scope = root / ".fa3-current-host/qualification-source-artifacts/test"
        scope.mkdir(parents=True)
        return td, root, scope

    def test_positive_validates_canonical_contract_registry(self):
        td, root, scope = self._root()
        try:
            result = run_mode(root, scope, "positive")
            self.assertEqual(result["status"], "PASS")
            self.assertGreater(result["contract_file_count"], 0)
            self.assertEqual(result["contract_file_count"], result["unique_identity_count"])
            self.assertTrue(result["event_schema_present"])
        finally:
            td.cleanup()

    def test_negative_duplicate_identity_is_rejected(self):
        td, root, scope = self._root()
        try:
            result = run_mode(root, scope, "negative")
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["rejection_observed"])
            self.assertTrue(any("duplicate contract identity" in x for x in result["rejection_findings"]))
        finally:
            td.cleanup()

    def test_rollback_restores_exact_valid_bytes(self):
        td, root, scope = self._root()
        try:
            result = run_mode(root, scope, "rollback")
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["mutation_rejected"])
            self.assertTrue(result["rollback_hash_equal"])
            self.assertTrue(result["restored_contract_valid"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])
            self.assertTrue((root / ROLLBACK_TARGET).is_file())
        finally:
            td.cleanup()

    def test_validator_rejects_missing_identity(self):
        td, root, scope = self._root()
        try:
            bad = scope / "bad.json"
            bad.write_text('{"schema":"fa3.test.v1"}\n', encoding="utf-8")
            findings = validate_contract_files([bad])
            self.assertTrue(any("contract identity missing" in item for item in findings))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
