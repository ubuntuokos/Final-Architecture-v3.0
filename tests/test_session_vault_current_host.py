import json, tempfile, unittest
from pathlib import Path
from src import fa3_session_vault_current_host_gate as gate

ROOT=Path(__file__).resolve().parents[1]

class SessionVaultCurrentHostTests(unittest.TestCase):
 def receipt(self):
  return {
   "schema":"fa3.session-vault-current-host-receipt.v1","status":"PASS",
   "real_execution":True,"synthetic":False,
   "image_path":str(Path.home()/".local/share/fa3/state/fa3-state.img"),
   "luks2":True,"external_storage_name_non_disclosing":True,
   "loop_setup_pass":True,"unlock_pass":True,"filesystem":"ext4",
   "luks_label":"FA3_STATE","filesystem_label":"FA3_STATE",
   "mount_pass":True,"mount_options":["nodev","nosuid","noexec"],
   "service_account_isolation_pass":True,"explicit_unmount_pass":True,
   "explicit_lock_pass":True,"loop_cleanup_pass":True,
   "opaque_backup_copy_pass":True,"opaque_backup_restore_unlock_pass":True,
   "opaque_backup_restore_mount_pass":True,
   "secret_service":{"configured":False,"lookup_pass_if_configured":None},
   "secret_values_collected":False,"runtime_promotion_eligible":True,
   "global_promotion_claim":False
  }
 def test_script_secret_is_interactive_not_argv_or_env(self):
  s=(ROOT/"bin/fa3-session-vault-current-host.sh").read_text()
  self.assertIn("udisksctl unlock --block-device",s)
  self.assertNotIn("--key-file",s)
  self.assertNotIn("FA3_VAULT_PASSPHRASE",s)
 def test_block_metadata_probe_is_privileged_and_diagnostic(self):
  s=(ROOT/"bin/fa3-session-vault-current-host.sh").read_text()
  self.assertIn('sudo blkid -p -o value -s "$tag" "$dev"',s)
  self.assertIn('detected=${fs_type:-unknown}',s)
  self.assertNotIn('$(blkid -o value -s TYPE "$CLEAR")',s)
 def test_script_requires_service_account_isolation(self):
  s=(ROOT/"bin/fa3-session-vault-current-host.sh").read_text()
  self.assertIn("sudo -u fa3-step-ca test -r",s)
  self.assertIn("sudo -u fa3-step-ca test -x",s)
 def test_script_proves_opaque_restore(self):
  s=(ROOT/"bin/fa3-session-vault-current-host.sh").read_text()
  self.assertIn("cp --reflink=never",s)
  self.assertIn("Re-enter the vault passphrase",s)
  self.assertIn("--read-only",s)
 def test_conformance_records_real_pass_but_stays_unpromoted(self):
  x=json.loads((ROOT/"canonical/FA3-SESSION-VAULT-RUNTIME-CONFORMANCE-001.json").read_text())
  self.assertEqual("CURRENT_HOST_PASS_RUNTIME_PROMOTION_ELIGIBLE",x["status"])
  self.assertEqual("evidence/receipts/session-vault-current-host.json",x["current_host_receipt"])
  self.assertTrue(x["current_host_result"]["real_execution"])
  self.assertTrue(x["current_host_result"]["runtime_promotion_eligible"])
  self.assertFalse(x["production_runtime_promoted"])
 def test_missing_receipt_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); (root/"reports").mkdir()
   self.assertEqual(2,gate.run_gate(root,Path("missing.json")))

if __name__=="__main__": unittest.main()
