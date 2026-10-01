from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fa3_current_host_delta_authority import compose_effective_host, plan_request, verify_delta_receipt


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


AUTHORITY = {
    "id": "FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001",
    "runtime_impact_classes": ["NONE", "LOCAL", "SHARED", "GLOBAL"],
    "full_requalification_trigger_flags": [
        "changes_capability_model",
        "changes_obligation_model",
        "changes_proof_registry",
        "changes_current_host_engine",
        "changes_evidence_or_promotion_authority",
        "changes_global_resource_authority",
        "changes_global_model_routing_authority",
        "changes_global_secret_or_security_authority",
        "changes_hardware_safety_authority",
        "changes_software_coexistence_authority",
    ],
    "mandatory_runtime_delta_capabilities": ["CAP-175"],
    "required_shared_gates": [
        "HARDWARE_SAFETY_ENVELOPE",
        "SOFTWARE_COEXISTENCE_HOST_NON_INTERFERENCE",
        "LICENSE_RIGHTS",
        "CURRENT_HOST_STRUCTURAL_IMPACT",
    ],
}


class CurrentHostDeltaAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "canonical").mkdir()
        (self.root / "evidence").mkdir()
        (self.root / "canonical/FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001.json").write_text(
            json.dumps(AUTHORITY), encoding="utf-8"
        )
        (self.root / "evidence/evidence-registry.json").write_text(
            json.dumps(
                {
                    "canonical_capability_count": 175,
                    "records": [{"subject_id": f"CAP-{i:03d}"} for i in range(1, 176)],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.td.cleanup()

    def request(self, impact="LOCAL", affected=None, consumers=None, **flag_overrides):
        flags = {key: False for key in AUTHORITY["full_requalification_trigger_flags"]}
        flags.update(
            {
                "hardware_surface_changed": False,
                "software_coexistence_surface_changed": False,
            }
        )
        flags.update(flag_overrides)
        return {
            "schema": "fa3.current-host-change-request.v1",
            "request_id": "REQ-001",
            "application_id": "fa3.video-editor",
            "base_release_digest": h("base"),
            "parent_effective_digest": h("base"),
            "change_digest": h("change"),
            "runtime_impact": impact,
            "changed_paths": ["apps/fa3-video-editor/runtime.py"],
            "affected_capabilities": affected or [],
            "consumer_capabilities": consumers or [],
            "flags": flags,
            "rationale": "Test request with explicit Current Host impact scope.",
            "global_promotion_claim": False,
        }

    def test_local_delta_requalifies_only_affected_plus_cap175(self):
        plan = plan_request(self.root, self.request(affected=["CAP-168"]))
        self.assertEqual("PASS", plan["status"])
        self.assertEqual("CAPABILITY_DELTA_REQUALIFICATION", plan["classification"])
        self.assertEqual(["CAP-168", "CAP-175"], plan["affected_capabilities"])
        self.assertEqual(6, plan["required_obligation_count"])

    def test_shared_delta_expands_to_consumers_plus_cap175(self):
        plan = plan_request(
            self.root,
            self.request("SHARED", affected=["CAP-168"], consumers=["CAP-170"]),
        )
        self.assertEqual("IMPACT_REQUALIFICATION", plan["classification"])
        self.assertEqual(["CAP-168", "CAP-170", "CAP-175"], plan["affected_capabilities"])
        self.assertEqual(9, plan["required_obligation_count"])

    def test_global_authority_change_escalates_to_full_175_525(self):
        plan = plan_request(
            self.root,
            self.request(
                "LOCAL",
                affected=["CAP-168"],
                changes_current_host_engine=True,
            ),
        )
        self.assertEqual("FULL_REQUALIFICATION", plan["classification"])
        self.assertEqual(175, plan["affected_capability_count"])
        self.assertEqual(525, plan["required_obligation_count"])

    def test_no_runtime_impact_requires_no_physical_delta(self):
        plan = plan_request(self.root, self.request("NONE"))
        self.assertEqual("NO_RUNTIME_IMPACT", plan["classification"])
        self.assertEqual(0, plan["required_obligation_count"])
        self.assertFalse(plan["physical_current_host_proof_required"])

    def test_unknown_capability_fails_closed(self):
        plan = plan_request(self.root, self.request(affected=["CAP-999"]))
        self.assertEqual("FAIL", plan["status"])
        self.assertTrue(plan["findings"])

    def _admitted_delta(self):
        plan = plan_request(self.root, self.request(affected=["CAP-168"]))
        proofs = [
            {
                "capability_id": row["capability_id"],
                "test_kind": row["test_kind"],
                "status": "PASS",
                "artifact_sha256": h(row["capability_id"] + row["test_kind"]),
            }
            for row in plan["required_obligations"]
        ]
        receipt = {
            "schema": "fa3.current-host-delta-receipt.v1",
            "plan_digest": plan["plan_digest"],
            "base_release_digest": plan["base_release_digest"],
            "parent_effective_digest": plan["parent_effective_digest"],
            "change_digest": plan["change_digest"],
            "physical_current_host_execution": True,
            "synthetic_current_host_pass": False,
            "historical_evidence_reused": False,
            "global_promotion_claim": False,
            "proofs": proofs,
            "shared_gates": {gate: "PASS" for gate in plan["required_shared_gates"]},
        }
        return plan, receipt, verify_delta_receipt(plan, receipt)

    def test_receipt_requires_exact_physical_obligation_set(self):
        plan, receipt, report = self._admitted_delta()
        self.assertEqual("PASS", report["result"])
        self.assertEqual(6, report["verified_obligation_count"])

        receipt["proofs"].pop()
        failed = verify_delta_receipt(plan, receipt)
        self.assertEqual("FAIL", failed["result"])

    def test_effective_host_composes_admitted_delta_chain(self):
        _, _, delta = self._admitted_delta()
        base = {
            "schema": "fa3.current-host-base-state.v1",
            "status": "CURRENT_HOST_BASE_ADMITTED",
            "capability_count": 175,
            "obligation_count": 525,
            "base_release_digest": h("base"),
            "effective_host_digest": h("base"),
        }
        effective = compose_effective_host(base, [delta])
        self.assertEqual("PASS", effective["status"])
        self.assertEqual(1, effective["delta_count"])
        self.assertEqual(delta["effective_host_digest"], effective["effective_host_digest"])

    def test_non_admitted_base_fails_closed(self):
        base = {
            "schema": "fa3.current-host-base-state.v1",
            "status": "PENDING_FRESH_EXACT_HEAD_CURRENT_HOST_EXECUTION",
            "capability_count": 175,
            "obligation_count": 525,
            "base_release_digest": h("base"),
            "effective_host_digest": h("base"),
        }
        effective = compose_effective_host(base, [])
        self.assertEqual("FAIL", effective["status"])


if __name__ == "__main__":
    unittest.main()
