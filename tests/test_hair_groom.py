from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_hair_groom_gate import PATHS, gate

def fixture(root: Path) -> None:
    for rel in PATHS.values():
        target=root/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/rel,target)

class HairGroomGateTests(unittest.TestCase):
    def test_canonical_static_materialization_passes(self):
        report=gate(ROOT)
        self.assertEqual(report["result"],"PASS",report["findings"])
        self.assertEqual(report["capability_baseline"],175)
        self.assertFalse(report["current_host_runtime_promotion_claim"])

    def test_capability_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            path=root/PATHS["profile"]
            row=json.loads(path.read_text())
            row["capability_bindings"].append("CAP-176")
            path.write_text(json.dumps(row))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-003",codes)

    def test_runtime_activation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            path=root/PATHS["profile"]
            row=json.loads(path.read_text())
            row["runtime_materialization"]["provider_activation"]=True
            path.write_text(json.dumps(row))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-009",codes)

    def test_intent_and_enforcement_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            intent_path=root/PATHS["intent"]
            intent=json.loads(intent_path.read_text())
            intent["declared_new_capabilities"]=["CAP-176"]
            intent_path.write_text(json.dumps(intent))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-006A",codes)

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            enforcement_path=root/PATHS["enforcement"]
            enforcement=json.loads(enforcement_path.read_text())
            enforcement["fail_closed"]=False
            enforcement["p0_invariants"]=[]
            enforcement_path.write_text(json.dumps(enforcement))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-006B",codes)

    def test_current_host_impact_runtime_flags_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            path=root/PATHS["impact"]
            row=json.loads(path.read_text())
            row["runtime_change"]=True
            row["provider_or_model_activation"]=True
            row["hardware_mutation"]=True
            path.write_text(json.dumps(row))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-020",codes)

    def test_manual_application_capability_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            path=root/PATHS["apps"]
            row=json.loads(path.read_text())
            hair=next(x for x in row["shared_capabilities"] if x["id"]=="FA3-SHARED-HAIR-GROOM-001")
            hair["fa3_bindings"]["capability_ids"]=["CAP-016"]
            path.write_text(json.dumps(row))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-014",codes)

    def test_pending_donor_consumption_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); fixture(root)
            path=root/PATHS["assessment"]
            row=json.loads(path.read_text())
            row["pending_or_unmerged_donors_consumed"]=True
            path.write_text(json.dumps(row))
            codes={x["code"] for x in gate(root)["findings"]}
            self.assertIn("HAIR-017",codes)

if __name__=="__main__":
    unittest.main()
