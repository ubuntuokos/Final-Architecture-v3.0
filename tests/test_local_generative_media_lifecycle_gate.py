from pathlib import Path
import unittest
from fa3_local_generative_media_lifecycle_gate import gate
ROOT=Path(__file__).resolve().parents[1]
class LocalGenerativeMediaLifecycleGateTests(unittest.TestCase):
    def test_gate(self):
        r=gate(ROOT)
        self.assertEqual("PASS",r["result"],r)
        self.assertFalse(r["current_host_runtime_promotion_claim"])
if __name__=="__main__": unittest.main()
