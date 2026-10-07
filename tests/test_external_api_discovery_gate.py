import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_external_api_discovery_gate as d
from fa3_release_baseline import module_active_capability_count

class ExternalAPIDiscoveryGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        for rel in (
            "src/fa3_api_mega_list_adapter.py",
            "src/fa3_external_discovery_store.py",
            "src/fa3_external_api_discovery_pipeline.py",
            "bin/fa3-external-api-discovery",
        ):
            source = ROOT / rel
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return td, root

    def _write(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        r = d.gate(ROOT)
        self.assertEqual("PASS", r["result"], r)
        self.assertEqual((17, 17), (r["regressions"]["passed"], r["regressions"]["total"]))
        self.assertFalse(r["runtime_provider_required"])
        self.assertEqual(module_active_capability_count(__file__), r["capability_count"])

    def test_catalog_listing_never_authorizes(self):
        self.assertTrue(d.metadata_boundary_valid(
            catalog_listing_authorizes=False,
            catalog_claim_is_canonical_evidence=False))
        self.assertFalse(d.metadata_boundary_valid(
            catalog_listing_authorizes=True,
            catalog_claim_is_canonical_evidence=False))

    def test_mcp_auto_registration_is_denied_without_full_admission(self):
        self.assertFalse(d.mcp_registration_allowed(
            admission_pass=False,
            central_gateway_mediated=True,
            source_self_authorizes=False))

    def test_secret_value_in_discovery_metadata_is_denied(self):
        self.assertFalse(d.secret_boundary_valid(
            auth_requirement_declared=True,
            secret_value_present_in_discovery_metadata=True))

    def test_egress_requires_ssrf_and_dns_rebinding_controls(self):
        self.assertFalse(d.egress_boundary_valid(
            canonical_egress_authorized=True,
            ssrf_controls=True,
            dns_rebinding_controls=False))

    def test_endpoint_dedupe_normalizes_case_default_port_and_trailing_slash(self):
        a = d.dedupe_key(provider_name="Example", endpoint_url="HTTPS://API.EXAMPLE.COM:443/v1/", protocol="REST")
        b = d.dedupe_key(provider_name="example", endpoint_url="https://api.example.com/v1", protocol="rest")
        self.assertEqual(a, b)

    def test_capability_mapping_uses_active_175_set(self):
        self.assertTrue(d.capability_mapping_valid(
            capability_id="CAP-175",
            vendor_defined_canonical_capability=False,
            root=ROOT))
        self.assertFalse(d.capability_mapping_valid(
            capability_id="CAP-176",
            vendor_defined_canonical_capability=False,
            root=ROOT))

    def test_capability_mapping_fails_closed_on_matrix_drift(self):
        td, root = self._copy_root()
        try:
            matrix = root / "canonical/conformance-matrix.csv"
            content = matrix.read_text(encoding="utf-8")
            self.assertIn(",CAP-175,", content)
            matrix.write_text(content.replace(",CAP-175,", ",CAP-176,", 1), encoding="utf-8")
            self.assertFalse(d.capability_mapping_valid(
                capability_id="CAP-175",
                vendor_defined_canonical_capability=False,
                root=root))
        finally:
            td.cleanup()

    def test_source_authority_escalation_fails_closed(self):
        td, root = self._copy_root()
        try:
            self._write(root / "canonical/external-discovery-authority-escalation.json", {
                "schema":"fa3.test.v1",
                "id":"T",
                "mcp_authority":"FA3-SOURCE-PUBLIC-APIS-001"
            })
            r = d.gate(root)
            self.assertEqual("FAIL", r["result"], r)
            self.assertEqual("FAIL", r["authority_scan"]["result"])
        finally:
            td.cleanup()

    def test_policy_binding_is_required(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/enforcement-policy.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["mandatory_reference_gates"] = [x for x in o["mandatory_reference_gates"] if x != d.GATE_ID]
            self._write(p, o)
            r = d.gate(root)
            self.assertEqual("FAIL", r["result"], r)
            self.assertTrue(any(x["code"] == "EXTDISC-REF-006" for x in r["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_candidate_store_policy_is_non_authoritative(self):
        policy = json.loads(
            (ROOT / "canonical/FA3-EXTERNAL-DISCOVERY-CANDIDATE-STORE-001.json").read_text()
        )
        self.assertFalse(policy["authority"])
        self.assertFalse(policy["canonical_source_of_truth"])
        self.assertTrue(policy["derived_state"])
        self.assertTrue(policy["rebuildable"])
        self.assertFalse(policy["network_fetch_permitted"])
        self.assertFalse(policy["automatic_donor_creation"])
        self.assertFalse(policy["automatic_provider_admission"])
        self.assertFalse(policy["automatic_mcp_registration"])

    def test_candidate_store_authority_escalation_fails_closed(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/FA3-EXTERNAL-DISCOVERY-CANDIDATE-STORE-001.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["automatic_provider_admission"] = True
            self._write(p, o)
            r = d.gate(root)
            self.assertEqual("FAIL", r["result"], r)
            self.assertTrue(
                any(x["code"] == "EXTDISC-REF-013" for x in r["reference"]["findings"])
            )
        finally:
            td.cleanup()

    def test_api_mega_list_missing_license_remains_restricted(self):
        ref = json.loads((ROOT / "canonical/references/FA3-API-MEGA-LIST-UPSTREAM-REFERENCE-2026-08-30.json").read_text())
        self.assertEqual("NO_REPOSITORY_LICENSE_DETECTED", ref["license_status"])
        self.assertEqual("DISCOVERY_METADATA_ONLY_UNTIL_LICENSE_AND_TERMS_ADMITTED", ref["local_ingestion_policy"])
        self.assertEqual(143, ref["fa3_disposition"]["canonical_capability_count"])

    def test_openclaw_catalog_is_restricted_discovery_only(self):
        ref = json.loads(
            (ROOT / "canonical/references/FA3-OPENCLAW-API-LIST-UPSTREAM-REFERENCE-2026-10-02.json").read_text()
        )
        self.assertEqual("NO_REPOSITORY_LICENSE_DETECTED", ref["license_status"])
        self.assertEqual(
            "DISCOVERY_METADATA_ONLY_UNTIL_LICENSE_AND_TERMS_ADMITTED",
            ref["local_ingestion_policy"],
        )
        self.assertTrue(ref["source_signals"]["affiliate_parameter_observed"])
        self.assertFalse(ref["source_signals"]["upstream_direct_mcp_language_is_admission"])
        self.assertFalse(ref["fa3_disposition"]["catalog_listing_is_authorization"])
        self.assertFalse(ref["fa3_disposition"]["affiliate_parameter_is_identity"])
        self.assertFalse(ref["fa3_disposition"]["runtime_provider"])

    def test_megalist_is_pattern_only(self):
        ref = json.loads((ROOT / "canonical/references/FA3-MEGALIST-UPSTREAM-REFERENCE-2026-08-30.json").read_text())
        self.assertFalse(ref["fa3_disposition"]["implementation_dependency"])
        self.assertIn("EXTERNAL_API_DISCOVERY_SOURCE", ref["not_classified_as"])

if __name__ == "__main__":
    unittest.main()
