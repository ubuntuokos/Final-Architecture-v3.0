import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class StepCaSessionVaultCeremonyTests(unittest.TestCase):
 def test_runner_uses_generic_state_image_and_correct_alias_semantics(self):
  s=(ROOT/"bin/fa3-step-ca-root-ceremony.sh").read_text()
  self.assertIn("/.local/share/fa3/state/fa3-state.img",s)
  self.assertNotIn("fa3-session-vault",s)
  self.assertIn("nodev,nosuid,noexec",s)
  self.assertIn('python3 ip findmnt',s)
  self.assertIn('stat find; do need',s)
  self.assertNotIn("fa3-session-vault/pki/root",(ROOT/"docs/security/FA3-STEP-CA-ROOT-CEREMONY.md").read_text())
 def test_root_secrets_never_enter_transfer_bundle(self):
  s=(ROOT/"bin/fa3-step-ca-root-ceremony.sh").read_text()
  self.assertIn('forbidden in root_ca_key root-password.txt',s)
  self.assertNotIn('install -m0600 "$ROOT_DIR/root_ca_key" "$TRANSFER',s)
  self.assertNotIn('install -m0600 "$ROOT_DIR/root-password.txt" "$TRANSFER',s)
 def test_online_transfer_contains_only_required_material(self):
  s=(ROOT/"bin/fa3-step-ca-root-ceremony.sh").read_text()
  for n in ("root_ca.crt","intermediate_ca.crt","intermediate_ca_key","intermediate-password.txt","jwk-password.txt","step-ca-root-ceremony.json"):
   self.assertIn(n,s)
 def test_ceremony_is_idempotent_and_partial_state_fails_closed(self):
  s=(ROOT/"bin/fa3-step-ca-root-ceremony.sh").read_text()
  self.assertIn("partial PKI material found",s)
  self.assertIn("present == 0",s)
 def test_vault_cleanup_failure_cannot_return_pass(self):
  s=(ROOT/"bin/fa3-step-ca-root-ceremony.sh").read_text()
  self.assertIn('trap cleanup EXIT',s)
  self.assertIn("trap 'exit 130' INT",s)
  self.assertIn("rc == 0 && cleanup_rc != 0",s)
  self.assertIn('echo "step-ca root ceremony: vault cleanup failed"',s)
  self.assertIn('if [[ "$RECEIPT_WRITTEN" == true ]]; then rm -f -- "$RECEIPT"; fi',s)
  self.assertIn('if [[ "$TRANSFER_CREATED" == true',s)
  self.assertNotIn('rm -rf -- "$TRANSFER"',s)
 def test_no_network_shutdown_requirement(self):
  s=(ROOT/"bin/fa3-step-ca-root-ceremony.sh").read_text()
  self.assertNotIn("nmcli networking off",s)
  self.assertNotIn("ip link set",s)
 def test_conformance_registers_runner(self):
  x=json.loads((ROOT/"canonical/FA3-STEP-CA-RUNTIME-CONFORMANCE-001.json").read_text())
  self.assertEqual("bin/fa3-step-ca-root-ceremony.sh",x["current_host_tooling"]["root_ceremony_runner"])
  manifest=json.loads((ROOT/"fa3-current-host/manifest.json").read_text())
  required=set(manifest["required_repository_paths"])
  self.assertIn(".github/workflows/fa3-step-ca-session-vault-ceremony.yml",required)
  self.assertIn("bin/fa3-step-ca-root-ceremony.sh",required)
  self.assertIn("tests/test_step_ca_session_vault_ceremony.py",required)
  surfaces={item["name"]:item for item in manifest["registered_current_host_surfaces"]}
  self.assertEqual("bin/fa3-step-ca-root-ceremony.sh",surfaces["step-ca-internal-pki"]["root_ceremony_runner"])

if __name__=="__main__": unittest.main()
