from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_resource_evidence_normalization_gate import (  # noqa: E402
    _reference_envelope,
    evaluate_resource_admission,
    gate,
    normalized_result,
    run_reference_scenarios,
    validate_evidence_envelope,
)


class ResourceEvidenceNormalizationTests(unittest.TestCase):
    def test_global_gate_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["capability_delta"], 0)
        self.assertEqual(report["architectural_authority_delta"], 0)

    def test_cu_tu_are_not_admission_inputs(self) -> None:
        passed = evaluate_resource_admission(
            {"gpu.vram_gib": 24, "pcie.h2d_gbps": 22},
            [
                {"metric": "gpu.vram_gib", "operator": ">=", "value": 24},
                {"metric": "pcie.h2d_gbps", "operator": ">=", "value": 20},
            ],
            {"status": "VALID", "lease_id": "lease-1", "diagnostics": {"cu": 0, "tu": 0}},
        )
        self.assertEqual(passed["result"], "PASS")

    def test_missing_required_metric_blocks(self) -> None:
        report = evaluate_resource_admission(
            {"gpu.vram_gib": 24},
            [{"metric": "pcie.h2d_gbps", "operator": ">=", "value": 20}],
            {"status": "VALID", "lease_id": "lease-1"},
        )
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["decision"]["exit_code"], 2)

    def test_invalid_hrb_lease_blocks(self) -> None:
        report = evaluate_resource_admission(
            {"gpu.vram_gib": 24},
            [{"metric": "gpu.vram_gib", "operator": ">=", "value": 24}],
            {"status": "EXPIRED", "lease_id": "lease-1"},
        )
        self.assertEqual(report["decision"]["reason_code"], "HRB_LEASE_INVALID")

    def test_tampered_payload_fails_integrity(self) -> None:
        envelope = _reference_envelope()
        envelope["payload"]["tampered"] = True
        self.assertIn("payload_sha256_mismatch", validate_evidence_envelope(envelope))

    def test_claim_and_non_claim_overlap_is_invalid(self) -> None:
        envelope = _reference_envelope()
        envelope["result"]["claims"].append("GLOBAL_FA3_PROMOTION")
        self.assertIn("claim_non_claim_overlap", validate_evidence_envelope(envelope))

    def test_current_host_requires_attestation_reference(self) -> None:
        envelope = _reference_envelope(current_host=True)
        del envelope["execution_context"]["host_attestation_ref"]
        self.assertIn("current_host_requires_host_attestation_ref", validate_evidence_envelope(envelope))

    def test_current_host_rejects_non_digest_attestation_reference(self) -> None:
        envelope = _reference_envelope(current_host=True)
        envelope["execution_context"]["host_attestation_ref"] = "FA3-HOST-IDENTIFIER-ONLY"
        self.assertIn(
            "current_host_requires_digest_bound_host_attestation_ref",
            validate_evidence_envelope(envelope),
        )

    def test_exit_code_contract_is_stable(self) -> None:
        self.assertEqual(normalized_result(gate_id="x", mode="x", result="PASS", reason_code="x")["decision"]["exit_code"], 0)
        self.assertEqual(normalized_result(gate_id="x", mode="x", result="PENDING", reason_code="x")["decision"]["exit_code"], 2)
        self.assertEqual(normalized_result(gate_id="x", mode="x", result="BLOCKED", reason_code="x")["decision"]["exit_code"], 2)
        self.assertEqual(normalized_result(gate_id="x", mode="x", result="ERROR", reason_code="x")["decision"]["exit_code"], 3)

    def test_reference_scenarios_cover_positive_negative_pending_and_scoped_host(self) -> None:
        report = run_reference_scenarios()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(
            [case["id"] for case in report["cases"]],
            ["REFERENCE_VALID", "CURRENT_HOST_MISSING", "TAMPERED_EVIDENCE", "SCOPED_CURRENT_HOST"],
        )


if __name__ == "__main__":
    unittest.main()
