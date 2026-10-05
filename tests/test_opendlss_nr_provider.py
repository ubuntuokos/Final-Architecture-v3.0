from __future__ import annotations
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_opendlss_nr_provider import OpenDlssNrError,validate_model_manifest

class OpenDlssNrProviderTests(unittest.TestCase):
    def test_model_manifest_stage_sha256(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); payload=b"fa3-neural-rendering-stage"; (root/"stage.bin").write_bytes(payload)
            (root/"manifest.json").write_text(json.dumps({"stages":[{"id":"s0","file":"stage.bin","packedByteLength":len(payload),"sha256":hashlib.sha256(payload).hexdigest()}],"tensors":[]}),encoding="utf-8")
            r=validate_model_manifest(root,True); self.assertEqual(1,r["stage_count"]); self.assertFalse(r["model_registry_admission_implied"])
    def test_model_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"stage.bin").write_bytes(b"x")
            (root/"manifest.json").write_text(json.dumps({"stages":[{"id":"s","file":"stage.bin","packedByteLength":1,"sha256":"0"*64}],"tensors":[]}),encoding="utf-8")
            with self.assertRaises(OpenDlssNrError) as c: validate_model_manifest(root,True)
            self.assertEqual("ODNR-STAGE-SHA256-MISMATCH",c.exception.code)
if __name__=="__main__": unittest.main()
