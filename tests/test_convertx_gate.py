import json
import tempfile
import unittest
from pathlib import Path

import fa3_convertx_adapter as a
import fa3_convertx_gate as g


class ConvertXGateTests(unittest.TestCase):
    def setUp(self):
        self.allowlist = {
            "default_policy": "DENY",
            "candidate_pairs": [
                {
                    "from": "image/png",
                    "to": "image/jpeg",
                    "state": "CANDIDATE",
                    "provider_converter": "vips",
                    "provider_target": "jpeg",
                }
            ],
        }
        self.active_allowlist = {
            "default_policy": "DENY",
            "candidate_pairs": [
                {
                    "from": "image/png",
                    "to": "image/jpeg",
                    "state": "ACTIVE",
                    "provider_converter": "vips",
                    "provider_target": "jpeg",
                }
            ],
        }
        self.runtime = {
            "non_root": True,
            "read_only_root": True,
            "cap_drop_all": True,
            "no_new_privileges": True,
            "seccomp": True,
            "resource_limits": True,
            "ephemeral_workspace": True,
            "host_mounts": "DENY",
            "outbound_network": "DENY",
            "image": "ghcr.io/c4illin/convertx@sha256:" + "a" * 64,
        }
        self.candidate_provider = {
            "status": "QUARANTINED",
            "machine_interface": {
                "machine_execution_enabled": False,
                "fa3_adapter_execution_contract_materialized": True,
                "fa3_candidate_executor_materialized": True,
                "candidate_validation_allowed_while_quarantined": True,
                "candidate_validation_is_production_routing": False,
            },
        }

    def test_regressions_pass(self):
        result = g.run_regressions()
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual(15, result["passed"])
        self.assertEqual(15, result["total"])

    def test_safe_candidate_pair_is_valid_for_planning(self):
        request = a.ConversionRequest("input.png", "image/png", "image/jpeg")
        pair = a.validate_request(request, self.allowlist)
        self.assertEqual("vips", pair["provider_converter"])

    def test_unknown_pair_is_denied(self):
        request = a.ConversionRequest("input.png", "image/png", "application/pdf")
        with self.assertRaises(a.AdmissionDenied):
            a.validate_request(request, self.allowlist)

    def test_xelatex_is_denied(self):
        request = a.ConversionRequest(
            "input.png", "image/png", "image/jpeg", converter_name="XeLaTeX"
        )
        with self.assertRaises(a.AdmissionDenied):
            a.validate_request(request, self.allowlist)

    def test_tex_input_is_denied(self):
        request = a.ConversionRequest("payload.tex", "image/png", "image/jpeg")
        with self.assertRaises(a.AdmissionDenied):
            a.validate_request(request, self.allowlist)

    def test_arbitrary_arguments_are_denied(self):
        request = a.ConversionRequest(
            "input.png", "image/png", "image/jpeg", provider_arguments=("--foo",)
        )
        with self.assertRaises(a.AdmissionDenied):
            a.validate_request(request, self.allowlist)

    def test_floating_image_is_denied(self):
        with self.assertRaises(a.AdmissionDenied):
            a.validate_runtime_contract({**self.runtime, "image": "ghcr.io/c4illin/convertx:latest"})

    def test_unrestricted_egress_is_denied(self):
        with self.assertRaises(a.AdmissionDenied):
            a.validate_runtime_contract({**self.runtime, "outbound_network": "ALLOW"})

    def test_candidate_validation_can_run_before_provider_promotion(self):
        request = a.ConversionRequest(
            "input.png", "image/png", "image/jpeg", hrb_lease_path="lease.json"
        )
        result = a.candidate_validation_admission(
            request,
            self.candidate_provider,
            self.allowlist,
            self.runtime,
            explicit=True,
        )
        self.assertEqual("ALLOW_CANDIDATE_VALIDATION", result["result"])
        self.assertFalse(result["production_routing_enabled"])
        self.assertEqual("vips", result["provider_converter"])

    def test_candidate_validation_must_be_explicit(self):
        request = a.ConversionRequest(
            "input.png", "image/png", "image/jpeg", hrb_lease_path="lease.json"
        )
        with self.assertRaises(a.AdmissionDenied):
            a.candidate_validation_admission(
                request,
                self.candidate_provider,
                self.allowlist,
                self.runtime,
                explicit=False,
            )

    def test_candidate_pair_is_not_production_active(self):
        provider = {
            "status": "APPROVED",
            "machine_interface": {
                "machine_execution_enabled": True,
                "fa3_adapter_execution_contract_materialized": True,
                "fa3_candidate_executor_materialized": True,
            },
        }
        request = a.ConversionRequest(
            "input.png", "image/png", "image/jpeg", hrb_lease_path="lease.json"
        )
        with self.assertRaises(a.AdmissionDenied):
            a.machine_execution_admission(request, provider, self.allowlist, self.runtime, {})

    def test_quarantined_provider_cannot_production_execute(self):
        request = a.ConversionRequest(
            "input.png", "image/png", "image/jpeg", hrb_lease_path="lease.json"
        )
        with self.assertRaises(a.ProviderQuarantined):
            a.machine_execution_admission(
                request,
                self.candidate_provider,
                self.active_allowlist,
                self.runtime,
                None,
            )

    def test_receipt_requires_real_e2e_properties(self):
        bad = {
            "schema": "fa3.convertx-current-host-receipt.v1",
            "provider_id": a.PROVIDER_ID,
            "status": "PASS",
            "evidence_level": "CURRENT_HOST_PRODUCTION_E2E_PASS",
            "candidate_validation": True,
            "production_routing_enabled": False,
            "synthetic_input": True,
            "real_output_hash_observed": True,
            "egress_denial_verified": True,
            "hrb_lease_verified": True,
            "provider_image": "ghcr.io/c4illin/convertx@sha256:" + "a" * 64,
        }
        with self.assertRaises(a.AdmissionDenied):
            a.validate_current_host_receipt(bad)

    def _write_gate_fixture(
        self,
        root: Path,
        *,
        adapter_contract: bool = False,
        candidate_executor: bool = False,
        machine_execution: bool = False,
    ):
        (root / "canonical").mkdir()
        docs = {
            "FA3-TOOLS-FABRIC-001.json": {
                "id": g.TOOLS_ID,
                "categories": [{"id": "CONVERSION", "canonical_execution_profile": g.PROFILE_ID}],
                "routing_contract": {"direct_provider_bypass": False},
            },
            "FA3-FILE-CONVERSION-001.json": {
                "id": g.PROFILE_ID,
                "fail_closed": True,
                "request_contract": {"arbitrary_cli_arguments_allowed": False},
                "security": {"xelatex": "DENY"},
            },
            "FA3-PROVIDER-CONVERTX-001.json": {
                "id": g.PROVIDER_ID,
                "status": "QUARANTINED",
                "machine_interface": {
                    "official_public_api_available": False,
                    "fa3_adapter_execution_contract_materialized": adapter_contract,
                    "fa3_candidate_executor_materialized": candidate_executor,
                    "candidate_validation_allowed_while_quarantined": True,
                    "candidate_validation_is_production_routing": False,
                    "machine_execution_enabled": machine_execution,
                },
                "upstream": {"production_tag_floating_allowed": False},
                "current_host_status": "PENDING_REAL_HOST_EXECUTION",
            },
            "FA3-CONVERTX-CONVERSION-ALLOWLIST-001.json": {
                "id": g.ALLOWLIST_ID,
                "default_policy": "DENY",
                "arbitrary_converter_arguments_allowed": False,
                "candidate_pairs": [
                    {
                        "from": "image/png",
                        "to": "image/jpeg",
                        "state": "CANDIDATE",
                        "provider_converter": "vips",
                        "provider_target": "jpeg",
                    }
                ],
                "explicit_denials": [{"converter_family": "XeLaTeX"}],
            },
            "FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json": {
                "id": g.CONFORMANCE_ID,
                "ci_conformance": {"current_host_claim_forbidden": True},
            },
        }
        for name, doc in docs.items():
            (root / "canonical" / name).write_text(json.dumps(doc), encoding="utf-8")

    def test_canonical_gate_passes_quarantine_without_executor_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_gate_fixture(root)
            result = g.gate(root)
            self.assertEqual("PASS", result["result"], result)
            self.assertEqual("QUARANTINED", result["provider_status"])
            self.assertFalse(result["machine_execution_enabled"])
            self.assertFalse(result["candidate_executor_materialized"])

    def test_quarantine_may_materialize_candidate_contract_without_production_routing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_gate_fixture(root, adapter_contract=True, candidate_executor=True)
            result = g.gate(root)
            self.assertEqual("PASS", result["result"], result)
            self.assertTrue(result["adapter_execution_contract_materialized"])
            self.assertTrue(result["candidate_executor_materialized"])
            self.assertFalse(result["machine_execution_enabled"])

    def test_quarantine_cannot_enable_production_machine_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_gate_fixture(root, adapter_contract=True, candidate_executor=True, machine_execution=True)
            result = g.gate(root)
            self.assertEqual("FAIL", result["result"], result)
            self.assertTrue(any(x["code"] == "CONVERTX-QUARANTINE-BYPASS" for x in result["findings"]))


if __name__ == "__main__":
    unittest.main()
