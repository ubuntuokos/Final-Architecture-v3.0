from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_ai_comms import CommunicationDenied, reference_cases, validate_message_envelope
from fa3_ai_comms_gate import gate


class AICommsPolicyTests(unittest.TestCase):
    def test_reference_positive_and_negative_cases(self) -> None:
        cases = reference_cases()
        self.assertTrue(all(cases.values()), cases)

    def test_private_codebook_fails_closed(self) -> None:
        payload = {
            "communication_mode": "HUMAN_LANGUAGE",
            "language_tag": "hu-HU",
            "human_readable_text": "Ezt az üzenetet embernek is teljesen értenie kell.",
            "human_readable_authoritative": True,
            "private_model_language": {"x1": "hidden meaning"},
        }
        with self.assertRaises(CommunicationDenied):
            validate_message_envelope(payload, sender="model-a", recipient="model-b")

    def test_undefined_machine_protocol_fails_closed(self) -> None:
        payload = {
            "communication_mode": "CANONICAL_STRUCTURED",
            "language_tag": "en-US",
            "human_readable_text": "The structured payload is supplemental only.",
            "human_readable_authoritative": True,
            "schema_id": "private-protocol",
            "structured_payload": {"x": 1},
            "structured_payload_semantics": "SUPPLEMENTAL_TO_HUMAN_TEXT",
        }
        with self.assertRaises(CommunicationDenied):
            validate_message_envelope(payload, sender="model-a", recipient="model-b")

    def test_declared_shorthand_is_allowed_only_with_expansion(self) -> None:
        payload = {
            "communication_mode": "CANONICAL_STRUCTURED",
            "language_tag": "en-US",
            "human_readable_text": "The delegated task is complete.",
            "human_readable_authoritative": True,
            "schema_id": "fa3.agent.status.v1",
            "structured_payload": {"status": "DONE"},
            "structured_payload_semantics": "SUPPLEMENTAL_TO_HUMAN_TEXT",
            "defined_terms": {"DONE": "The delegated task is complete."},
        }
        result = validate_message_envelope(payload, sender="model-a", recipient="model-b")
        self.assertEqual(result["result"], "ALLOW")

    def test_repository_gate_passes(self) -> None:
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)
        self.assertEqual(report["capability_delta"], 0)
        self.assertEqual(report["authority_delta"], 0)
        self.assertFalse(report["current_host_production_claim"])
        self.assertTrue(report["model_router_reused"])
        self.assertFalse(report["parallel_model_router_created"])


if __name__ == "__main__":
    unittest.main()
