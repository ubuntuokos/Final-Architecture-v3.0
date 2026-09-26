import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_cap074_service_catalog_current_host import (
    CATALOG_PATH,
    _run_negative,
    _run_positive,
    _run_rollback,
    validate_catalog,
)


class Cap074ServiceCatalogCurrentHostTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        source = ROOT / CATALOG_PATH
        target = root / CATALOG_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)

        for rel in [
            "deployment/mcp-gateway/fa3-mcp-gateway-user.service.in",
            "deployment/mcp-gateway/fa3-mcp-gateway.service",
            "deployment/presenton/presenton.container",
            "deployment/sillytavern-kde/systemd/user/sillytavern-kde.service",
            "deployment/step-ca/fa3-step-ca.service",
            "canonical/mcp-capability-registry.json",
        ]:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, dst)

        scope = root / ".fa3-current-host/qualification-source-artifacts/cap074"
        scope.mkdir(parents=True)
        return td, root, scope

    def test_positive_validates_real_service_dependency_graph(self):
        result = _run_positive(ROOT, ROOT / ".fa3-current-host/test-fixtures/cap074-positive")
        self.assertEqual(result["status"], "PASS")
        self.assertGreaterEqual(result["service_count"], 5)
        self.assertGreater(result["resource_count"], 0)
        self.assertGreater(result["edge_count"], 0)
        self.assertTrue(result["source_bound_edges"])
        self.assertTrue(result["service_cycle_free"])

    def test_dangling_dependency_is_rejected(self):
        catalog = json.loads((ROOT / CATALOG_PATH).read_text(encoding="utf-8"))
        bad = copy.deepcopy(catalog)
        bad["edges"][0]["target"] = "res:not-present"
        findings = validate_catalog(ROOT, bad)
        self.assertTrue(any("dangling dependency target" in item for item in findings))

    def test_service_cycle_is_rejected(self):
        catalog = json.loads((ROOT / CATALOG_PATH).read_text(encoding="utf-8"))
        bad = copy.deepcopy(catalog)
        first = bad["services"][0]
        second = bad["services"][1]
        token_first = (ROOT / first["source_path"]).read_text(encoding="utf-8").splitlines()[0]
        token_second = (ROOT / second["source_path"]).read_text(encoding="utf-8").splitlines()[0]
        bad["edges"].append({"source": first["id"], "target": second["id"], "relation": "TEST_DEPENDS_ON", "evidence_token": token_first})
        bad["edges"].append({"source": second["id"], "target": first["id"], "relation": "TEST_DEPENDS_ON", "evidence_token": token_second})
        findings = validate_catalog(ROOT, bad)
        self.assertTrue(any("service dependency cycle detected" in item for item in findings))

    def test_negative_drill_rejects_dangling_and_cycle(self):
        td, root, scope = self._root()
        try:
            result = _run_negative(root, scope)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["dangling_dependency_rejected"])
            self.assertTrue(result["service_cycle_rejected"])
        finally:
            td.cleanup()

    def test_rollback_restores_exact_catalog_bytes(self):
        td, root, scope = self._root()
        try:
            result = _run_rollback(root, scope)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["fault_detected"])
            self.assertTrue(result["rollback_hash_equal"])
            self.assertTrue(result["restored_catalog_valid"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
