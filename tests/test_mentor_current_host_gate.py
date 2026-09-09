import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_mentor_current_host import (
    CAPABILITY_COUNT, EVIDENCE_AUTHORITY, EVIDENCE_LEVEL, KNOWLEDGE_AUTHORITY,
    MCP_AUTHORITY, PARENT_PROFILE_ID, PROFILE_ID, bkt_update, endpoint_is_loopback,
    fsrs_style_schedule, receipt_digest, validate_receipt,
)
from fa3_mentor_current_host_gate import gate


def good_receipt():
    r = {
        "schema": "fa3.mentor-current-host-receipt.v1",
        "profile_id": PROFILE_ID,
        "parent_profile_id": PARENT_PROFILE_ID,
        "status": "PASS",
        "host_scope": "CURRENT_HOST",
        "fixture_semantics": "REAL_CURRENT_HOST_EXECUTION",
        "evidence_level": EVIDENCE_LEVEL,
        "capability_count_after": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "components": {
            "mentor_runtime": {"status": "PASS"},
            "central_mcp": {"status": "PASS", "authority_id": MCP_AUTHORITY, "execution_performed_by_mentor": False},
            "knowledge_rag": {"status": "PASS", "authority_id": KNOWLEDGE_AUTHORITY, "provenance_refs": ["SRC-1"]},
            "memory": {"status": "PASS", "authority_id": "FA3-AUTH-MEMORY-CURRENT", "explicit_user_consent": True, "write_via_central_mcp": True, "marker_roundtrip": True},
            "evidence": {"status": "PASS", "authority_id": EVIDENCE_AUTHORITY, "evidence_id": "E-1"},
            "mastery": {"status": "PASS", "p_known_before": 0.2, "p_known_after": 0.7, "interval_days": 2, "evidence_refs": ["E-1"]},
            "bubblewrap": {"status": "PASS", "backend": "bubblewrap", "positive_lab": True, "network_denied": True, "host_write_denied": True, "timeout_terminated": True, "writable_host_paths": []},
        },
        "observed_authorities": [MCP_AUTHORITY, KNOWLEDGE_AUTHORITY, "FA3-AUTH-MEMORY-CURRENT", EVIDENCE_AUTHORITY],
    }
    r["receipt_sha256"] = receipt_digest(r)
    return r


class MentorCurrentHostTests(unittest.TestCase):
    def test_bkt_learning_moves_probability_up_on_correct(self):
        self.assertGreater(bkt_update(0.2, True), 0.2)

    def test_fsrs_style_schedule_positive(self):
        s = fsrs_style_schedule(previous_stability_days=1, difficulty=5, correct=True, p_known=0.7)
        self.assertGreater(s["interval_days"], 0)
        self.assertGreater(s["stability_days"], 0)

    def test_endpoint_loopback_policy(self):
        self.assertTrue(endpoint_is_loopback("http://127.0.0.1:8787/health"))
        self.assertTrue(endpoint_is_loopback("http://localhost:8787/health"))
        self.assertFalse(endpoint_is_loopback("https://example.com/health"))

    def test_good_receipt_validates(self):
        self.assertEqual([], validate_receipt(good_receipt()))

    def test_mock_receipt_rejected(self):
        r = good_receipt()
        r["fixture_semantics"] = "MOCK"
        self.assertTrue(any(x["code"] == "MENTOR-HOST-004" for x in validate_receipt(r)))

    def test_mentor_authority_rejected(self):
        r = good_receipt()
        r["components"]["memory"]["authority_id"] = PARENT_PROFILE_ID
        r["observed_authorities"].append(PARENT_PROFILE_ID)
        findings = validate_receipt(r)
        self.assertTrue(any(x["code"] in {"MENTOR-HOST-013", "MENTOR-HOST-021"} for x in findings))

    def test_gate_checks_receipt_digest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            receipt = good_receipt()
            path = root / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            report = gate(root, path)
            self.assertEqual("PASS", report["result"], report)
            receipt["components"]["mastery"]["interval_days"] = 99
            path.write_text(json.dumps(receipt), encoding="utf-8")
            report = gate(root, path)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "MENTOR-HOST-GATE-001" for x in report["findings"]))


if __name__ == "__main__":
    unittest.main()
