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
 def test_single_user_default_has_no_second_login(self):
  p=json.loads((ROOT/"canonical/profiles/FA3-SESSION-VAULT-001.json").read_text())
  d=json.loads((ROOT/"canonical/decisions/FA3-DEC-SESSION-VAULT-2026-09-20.json").read_text())
  main=(ROOT/"apps/fa3-control-center/qml/Main.qml").read_text()
  cmake=(ROOT/"apps/fa3-control-center/CMakeLists.txt").read_text()
  self.assertFalse(p["session_semantics"]["separate_fa3_login_required"])
  self.assertFalse(p["multi_user"]["default_enabled"])
  self.assertIn("NO_SEPARATE_FA3_LOGIN_FOR_SINGLE_USER_DEFAULT",d["constraints"])
  self.assertNotIn("SessionVaultLogin",main)
  self.assertNotIn("SessionVaultLogin.qml",cmake)
  self.assertFalse((ROOT/"apps/fa3-control-center/qml/SessionVaultLogin.qml").exists())
 def test_auto_unlock_is_best_effort_not_app_gate(self):
  s=(ROOT/"apps/fa3-control-center/src/SessionVaultService.cpp").read_text()
  self.assertIn("tryAutoUnlock",s)
  self.assertIn("QTimer::singleShot",s)
  self.assertIn('m_statusText = QStringLiteral("LOCKED")',s)
 def test_filesystem_label_fits_ext4_limit(self):
  p=json.loads((ROOT/"canonical/profiles/FA3-SESSION-VAULT-001.json").read_text())
  label=p["storage"]["filesystem_label"]
  self.assertLessEqual(len(label),16)
  s=(ROOT/"bin/fa3-session-vault-init").read_text()
  self.assertIn("--label "+label,s)
  self.assertIn("-L "+label,s)
  self.assertNotIn("FA3_SESSION_VAULT",s)
 def test_runtime_is_not_falsely_promoted(self):
  x=json.loads((ROOT/"canonical/FA3-SESSION-VAULT-RUNTIME-CONFORMANCE-001.json").read_text())
  self.assertEqual("MATERIALIZED_PENDING_REAL_CURRENT_HOST_EXECUTION",x["status"]); self.assertFalse(x["production_runtime_promoted"])
if __name__=="__main__": unittest.main()
