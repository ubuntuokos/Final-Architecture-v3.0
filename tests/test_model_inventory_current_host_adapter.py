import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_inventory_current_host_adapter import (
    CANONICAL_STORE_ID,EVIDENCE_LEVEL,PROVIDER_IDS,canonical_json_sha256,
    detect_canonical_store,regression_check,scan_model_tree,
)
from fa3_model_inventory_current_host_gate import reference_check

class ModelInventoryCurrentHostAdapterTests(unittest.TestCase):
    def test_regression_passes(self):
        report=regression_check(); self.assertEqual("PASS",report["result"],report); self.assertEqual(report["passed"],report["total"])

    def test_canonical_store_scan_is_read_only_and_hashes_real_file(self):
        with tempfile.TemporaryDirectory() as td:
            models=Path(td)/"models"/"image"; models.mkdir(parents=True)
            model=models/"tiny.safetensors"; model.write_bytes(b"FA3-CANONICAL-STORE-TEST-MODEL")
            before=model.read_bytes(); scan=scan_model_tree(Path(td)/"models"); after=model.read_bytes()
            self.assertEqual(before,after); self.assertEqual(1,scan["entry_count"])
            self.assertEqual("image/tiny.safetensors",scan["representative"]["relative_path"])
            self.assertEqual(64,len(scan["representative"]["sha256"])); self.assertEqual(64,len(scan["inventory_manifest_sha256"]))

    def test_configured_canonical_store_is_detected_without_path_identity(self):
        with tempfile.TemporaryDirectory() as td:
            store=Path(td)/"canonical-models"; store.mkdir()
            with patch("fa3_model_inventory_current_host_adapter.canonical_store_candidates",return_value=[store]):
                got,meta=detect_canonical_store()
            self.assertEqual(store.resolve(),got); self.assertEqual("FA3_CONFIG_OR_XDG_CANONICAL_STORE",meta["source"])

    def test_inventory_digest_is_key_order_stable(self):
        self.assertEqual(canonical_json_sha256({"a":1,"b":2}),canonical_json_sha256({"b":2,"a":1}))

    def test_canonical_store_is_separate_from_provider_set(self):
        self.assertNotIn(CANONICAL_STORE_ID,PROVIDER_IDS); self.assertEqual(3,len(PROVIDER_IDS)); self.assertIn("READ_ONLY",EVIDENCE_LEVEL)

    def test_reference_contract_is_materialized(self):
        report=reference_check(ROOT); self.assertEqual("PASS",report["result"],report)

if __name__=="__main__": unittest.main()
