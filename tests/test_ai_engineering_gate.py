import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_release_baseline import module_active_capability_count
import fa3_ai_engineering_gate as a


class AIEngineeringGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    def _write(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        r = a.gate(ROOT)
        self.assertEqual(r["result"], "PASS", r)
        self.assertEqual(r["gate_id"], a.GATE_ID)
        self.assertEqual(r["source_id"], a.SOURCE_ID)
        self.assertEqual(r["capability_count"], module_active_capability_count(__file__))
        self.assertFalse(r["runtime_provider_required"])
        self.assertFalse(r["current_host_runtime_evidence_required"])
        self.assertEqual(r["reuse_governance"]["result"], "PASS")
        self.assertEqual(r["regressions"]["passed"], 14)

    def test_regression_matrix_14_of_14(self):
        r = a.run_regressions()
        self.assertEqual(r["result"], "PASS", r)
        self.assertEqual((r["passed"], r["total"]), (14, 14))

    def test_registry_publication_not_admission(self):
        self.assertFalse(a.registry_admission_valid(
            published=True, immutable_identity=False, integrity_verified=False,
            provenance_verified=False, policy_admitted=False))
        self.assertTrue(a.registry_admission_valid(
            published=True, immutable_identity=True, integrity_verified=True,
            provenance_verified=True, policy_admitted=True))

    def test_skill_context_is_not_authority(self):
        self.assertFalse(a.execution_control_valid(
            context_or_skill_active=True, capability_exposed=True, authorized=False,
            approval_required=False, approved=False, sandboxed=True, verification_ready=True))

    def test_agent_cannot_self_promote(self):
        self.assertFalse(a.completion_state_valid(
            requested_state="PROMOTED", deterministic_gate_pass=False,
            independent_of_actor_claim=False, evidence_bound=True))
        self.assertTrue(a.completion_state_valid(
            requested_state="PROMOTED", deterministic_gate_pass=True,
            independent_of_actor_claim=True, evidence_bound=True))

    def test_execution_evidence_requires_environment_identity(self):
        e = {
            "command": "tool", "argv": ["tool"], "cwd": "/w",
            "actor_identity": "agent", "capability_or_request_id": "REQ-1",
            "input_artifact_refs": [], "exit_code": 0, "output_artifact_refs": []
        }
        self.assertFalse(a.execution_evidence_valid(e))
        e["environment_identity"] = "env@sha256:abc"
        self.assertTrue(a.execution_evidence_valid(e))

    def test_negative_and_boundary_evidence_required(self):
        self.assertFalse(a.conformance_evidence_valid(positive=True, negative=False, boundary=True))
        self.assertTrue(a.conformance_evidence_valid(positive=True, negative=True, boundary=True))

    def test_raw_boundary_and_adapter_projection_both_required(self):
        self.assertFalse(a.protocol_projection_evidence_valid(
            raw_boundary=False, adapter_projection=True, same_exchange_identity=True))

    def test_ingress_origin_egress_all_required(self):
        self.assertFalse(a.gateway_trace_valid(
            ingress=True, origin=False, egress=True, correlation_id="c"))
        self.assertTrue(a.gateway_trace_valid(
            ingress=True, origin=True, egress=True, correlation_id="c"))

    def test_automatic_downgrade_denied(self):
        self.assertFalse(a.downgrade_allowed(
            explicit_permission=False, bounded_scope=True,
            target_version="v1", compatibility_evidence=True))

    def test_redaction_must_precede_persistence(self):
        self.assertFalse(a.redaction_order_valid(["SERIALIZE", "REDACT", "HASH", "STORE"]))
        self.assertTrue(a.redaction_order_valid(["REDACT", "SERIALIZE", "HASH", "STORE"]))

    def test_rollback_readiness_required(self):
        self.assertFalse(a.rollback_ready(
            target_version="v1", artifact_digest="", health_evidence=True,
            route_restore_procedure=True, trusted_readiness_evidence=True))

    def test_progressive_disclosure_cannot_grant_authority(self):
        self.assertFalse(a.progressive_disclosure_valid(
            discovered=True, activated=False, branch_context_loaded=True, grants_authority=False))
        self.assertFalse(a.progressive_disclosure_valid(
            discovered=True, activated=True, branch_context_loaded=True, grants_authority=True))
        self.assertTrue(a.progressive_disclosure_valid(
            discovered=True, activated=True, branch_context_loaded=True, grants_authority=False))

    def test_reference_source_cannot_auto_install_or_activate(self):
        self.assertFalse(a.reference_reuse_boundary_valid(
            reference_only=True, automatic_fetch=False, automatic_install=True,
            automatic_activation=False, authority=False))
        self.assertTrue(a.reference_reuse_boundary_valid(
            reference_only=True, automatic_fetch=False, automatic_install=False,
            automatic_activation=False, authority=False))

    def test_software_coexistence_forbids_host_hijack(self):
        self.assertFalse(a.coexistence_boundary_valid(
            namespaced=True, upstream_uninstall_required=False,
            global_mutation=True, default_port_hijack=False))
        self.assertFalse(a.coexistence_boundary_valid(
            namespaced=True, upstream_uninstall_required=True,
            global_mutation=False, default_port_hijack=False))
        self.assertTrue(a.coexistence_boundary_valid(
            namespaced=True, upstream_uninstall_required=False,
            global_mutation=False, default_port_hijack=False))

    def test_hardware_audit_is_vendor_neutral_and_does_not_claim_runtime(self):
        self.assertFalse(a.hardware_reference_valid(
            vendor_neutral=True, cpu_only_viable=True, accelerator_cardinality="1",
            global_accelerator_requirement=True, current_host_runtime_promotion_claim=True))
        self.assertTrue(a.hardware_reference_valid(
            vendor_neutral=True, cpu_only_viable=True, accelerator_cardinality="0..N",
            global_accelerator_requirement=False, current_host_runtime_promotion_claim=False))

    def test_reuse_catalog_exposes_reference_and_pattern_bundle_non_authoritatively(self):
        r = a.reuse_governance_check(ROOT)
        self.assertEqual(r["result"], "PASS", r)
        self.assertGreater(r["catalog_entry_count"], 0)

    def test_reference_commit_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/references/FA3-AI-ENGINEERING-UPSTREAM-REFERENCE-2026-08-30.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["immutable_reference_commit"] = "main"
            self._write(p, o)
            self.assertEqual(a.gate(root)["result"], "FAIL")
        finally:
            td.cleanup()

    def test_missing_reuse_assessment_fails_closed(self):
        td, root = self._copy_root()
        try:
            (root / "canonical/assessments/FA3-AI-ENGINEERING-REFERENCE-REUSE-ASSESSMENT-001.json").unlink()
            r = a.gate(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertEqual(r["reuse_governance"]["result"], "FAIL")
        finally:
            td.cleanup()

    def test_pattern_bundle_authority_escalation_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/patterns/FA3-AI-ENGINEERING-DERIVED-PATTERNS-001.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["authority"] = True
            self._write(p, o)
            r = a.gate(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertEqual(r["reuse_governance"]["result"], "FAIL")
        finally:
            td.cleanup()

    def test_release_projection_reconciliation_missing_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o.pop("ai_engineering_reference_reconciliation", None)
            self._write(p, o)
            r = a.gate(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertTrue(any(
                x["code"] == "AIENG-REUSE-015"
                for x in r["reuse_governance"]["findings"]
            ))
        finally:
            td.cleanup()

    def test_source_authority_escalation_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/ai-engineering-authority-escalation.json"
            self._write(p, {
                "schema": "fa3.test.v1",
                "id": "T",
                "evidence_authority": a.SOURCE_ID
            })
            r = a.gate(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertEqual(r["authority_scan"]["result"], "FAIL")
        finally:
            td.cleanup()

    def test_policy_binding_is_required(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/enforcement-policy.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["mandatory_reference_gates"] = [
                x for x in o["mandatory_reference_gates"] if x != a.GATE_ID
            ]
            self._write(p, o)
            r = a.gate(root)
            self.assertEqual(r["result"], "FAIL")
            self.assertTrue(any(x["code"] == "AIENG-REF-009" for x in r["reference"]["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
