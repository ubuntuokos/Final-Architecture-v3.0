from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_voice_studio_gate import gate
class VoiceStudioApplicationGateTests(unittest.TestCase):
 def test_gate(self):
  r=gate(ROOT);self.assertEqual("PASS",r["result"],r)
if __name__=="__main__":unittest.main()
