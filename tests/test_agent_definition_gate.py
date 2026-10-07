from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fa3_agent_definition_gate import definition_valid, gate, regressions, template_valid

ROOT = Path(__file__).resolve().parents[1]


class AgentDefinitionGateTests(unittest.TestCase):
    def test_regression_matrix_passes(self):
        report = regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["total"], 12)
        self.assertEqual(report["passed"], 12)

    def test_registry_definitions_cannot_escalate_authority(self):
        registry = json.loads((ROOT / "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json").read_text(encoding="utf-8"))
        definition = copy.deepcopy(registry["definitions"][0])
        self.assertTrue(definition_valid(definition))
        definition["authority_grants"] = ["FA3-AUTH-SECURITY-GOV-001"]
        self.assertFalse(definition_valid(definition))

    def test_registry_definitions_cannot_bind_runtime_provider(self):
        registry = json.loads((ROOT / "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json").read_text(encoding="utf-8"))
        definition = copy.deepcopy(registry["definitions"][0])
        definition["runtime_provider_binding"] = "FA3-PROVIDER-CREWAI-001"
        self.assertFalse(definition_valid(definition))

    def test_templates_cannot_become_durable_workflow_authority(self):
        registry = json.loads((ROOT / "canonical/FA3-AGENT-DEFINITION-REGISTRY-001.json").read_text(encoding="utf-8"))
        template = copy.deepcopy(registry["templates"][0])
        self.assertTrue(template_valid(template))
        template["durable_workflow_authority"] = True
        self.assertFalse(template_valid(template))

    def test_canonical_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS", report)


if __name__ == "__main__":
    unittest.main()
