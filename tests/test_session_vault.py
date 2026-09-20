import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SessionVaultTests(unittest.TestCase):
 def test_profile_is_provider_neutral_and_no_new_authority(self):
  x=json.loads((ROOT/"canonical/profiles/FA3-SESSION-VAULT-001.json").read_text())
  self.assertTrue(x["provider_neutral"]); self.assertFalse(x["new_capability"]); self.assertFalse(x["new_architectural_authority"]); self.assertEqual(143,x["capability_count"])
 def test_removable_media_is_optional(self):
  x=json.loads((ROOT/"canonical/session-vault-enforcement.json").read_text())
  self.assertIn("NO_MANDATORY_REMOVABLE_MEDIA",x["p0_invariants"])
 def test_gui_backend_uses_udisks_dbus(self):
  s=(ROOT/"apps/fa3-control-center/src/SessionVaultService.cpp").read_text()
  self.assertIn("org.freedesktop.UDisks2",s); self.assertIn("LoopSetup",s); self.assertIn("org.freedesktop.UDisks2.Encrypted",s)
 def test_secret_service_is_standard_adapter(self):
  s=(ROOT/"apps/fa3-control-center/src/SessionVaultService.cpp").read_text()
  self.assertIn("secret-tool",s); self.assertNotIn("kwallet",s.lower())
 def test_initializer_has_no_secret_file(self):
  s=(ROOT/"bin/fa3-session-vault-init").read_text()
  self.assertIn("--key-file -",s); self.assertNotIn("password.txt",s); self.assertIn("nodev,nosuid,noexec",s)
 def test_runtime_is_not_falsely_promoted(self):
  x=json.loads((ROOT/"canonical/FA3-SESSION-VAULT-RUNTIME-CONFORMANCE-001.json").read_text())
  self.assertEqual("MATERIALIZED_PENDING_REAL_CURRENT_HOST_EXECUTION",x["status"]); self.assertFalse(x["production_runtime_promoted"])
if __name__=="__main__": unittest.main()
