from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_voice_studio_current_host_gate import run
class VoiceStudioCurrentHostReferenceTests(unittest.TestCase):
 def test_reference_loopback(self):
  r=run(ROOT);self.assertEqual("PASS",r["result"],r);self.assertFalse(r["production_promotion_claim"])
if __name__=="__main__":unittest.main()
