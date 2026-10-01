from __future__ import annotations
import json, shutil, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_donor_derived_shared_fabrics import validate

FILES=[
"canonical/FA3-DONOR-DERIVED-SHARED-FABRICS-001.json",
"canonical/assessments/FA3-DONOR-DERIVED-SHARED-FABRICS-REUSE-ASSESSMENT-001.json",
"canonical/decisions/FA3-DEC-DONOR-DERIVED-SHARED-FABRICS-2026-10-01.json",
"canonical/intents/FA3-DONOR-DERIVED-SHARED-FABRICS-APPLICATION-INTENT-001.json",
"canonical/FA3-DONOR-DERIVED-SHARED-FABRICS-CURRENT-HOST-IMPACT-001.json",
"canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json",
"canonical/providers/FA3-PROVIDER-OPENHANDS-001.json",
"canonical/references/FA3-OPENHANDS-UPSTREAM-REFERENCE-2026-09-01.json",
]
COMPONENTS=[
"FA3-SHARED-AGENT-OPERATIONS-COMPOSITION-001",
"FA3-SHARED-RESOURCE-APPLICATION-COMPOSITION-001",
"FA3-SHARED-RETRIEVAL-QUALITY-COMPOSITION-001",
"FA3-SHARED-NETWORK-TRANSPORT-COMPOSITION-001",
"FA3-SHARED-CREATIVE-PRODUCTION-COMPOSITION-001",
]
def fixture(dst:Path):
    for rel in FILES:
        p=dst/rel; p.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/rel,p)
    for cid in COMPONENTS:
        for base,suffix in (("canonical/profiles",cid),("canonical/contracts",cid.replace("-001","-CONTRACTS-001"))):
            src=ROOT/base/f"{suffix}.json"; p=dst/base/f"{suffix}.json"; p.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,p)

class Tests(unittest.TestCase):
    def test_canonical(self):
        r=validate(ROOT); self.assertEqual(r["validation"]["result"],"PASS",r["validation"]["findings"]); self.assertEqual(r["sources"],13); self.assertEqual(r["components"],5)
    def test_owner_marker_gate(self):
        data=json.loads((ROOT/FILES[0]).read_text()); self.assertEqual(sum(x["registration_status"]=="EXISTING_CANONICAL_REFERENCE" for x in data["sources"]),1)
        self.assertTrue(all(x["registration_status"] in {"OWNER_MARKER_REQUIRED","EXISTING_CANONICAL_REFERENCE"} for x in data["sources"]))
    def test_no_donor_ids_forged(self):
        data=json.loads((ROOT/FILES[0]).read_text()); self.assertTrue(all("donor_id" not in x for x in data["sources"]))
    def test_capability_delta_zero(self):
        data=json.loads((ROOT/FILES[0]).read_text()); self.assertFalse(data["new_capability"]); self.assertEqual(data["capability_baseline"],175)
    def test_self_promotion_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fixture(root); p=root/FILES[0]; d=json.loads(p.read_text()); d["sources"][0]["registration_status"]="ACCEPTED_REFERENCE"; p.write_text(json.dumps(d))
            self.assertIn("SOURCE_STATUS_INVALID",{x["code"] for x in validate(root)["validation"]["findings"]})
    def test_capability_176_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fixture(root); p=root/"canonical/profiles/FA3-SHARED-AGENT-OPERATIONS-COMPOSITION-001.json"; d=json.loads(p.read_text()); d["capability_bindings"].append("CAP-176"); p.write_text(json.dumps(d))
            codes={x["code"] for x in validate(root)["validation"]["findings"]}; self.assertIn("CAPABILITY_BINDING_PARITY",codes); self.assertIn("CAPABILITY_OUT_OF_BASELINE",codes)
    def test_runtime_activation_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fixture(root); p=root/"canonical/profiles/FA3-SHARED-NETWORK-TRANSPORT-COMPOSITION-001.json"; d=json.loads(p.read_text()); d["runtime_materialization"]["new_socket"]=True; p.write_text(json.dumps(d))
            self.assertIn("STATIC_RUNTIME_ACTIVATION",{x["code"] for x in validate(root)["validation"]["findings"]})
if __name__=="__main__": unittest.main()
