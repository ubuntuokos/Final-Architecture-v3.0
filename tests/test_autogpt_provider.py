from __future__ import annotations

import unittest

from fa3_autogpt_provider import (
    AdmissionError,
    AutoGPTProvider,
    CAPABILITY,
    PROVIDER_ID,
    REQUEST_SCHEMA,
    STORE_VALUE_BLOCK_ID,
    canonical_digest,
    validate_request,
)


def good_request():
    return {
        "schema": REQUEST_SCHEMA,
        "request_id": "req-1",
        "caller_identity": "user-1",
        "delegation_id": "delegation-1",
        "workflow_run_id": "workflow-1",
        "capability_id": "CAP-028",
        "provider_id": PROVIDER_ID,
        "block_id": STORE_VALUE_BLOCK_ID,
        "authorization_decision": {
            "authority": "FA3-AUTH-SECURITY-GOV-001",
            "decision": "ALLOW",
            "decision_id": "policy-1",
            "capabilities": [CAPABILITY],
        },
        "mcp_admission": {
            "authority": "FA3-AUTH-MCP-GATEWAY-001",
            "decision": "ALLOW",
            "admission_id": "mcp-1",
            "capability": CAPABILITY,
        },
        "host_resource_admission": {
            "authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "decision": "ALLOW",
            "admission_id": "hrb-1",
            "resource_class": "CPU_RAM_ONLY",
            "accelerator_lease_id": "NONE_REQUIRED",
        },
        "input": {"input": "fa3-autogpt-nonce"},
        "timeout_seconds": 10,
        "network_egress_allowed": False,
    }


class AutoGPTProviderTests(unittest.TestCase):
    def test_request_admitted(self):
        validate_request(good_request())

    def test_missing_delegation_denied(self):
        r=good_request(); r["delegation_id"]=""
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_external_policy_deny_denied(self):
        r=good_request(); r["authorization_decision"]["decision"]="DENY"
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_mcp_bypass_denied(self):
        r=good_request(); r["mcp_admission"]["authority"]=PROVIDER_ID
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_accelerator_request_denied(self):
        r=good_request(); r["host_resource_admission"]["accelerator_lease_id"]="gpu-lease"
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_unknown_block_denied(self):
        r=good_request(); r["block_id"]="00000000-0000-0000-0000-000000000000"
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_remote_provider_url_denied(self):
        with self.assertRaises(AdmissionError):
            AutoGPTProvider("https://example.com:443","agpt_test")

    def test_loopback_literal_required(self):
        with self.assertRaises(AdmissionError):
            AutoGPTProvider("http://localhost:58006","agpt_test")

    def test_credential_field_denied(self):
        r=good_request(); r["input"]={"input":"x","api_key":"secret"}
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_oversize_input_denied(self):
        r=good_request(); r["input"]={"input":"x"*4097}
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_timeout_denied(self):
        r=good_request(); r["timeout_seconds"]=31
        with self.assertRaises(AdmissionError): validate_request(r)

    def test_deterministic_execution_and_evidence(self):
        def fake(method,url,key,payload,timeout):
            self.assertEqual(method,"POST")
            self.assertEqual(key,"agpt_test")
            return 200, {"output":[payload["input"]]}
        p=AutoGPTProvider("http://127.0.0.1:58006","agpt_test",request_fn=fake)
        result=p.execute(good_request())
        self.assertEqual(result["result_status"],"PASS")
        self.assertFalse(result["secret_material_recorded"])
        self.assertTrue(result["input_digest"].startswith("sha256:"))
        self.assertTrue(result["output_digest"].startswith("sha256:"))

    def test_unauthenticated_probe(self):
        def fake(method,url,key,payload,timeout):
            return 401, {"detail":"Missing authentication"}
        p=AutoGPTProvider("http://127.0.0.1:58006","agpt_test",request_fn=fake)
        self.assertTrue(p.unauthenticated_denied())

    def test_scope_escalation_probe(self):
        def fake(method,url,key,payload,timeout):
            return 403, {"detail":"Missing required permission(s): EXECUTE_GRAPH"}
        p=AutoGPTProvider("http://127.0.0.1:58006","agpt_test",request_fn=fake)
        self.assertTrue(p.graph_scope_escalation_denied())

    def test_digest_is_canonical(self):
        self.assertEqual(canonical_digest({"b":2,"a":1}), canonical_digest({"a":1,"b":2}))


if __name__=="__main__":
    unittest.main()
