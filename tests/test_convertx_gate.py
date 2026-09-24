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
            "candidate_pairs": [{
                "from": "image/png", "to": "image/jpeg", "state": "CANDIDATE",
                "provider_converter": "vips", "provider_target": "jpeg",
            }],
        }
        self.active_allowlist = {
            "default_policy": "DENY",
            "candidate_pairs": [{
                "from": "image/png", "to": "image/jpeg", "state": "ACTIVE",
                "provider_converter": "vips", "provider_target": "jpeg",
            }],
        }
        self.runtime = {
            "non_root": True, "read_only_root": True, "cap_drop_all": True,
            "no_new_privileges": True, "seccomp": True, "resource_limits": True,
            "ephemeral_workspace": True, "host_mounts": "DENY", "outbound_network": "DENY",
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
        self.assertEqual(16, result["passed"])
        self.assertEqual(16, result["total"])

    def test_safe_candidate_pair_is_valid_for_planning(self):
        request = a.ConversionRequest("input.png", "image/png", "image/jpeg")
        self.assertEqual("vips", a.validate_request(request, self.allowlist)["provider_converter"])

    def test_unknown_pair_is_denied(self):
        with self.assertRaises(a.AdmissionDenied):
            a.validate_request(a.ConversionRequest("input.png", "image/png", "application/pdf"), self.allowlist)

    def test_quarantined_provider_cannot_production_execute(self):
        request = a.ConversionRequest("input.png", "image/png", "image/jpeg", resource_admission_path="resource.json")
        with self.assertRaises(a.ProviderQuarantined):
            a.machine_execution_admission(
                request, self.candidate_provider, self.active_allowlist, self.runtime, None,
                resource_admission_verified=True,
            )

    def _write_gate_fixture(self, root: Path, *, machine_execution: bool = False):
        (root / "canonical/contracts").mkdir(parents=True)
        (root / "canonical/assessments").mkdir()
        (root / "canonical/actions").mkdir()
        (root / "apps/fa3-control-center/qml").mkdir(parents=True)
        (root / "src").mkdir()
        (root / g.EXECUTOR_PATH).write_text("# executor\n", encoding="utf-8")

        docs = {
            "FA3-TOOLS-FABRIC-001.json": {
                "id": g.TOOLS_ID,
                "categories": [{"id": "CONVERSION", "canonical_execution_profile": g.PROFILE_ID}],
                "gui_contract": {"route_id": "create.tools", "direct_execution": False},
                "routing_contract": {
                    "direct_provider_bypass": False,
                    "execution_fabric": "FA3-UNIFIED-ACTION-FABRIC-001",
                },
            },
            "FA3-FILE-CONVERSION-001.json": {
                "id": g.PROFILE_ID,
                "fail_closed": True,
                "request_contract": {"arbitrary_cli_arguments_allowed": False},
                "security": {"xelatex": "DENY"},
                "execution_fabric": "FA3-UNIFIED-ACTION-FABRIC-001",
                "uaf_actions": sorted(g.ACTION_IDS),
                "routing": {"policy": "SPECIALIZED_PROVIDER_FIRST"},
                "decision_fabric": {"provider_selection_authority": False},
            },
            "FA3-PROVIDER-CONVERTX-001.json": {
                "id": g.PROVIDER_ID,
                "status": "QUARANTINED",
                "distribution_class": "USER_LOCAL_EXTERNAL",
                "product_bundle_allowed": False,
                "execution_boundary": {"direct_gui_provider_bypass": False},
                "machine_interface": {
                    "official_public_api_available": False,
                    "fa3_adapter_execution_contract_materialized": True,
                    "fa3_candidate_executor_materialized": True,
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
                "candidate_pairs": [{
                    "from": "image/png", "to": "image/jpeg", "state": "CANDIDATE",
                    "provider_converter": "vips", "provider_target": "jpeg",
                }],
                "explicit_denials": [{"converter_family": "XeLaTeX"}],
            },
            "FA3-CONVERTX-RUNTIME-CONFORMANCE-001.json": {
                "id": g.CONFORMANCE_ID,
                "ci_conformance": {"current_host_claim_forbidden": True},
                "resource_admission": {
                    "current_authoritative_cpu_memory_verifier": "HRB_NON_ACCELERATOR_AUTHORIZATION_UNMATERIALIZED",
                    "existing_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
                },
            },
        }
        for name, doc in docs.items():
            (root / "canonical" / name).write_text(json.dumps(doc), encoding="utf-8")

        contract = {
            "id": g.CONTRACT_ID,
            "upstream_reference": {"release": "v0.18.0"},
            "scope": "CANDIDATE_VALIDATION_ONLY",
            "production_routing": False,
            "endpoint_policy": {"base_url": "LOOPBACK_ONLY"},
            "execution_boundary": {
                "fabric": "FA3-UNIFIED-ACTION-FABRIC-001",
                "direct_agent_provider_bypass": False,
            },
        }
        (root / "canonical/contracts/FA3-CONVERTX-ADAPTER-CONTRACTS-001.json").write_text(json.dumps(contract), encoding="utf-8")

        assessment = {
            "assessment": "OPTIONAL",
            "covered_ids": [g.TOOLS_ID, g.PROFILE_ID, g.PROVIDER_ID],
            "project_radar_checked": True,
        }
        (root / "canonical/assessments/FA3-TOOLS-FILE-CONVERSION-DECISION-ASSESSMENT-2026-09-24.json").write_text(json.dumps(assessment), encoding="utf-8")

        (root / "canonical/distribution-registry.json").write_text(json.dumps({
            "records": [{"subject_id": g.PROVIDER_ID, "class": "USER_LOCAL_EXTERNAL", "release_bundle_status": "EXCLUDED"}]
        }), encoding="utf-8")
        (root / "canonical/FA3-GUI-SURFACE-REGISTRY-001.json").write_text(json.dumps({
            "surfaces": [{"route_id": "create.tools", "mutation": "DRAFT_ONLY"}]
        }), encoding="utf-8")

        for action_id in g.ACTION_IDS:
            payload = {
                "schema": "fa3.uaf.action-contract.v1",
                "id": action_id,
                "resources": {"hrb_required": action_id == "file.convert.execute"},
            }
            (root / "canonical/actions" / f"{action_id}.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_canonical_gate_passes_materialized_quarantine(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_gate_fixture(root)
            result = g.gate(root)
            self.assertEqual("PASS", result["result"], result)
            self.assertEqual("HRB_NON_ACCELERATOR_AUTHORIZATION_UNMATERIALIZED", result["resource_admission_state"])
            self.assertFalse(result["machine_execution_enabled"])

    def test_quarantine_cannot_enable_production_machine_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_gate_fixture(root, machine_execution=True)
            result = g.gate(root)
            self.assertEqual("FAIL", result["result"], result)
            self.assertTrue(any(x["code"] == "CONVERTX-QUARANTINE-BYPASS" for x in result["findings"]))


if __name__ == "__main__":
    unittest.main()
