from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from fa3_agent_application_blueprint import BlueprintContractError, compile_blueprint, validate_blueprint

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "agent-application-blueprint-research.json"


class Tests(unittest.TestCase):
    def load(self):
        return json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_compile_provider_neutral_plan(self):
        result = compile_blueprint(ROOT, self.load())
        self.assertEqual(result["schema"], "fa3.agent-application-blueprint-compile.v1")
        self.assertTrue(result["provider_neutral"])
        self.assertFalse(result["architectural_authority"])
        self.assertEqual(result["capability_delta"], 0)
        self.assertEqual(result["durable_lifecycle_authority"], "Temporal")
        self.assertEqual(result["execution_fabric"], "FA3-UNIFIED-ACTION-FABRIC-001")
        self.assertEqual(result["work_plan"]["status"], "READY")
        self.assertEqual(len(result["digest"]), 64)
        self.assertEqual(result["reviewed_task_ids"], ["research"])
        for decision in result["work_plan"]["decisions"]:
            meta = next(t for t in self.load()["tasks"] if t["task_id"] == decision["task_id"])
            self.assertIn(meta["task_id"], {"plan", "research", "review"})

    def test_role_authority_rejected(self):
        value = self.load()
        value["roles"][0]["authority_scope"] = ["security_policy"]
        with self.assertRaises(BlueprintContractError):
            validate_blueprint(value)

    def test_undeclared_capability_rejected(self):
        value = self.load()
        value["tasks"][1]["required_capabilities"].append("model_routing")
        with self.assertRaises(BlueprintContractError):
            validate_blueprint(value)

    def test_self_review_rejected(self):
        value = self.load()
        value["tasks"][2]["role_id"] = "research-worker"
        with self.assertRaises(BlueprintContractError):
            validate_blueprint(value)

    def test_temporal_singularity_rejected(self):
        value = self.load()
        value["execution_policy"]["durable_lifecycle_authority"] = "Conductor"
        with self.assertRaises(BlueprintContractError):
            validate_blueprint(value)

    def test_direct_provider_invocation_rejected(self):
        value = self.load()
        value["execution_policy"]["direct_provider_invocation"] = True
        with self.assertRaises(BlueprintContractError):
            validate_blueprint(value)


if __name__ == "__main__":
    unittest.main()
