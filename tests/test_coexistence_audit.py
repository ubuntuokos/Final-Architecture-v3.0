import json, tempfile, unittest
from pathlib import Path
from fa3_coexistence_audit import audit

class CoexistenceAuditTests(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        (root/"canonical/decisions").mkdir(parents=True)
        (root/"canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json").write_text("{\"schema\":\"fa3.release-capability-baseline.v1\",\"id\":\"FA3-RELEASE-CAPABILITY-BASELINE-001\",\"baseline_semantics\":\"RELEASE_SCOPED\",\"current_release\":\"test/v3.1.0\",\"current_release_capability_count\":175,\"release_baselines\":[{\"release\":\"test/v3.1.0\",\"capability_count\":175,\"status\":\"ACTIVE_BASELINE\"}]}")
        (root/"canonical/intents").mkdir()
        (root/"canonical/providers").mkdir()
        (root/"canonical/coexistence/footprints").mkdir(parents=True)
        (root/"deployment/x").mkdir(parents=True)
        (root/"canonical/FA3-COEXISTENCE-POLICY-001.json").write_text(json.dumps({"capability_count":175,"capability_delta":0,"authority_delta":0,"system_dependency_package_management":{"generic_linux_distribution":True,"installer_or_provisioning_package_may_invoke_native_package_manager":True,"scope":"DECLARED_SYSTEM_DEPENDENCIES_ONLY","native_package_manager_discovery_required":True,"single_distribution_or_single_package_manager_hardcoding_forbidden":True,"application_runtime_package_manager_mutation":"DENY","provider_runtime_bootstrap_package_manager_mutation":"DENY","current_host_test_package_manager_mutation":"DENY","explicit_dependency_manifest_required":True,"package_transaction_receipt_required":True}}))
        (root/"canonical/decisions/FA3-DEC-SOFTWARE-COEXISTENCE-2026-09-26.json").write_text(json.dumps({"capability_count":175,"truth_boundary":{"static_pass_is_current_host_pass":False,"physical_current_host_evidence_required_for_runtime_pass":True},"installer_package_manager_boundary":{"generic_linux":True,"system_installer_may_install_declared_system_dependencies_with_detected_native_package_manager":True,"runtime_and_provider_bootstrap_may_not_mutate_host_global_package_state":True,"no_single_distribution_package_manager_is_canonical":True}}))
        return td,root
    def test_detects_unnamespaced_service(self):
        td,root=self.fixture()
        try:
            (root/"deployment/x/upstream.service").write_text("[Service]\nExecStart=/bin/true\n")
            r=audit(root)
            self.assertEqual(r["static_result"],"FAIL")
            self.assertTrue(any(x["code"]=="COEX-020" for x in r["findings"]))
            self.assertEqual(r["capability_count"],175)
            self.assertFalse(r["runtime_promotion_claim"])
        finally: td.cleanup()
    def test_static_pass_never_promotes_runtime(self):
        td,root=self.fixture()
        try:
            r=audit(root)
            self.assertEqual(r["static_result"],"PASS")
            self.assertEqual(r["current_host_status"],"PENDING_CURRENT_HOST")
            self.assertFalse(r["runtime_promotion_claim"])
        finally: td.cleanup()

    def test_system_authority_incomplete_controls_remain_pending(self):
        td,root=self.fixture()
        try:
            fp=root/"canonical/coexistence/footprints/mcp.json"
            fp.write_text(json.dumps({
                "schema":"fa3.coexistence-footprint.v1",
                "component_id":"FA3-MCP-GATEWAY-001",
                "classification":"SYSTEM_LEVEL_AUTHORITY",
                "risk":"P0",
                "upstream_relation":"REPLACES_CAPABILITY_NOT_APPLICATION",
                "coexistence":{"executables":[],"services":["fa3-mcp-gateway.service"],"sockets":["$XDG_RUNTIME_DIR/fa3/mcp-gateway.sock"],"ports":[18790],"config_paths":[],"data_paths":[],"cache_paths":[],"desktop_ids":[],"mime_types":[],"protocol_handlers":[],"env_mutations":[],"databases":[],"plugin_paths":[],"external_app_integrations":[],"requires_upstream_uninstall":False,"global_environment_mutation":False,"claims_default_port":False},
                "authority_controls":{"authority_id":"FA3-AUTH-MCP-GATEWAY-001","conflict_detection":True,"previous_state_capture":False,"controlled_mutation":False,"rollback":True,"recovery_evidence":False},
                "evidence":{"static_status":"PENDING","current_host_status":"PENDING_CURRENT_HOST","runtime_promotion_claim":False,"artifacts":[]}
            }))
            r=audit(root)
            self.assertEqual(r["static_result"],"PASS")
            rows=[x for x in r["coverage"] if x.get("id")=="FA3-MCP-GATEWAY-001"]
            self.assertTrue(any(x["status"]=="PENDING_AUTHORITY_CONTROL_REMEDIATION" for x in rows))
            self.assertEqual(r["current_host_status"],"PENDING_CURRENT_HOST")
        finally: td.cleanup()

    def test_generic_linux_package_manager_boundary_fails_closed_when_weakened(self):
        td,root=self.fixture()
        try:
            p=root/"canonical/FA3-COEXISTENCE-POLICY-001.json"
            obj=json.loads(p.read_text())
            obj["system_dependency_package_management"]["provider_runtime_bootstrap_package_manager_mutation"]="ALLOW"
            p.write_text(json.dumps(obj))
            r=audit(root)
            self.assertEqual(r["static_result"],"FAIL")
            self.assertTrue(any(x["code"]=="COEX-004" for x in r["findings"]))
        finally: td.cleanup()

    def test_secret_broker_installer_and_uninstaller_are_ownership_safe(self):
        root=Path(__file__).resolve().parents[1]
        install=(root/"bin/fa3-secret-broker-install").read_text(encoding="utf-8")
        uninstall=(root/"bin/fa3-secret-broker-uninstall").read_text(encoding="utf-8")
        self.assertIn("fa3.secret-broker-install-manifest.v1", install)
        self.assertIn("DENY: destination exists without FA3 ownership proof", install)
        self.assertIn("DENY: installed FA3 file drifted outside installer ownership", install)
        self.assertIn("DENY: ownership manifest missing", uninstall)
        self.assertIn("refusing ambiguous removal", uninstall)
        self.assertIn("Preserved: /var/lib/fa3/state and /etc/fa3/secret-policy.d", uninstall)

if __name__=="__main__":
    unittest.main()
