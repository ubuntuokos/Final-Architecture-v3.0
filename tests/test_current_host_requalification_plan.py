from __future__ import annotations
import json, shutil, tempfile, unittest
from pathlib import Path
from fa3_current_host_requalification_plan import build_requalification_plan
ROOT=Path(__file__).resolve().parents[1]
POLICY=Path("canonical/FA3-CURRENT-HOST-STRUCTURAL-CHANGE-POLICY-001.json")
DELTA=Path("canonical/FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001.json")
BASE=Path("canonical/FA3-CURRENT-HOST-BASE-STATE-001.json")
MANIFEST=Path("fa3-current-host/manifest.json")
class T(unittest.TestCase):
 def root(self,admitted=False):
  td=tempfile.TemporaryDirectory(); r=Path(td.name); (r/POLICY).parent.mkdir(parents=True,exist_ok=True)
  shutil.copy2(ROOT/POLICY,r/POLICY)
  shutil.copy2(ROOT/DELTA,r/DELTA)
  (r/BASE).write_text(json.dumps({
   "schema":"fa3.current-host-base-state.v1",
   "status":"CURRENT_HOST_BASE_ADMITTED" if admitted else "PENDING_FRESH_EXACT_HEAD_CURRENT_HOST_EXECUTION",
   "capability_count":175,"obligation_count":525,
   "base_release_digest":"a"*64 if admitted else None,
   "effective_host_digest":"a"*64 if admitted else None
  }))
  (r/MANIFEST).parent.mkdir(parents=True,exist_ok=True)
  (r/MANIFEST).write_text(json.dumps({"active_closure":{"status":"PENDING_FRESH_EXACT_HEAD_PHYSICAL_EXECUTION"}}))
  return td,r
 def rec(self,r,**kw):
  rel="canonical/current-host-impact/X.json"; p=r/rel; p.parent.mkdir(parents=True,exist_ok=True)
  row={"schema":"fa3.current-host-structural-impact.v1","physical_requalification_required":True,"historical_evidence_reused":False}; row.update(kw)
  p.write_text(json.dumps(row)); return rel
 def report(self,rel=None,changed=None): return {"result":"PASS","impact_records":[rel] if rel else [],"changed_files":changed or []}
 def test_none(self):
  td,r=self.root()
  try:self.assertEqual("NONE",build_requalification_plan(r,self.report(),projection_valid=True,main_in_lineage=True)["mode"])
  finally:td.cleanup()
 def test_no_base_escalates_to_full(self):
  td,r=self.root(False)
  try:
   rel=self.rec(r,affected_capability_ids=["CAP-013"]); x=build_requalification_plan(r,self.report(rel),projection_valid=True,main_in_lineage=True)
   self.assertEqual("FULL",x["mode"]); self.assertTrue(x["execution_ready"])
  finally:td.cleanup()
 def test_admitted_base_scopes(self):
  td,r=self.root(True)
  try:
   rel=self.rec(r,affected_capability_ids=["CAP-083","CAP-013"]); x=build_requalification_plan(r,self.report(rel),projection_valid=True,main_in_lineage=True)
   self.assertEqual("SCOPED",x["mode"]); self.assertEqual(["CAP-013","CAP-083","CAP-175"],x["affected_capability_ids"])
  finally:td.cleanup()
 def test_explicit_full(self):
  td,r=self.root(True)
  try:
   rel=self.rec(r,physical_requalification_scope="ACTIVE_175_CAPABILITIES_525_OBLIGATIONS")
   self.assertEqual("FULL",build_requalification_plan(r,self.report(rel),projection_valid=True,main_in_lineage=True)["mode"])
  finally:td.cleanup()
 def test_projection_barrier(self):
  td,r=self.root(False)
  try:
   rel=self.rec(r,physical_requalification_scope="FULL-525"); x=build_requalification_plan(r,self.report(rel),projection_valid=False,main_in_lineage=True)
   self.assertFalse(x["execution_ready"])
  finally:td.cleanup()
 def test_underdeclared_scoped_fails(self):
  td,r=self.root(True)
  try:
   rel=self.rec(r); x=build_requalification_plan(r,self.report(rel),projection_valid=True,main_in_lineage=True)
   self.assertEqual("BLOCKED",x["mode"]); self.assertEqual("FAIL",x["result"])
  finally:td.cleanup()
if __name__=="__main__": unittest.main()
