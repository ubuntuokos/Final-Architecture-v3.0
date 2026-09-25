import tempfile,unittest
from pathlib import Path
from src import fa3_secret_broker_current_host_gate as g
class SecretBrokerCurrentHostTests(unittest.TestCase):
    def good(self):
        return {"schema":g.SCHEMA,"status":"PASS","real_execution":True,"synthetic":False,"luks2":True,"filesystem":"ext4",
                "mount_options":["rw","nodev","nosuid","noexec"],"broker_unprivileged":True,"broker_user":"fa3-secret-broker","bridge_source_commit":"a"*40,
                "checks":{k:True for k in g.REQUIRED_CHECKS},
                "secret_values_collected":False,"runtime_promotion_eligible":True,"global_promotion_claim":False,
                "new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143}
    def test_good_receipt(self):self.assertEqual([],g.validate(self.good()))
    def test_missing_or_invalid_bridge_source_denied(self):
        x=self.good();x["bridge_source_commit"]="bad";self.assertTrue(g.validate(x))
        x=self.good();x["checks"]["current_host_privileged_bridge_source_binding_pass"]=False;self.assertTrue(g.validate(x))
    def test_missing_non_root_admin_authorization_denied(self):
        x=self.good();x["checks"]["non_root_admin_authorization_pass"]=False;self.assertTrue(g.validate(x))
    def test_missing_host_mount_namespace_visibility_denied(self):
        x=self.good();x["checks"]["host_mount_namespace_visibility_pass"]=False;self.assertTrue(g.validate(x))
    def test_persistent_admin_probe_denied(self):
        x=self.good();x["checks"]["ephemeral_admin_probe_removed_pass"]=False;self.assertTrue(g.validate(x))
    def test_synthetic_denied(self):
        x=self.good();x["synthetic"]=True;self.assertTrue(g.validate(x))
    def test_missing_credential_scope_proof_denied(self):
        x=self.good();x["checks"]["credential_scope_enforced"]=False;self.assertTrue(g.validate(x))
    def test_missing_rotation_or_revocation_denied(self):
        for key in ("rotation_pass","revocation_pass","metadata_only_list_pass","policy_preflight_pass","policy_install_remove_pass","restore_secret_read_pass","encrypted_systemd_unlock_runtime_pass","systemd_target_lifecycle_pass","systemd_e2e_artifact_cleanup_pass","hardware_neutral_systemd_credential_host_key_mode_pass","luks_unlock_key_rotation_pass","old_unlock_key_rejected_after_rekey","new_unlock_key_accepted_after_rekey","rekey_final_closed_state_pass"):
            x=self.good();x["checks"][key]=False;self.assertTrue(g.validate(x))
    def test_missing_systemd_rw_or_write_proof_denied(self):
        for key in ("systemd_vault_rw_mount_pass","systemd_broker_write_read_revoke_pass"):
            x=self.good();x["checks"][key]=False;self.assertTrue(g.validate(x))
        x=self.good();x["mount_options"]=["nodev","nosuid","noexec"];self.assertTrue(g.validate(x))
    def test_open_vault_cannot_claim_fa3_exit(self):
        x=self.good();x["checks"]["fa3_exit_closed_state_pass"]=False;self.assertTrue(g.validate(x))
    def test_secret_collection_denied(self):
        x=self.good();x["secret_values_collected"]=True;self.assertTrue(g.validate(x))
    def test_missing_receipt_fail_closed_when_required(self):
        with tempfile.TemporaryDirectory() as td:
            r=g.gate(Path(td),None,True);self.assertEqual("FAIL",r["result"])
if __name__=="__main__":unittest.main()
