from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/"canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY=ROOT/"canonical/enforcement-policy.json"
EVIDENCE=ROOT/"evidence/evidence-registry.json"
DISTRIBUTION=ROOT/"canonical/distribution-registry.json"
GATESET="FA3-EMBEDDING-FABRIC-GATESET-001"
PROVIDERS={"FA3-PROVIDER-TEI-001","FA3-PROVIDER-MODEL2VEC-001","FA3-PROVIDER-FLAG-EMBEDDING-001"}

def load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

class EmbeddingFabricGlobalReconciliationTests(unittest.TestCase):
    def test_global_gate_binding_and_capability_count(self):
        policy=load(POLICY); release=load(RELEASE)
        self.assertIn(GATESET,policy["mandatory_reference_gates"])
        self.assertIn(GATESET,release["mandatory_reference_gates"])
        self.assertEqual(set(policy["mandatory_reference_gates"]),set(release["mandatory_reference_gates"]))
        self.assertEqual(143,policy["canonical_capability_count"])
        self.assertEqual(143,release["invariants"]["canonical_capability_count"])

    def test_release_reconciliation_is_non_promoting(self):
        rec=load(RELEASE)["embedding_fabric_reconciliation"]
        self.assertEqual("FA3-EMBEDDING-FABRIC-001",rec["profile_id"])
        self.assertEqual(0,rec["new_capabilities"])
        self.assertEqual(0,rec["new_architectural_authorities"])
        self.assertFalse(rec["current_host_runtime_promotion_claim"])
        self.assertFalse(rec["global_promotion_claim"])

    def test_release_surface_is_manifested(self):
        release=load(RELEASE)
        manifest={x["path"] for x in release["manifest"]}
        required={
            "canonical/profiles/FA3-EMBEDDING-FABRIC-001.json",
            "canonical/contracts/FA3-EMBEDDING-FABRIC-CONTRACTS-001.json",
            "canonical/decisions/FA3-DEC-EMBEDDING-FABRIC-2026-09-25.json",
            "canonical/embedding-fabric-enforcement.json",
            "canonical/FA3-GATE-EMBEDDING-FABRIC-001.json",
            "src/fa3_embedding_fabric_gate.py",
            "tests/test_embedding_fabric_gate.py",
            "tests/test_embedding_fabric_global_reconciliation.py",
            ".github/workflows/fa3-embedding-fabric.yml",
            "docs/FA3-EMBEDDING-FABRIC-001.md",
            "canonical/profiles/FA3-BROWSER-SEMANTIC-FIND-001.json",
            "canonical/contracts/FA3-BROWSER-SEMANTIC-FIND-CONTRACTS-001.json",
        }
        self.assertTrue(required.issubset(manifest),sorted(required-manifest))

    def test_external_provider_distribution_is_fail_closed(self):
        records={x["subject_id"]:x for x in load(DISTRIBUTION)["records"]}
        for pid in PROVIDERS:
            self.assertEqual("USER_LOCAL_EXTERNAL",records[pid]["class"])
            self.assertEqual("EXCLUDED",records[pid]["release_bundle_status"])

    def test_evidence_registry_does_not_claim_runtime_pass(self):
        rec=load(EVIDENCE)["embedding_fabric_reconciliation"]
        self.assertEqual("PENDING_REAL_CURRENT_HOST_E2E",rec["current_host_runtime_evidence"])
        self.assertFalse(rec["production_provider_admission"])
        self.assertFalse(rec["global_promotion_claim"])

if __name__=="__main__":
    unittest.main()
