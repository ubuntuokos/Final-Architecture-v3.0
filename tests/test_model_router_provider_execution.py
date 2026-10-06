import unittest
from fa3_model_router_provider_execution import CredentialCandidate, ExecutionDenied, ProviderExecutionManager, choose_credential, rebind_action, protocol_projection_status, execution_receipt
from fa3_model_router_provider_execution_gate import regressions

class ProviderExecutionTests(unittest.TestCase):
    def test_regression_matrix(self): self.assertEqual(regressions()["result"],"PASS")
    def test_session_affinity(self):
        rows=[CredentialCandidate("p","secretref:p/a","HEALTHY",True),CredentialCandidate("p","secretref:p/b","HEALTHY",True)]
        self.assertEqual(choose_credential(rows,provider_id="p",session_credential_ref="secretref:p/b").credential_ref,"secretref:p/b")
    def test_unadmitted_provider_is_not_eligible(self):
        with self.assertRaises(ExecutionDenied): choose_credential([CredentialCandidate("p","secretref:p/a","HEALTHY",False)],provider_id="p")
    def test_cross_provider_requires_router(self): self.assertEqual(rebind_action("QUOTA",False),"MODEL_ROUTER_REEVALUATION_REQUIRED")
    def test_security_schema_loss_fails_closed(self): self.assertEqual(protocol_projection_status(unsupported_fields={"pattern"},security_relevant_fields={"pattern"}),"UNSUPPORTED_FAIL_CLOSED")
    def test_stateful_session_affinity_and_intra_provider_rebind(self):
        rows=[CredentialCandidate("p","secretref:p/a","HEALTHY",True),CredentialCandidate("p","secretref:p/b","HEALTHY",True)]
        mgr=ProviderExecutionManager(rows,lease_ttl_seconds=30)
        first=mgr.select(provider_id="p",session_id="session",now=1)
        second=mgr.select(provider_id="p",session_id="session",now=2)
        self.assertTrue(second["reused_session_binding"])
        self.assertEqual(first["credential_ref_sha256"],second["credential_ref_sha256"])
        rb=mgr.record_failure(session_id="session",error_class="RATE_LIMIT",now=3,retry_after_seconds=60)
        self.assertEqual(rb["action"],"INTRA_PROVIDER_REBIND")
        self.assertFalse(rb["cross_provider_transition"])
        self.assertNotEqual(rb["old_credential_ref_sha256"],rb["new_credential_ref_sha256"])
    def test_circuit_breaker_never_cross_routes(self):
        mgr=ProviderExecutionManager([CredentialCandidate("p","secretref:p/a","HEALTHY",True)],circuit_threshold=1)
        mgr.select(provider_id="p",session_id="session",now=1)
        rb=mgr.record_failure(session_id="session",error_class="PROVIDER_5XX",now=2)
        self.assertEqual(rb["action"],"MODEL_ROUTER_REEVALUATION_REQUIRED")
        self.assertFalse(rb["cross_provider_transition"])
    def test_safe_snapshot_contains_hashes_not_refs(self):
        mgr=ProviderExecutionManager([CredentialCandidate("p","secretref:p/a","HEALTHY",True)])
        snap=mgr.safe_snapshot(now=1)
        self.assertFalse(snap["raw_credential_present"])
        self.assertNotIn("credential_ref",snap["credentials"][0])
        self.assertIn("credential_ref_sha256",snap["credentials"][0])
    def test_pool_traversal_is_bounded(self):
        rows=[CredentialCandidate("p",f"secretref:p/{x}","HEALTHY",True) for x in ("a","b","c","d")]
        mgr=ProviderExecutionManager(rows,max_rebind_attempts=2,max_credentials_per_request=3)
        mgr.select(provider_id="p",session_id="s",now=1)
        self.assertEqual("INTRA_PROVIDER_REBIND",mgr.record_failure(session_id="s",error_class="RATE_LIMIT",now=2)["action"])
        self.assertEqual("INTRA_PROVIDER_REBIND",mgr.record_failure(session_id="s",error_class="RATE_LIMIT",now=3)["action"])
        r=mgr.record_failure(session_id="s",error_class="RATE_LIMIT",now=4)
        self.assertEqual("MODEL_ROUTER_REEVALUATION_REQUIRED",r["action"])
        self.assertEqual("POOL_TRAVERSAL_BOUNDED",r["reason"])
        self.assertTrue(r["traversal_budget_exhausted"])
        self.assertIn(r["exhaustion_reason"],{"MAX_REBIND_ATTEMPTS_EXHAUSTED","MAX_CREDENTIALS_PER_REQUEST_EXHAUSTED"})
        self.assertFalse(r["provider_pool_exhausted"])
        self.assertLessEqual(r["pool_traversal_count"],3)
    def test_no_eligible_credential_returns_explicit_pool_exhaustion_receipt(self):
        mgr=ProviderExecutionManager([CredentialCandidate("p","secretref:p/a","HEALTHY",True)],max_rebind_attempts=3,max_credentials_per_request=3)
        mgr.select(provider_id="p",session_id="s",now=1)
        r=mgr.record_failure(session_id="s",error_class="RATE_LIMIT",now=2)
        self.assertEqual("MODEL_ROUTER_REEVALUATION_REQUIRED",r["action"])
        self.assertTrue(r["provider_pool_exhausted"])
        self.assertEqual("NO_ELIGIBLE_CREDENTIAL_REMAINING",r["exhaustion_reason"])
        self.assertFalse(r["cross_provider_transition"])

    def test_tiered_backoff_and_health_dimensions(self):
        row=CredentialCandidate("p","secretref:p/a","HEALTHY",True,model_id="m",endpoint_id="e")
        mgr=ProviderExecutionManager([row],backoff_schedule_seconds=(5,15,30))
        mgr.select(provider_id="p",session_id="s",now=1)
        r=mgr.record_failure(session_id="s",error_class="TRANSIENT_NETWORK",now=2)
        self.assertEqual("RETRY_SAME_CREDENTIAL",r["action"])
        self.assertEqual(5.0,r["backoff_seconds"])
        snap=mgr.safe_snapshot(now=2)["credentials"][0]
        self.assertEqual(("HEALTHY","HEALTHY","HEALTHY"),(snap["provider_health"],snap["model_health"],snap["endpoint_health"]))
    def test_receipt_redacts_reference(self):
        r=execution_receipt(CredentialCandidate("p","secretref:p/a","HEALTHY",True),logical_route="x",physical_model="y",selection_reason="z")
        self.assertNotIn("credential_ref",r); self.assertFalse(r["raw_credential_present"])
    def test_active_antigravity_derived_records_follow_release_baseline(self):
        import json
        from pathlib import Path
        from fa3_release_baseline import active_capability_count
        root=Path(__file__).resolve().parents[1]
        expected=active_capability_count(root)
        paths=[
            "canonical/profiles/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-001.json",
            "canonical/profiles/FA3-LLM-PROTOCOL-COMPAT-001.json",
            "canonical/contracts/FA3-MODEL-ROUTER-EXECUTION-CONTRACTS-001.json",
            "canonical/contracts/FA3-LLM-PROTOCOL-COMPAT-CONTRACTS-001.json",
            "canonical/model-router-provider-execution-enforcement.json",
            "canonical/FA3-GATE-MODEL-ROUTER-PROVIDER-EXECUTION-001.json",
            "canonical/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CORE-CLOSURE-001.json",
            "canonical/decisions/FA3-DEC-ANTIGRAVITY-DERIVED-EXECUTION-MEDIATION-2026-09-24.json",
        ]
        for rel in paths:
            row=json.loads((root/rel).read_text())
            self.assertEqual(expected,row["capability_count"],rel)
            self.assertEqual("FA3-DEC-CAPABILITY-MODEL-175-2026-09-26",row["capability_model_reconciliation"],rel)
        historical=json.loads((root/"evidence/reference/model-router-provider-execution-ci-2026-09-24.json").read_text())
        self.assertEqual(143,historical["capability_count"])
class ProviderExecutionCoreClosureTests(unittest.TestCase):
    def test_core_closure_is_provider_independent(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        closure=json.loads((root/"canonical/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CORE-CLOSURE-001.json").read_text())
        current=json.loads((root/"canonical/FA3-MODEL-ROUTER-PROVIDER-EXECUTION-CURRENT-HOST-CONFORMANCE-001.json").read_text())
        openai=json.loads((root/"canonical/providers/FA3-PROVIDER-OPENAI-API-001.json").read_text())
        self.assertEqual(closure["status"],"CLOSED_STATIC_DETERMINISTIC_REGRESSION_PASS")
        self.assertFalse(closure["physical_provider_evidence"]["blocks_core_closure"])
        self.assertFalse(closure["provider_admission_model"]["generic_core_recertification_per_provider"])
        self.assertFalse(current["blocks_core_closure"])
        self.assertEqual(openai["current_host_production_evidence"],"PENDING_EXTERNAL_BILLING")
        self.assertFalse(openai["provider_execution_core_closure_dependency"])

    def test_provider_gui_finalization_obligation_is_durable(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        gui=json.loads((root/"canonical/FA3-GUI-SURFACE-REGISTRY-001.json").read_text())
        route=next(x for x in gui["surfaces"] if x.get("route_id")=="models.providers")
        obligation=route["provider_gui_completion_obligation"]
        self.assertEqual(obligation["status"],"MANDATORY_ON_PROVIDER_GUI_FINALIZATION")
        self.assertTrue(obligation["provider_specific_admission_evidence_required"])
        self.assertFalse(obligation["core_recertification_required"])
        self.assertIn("OPENAI_EXTERNAL_BILLING_CURRENT_HOST_E2E",obligation["required_followups"])
        self.assertIn("GOOGLE_GEMINI_PROVIDER_ADMISSION_IF_SELECTED",obligation["required_followups"])
        self.assertIn("GITHUB_COPILOT_PROVIDER_ADMISSION_IF_SELECTED",obligation["required_followups"])

if __name__=="__main__": unittest.main()
