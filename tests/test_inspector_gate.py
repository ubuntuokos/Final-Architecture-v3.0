from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_inspector import classify_inspection
from fa3_inspector_gate import validate

BASE = {
    "subject_id": "FA3-CAP-P0", "level": "L3_PRODUCTION", "executor_id": "worker-a", "inspector_id": "inspector-b",
    "evidence_present": True, "evidence_fresh": True, "self_attestation_only": False,
    "canonical_compliant": True, "implementation_verified": True, "reproducible": True, "runtime_verified": True,
}

class InspectorGateTests(unittest.TestCase):
    def test_canonical_gate(self):
        self.assertEqual(validate(), [])

    def test_independent_production_pass(self):
        result = classify_inspection(dict(BASE))
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["promotion_allowed"])
        self.assertFalse(result["subject_mutation_allowed"])

    def test_self_attestation_only_is_blocked(self):
        request = dict(BASE); request["self_attestation_only"] = True
        self.assertEqual(classify_inspection(request)["status"], "BLOCKED")

    def test_same_actor_is_blocked(self):
        request = dict(BASE); request["inspector_id"] = request["executor_id"]
        self.assertEqual(classify_inspection(request)["status"], "BLOCKED")

    def test_missing_stale_drift_and_inconclusive(self):
        request = dict(BASE); request["evidence_present"] = False
        self.assertEqual(classify_inspection(request)["status"], "EVIDENCE_MISSING")
        request = dict(BASE); request["evidence_fresh"] = False
        self.assertEqual(classify_inspection(request)["status"], "EVIDENCE_STALE")
        request = dict(BASE); request["drift_detected"] = True
        self.assertEqual(classify_inspection(request)["status"], "DRIFT_DETECTED")
        request = dict(BASE); request["reproducible"] = False
        self.assertEqual(classify_inspection(request)["status"], "INCONCLUSIVE")

if __name__ == "__main__":
    unittest.main()
