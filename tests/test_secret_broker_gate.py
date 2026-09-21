import json,os,pwd,subprocess,tempfile,unittest
from pathlib import Path
from src import fa3_secret_broker_gate as g
ROOT=Path(__file__).resolve().parents[1]

class SecretBrokerGateTests(unittest.TestCase):
    def test_static_gate_passes(self):
        r=g.check();self.assertEqual("PASS",r["result"],r)
    def test_session_and_machine_vaults_are_separate(self):
        p=json.loads((ROOT/"canonical/profiles/FA3-SESSION-VAULT-001.json").read_text())
        self.assertEqual("FA3-SECRET-BROKER-001",p["machine_secret_boundary"]["profile"])
        self.assertEqual("FORBIDDEN",p["machine_secret_boundary"]["raw_machine_application_secret_storage"])
        init=(ROOT/"bin/fa3-session-vault-init").read_text()
        self.assertNotIn('$MNT/credentials',init);self.assertIn('$MNT/secret-refs',init)
    def test_image_name_is_generic_and_non_disclosing(self):
        p=json.loads((ROOT/"canonical/profiles/FA3-SECRET-BROKER-001.json").read_text())
        image=Path(p["storage_classes"]["machine_service"]["default_image"]).name.lower()
        for forbidden in ("secret","credential","token","password","passwd","key","auth"):
            self.assertNotIn(forbidden,image)
        self.assertEqual("GENERIC_NON_DISCLOSING",p["storage_classes"]["machine_service"]["external_naming_policy"])
        self.assertEqual("CREDENTIAL_SECRETS_ONLY",p["secret_scope"]["mode"])
        self.assertFalse(p["portability"]["desktop_environment_required"])
        self.assertFalse(p["portability"]["display_server_required"])

    def test_fa3_exit_requires_closed_vault(self):
        p=json.loads((ROOT/"canonical/profiles/FA3-SECRET-BROKER-001.json").read_text())
        x=p["lifecycle"]["fa3_exit_contract"]
        self.assertEqual("/usr/local/sbin/fa3-secrets-lifecycle exit",x["command"])
        self.assertIn("SECRETS_TARGET_INACTIVE",x["completion_requires"])
        self.assertIn("VAULT_UNMOUNTED",x["completion_requires"])
        self.assertIn("LUKS_MAPPING_CLOSED",x["completion_requires"])
        unit=(ROOT/"deployment/secrets/fa3-secret-vault.service").read_text()
        self.assertIn("ExecStopPost=/usr/local/libexec/fa3-secret-vault-mount assert-closed",unit)
        lifecycle=(ROOT/"libexec/fa3-secrets-lifecycle.sh").read_text()
        self.assertIn("systemctl stop fa3-secrets.target",lifecycle)
        self.assertIn("systemctl is-active --quiet fa3-secrets.target",lifecycle)
        self.assertIn("assert_closed",lifecycle)

    def test_policy_preflight_validation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"policy.json"
            user=pwd.getpwuid(os.getuid()).pw_name
            good={"schema":"fa3.secret-projection-policy.v1","secret_id":"test/user-token","classification":"USER_SESSION_SECRET","secret_kind":"API_TOKEN",
                  "allowed_consumers":[{"consumer_id":"TEST","allowed_unix_users":[user],"allowed_executables":[],"allowed_systemd_units":[]}],
                  "allowed_projections":["UDS_SINGLE_SECRET"],"exportable":False}
            p.write_text(json.dumps(good))
            subprocess.run(["python3",str(ROOT/"bin/fa3-secret-policyctl"),"check",str(p)],check=True,capture_output=True,text=True)
            good["exportable"]=True;p.write_text(json.dumps(good))
            r=subprocess.run(["python3",str(ROOT/"bin/fa3-secret-policyctl"),"check",str(p)],capture_output=True,text=True)
            self.assertNotEqual(0,r.returncode)

    def test_operator_surface_is_single_entrypoint(self):
        admin=(ROOT/"bin/fa3-secrets-admin").read_text()
        for token in ("put","rotate","revoke","metadata","list","policy-install","policy-remove","backup","restore","rekey","assert-closed"):
            self.assertIn(token,admin)
        recovery=(ROOT/"bin/fa3-secret-vault-recovery").read_text()
        self.assertIn("vault_closed_during_backup",recovery)
        self.assertIn('"final_vault_state":"CLOSED"',recovery)

    def test_rekey_is_fail_closed_and_hardware_neutral(self):
        rekey=(ROOT/"bin/fa3-secret-vault-rekey").read_text()
        self.assertIn("--with-key=host",rekey)
        self.assertIn("luksAddKey",rekey)
        self.assertIn("luksRemoveKey",rekey)
        self.assertIn("open --test-passphrase",rekey)
        self.assertIn("FA3_REKEY_NEW_KEY_FILE",rekey)
        self.assertIn("final state: CLOSED",rekey)

    def test_current_host_privileged_bridge_is_exact_and_source_bound(self):
        installer=(ROOT/"bin/fa3-install-secret-broker-current-host-bridge.sh").read_text()
        client=(ROOT/"libexec/fa3-secret-broker-current-host-bridge.sh").read_text()
        helper=(ROOT/"libexec/fa3-secret-broker-current-host-root.sh").read_text()
        workflow=(ROOT/".github/workflows/fa3-secret-broker-current-host.yml").read_text()
        profile=json.loads((ROOT/"canonical/profiles/FA3-SECRET-BROKER-001.json").read_text())
        boundary=profile["current_host_privilege_boundary"]
        self.assertEqual("NON_ROOT",boundary["runner_identity"])
        self.assertEqual("NOPASSWD_SINGLE_HELPER_NO_ARGUMENTS",boundary["sudo_policy"])
        self.assertEqual("FORBIDDEN",boundary["general_passwordless_sudo"])
        self.assertIn('NOPASSWD: %s ""',installer)
        self.assertNotIn("NOPASSWD: ALL",installer)
        self.assertIn("privileged helper accepts no arguments",helper)
        self.assertIn("SOURCE_COMMIT",helper)
        self.assertIn("privileged bridge source drift",client)
        self.assertIn("/usr/local/bin/fa3-secret-broker-current-host-bridge run",workflow)
        self.assertNotIn('run: sudo FA3_REPO_ROOT',workflow)

    def test_runtime_scripts_do_not_use_secret_env_or_argv(self):
        init=(ROOT/"bin/fa3-secret-vault-init").read_text()
        mount=(ROOT/"libexec/fa3-secret-vault-mount.sh").read_text()
        client=(ROOT/"bin/fa3-secretctl").read_text()
        self.assertIn("systemd-creds encrypt",init)
        self.assertIn("--with-key=host",init)
        self.assertIn("CREDENTIALS_DIRECTORY",mount)
        self.assertNotIn("FA3_SECRET_VALUE",init+mount+client)
    def test_shell_syntax(self):
        for path in ["bin/fa3-secret-vault-init","bin/fa3-secret-broker-install","bin/fa3-secret-broker-current-host.sh","bin/fa3-secret-vault-recovery","bin/fa3-secret-vault-rekey","bin/fa3-secrets-admin","bin/fa3-install-secret-broker-current-host-bridge.sh","libexec/fa3-secret-vault-mount.sh","libexec/fa3-secrets-lifecycle.sh","libexec/fa3-secret-broker-current-host-root.sh","libexec/fa3-secret-broker-current-host-bridge.sh"]:
            subprocess.run(["bash","-n",str(ROOT/path)],check=True)

if __name__=="__main__":unittest.main()
