import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_model_inventory_current_host_adapter import (
    EVIDENCE_LEVEL,
    PROVIDER_IDS,
    STABILITY_MATRIX_PROVIDER_ID,
    canonical_json_sha256,
    detect_stability_matrix_library,
    regression_check,
    scan_model_tree,
)
from fa3_model_inventory_current_host_gate import reference_check


class ModelInventoryCurrentHostAdapterTests(unittest.TestCase):
    def test_regression_passes(self):
        report = regression_check()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(report["passed"], report["total"])

    def test_stability_matrix_scan_is_read_only_and_hashes_real_file(self):
        with tempfile.TemporaryDirectory() as td:
            library = Path(td) / "StabilityMatrix"
            models = library / "Models" / "StableDiffusion"
            models.mkdir(parents=True)
            model = models / "tiny.safetensors"
            model.write_bytes(b"FA3-STABILITY-MATRIX-TEST-MODEL")
            before = model.read_bytes()
            scan = scan_model_tree(library / "Models")
            after = model.read_bytes()
            self.assertEqual(before, after)
            self.assertEqual(1, scan["entry_count"])
            self.assertEqual("StableDiffusion/tiny.safetensors", scan["representative"]["relative_path"])
            self.assertEqual(64, len(scan["representative"]["sha256"]))
            self.assertEqual(64, len(scan["inventory_manifest_sha256"]))

    def test_settings_override_is_honored_without_path_identity(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            library = base / "Library"
            override = base / "SharedModels"
            library.mkdir()
            override.mkdir()
            (library / "settings.json").write_text(json.dumps({"ModelDirectoryOverride": str(override)}), encoding="utf-8")
            with patch("fa3_model_inventory_current_host_adapter.stability_matrix_library_candidates", return_value=[library]):
                got_library, got_models, meta = detect_stability_matrix_library()
            self.assertEqual(library.resolve(), got_library)
            self.assertEqual(override.resolve(), got_models)
            self.assertTrue(meta["override_used"])

    def test_inventory_digest_is_key_order_stable(self):
        self.assertEqual(
            canonical_json_sha256({"a": 1, "b": 2}),
            canonical_json_sha256({"b": 2, "a": 1}),
        )

    def test_provider_set_includes_stability_matrix(self):
        self.assertIn(STABILITY_MATRIX_PROVIDER_ID, PROVIDER_IDS)
        self.assertEqual(4, len(PROVIDER_IDS))
        self.assertIn("READ_ONLY", EVIDENCE_LEVEL)

    def test_reference_contract_is_materialized(self):
        report = reference_check(ROOT)
        self.assertEqual("PASS", report["result"], report)


if __name__ == "__main__":
    unittest.main()
