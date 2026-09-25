import json,subprocess,tempfile,unittest
from pathlib import Path
from src.fa3_diffusion_studio_gate import gate
ROOT=Path(__file__).resolve().parents[1];AD=ROOT/'src/fa3_diffusion_studio_adapter.py'
class T(unittest.TestCase):
 def test_gate(self):self.assertEqual(gate(ROOT)['result'],'PASS')
 def test_capabilities(self):
  p=subprocess.run(['python',str(AD),'capabilities'],text=True,capture_output=True);self.assertEqual(p.returncode,0);self.assertIn('CAP-121',p.stdout)
 def test_escape_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   q={'schema':'fa3.provider-request.v1','provider_id':'FA3-PROVIDER-DIFFUSION-STUDIO-001','request_id':'t','operation':'timeline.insert','idempotency_key':'i','args':{'project_root':d,'relative_path':'../x.tsx','content':'x','dry_run':True}}
   p=subprocess.run(['python',str(AD),'invoke'],input=json.dumps(q),text=True,capture_output=True);self.assertEqual(p.returncode,2)
 def test_destructive_requires_receipts(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'main.tsx').write_text('old');q={'schema':'fa3.provider-request.v1','provider_id':'FA3-PROVIDER-DIFFUSION-STUDIO-001','request_id':'t','operation':'timeline.delete','idempotency_key':'i','args':{'project_root':d,'relative_path':'main.tsx','content':'new'}}
   p=subprocess.run(['python',str(AD),'invoke'],input=json.dumps(q),text=True,capture_output=True);self.assertEqual(p.returncode,2)
if __name__=='__main__':unittest.main()
