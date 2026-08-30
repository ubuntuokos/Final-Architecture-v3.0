import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_external_api_discovery_gate as d

class ExternalAPIDiscoveryGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    def _write(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        r = d.gate(ROOT)
        self.assertEqual("PASS", r["result"], r)
        self.assertEqual((13, 13), (r["regressions"]["passed"], r["regressions"]["total"]))
        self.assertFalse(r["runtime_provider_required"])
        self.assertEqual(143, r["capability_count"])

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

    def test_api_mega_list_missing_license_remains_restricted(self):
        ref = json.loads((ROOT / "canonical/references/FA3-API-MEGA-LIST-UPSTREAM-REFERENCE-2026-08-30.json").read_text())
        self.assertEqual("NO_REPOSITORY_LICENSE_DETECTED", ref["license_status"])
        self.assertEqual("DISCOVERY_METADATA_ONLY_UNTIL_LICENSE_AND_TERMS_ADMITTED", ref["local_ingestion_policy"])

    def test_megalist_is_pattern_only(self):
        ref = json.loads((ROOT / "canonical/references/FA3-MEGALIST-UPSTREAM-REFERENCE-2026-08-30.json").read_text())
        self.assertFalse(ref["fa3_disposition"]["implementation_dependency"])
        self.assertIn("EXTERNAL_API_DISCOVERY_SOURCE", ref["not_classified_as"])

if __name__ == "__main__":
    unittest.main()
