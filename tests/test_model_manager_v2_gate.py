import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_manager_v2_gate import (
    GATE_ID, PROVIDER_IDS, REGISTRY_ID, RULES,
    gate, reference_check, run_regressions, scan_authority_assignments,
)

class ModelManagerV2GateTests(unittest.TestCase):
    def _copy_root(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        for name in ("canonical","evidence"):
            shutil.copytree(ROOT/name,root/name)
        for rel in (
            "src/fa3_model_manager_provider_adapter.py",
            "src/fa3_model_manager_current_host_gate.py",
            "evidence/collect-model-manager-current-host.py",
            "bin/fa3-model-manager-current-host.sh",
            ".github/workflows/fa3-model-manager-current-host.yml",
        ):
            src=ROOT/rel
            dst=root/rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)
        return td,root

    def _write(self,path,obj):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")

    def test_v2_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual("PASS",report["result"],report)
        self.assertEqual(GATE_ID,report["gate_id"])
        self.assertEqual(REGISTRY_ID,report["model_registry_id"])
        self.assertEqual(PROVIDER_IDS,report["provider_ids"])
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_exact_extended_regressions_pass(self):
        report=run_regressions()
        self.assertEqual("PASS",report["result"])
        self.assertEqual(15,report["passed"])
        self.assertEqual(15,report["total"])
        self.assertEqual(RULES,[x["invariant"] for x in report["cases"]])

    def test_floating_latest_blocks_reference(self):
        td,root=self._copy_root()
        try:
            p=root/"canonical/providers/FA3-PROVIDER-HF-MODEL-STORE-001.json"
            obj=json.loads(p.read_text(encoding="utf-8"))
            obj["upstream_release_commit"]="latest"
            self._write(p,obj)
            report=reference_check(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="MODEL-MGR-V2-REF-013" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_provider_cannot_become_authority(self):
        td,root=self._copy_root()
        try:
            self._write(root/"canonical/model-manager-v2-authority-mutation.json",{
                "id":"TEST-MUTATION",
                "model_routing_authority":"FA3-PROVIDER-OLLAMA-MODEL-001"
            })
            report=scan_authority_assignments(root)
            self.assertEqual("FAIL",report["result"])
            self.assertTrue(any(x["code"]=="MODEL-MGR-V2-AUTH-001" for x in report["findings"]))
        finally:
            td.cleanup()

if __name__=="__main__":
    unittest.main()
