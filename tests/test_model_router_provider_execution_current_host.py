import json, tempfile, unittest, subprocess, sys
from pathlib import Path
from fa3_model_router_provider_execution_current_host_gate import REQUIRED_CHECKS

ROOT=Path(__file__).resolve().parents[1]

class CurrentHostReceiptContractTests(unittest.TestCase):
    def test_required_matrix_contains_rollback_and_negative_boundaries(self):
        self.assertIn("rollback_pass",REQUIRED_CHECKS)
        self.assertIn("unadmitted_provider_denied_pass",REQUIRED_CHECKS)
        self.assertIn("cross_provider_silent_fallback_denied_pass",REQUIRED_CHECKS)
        self.assertIn("raw_secret_absent_from_evidence_pass",REQUIRED_CHECKS)
        self.assertIn("credential_authentication_enforced_pass",REQUIRED_CHECKS)
        self.assertIn("runtime_model_discovery_pass",REQUIRED_CHECKS)
    def test_no_mock_semantic_in_required_checks(self):
        self.assertFalse(any("mock" in name or "synthetic" in name for name in REQUIRED_CHECKS))
    def test_real_producer_and_two_credential_contract_are_materialized(self):
        producer=(ROOT/"bin/fa3-model-router-provider-execution-current-host.py").read_text(encoding="utf-8")
        schema=json.loads((ROOT/"canonical/contracts/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFIG-001.schema.json").read_text(encoding="utf-8"))
        self.assertIn("receipt_proves_provider",producer)
        self.assertIn("fa3-secretctl",producer)
        self.assertIn("credential_authentication_enforced",producer)
        self.assertIn("discover_working_chat_model",producer)
        self.assertIn("fa3.current-host-evidence-reference.v1",producer)
        self.assertEqual(schema["properties"]["credentials"]["minItems"],2)
    def test_provisioning_harness_shell_syntax(self):
        subprocess.run(["bash","-n",str(ROOT/"bin/fa3-model-router-provider-execution-current-host-provision.sh")],check=True)
        harness=(ROOT/"bin/fa3-model-router-provider-execution-current-host-provision.sh").read_text(encoding="utf-8")
        self.assertIn("/dev/tty",harness)
        self.assertIn("fa3-provider-exec-probe.service",harness)
        self.assertIn("SupplementaryGroups=fa3-secret-clients",harness)
        self.assertIn("CURRENT_HOST_PASS",harness)
        self.assertIn("--preferred-model",harness)
        self.assertIn("evidence/reference/secret-broker-current-host-2026-09-21.json",harness)
        self.assertNotIn('/usr/local/libexec/fa3-secret-broker-current-host-root >/dev/null',harness)
        marker="python3 - \"$SECRET_RECEIPT_REFERENCE\" <<'PY'\n"
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
        self.assertFalse(provider["normal_application_routing_enabled"])
        self.assertEqual("FA3-SECRET-BROKER-001",provider["authority_boundaries"]["secrets"])
        self.assertFalse(policy["activation"]["automatic_activation"])
        self.assertFalse(policy["activation"]["silent_local_to_cloud_fallback"])
if __name__=="__main__": unittest.main()
