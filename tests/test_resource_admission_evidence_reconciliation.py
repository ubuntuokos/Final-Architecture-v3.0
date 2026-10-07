from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/fa3_reconcile_resource_admission_evidence.py"
spec = importlib.util.spec_from_file_location("fa3_reconcile_resource_admission_evidence", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def acceptance():
    return {
        "schema": "fa3.resource-admission-current-host.production-evidence-acceptance.v1",
        "status": "REAL_EXECUTION_PASS_CAPTURED_PER_WORKLOAD_READMISSION_REQUIRED",
        "subject": {
            "capability_id": "CAP-006",
            "capability": "Resource Fabric",
            "gate_id": "FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001",
            "evidence_level": "CURRENT_HOST_RESOURCE_ADMISSION_PASS",
        },
        "source_evidence": {"receipt_sha256": "a" * 64},
        "claims": ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"],
        "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E"],
        "archival_semantics": {
            "historical_execution_pass": True,
            "current_or_future_workload_authorization": False,
            "future_workloads_require_fresh_hrb_lease": True,
            "future_workloads_require_fresh_resource_admission": True,
        },
        "projection_semantics": {
            "component_pass_claim": True,
            "global_promotion_claim": False,
            "provider_runtime_e2e_claim": False,
            "capability_delta": 0,
            "authority_delta": 0,
        },
    }


def fixture_root(base: Path):
    write_json(base / mod.GATE_PATH, {"id": mod.GATE_ID, "status": "MATERIALIZED_REAL_EXECUTION_PENDING", "global_promotion_claim": False})
    write_json(base / mod.DECISION_PATH, {"id": mod.DECISION_ID, "production_evidence_status": "PENDING_REAL_CURRENT_HOST_EXECUTION"})
    write_json(
        base / mod.MANIFEST_PATH,
        {
            "required_repository_paths": [],
            "registered_current_host_surfaces": [
                {
                    "name": "resource-admission",
                    "collection_status": "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING",
                    "global_promotion_claim": False,
                }
            ],
        },
    )
    records = []
    for i in range(1, 144):
        cap = f"CAP-{i:03d}"
        records.append(
            {
                "evidence_id": f"EVID-{cap}-CURRENT-HOST",
                "subject_id": cap,
                "subject": "Resource Fabric" if cap == "CAP-006" else f"Fixture {cap}",
                "runtime_conformance": "EVIDENCE-PENDING",
                "status": "PENDING_CURRENT_HOST",
                "blocking": True,
                "promotion_state": "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE",
                "source_decision_ids": [],
                "evidence_artifacts": [],
            }
        )
    write_json(
        base / mod.REGISTRY_PATH,
        {
            "schema": "fa3.evidence.registry.v1",
            "canonical_capability_count": 143,
            "record_count": 143,
            "status": "PENDING_CURRENT_HOST",
            "records": records,
        },
    )


class ResourceAdmissionEvidenceReconciliationTests(unittest.TestCase):
    def test_scoped_cap006_projection_preserves_top_level_state_and_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture_root(root)
            acceptance_path = root / "acceptance.json"
            write_json(acceptance_path, acceptance())
            mod.reconcile(root, acceptance_path)

            registry = json.loads((root / mod.REGISTRY_PATH).read_text())
            self.assertEqual(registry["canonical_capability_count"], 143)
            self.assertEqual(registry["record_count"], 143)
            self.assertEqual(len(registry["records"]), 143)
            cap = next(item for item in registry["records"] if item["subject_id"] == "CAP-006")
            self.assertEqual(cap["runtime_conformance"], "EVIDENCE-PENDING")
            self.assertEqual(cap["status"], "PENDING_CURRENT_HOST")
            self.assertTrue(cap["blocking"])
            self.assertEqual(cap["promotion_state"], "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE")
            projection = cap["resource_admission_current_host_projection_status"]
            self.assertTrue(projection["component_pass_claim"])
            self.assertFalse(projection["global_promotion_claim"])
            self.assertFalse(projection["current_or_future_workload_authorization"])
            self.assertTrue(projection["future_workloads_require_fresh_hrb_lease"])
            self.assertTrue((root / mod.ACCEPTED_EVIDENCE_PATH).is_file())

    def test_global_promotion_claim_blocks_reconciliation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture_root(root)
            record = acceptance()
            record["projection_semantics"]["global_promotion_claim"] = True
            acceptance_path = root / "acceptance.json"
            write_json(acceptance_path, record)
            with self.assertRaises(mod.ReconcileError):
                mod.reconcile(root, acceptance_path)


if __name__ == "__main__":
    unittest.main()
