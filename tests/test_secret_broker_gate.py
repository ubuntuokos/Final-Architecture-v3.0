import json,subprocess,unittest
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

    def test_runtime_scripts_do_not_use_secret_env_or_argv(self):
        init=(ROOT/"bin/fa3-secret-vault-init").read_text()
        mount=(ROOT/"libexec/fa3-secret-vault-mount.sh").read_text()
        client=(ROOT/"bin/fa3-secretctl").read_text()
        self.assertIn("systemd-creds encrypt",init)
        self.assertIn("CREDENTIALS_DIRECTORY",mount)
        self.assertNotIn("FA3_SECRET_VALUE",init+mount+client)
    def test_shell_syntax(self):
        for path in ["bin/fa3-secret-vault-init","bin/fa3-secret-broker-install","bin/fa3-secret-broker-current-host.sh","libexec/fa3-secret-vault-mount.sh"]:
            subprocess.run(["bash","-n",str(ROOT/path)],check=True)

if __name__=="__main__":unittest.main()
