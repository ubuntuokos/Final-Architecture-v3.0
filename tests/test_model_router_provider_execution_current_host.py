import importlib.util, json, tempfile, unittest, subprocess, sys
from pathlib import Path
from fa3_model_router_provider_execution_current_host_gate import REQUIRED_CHECKS

ROOT=Path(__file__).resolve().parents[1]

class CurrentHostReceiptContractTests(unittest.TestCase):
    def test_required_matrix_contains_rollback_and_negative_boundaries(self):
        self.assertIn("rollback_pass",REQUIRED_CHECKS)
        self.assertIn("provisioning_cleanup_pass",REQUIRED_CHECKS)
        self.assertIn("unadmitted_provider_denied_pass",REQUIRED_CHECKS)
        self.assertIn("cross_provider_silent_fallback_denied_pass",REQUIRED_CHECKS)
        self.assertIn("raw_secret_absent_from_evidence_pass",REQUIRED_CHECKS)
        self.assertIn("credential_authentication_enforced_pass",REQUIRED_CHECKS)
        self.assertIn("credential_a_upstream_preflight_pass",REQUIRED_CHECKS)
        self.assertIn("credential_b_upstream_preflight_pass",REQUIRED_CHECKS)
        self.assertIn("runtime_model_discovery_pass",REQUIRED_CHECKS)
    def test_no_mock_semantic_in_required_checks(self):
        self.assertFalse(any("mock" in name or "synthetic" in name for name in REQUIRED_CHECKS))
    def test_real_producer_and_two_credential_contract_are_materialized(self):
        producer=(ROOT/"bin/fa3-model-router-provider-execution-current-host.py").read_text(encoding="utf-8")
        schema=json.loads((ROOT/"canonical/contracts/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFIG-001.schema.json").read_text(encoding="utf-8"))
        self.assertIn("receipt_proves_provider",producer)
        self.assertIn("secret_broker_request",producer)
        self.assertIn('"projection": "UDS_SINGLE_SECRET"',producer)
        self.assertNotIn('str(root / "bin/fa3-secretctl")',producer)
        self.assertIn("credential_authentication_enforced",producer)
        self.assertIn("discover_working_chat_model",producer)
        self.assertIn("credential_upstream_preflight",producer)
        self.assertIn("parse_provider_error",producer)
        self.assertNotIn('error.get("message")',producer)
        self.assertIn("fa3.current-host-evidence-reference.v1",producer)
        self.assertEqual(schema["properties"]["credentials"]["minItems"],2)
    def test_sanitized_provider_error_excludes_message_and_untrusted_tokens(self):
        spec=importlib.util.spec_from_file_location(
            "fa3_provider_execution_current_host_error_test",
            ROOT/"bin/fa3-model-router-provider-execution-current-host.py",
        )
        self.assertIsNotNone(spec)
        module=importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        raw=json.dumps({
            "error":{
                "message":"sensitive account-specific text sk-DO-NOT-LOG",
                "type":"ip_not_authorized",
                "code":"invalid_api_key",
            }
        }).encode()
        self.assertEqual(
            module.parse_provider_error(raw),
            ("ip_not_authorized","invalid_api_key"),
        )
        raw=json.dumps({"error":{"type":"bad token with spaces","code":{"nested":True}}}).encode()
        self.assertEqual(
            module.parse_provider_error(raw),
            ("unspecified","unspecified"),
        )

    def test_terminal_billing_blocker_is_fail_closed(self):
        spec=importlib.util.spec_from_file_location(
            "fa3_provider_execution_current_host_billing_test",
            ROOT/"bin/fa3-model-router-provider-execution-current-host.py",
        )
        self.assertIsNotNone(spec)
        module=importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        self.assertTrue(module.terminal_billing_blocker(
            module.ProviderHTTPError(429,"insufficient_quota","credit_balance_exhausted")
        ))
        self.assertTrue(module.terminal_billing_blocker(
            module.ProviderHTTPError(429,"insufficient_quota","project_spend_limit_exceeded")
        ))
        self.assertFalse(module.terminal_billing_blocker(
            module.ProviderHTTPError(429,"rate_limit_error","rate_limit_exceeded")
        ))
        self.assertFalse(module.terminal_billing_blocker(
            module.ProviderHTTPError(404,"invalid_request_error","model_not_found")
        ))

    def test_endpoint_paths_are_relative_to_api_base(self):
        spec=importlib.util.spec_from_file_location(
            "fa3_provider_execution_current_host",
            ROOT/"bin/fa3-model-router-provider-execution-current-host.py",
        )
        self.assertIsNotNone(spec)
        module=importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.url_join("http://127.0.0.1:12345/v1","models"),
            "http://127.0.0.1:12345/v1/models",
        )
        self.assertEqual(
            module.url_join("http://127.0.0.1:12345/v1","chat/completions"),
            "http://127.0.0.1:12345/v1/chat/completions",
        )
        with self.assertRaises(module.ProbeDenied):
            module.url_join("http://127.0.0.1:12345/v1","/v1/models")

    def test_provisioning_harness_shell_syntax(self):
        subprocess.run(["bash","-n",str(ROOT/"bin/fa3-model-router-provider-execution-current-host-provision.sh")],check=True)
        harness=(ROOT/"bin/fa3-model-router-provider-execution-current-host-provision.sh").read_text(encoding="utf-8")
        self.assertIn("/dev/tty",harness)
        self.assertIn("fa3-provider-exec-probe.service",harness)
        self.assertIn("SupplementaryGroups=fa3-secret-clients",harness)
        self.assertIn('"allowed_executables":[]',harness)
        self.assertNotIn('"allowed_executables":[python_exe]',harness)
        self.assertIn('"allowed_systemd_units":[unit]',harness)
        self.assertIn('"models_path":"models"',harness)
        self.assertIn('"chat_path":"chat/completions"',harness)
        self.assertNotIn('"models_path":"/v1/models"',harness)
        self.assertNotIn('"chat_path":"/v1/chat/completions"',harness)
        self.assertIn("CURRENT_HOST_PASS",harness)
        self.assertIn("--preferred-model",harness)
        self.assertIn("evidence/reference/secret-broker-current-host-2026-09-24.json",harness)
        self.assertNotIn('SECRET_RECEIPT_REFERENCE="$ROOT/evidence/reference/secret-broker-current-host-2026-09-21.json"',harness)
        self.assertIn('conformance.get("production_runtime_promoted") is not True',harness)
        self.assertIn('gate.get("production_runtime_promoted") is not True',harness)
        self.assertIn('enforcement.get("production_runtime_promoted") is not True',harness)
        self.assertNotIn('/usr/local/libexec/fa3-secret-broker-current-host-root >/dev/null',harness)
        self.assertIn("/var/lib/fa3/state/fa3-machine-state.img",harness)
        self.assertIn("/etc/credstore.encrypted/fa3-machine-state-key.cred",harness)
        self.assertIn("sudo /usr/local/sbin/fa3-secret-vault-init",harness)
        self.assertIn("cmp -s",harness)
        self.assertIn("sudo bash bin/fa3-secret-broker-install",harness)
        self.assertIn("provisioning_cleanup_pass",harness)
        self.assertIn("stale provider execution probe identity detected",harness)
        self.assertIn('systemctl is-active --quiet "$PROBE_UNIT"',harness)
        self.assertIn('pgrep -u "$PROBE_USER"',harness)
        self.assertIn("stale reserved provider-execution SecretRef detected",harness)
        self.assertIn("stale reserved provider-execution policy detected and removed",harness)
        self.assertIn('/usr/local/sbin/fa3-secret-policyctl remove "$sid"',harness)
        self.assertNotIn('/usr/local/sbin/fa3-secret-policyctl show "$sid"',harness)
        self.assertIn('userdel "$PROBE_USER"',harness)
        self.assertLess(harness.index('if ! cleanup; then'),harness.index('echo "FA3 PROVIDER EXECUTION CURRENT-HOST: PASS"'))
        marker='python3 - "$SECRET_RECEIPT_REFERENCE" "$ROOT/canonical/FA3-SECRET-BROKER-RUNTIME-CONFORMANCE-001.json" "$ROOT/canonical/FA3-GATE-SECRET-BROKER-001.json" "$ROOT/canonical/secret-broker-enforcement.json" <<\'PY\'\n'
        self.assertIn(marker,harness)
        embedded=harness.split(marker,1)[1].split("\nPY\n",1)[0]
        compile(embedded,"secret-receipt-validator","exec")
        self.assertNotIn('if (\\n',embedded)

    def test_openai_evidence_adapter_is_bounded_and_explicit(self):
        subprocess.run(["bash","-n",str(ROOT/"bin/fa3-openai-provider-execution-current-host-close.sh")],check=True)
        bridge=(ROOT/"bin/fa3-openai-loopback-bridge.py").read_text(encoding="utf-8")
        closer=(ROOT/"bin/fa3-openai-provider-execution-current-host-close.sh").read_text(encoding="utf-8")
        provider=json.loads((ROOT/"canonical/providers/FA3-PROVIDER-OPENAI-API-001.json").read_text(encoding="utf-8"))
        policy=json.loads((ROOT/"canonical/FA3-OPENAI-API-EXTERNAL-POLICY-001.json").read_text(encoding="utf-8"))
        self.assertIn("https://api.openai.com/v1",bridge)
        subprocess.run([sys.executable,"-m","py_compile",str(ROOT/"bin/fa3-openai-loopback-bridge.py")],check=True)
        self.assertIn("HTTPSHandler(context=ssl.create_default_context())",bridge)
        self.assertNotIn("open(req, timeout=180.0, context=",bridge)
        self.assertIn("fixed FA3 provider-execution probe content",bridge)
        self.assertIn("FA3-PROVIDER-OPENAI-API-001",closer)
        self.assertIn("runtime discovery from this API project",closer)
        self.assertIn("FA3_OPENAI_PROBE_MODEL",closer)
        self.assertNotIn("gpt-4o-mini",closer)
        self.assertIn("/dev/tty",closer)
        self.assertIn("PROVISION_RC=$?",closer)
        self.assertIn("closure PASS withheld",closer)
        self.assertIn('rm -f "$PROVIDER_SOURCE" "$PROVIDER_RECEIPT"',closer)
        self.assertIn('trap \'exit 130\' INT',closer)
        self.assertIn('trap \'exit 143\' TERM',closer)
        self.assertIn('PROVIDER_RUN_ROOT="/run/fa3/model-router-provider-execution"',closer)
        self.assertIn('PROVIDER_RECEIPT="$PROVIDER_RUN_ROOT/current-host-receipt.json"',closer)
        self.assertNotIn("/run/fa3/model-router/provider-execution/current-host-receipt.json",closer)
        self.assertIn("fa3.model-router-provider-execution-current-host.v1",closer)
        self.assertIn("CURRENT_HOST_REAL_PROVIDER_EXECUTION_E2E_PASS",closer)
        self.assertIn("provisioning_cleanup_pass",closer)
        self.assertIn("stale provider execution probe identity detected",closer)
        self.assertIn("provisioner recovery will validate and remove it",closer)
        self.assertNotIn("safe recovery: sudo userdel fa3-provider-exec-probe",closer)
        self.assertIn("systemctl is-active --quiet fa3-provider-exec-probe.service",closer)
        self.assertIn("pgrep -u fa3-provider-exec-probe",closer)
        self.assertIn('getent group fa3-secret-clients',closer)
        self.assertIn('chown root:fa3-secret-clients "$ADMISSION_RECEIPT"',closer)
        self.assertIn('chmod 0640 "$ADMISSION_RECEIPT"',closer)
        self.assertNotIn('chmod 0644 "$ADMISSION_RECEIPT"',closer)
        self.assertLess(closer.index("PROVISION_RC=$?"),closer.index("FA3 OPENAI PROVIDER EXECUTION CURRENT-HOST CLOSURE: PASS"))
        self.assertFalse(provider["normal_application_routing_enabled"])
        self.assertEqual("FA3-SECRET-BROKER-001",provider["authority_boundaries"]["secrets"])
        self.assertFalse(policy["activation"]["automatic_activation"])
        self.assertFalse(policy["activation"]["silent_local_to_cloud_fallback"])
if __name__=="__main__": unittest.main()
