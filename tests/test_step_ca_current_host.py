import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import fa3_step_ca_current_host_gate as g
ROOT=Path(__file__).resolve().parents[1]
COLLECTOR_SPEC=importlib.util.spec_from_file_location("fa3_step_ca_current_host_collector",ROOT/"evidence/collect-step-ca-current-host.py")
COLLECTOR=importlib.util.module_from_spec(COLLECTOR_SPEC); COLLECTOR_SPEC.loader.exec_module(COLLECTOR)
def good():
 d="a"*64
 return {"schema":"fa3.step-ca-current-host-receipt.v1","provider_id":g.PROVIDER_ID,"status":"PASS","evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS","synthetic":False,"supply_chain":{"status":"PASS","server":{"version":"0.30.2","asset_sha256":d,"binary_sha256":d,"sigstore_verified":True},"client":{"version":"0.30.6","asset_sha256":d,"binary_sha256":d,"sigstore_verified":True}},"root_ceremony":{"status":"PASS","network_default_route_present":True,"root_private_key_bytes_collected":False,"root_private_key_exported_online":False,"chain_verification":"PASS"},"activation":{"status":"PASS","service_user":"fa3-step-ca","root_private_key_present_online":False,"intermediate_key_encrypted":True,"systemd_credential_unlock":True,"transfer_bundle_removed":True},"runtime":{"service_active":True,"bind":"127.0.0.1:9443","root_private_key_present_online":False,"certificate_chain_valid":True},"e2e":{"acme_issue_pass":True,"acme_reorder_pass":True,"mtls_pass":True,"ssh_certificate_pass":True,"trust_bundle_pass":True,"max_observed_tls_ttl_hours":0.2},"backup_restore":{"status":"PASS","root_private_key_in_backup":False,"unlock_secret_in_backup":False,"shadow_health_pass":True,"post_restore_issuance_pass":True},"secret_values_collected":False,"runtime_promotion_eligible":True,"global_promotion_claim":False,"new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143}
class T(unittest.TestCase):
 def test_good(self): self.assertEqual([],g.validate_receipt(good()))
 def test_root_online_fails(self):
  x=good(); x["runtime"]["root_private_key_present_online"]=True; self.assertTrue(g.validate_receipt(x))
 def test_retained_transfer_bundle_fails(self):
  x=good(); x["activation"]["transfer_bundle_removed"]=False; self.assertTrue(g.validate_receipt(x))
 def test_missing_receipt_fails(self):
  with tempfile.TemporaryDirectory() as d: self.assertEqual("FAIL",g.gate(Path(d))["result"])
 def test_tool_lock(self):
  x=json.loads((ROOT/"canonical/step-ca-current-host-tool-lock.json").read_text()); self.assertEqual({"amd64","arm64"},set(x["server"]["artifacts"]))
 def test_ssh_paths(self):
  x=json.loads((ROOT/"deployment/step-ca/ca.json.example").read_text()); self.assertIn("ssh_host_ca_key",x["ssh"]["hostKey"])
 def test_ca_tls_endpoint_identity_matches_loopback_url(self):
  x=json.loads((ROOT/"deployment/step-ca/ca.json.example").read_text())
  self.assertEqual("127.0.0.1:9443",x["address"])
  self.assertIn("127.0.0.1",x["dnsNames"])
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
 def test_root_ceremony_network_state_is_not_admission_criterion(self):
  collector=(ROOT/"evidence/collect-step-ca-root-ceremony.py").read_text()
  gate=(ROOT/"src/fa3_step_ca_current_host_gate.py").read_text()
  enforcement=json.loads((ROOT/"canonical/step-ca-current-host-enforcement.json").read_text())
  schema=json.loads((ROOT/"canonical/schemas/step-ca-root-ceremony-receipt.v1.json").read_text())
  self.assertNotIn("offline ceremony host has a default route",collector)
  self.assertNotIn('c.get("network_default_route_present") is False',gate)
  self.assertNotIn("OFFLINE_CEREMONY_DEFAULT_ROUTE_FORBIDDEN",enforcement["p0_invariants"])
  self.assertEqual("boolean",schema["properties"]["network_default_route_present"]["type"])
  self.assertNotIn("network_default_route_present",schema["required"])
 def test_root_custody_default_is_local_encrypted_and_redundant(self):
  enforcement=json.loads((ROOT/"canonical/step-ca-current-host-enforcement.json").read_text())
  decision=json.loads((ROOT/"canonical/decisions/FA3-DEC-STEP-CA-CURRENT-HOST-2026-09-20.json").read_text())
  collector=(ROOT/"evidence/collect-step-ca-root-ceremony.py").read_text()
  policy=enforcement["root_custody_policy"]
  self.assertTrue(policy["same_host_allowed"])
  self.assertFalse(policy["removable_media_required"])
  self.assertFalse(policy["hsm_required"])
  self.assertFalse(policy["air_gap_required"])
  self.assertEqual("REDUNDANT_ENCRYPTED_BACKUP_REQUIRED",policy["durability"])
  self.assertIn("SAME_HOST_ENCRYPTED_ROOT_STORAGE_ALLOWED_OUTSIDE_STEP_CA_RUNTIME",decision["constraints"])
  self.assertIn("ROOT_CUSTODY_BACKUP_MUST_BE_REDUNDANT_AND_ENCRYPTED",decision["constraints"])
  self.assertIn('default="local-protected-storage"',collector)
 def test_collector_no_root_key_arg(self): self.assertNotIn("--root-key",(ROOT/"evidence/collect-step-ca-root-ceremony.py").read_text())
 def test_unprivileged_collector_uses_attestation_and_key_metadata_not_secret_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   key=Path(d)/"intermediate_ca_key"; key.write_text("collector must not read these bytes")
   key.chmod(0o600); account=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())
   self.assertTrue(COLLECTOR.intermediate_key_boundary(key,{"intermediate_key_encrypted":True},account))
   self.assertFalse(COLLECTOR.intermediate_key_boundary(key,{"intermediate_key_encrypted":False},account))
   key.chmod(0o640)
   self.assertFalse(COLLECTOR.intermediate_key_boundary(key,{"intermediate_key_encrypted":True},account))
  self.assertNotIn("ik.read_text",(ROOT/"evidence/collect-step-ca-current-host.py").read_text())
 def test_unprivileged_collector_can_reach_public_evidence_and_stat_known_secret_metadata(self):
  bootstrap=(ROOT/"bin/fa3-step-ca-bootstrap.sh").read_text()
  activation=(ROOT/"bin/fa3-step-ca-activate.sh").read_text()
  collector=(ROOT/"evidence/collect-step-ca-current-host.py").read_text()
  for script in (bootstrap,activation):
   self.assertIn('-m0755 /var/lib/fa3-step-ca/{certs,evidence}',script)
   self.assertIn('-m0711 /var/lib/fa3-step-ca/secrets',script)
   self.assertIn('-m0700 /var/lib/fa3-step-ca/db',script)
  self.assertIn('chmod 0644 /var/lib/fa3-step-ca/evidence/activation.json',activation)
  self.assertIn('online Root private key forbidden',activation)
  self.assertIn('act.get("root_private_key_present_online") is not False or rootkey()',collector)
 def test_activation_removes_ephemeral_transfer_bundle(self):
  s=(ROOT/"bin/fa3-step-ca-activate.sh").read_text()
  self.assertIn('rm -f -- "$T/$f"',s)
  self.assertIn('rmdir -- "$T"',s)
  self.assertIn('"transfer_bundle_removed":True',s)
 def test_pinned_cli_provisioner_add_has_required_target_identity(self):
  s=(ROOT/"bin/fa3-step-ca-activate.sh").read_text()
  self.assertIn('--ca-url https://127.0.0.1:9443',s)
  self.assertIn('--root /var/lib/fa3-step-ca/certs/root_ca.crt',s)
  self.assertIn('--ca-config /etc/fa3/step-ca/ca.json',s)
 def test_ssh_e2e_is_noninteractive_inside_ephemeral_root_only_directory(self):
  s=(ROOT/"bin/fa3-step-ca-e2e.sh").read_text()
  for flag in ('--no-agent','--no-password','--insecure','--not-after 10m'):
   self.assertIn(flag,s)
 def test_acme_e2e_uses_ephemeral_port_and_restores_service(self):
  s=(ROOT/"bin/fa3-step-ca-e2e.sh").read_text()
  self.assertNotIn('--http-listen 127.0.0.1:80',s)
  self.assertIn('--acme-http-port=$ACME_HTTP_PORT',s)
  self.assertIn('--http-listen "127.0.0.1:$ACME_HTTP_PORT"',s)
  self.assertGreaterEqual(s.count('--standalone'),2)
  self.assertIn('90-fa3-e2e-acme-port.conf',s)
  self.assertIn('execstart_signature()',s)
  self.assertIn('PRODUCTION_EXECSTART_SIGNATURE="$(execstart_signature)"',s)
  self.assertIn('[[ "$signature" == "$PRODUCTION_EXECSTART_SIGNATURE" ]]',s)
  self.assertIn('path.group(1).strip()',s)
  self.assertIn('argv.group(1).strip()',s)
  self.assertNotIn('[[ "$execstart" == "$PRODUCTION_EXECSTART" ]]',s)
  self.assertIn('"host_port_80_untouched": True',s)
 def test_mtls_e2e_sends_intermediate_chain_and_reports_failures(self):
  s=(ROOT/"bin/fa3-step-ca-e2e.sh").read_text()
  self.assertGreaterEqual(s.count('-cert_chain "$IC"'),2)
  self.assertIn('openssl verify -purpose sslserver -CAfile "$RC" -untrusted "$IC" "$TMP/b.crt"',s)
  self.assertIn('openssl verify -purpose sslclient -CAfile "$RC" -untrusted "$IC" "$TMP/c.crt"',s)
  self.assertIn('echo "mTLS handshake failed" >&2',s)
  self.assertIn("for command in curl flock openssl python3 sed seq ssh-keygen ss systemctl; do",s)\n  self.assertIn('STEP_BIN="/usr/local/lib/fa3/step-cli/0.30.6/bin/step"',s)
 def test_restore_cleanup_is_fail_safe(self):
  s=(ROOT/"bin/fa3-step-ca-backup-restore-drill.sh").read_text()
  self.assertIn('if [[ -n "$PID" ]] && kill -0 "$PID"',s)
  self.assertIn('if [[ "$PRIMARY_STOPPED" == true ]]; then systemctl start fa3-step-ca.service; fi',s)
  self.assertIn("trap cleanup EXIT",s)
 def test_current_host_runtime_promoted_only(self):
  x=json.loads((ROOT/"canonical/FA3-STEP-CA-RUNTIME-CONFORMANCE-001.json").read_text())
  self.assertEqual("CURRENT_HOST_PRODUCTION_E2E_PASS",x["status"])
  self.assertTrue(x["production_runtime_promoted"])
  self.assertEqual("CURRENT_HOST_PROVIDER_RUNTIME_ONLY",x["production_promotion_scope"])
  self.assertFalse(x["global_promotion_claim"])
  self.assertIsNone(x["durable_current_host_evidence_reference"])\n  self.assertEqual("evidence/reference/step-ca-current-host-2026-09-20.json",x["superseded_historical_evidence"])
if __name__=="__main__": unittest.main()
