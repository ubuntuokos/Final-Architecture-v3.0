import json,os,pwd,subprocess,tempfile,unittest
from pathlib import Path
from src import fa3_secret_broker_gate as g
from src.fa3_secret_broker_current_host_gate import REQUIRED_CHECKS
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

    def test_vault_service_capabilities_are_minimal_and_diagnostic(self):
        profile=json.loads((ROOT/"canonical/profiles/FA3-SECRET-BROKER-001.json").read_text())
        caps=profile["lifecycle"]["vault_service_capabilities"]
        expected={"CAP_SYS_ADMIN"}
        self.assertEqual(expected,set(caps["bounding_set"]))
        self.assertEqual(expected,set(caps["ambient"]))
        self.assertEqual("FORBIDDEN",caps["broader_capabilities"])
        unit=(ROOT/"deployment/secrets/fa3-secret-vault.service").read_text()
        self.assertIn("CapabilityBoundingSet=CAP_SYS_ADMIN",unit)
        self.assertIn("AmbientCapabilities=CAP_SYS_ADMIN",unit)
        self.assertNotIn("CAP_CHOWN",unit)
        self.assertNotIn("CAP_FOWNER",unit)
        self.assertIn("ReadWritePaths=/run /var/lib/fa3/state/fa3-machine-state.img",unit)
        lifecycle=(ROOT/"libexec/fa3-secrets-lifecycle.sh").read_text()
        self.assertIn("diagnose_runtime",lifecycle)
        self.assertIn('journalctl --no-pager -n 160 -u fa3-secret-vault.service -u "$MOUNT_UNIT" -u fa3-secret-broker.service',lifecycle)

    def test_vault_mount_is_systemd_managed_and_mapper_service_is_separate(self):
        profile=json.loads((ROOT/"canonical/profiles/FA3-SECRET-BROKER-001.json").read_text())
        contract=profile["lifecycle"]["mount_namespace_contract"]
        self.assertEqual("run-fa3-machine\\x2dstate.mount",contract["mount_unit"])
        self.assertEqual("SYSTEM_MANAGER_MAIN_MOUNT_NAMESPACE",contract["mount_visibility"])
        self.assertEqual("LUKS_MAPPER_ONLY",contract["credential_service_role"])
        self.assertEqual("FORBIDDEN",contract["credential_service_mount_ownership"])
        self.assertEqual("MAY_BE_PRIVATE",contract["credential_service_filesystem_namespace"])
        self.assertEqual("NOT_REQUIRED",contract["pid1_namespace_introspection"])
        self.assertEqual("HELPER_ASSERT_BROKER_OPEN_NO_DEVICE_ACCESS",contract["broker_mount_validation"])
        self.assertEqual("LIFECYCLE_ASSERT_OPEN_RESOLVES_EXPECTED_MAPPER",contract["host_mount_source_validation"])
        mount_unit=(ROOT/"deployment/secrets/run-fa3-machine\\x2dstate.mount").read_text()
        self.assertIn("What=/dev/mapper/fa3-machine-state",mount_unit)
        self.assertIn("Where=/run/fa3/machine-state",mount_unit)
        self.assertIn("Type=ext4",mount_unit)
        self.assertIn("Options=rw,nodev,nosuid,noexec",mount_unit)
        helper=(ROOT/"libexec/fa3-secret-vault-mount.sh").read_text()
        self.assertNotIn("/proc/1/ns/mnt",helper)
        self.assertIn("open_mapper",helper)
        self.assertIn("close_mapper",helper)
        self.assertIn("vault mount source mismatch",helper)
        self.assertIn("for o in rw nodev nosuid noexec",helper)
        self.assertIn("vault mount must be writable",helper)
        self.assertIn("FA3_MAPPER_CLOSE_ATTEMPTS",helper)
        self.assertIn('findmnt -rn -S "/dev/mapper/$MAPPER"',helper)
        self.assertIn("bounded close attempts",helper)
        broker=(ROOT/"deployment/secrets/fa3-secret-broker.service").read_text()
        self.assertIn("Group=fa3-secret-clients",broker)
        self.assertIn("SupplementaryGroups=fa3-secret-broker",broker)
        self.assertIn("RuntimeDirectoryMode=0750",broker)
        self.assertNotIn("chgrp fa3-secret-clients /run/fa3-secret-broker",broker)
        self.assertIn("Requires=run-fa3-machine\\x2dstate.mount",broker)
        self.assertIn("ExecStartPre=/usr/local/libexec/fa3-secret-vault-mount assert-broker-open",broker)
        self.assertIn("PrivateDevices=true",broker)
        lifecycle=(ROOT/"libexec/fa3-secrets-lifecycle.sh").read_text()
        self.assertIn('systemctl stop "$MOUNT_UNIT"',lifecycle)
        self.assertIn('"$VAULT_MOUNT_HELPER" close-mapper',lifecycle)

    def test_current_host_runtime_requalification_is_fail_closed(self):
        conformance=json.loads((ROOT/"canonical/FA3-SECRET-BROKER-RUNTIME-CONFORMANCE-001.json").read_text())
        gate=json.loads((ROOT/"canonical/FA3-GATE-SECRET-BROKER-001.json").read_text())
        enforcement=json.loads((ROOT/"canonical/secret-broker-enforcement.json").read_text())
        historical=json.loads((ROOT/"evidence/reference/secret-broker-current-host-2026-09-21.json").read_text())
        decision=json.loads((ROOT/"canonical/decisions/FA3-DEC-SECRET-BROKER-REQUALIFICATION-2026-09-24.json").read_text())
        registry=json.loads((ROOT/"evidence/evidence-registry.json").read_text())
        self.assertEqual("CURRENT_HOST_REQUALIFICATION_REQUIRED",conformance["status"])
        self.assertFalse(conformance["production_runtime_promoted"])
        self.assertIsNone(conformance["current_host_evidence_ref"])
        self.assertEqual("evidence/reference/secret-broker-current-host-2026-09-21.json",conformance["superseded_current_host_evidence_ref"])
        self.assertIn("SYSTEMD_VAULT_RW_MOUNT_PASS",conformance["required_checks"])
        self.assertIn("SYSTEMD_BROKER_WRITE_READ_REVOKE_PASS",conformance["required_checks"])
        self.assertFalse(gate["production_runtime_promoted"])
        self.assertIsNone(gate["current_host_evidence_ref"])
        self.assertFalse(enforcement["production_runtime_promoted"])
        self.assertIsNone(enforcement["current_host_evidence_ref"])
        self.assertEqual("PASS",historical["result"])
        self.assertEqual("CURRENT_HOST_ADMITTED",historical["status"])
        self.assertEqual("CANONICAL_REQUALIFICATION_REQUIRED",decision["status"])
        self.assertFalse(decision["decision"]["production_runtime_promoted"])
        cap3=next(x for x in registry["records"] if x["subject_id"]=="CAP-003")
        self.assertEqual("PENDING_CURRENT_HOST",cap3["status"])
        self.assertEqual("CURRENT_HOST_REQUALIFICATION_REQUIRED",cap3["secret_broker_projection_status"]["runtime_status"])
        self.assertFalse(cap3["secret_broker_projection_status"]["production_runtime_admitted"])
        self.assertFalse(cap3["secret_broker_projection_status"]["global_promotion_claim"])

    def test_current_host_receipt_schema_requires_rw_and_systemd_write_proof(self):
        schema=json.loads((ROOT/"canonical/schemas/secret-broker-current-host-receipt.v1.json").read_text())
        self.assertEqual(["rw","nodev","nosuid","noexec"],schema["properties"]["mount_options"]["const"])
        required=set(schema["properties"]["checks"]["required"])
        self.assertIn("systemd_vault_rw_mount_pass",required)
        self.assertIn("systemd_broker_write_read_revoke_pass",required)
        self.assertTrue(schema["properties"]["checks"]["properties"]["systemd_vault_rw_mount_pass"]["const"])
        self.assertTrue(schema["properties"]["checks"]["properties"]["systemd_broker_write_read_revoke_pass"]["const"])

    def test_lifecycle_start_requires_broker_readiness_and_health(self):
        profile=json.loads((ROOT/"canonical/profiles/FA3-SECRET-BROKER-001.json").read_text())
        expected={"SECRETS_TARGET_ACTIVE","MAPPER_SERVICE_ACTIVE","SYSTEMD_MOUNT_UNIT_ACTIVE","VAULT_MOUNT_VALIDATED","VAULT_MOUNT_WRITABLE","LUKS_MAPPING_OPEN","BROKER_SERVICE_ACTIVE","BROKER_SOCKET_PRESENT","BROKER_HEALTH_PASS"}
        self.assertEqual(expected,set(profile["lifecycle"]["start_completion_requires"]))
        self.assertEqual("FAIL_CLOSED_ROLLBACK_TO_CLOSED",profile["lifecycle"]["start_readiness_timeout"])
        lifecycle=(ROOT/"libexec/fa3-secrets-lifecycle.sh").read_text()
        self.assertIn("wait_broker_ready",lifecycle)
        self.assertIn('[[ -S "$BROKER_SOCKET" ]]',lifecycle)
        self.assertIn('"$BROKER_HEALTH_CLI" --socket "$BROKER_SOCKET" health',lifecycle)
        self.assertIn("broker readiness/health timeout",lifecycle)
        self.assertIn("systemctl stop fa3-secrets.target",lifecycle)
        current_host=(ROOT/"bin/fa3-secret-broker-current-host.sh").read_text()
        self.assertIn('/usr/local/sbin/fa3-secrets-lifecycle start',current_host)
        self.assertIn("broker health failed after lifecycle readiness PASS",current_host)

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
        self.assertIn('"deployment/secrets/run-fa3-machine\\\\x2dstate.mount"',installer)
        self.assertIn("privileged helper accepts no arguments",helper)
        self.assertIn("SOURCE_COMMIT",helper)
        self.assertIn("privileged bridge source drift",client)
        self.assertIn("/usr/local/bin/fa3-secret-broker-current-host-bridge run",workflow)
        self.assertIn("collect-secret-broker-current-host-reference.py",workflow)
        self.assertIn("secret-broker-current-host-reference-candidate.json",workflow)
        self.assertNotIn('run: sudo FA3_REPO_ROOT',workflow)
        self.assertEqual("DEDICATED_EPHEMERAL_NON_ROOT",boundary["broker_admin_e2e_identity"])
        self.assertEqual({"fa3-secret-admin","fa3-secret-clients"},set(boundary["broker_admin_required_groups"]))
        self.assertEqual("FORBIDDEN",boundary["root_peer_admin_assumption_for_e2e"])
        self.assertEqual("REMOVE_BEFORE_RECEIPT",boundary["broker_admin_e2e_cleanup"])
        current_host=(ROOT/"bin/fa3-secret-broker-current-host.sh").read_text()
        self.assertIn('ADMIN_USER="fa3-sb-admin-probe"',current_host)
        self.assertIn('--groups fa3-secret-admin,fa3-secret-clients "$ADMIN_USER"',current_host)
        self.assertIn('runuser -u "$ADMIN_USER"',current_host)
        self.assertIn('userdel "$ADMIN_USER"',current_host)
        self.assertIn('"ephemeral_admin_probe_removed_pass":True',current_host)
        self.assertIn('"host_mount_namespace_visibility_pass":True',current_host)
        self.assertIn('"systemd_vault_rw_mount_pass":True',current_host)
        self.assertIn('"systemd_broker_write_read_revoke_pass":True',current_host)
        self.assertIn("ReadWritePaths=$SIMG",current_host)
        self.assertIn("fa3-secret-broker-current-host.lock",current_host)
        self.assertIn("fa3-machine-state-e2e-*",current_host)
        self.assertIn("preserving E2E backing image because systemd mount/mapper cleanup is incomplete",current_host)
        for phase in ("[1/4]","[2/4]","[3/4]","[4/4]"):
            self.assertIn(phase,current_host)
        self.assertIn('FA3_MACHINE_STATE_MAPPER="$MAPPER"',current_host)
        self.assertIn('FA3_MACHINE_STATE_MAPPER="$RMAPPER"',current_host)
        self.assertIn('/usr/local/libexec/fa3-secret-vault-mount close-mapper',current_host)
        self.assertIn("/dev/mapper/fa3-machine-state",current_host)

    def test_current_host_reference_collector_requires_new_evidence_matrix(self):
        collector=ROOT/"evidence/collect-secret-broker-current-host-reference.py"
        subprocess.run(["python3","-m","py_compile",str(collector)],check=True)
        head=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
        with tempfile.TemporaryDirectory() as td_raw:
            td=Path(td_raw)
            receipt=td/"receipt.json"
            report=td/"gate.json"
            output=td/"reference.json"
            receipt.write_text(json.dumps({
                "schema":"fa3.secret-broker-current-host-receipt.v1",
                "status":"PASS","real_execution":True,"synthetic":False,
                "executed_at":"2026-09-24T00:00:00+00:00",
                "bridge_source_commit":head,"luks2":True,"filesystem":"ext4",
                "mount_options":["rw","nodev","nosuid","noexec"],
                "broker_unprivileged":True,"broker_user":"fa3-secret-broker",
                "checks":{name:True for name in REQUIRED_CHECKS},
                "test_unlock_key_ephemeral":True,"secret_values_collected":False,
                "runtime_promotion_eligible":True,"global_promotion_claim":False,
                "new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":143
            }))
            report.write_text(json.dumps({
                "schema":"fa3.secret-broker-current-host-gate-report.v1",
                "gate_id":"FA3-GATE-SECRET-BROKER-CURRENT-HOST-001",
                "result":"PASS","status":"CURRENT_HOST_PASS","findings":[],
                "global_promotion_claim":False
            }))
            env=dict(os.environ); env["PYTHONPATH"]=str(ROOT/"src")
            subprocess.run([
                "python3",str(collector),"--root",str(ROOT),
                "--receipt",str(receipt),"--gate-report",str(report),
                "--output",str(output)
            ],check=True,env=env,capture_output=True,text=True)
            ref=json.loads(output.read_text())
            self.assertEqual("PASS",ref["result"])
            self.assertEqual("CURRENT_HOST_ADMITTED",ref["status"])
            self.assertEqual(head,ref["source"]["tested_repository_head"])
            self.assertTrue(ref["checks"]["systemd_vault_rw_mount_pass"])
            self.assertTrue(ref["checks"]["systemd_broker_write_read_revoke_pass"])

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
