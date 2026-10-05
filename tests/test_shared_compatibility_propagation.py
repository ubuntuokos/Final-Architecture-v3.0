from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_application_donor_index import build_index  # noqa: E402
from fa3_shared_compatibility_propagation_gate import (  # noqa: E402
    expected_components_for_application,
    gate,
    validate_assessment,
)


class SharedCompatibilityPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = ROOT
        cls.index = build_index(ROOT)

    def assessment(self, application_id: str, state: str, components: list[str]) -> dict:
        return {
            "schema": "fa3.application-compatibility-assessment.v1",
            "assessment_id": "TEST-COMPAT-001",
            "application_id": application_id,
            "application_state": state,
            "source_commit": "0" * 40,
            "applicable_shared_components": components,
            "compatibility_results": [
                {"shared_component_id": sid, "disposition": "NO_CHANGE"}
                for sid in components
            ],
            "overall_result": "PASS",
            "capability_regression": False,
            "new_architectural_authority": False,
            "current_host_impact": "NO_RUNTIME_IMPACT",
        }

    def test_static_policy_gate_passes(self) -> None:
        report = gate(self.root)
        self.assertEqual(report["result"], "PASS", report["findings"])
        self.assertEqual(report["capability_baseline"], 175)
        self.assertEqual(report["new_capabilities"], 0)
        self.assertEqual(report["new_architectural_authorities"], 0)
        self.assertEqual(
            report["enforcement_mode"],
            "STAGED_DURING_ACTIVE_PR_RECONCILIATION",
        )

    def test_registered_application_must_cover_derived_shared_scope(self) -> None:
        assessment = self.assessment("fa3.video-editor", "PLANNED", [])
        findings = validate_assessment(assessment, self.index, require_pass=True)
        codes = {row["code"] for row in findings}
        self.assertIn("COMPAT-ASM-007", codes)

    def test_registered_application_complete_scope_passes(self) -> None:
        components = sorted(
            expected_components_for_application(self.index, "fa3.video-editor")
        )
        self.assertTrue(components)
        assessment = self.assessment("fa3.video-editor", "PLANNED", components)
        findings = validate_assessment(assessment, self.index, require_pass=True)
        self.assertEqual(findings, [])

    def test_future_application_can_be_assessed_without_second_registry(self) -> None:
        known = sorted({
            edge["shared_capability_id"]
            for edge in self.index["shared_capability_consumer_map"]["edges"]
        })
        self.assertTrue(known)
        assessment = self.assessment("future.example-app", "FUTURE", [known[0]])
        findings = validate_assessment(assessment, self.index, require_pass=True)
        self.assertEqual(findings, [])

    def test_capability_regression_fails_closed(self) -> None:
        known = sorted({
            edge["shared_capability_id"]
            for edge in self.index["shared_capability_consumer_map"]["edges"]
        })
        assessment = self.assessment("future.example-app", "FUTURE", [known[0]])
        assessment["capability_regression"] = True
        codes = {
            row["code"]
            for row in validate_assessment(assessment, self.index, require_pass=True)
        }
        self.assertIn("COMPAT-ASM-015", codes)


if __name__ == "__main__":
    unittest.main()
