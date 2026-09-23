from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_router_gate import gate


class TestModelRouterGate(unittest.TestCase):
    def test_repository_conformance(self):
        result=gate(ROOT)
        self.assertEqual(result["result"],"PASS",result.get("findings"))
        self.assertEqual(result["capability_delta"],0)
        self.assertEqual(result["authority_delta"],0)
        self.assertFalse(result["current_host_claim"])


if __name__=="__main__":
    unittest.main()
