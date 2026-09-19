import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_mat001_foundation_current_host import (
    CAPABILITIES,
    expected_source_decisions,
    validate_bind_target,
    validate_exact_coverage,
    validate_provider_route,
    validate_secret_mode,
)


class Mat001FoundationCurrentHostTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        records = []
        for cap in CAPABILITIES:
            records.append({
                "subject_id": cap,
                "source_decision_ids": [f"DEC-{cap}", "FA3-CORE-001"],
            })
        (root / "evidence/evidence-registry.json").write_text(
            json.dumps({"records": records}) + "\n", encoding="utf-8"
        )
        return td, root

    def test_exact_coverage_is_ordered_and_fail_closed(self):
        td, root = self._root()
        try:
            expected = expected_source_decisions(root, "CAP-001")
            self.assertEqual(expected, ["DEC-CAP-001", "FA3-CORE-001"])
            self.assertEqual(validate_exact_coverage(root, "CAP-001", expected), expected)
            with self.assertRaises(RuntimeError):
                validate_exact_coverage(root, "CAP-001", list(reversed(expected)))
        finally:
            td.cleanup()

    def test_network_policy_is_loopback_only(self):
        self.assertTrue(validate_bind_target("127.0.0.1"))
        self.assertTrue(validate_bind_target("::1"))
        self.assertFalse(validate_bind_target("0.0.0.0"))
        self.assertFalse(validate_bind_target("::"))
        self.assertFalse(validate_bind_target("192.0.2.1"))

    def test_secret_mode_rejects_group_or_world_access(self):
        self.assertTrue(validate_secret_mode(stat.S_IFREG | 0o600))
        self.assertTrue(validate_secret_mode(stat.S_IFREG | 0o400))
        self.assertFalse(validate_secret_mode(stat.S_IFREG | 0o640))
        self.assertFalse(validate_secret_mode(stat.S_IFREG | 0o604))

    def test_model_route_requires_registered_local_provider(self):
        allowed = {"FA3-PROVIDER-LOCAL-001"}
        self.assertTrue(validate_provider_route({
            "provider_id": "FA3-PROVIDER-LOCAL-001",
            "backend": "local",
            "local_only": True,
        }, allowed))
        self.assertFalse(validate_provider_route({
            "provider_id": "FA3-PROVIDER-UNKNOWN",
            "backend": "local",
            "local_only": True,
        }, allowed))
        self.assertFalse(validate_provider_route({
            "provider_id": "FA3-PROVIDER-LOCAL-001",
            "backend": "remote",
            "local_only": False,
        }, allowed))

    def test_mat001_capability_set_is_exact_first_batch(self):
        self.assertEqual(CAPABILITIES, ("CAP-001", "CAP-002", "CAP-003", "CAP-004", "CAP-005"))


if __name__ == "__main__":
    unittest.main()
