import json,tempfile,unittest
from pathlib import Path
import fa3_step_ca_current_host_gate as g
ROOT=Path(__file__).resolve().parents[1]
def good():
 d="a"*64
 return {"schema":"fa3.step-ca-current-host-receipt.v1","provider_id":g.PROVIDER_ID,"status":"PASS","evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS","synthetic":False,"supply_chain":{"status":"PASS","server":{"version":"0.30.2","asset_sha256":d,"binary_sha256":d,"sigstore_verified":True},"client":{"version":"0.30.6","asset_sha256":d,"binary_sha256":d,"sigstore_verified":True}},"root_ceremony":{"status":"PASS","network_default_route_present":False,"root_private_key_bytes_collected":False,"root_private_key_exported_online":False,"chain_verification":"PASS"},"activation":{"status":"PASS","service_user":"fa3-step-ca","root_private_key_present_online":False,"intermediate_key_encrypted":True,"systemd_credential_unlock":True},"runtime":{"service_active":True,"bind":"127.0.0.1:9443","root_private_key_present_online":False,"certificate_chain_valid":True},"e2e":{"acme_issue_pass":True,"acme_reorder_pass":True,"mtls_pass":True,"ssh_certificate_pass":True,"trust_bundle_pass":True,"max_observed_tls_ttl_hours":0.2},"backup_restore":{"status":"PASS","root_private_key_in_backup":False,"unlock_secret_in_backup":False,"shadow_health_pass":True,"post_restore_issuance_pass":True},"secret_values_collected":False,"runtime_promotion_eligible":True,"global_promotion_claim":False,"new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143}
class T(unittest.TestCase):
 def test_good(self): self.assertEqual([],g.validate_receipt(good()))
 def test_root_online_fails(self):
  x=good(); x["runtime"]["root_private_key_present_online"]=True; self.assertTrue(g.validate_receipt(x))
 def test_missing_receipt_fails(self):
  with tempfile.TemporaryDirectory() as d: self.assertEqual("FAIL",g.gate(Path(d))["result"])
 def test_tool_lock(self):
  x=json.loads((ROOT/"canonical/step-ca-current-host-tool-lock.json").read_text()); self.assertEqual({"amd64","arm64"},set(x["server"]["artifacts"]))
 def test_ssh_paths(self):
  x=json.loads((ROOT/"deployment/step-ca/ca.json.example").read_text()); self.assertIn("ssh_host_ca_key",x["ssh"]["hostKey"])
 def test_bootstrap_never_makes_root(self): self.assertNotIn("root_ca_key",(ROOT/"bin/fa3-step-ca-bootstrap.sh").read_text())
 def test_bootstrap_fetch_verify_is_nounset_safe(self):
  s=(ROOT/"bin/fa3-step-ca-bootstrap.sh").read_text()
  self.assertNotIn('out="$7" base="https://github.com/$repo/releases/download/v$ver"',s)
  self.assertIn('out="$7" verifier="$8"; local base; base="https://github.com/$repo/releases/download/v$ver"',s)
  self.assertIn('"$verifier" verify-blob',s)
 def test_bootstrap_self_bootstraps_pinned_cosign(self):
  s=(ROOT/"bin/fa3-step-ca-bootstrap.sh").read_text()
  self.assertIn("bootstrap_cosign",s)
  self.assertIn("cosign 3.1.2 verifier",s)
  self.assertIn("3ef5d389c3f508b96025fd1b92744a305c46e95951c91242b57467567d5622db",s)
  self.assertIn("f7622ed3cf22e55e1ae6377c080979ff77a22da9981c11df222a2e444991e7cf",s)
  self.assertIn("90e7ae0b5dfd60f20816b52c012addf7fc055ebcc7bea4ce81c428ca8518c302",s)
  self.assertNotIn('"$(cosign_bin)" verify-blob',s)
 def test_bootstrap_checksum_matching_is_exact_and_fail_closed(self):
  s=(ROOT/"bin/fa3-step-ca-bootstrap.sh").read_text()
  self.assertIn("verify_checksum_entry",s)
  self.assertIn('$2 == name {print}',s)
  self.assertIn("must contain exactly one entry",s)
  self.assertNotIn('grep -F "$asset" cosign_checksums.txt',s)
  self.assertNotIn('grep -F "$asset" checksums.txt',s)
 def test_collector_no_root_key_arg(self): self.assertNotIn("--root-key",(ROOT/"evidence/collect-step-ca-root-ceremony.py").read_text())
 def test_not_promoted(self):
  x=json.loads((ROOT/"canonical/FA3-STEP-CA-RUNTIME-CONFORMANCE-001.json").read_text()); self.assertEqual("MATERIALIZED_PENDING_REAL_CURRENT_HOST_EXECUTION",x["status"]); self.assertFalse(x["production_runtime_promoted"])
if __name__=="__main__": unittest.main()
