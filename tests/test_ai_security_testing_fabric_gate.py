import json
import unittest
from pathlib import Path
import fa3_ai_security_testing_fabric_gate as g

ROOT=Path(__file__).resolve().parents[1]

class AISecurityTestingFabricGateTests(unittest.TestCase):
    def test_reference_gate_passes(self):
        self.assertEqual("PASS",g.gate(ROOT)["result"])
    def test_legacy_pyrit_artifacts_are_absent(self):
        self.assertTrue(all(not (ROOT/p).exists() for p in g.LEGACY_PYRIT_PATHS))
    def test_source_roles_are_bounded(self):
        data=json.loads((ROOT/"canonical/references/FA3-AI-SECURITY-TESTING-SOURCES-2026-09-25.json").read_text())
        by={x["name"]:x for x in data["sources"]}
        self.assertEqual("ADVERSARIAL_ENGINE_CANDIDATE",by["PyRIT"]["role"])
        self.assertEqual("PENDING_FABRIC_ENGINE_ADMISSION",by["PyRIT"]["runtime_status"])
        self.assertEqual("REUSE_EXISTING_FA3_GARAK_RUNTIME_NO_DUPLICATE_INSTALL",by["garak"]["runtime_status"])
        for name in ("Inspect AI","AgentDojo","Agent Scan","Promptfoo","DeepTeam"):
            self.assertEqual("REFERENCE_ONLY",by[name]["runtime_status"])
if __name__=="__main__":
    unittest.main()
