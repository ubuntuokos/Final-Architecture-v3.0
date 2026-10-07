from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from unittest import mock
import fa3_dev_mode,fa3_dev_update_gate,fa3_update_fabric
from fa3_uaf import ActionRegistry
class Tests(unittest.TestCase):
 def test_gate(self):
  r=fa3_dev_update_gate.check();self.assertEqual(r["status"],"PASS",r["blocking_findings"]);self.assertFalse(r["runtime_promotion_claimed"])
 def test_manifest_deterministic(self):
  a=fa3_dev_mode.build_index_manifest();b=fa3_dev_mode.build_index_manifest();self.assertEqual(a["manifest_digest"],b["manifest_digest"]);self.assertTrue(a["binds_git_mode"])
 def test_sticky_taint(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);s=d/"session.json";s.write_text(json.dumps({"schema":"fa3.dev-session.v1","environment":"development","tainted":False,"taint_reasons":[]}))
   with mock.patch.object(fa3_dev_mode,"STATE_DIR",d),mock.patch.object(fa3_dev_mode,"SESSION_PATH",s):
    self.assertEqual(fa3_dev_mode._sticky_taint(["HASH_MISMATCH"]),["HASH_MISMATCH"]);self.assertEqual(fa3_dev_mode._sticky_taint([]),["HASH_MISMATCH"])
 def test_low_risk_security_auto(self):
  r=fa3_update_fabric.classify({"id":"openssl-security","class":"OS_MANAGED","security_update":True,"impact":"QUICK"});self.assertTrue(r["auto_install"]);self.assertFalse(r["host_critical"])
 def test_host_critical_generic(self):
  r=fa3_update_fabric.classify({"id":"accelerator-driver-security","class":"HOST_CRITICAL","security_update":True,"impact":"HOST_CRITICAL"});self.assertFalse(r["auto_install"]);self.assertTrue(r["stage"]);self.assertTrue(r["user_activation_required"])
 def test_model_download_explicit(self):
  r=fa3_update_fabric.classify({"id":"model-v2","class":"MODEL","large_model_download":True});self.assertFalse(r["auto_install"]);self.assertTrue(r["user_activation_required"])
 def test_restart_defers_for_workload(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);rs=d/"restart-required.json"
   with mock.patch.object(fa3_update_fabric,"STATE_DIR",d),mock.patch.object(fa3_update_fabric,"RESTART_STATE",rs):
    fa3_update_fabric.set_restart_required("host",["kernel"],["render"]);r=fa3_update_fabric.choose_restart("RESTART_NOW",["render"],None);self.assertEqual(r["state"],"DEFERRED");self.assertFalse(r["resolved"])
 def test_cpu_only_vendor_neutral_policy(self):
  d=json.loads((fa3_update_fabric.ROOT/"config/fa3-dev-policy.json").read_text());u=json.loads((fa3_update_fabric.ROOT/"config/fa3-update-policy.json").read_text())
  self.assertTrue(d["host_resource_broker"]["cpu_only_valid"]);self.assertEqual(d["host_resource_broker"]["accelerator_cardinality"],"0..N");self.assertIsNone(d["host_resource_broker"]["global_vendor_pin"]);self.assertNotIn("CUDA",json.dumps(u));self.assertNotIn("NVIDIA_driver",json.dumps(u))
 def test_uaf_actions(self):
  reg=ActionRegistry.from_directory(fa3_update_fabric.ROOT/"canonical/actions");ids={x.action_id for x in reg.list()}
  self.assertTrue({"development.enter","development.snapshot","development.freeze","update.check","update.apply-selected","update.security","update.restart-choice","update.rollback"}.issubset(ids))
if __name__=="__main__":unittest.main()
