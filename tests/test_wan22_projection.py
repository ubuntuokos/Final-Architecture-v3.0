import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

modelset=load_module("fa3_wan22_model_set_admit","bin/fa3-wan22-model-set-admit.py")
wrapper=load_module("fa3_wan22_provider_exec","bin/fa3-wan22-provider-exec.py")

class Wan22ProjectionTests(unittest.TestCase):
    def test_frame_count_is_4n_plus_1(self):
        for duration in (1,2,5,8):
            n=wrapper.frame_num({"duration":duration})
            self.assertEqual((n-1)%4,0)
            self.assertGreaterEqual(n,5)

    def test_provider_projection_does_not_embed_cloud_prompt_extension(self):
        self.assertEqual(wrapper.size_from_ir({"resolution":"720P","ratio":"16:9"}),"1280*720")
        with self.assertRaises(wrapper.WanExecutionDenied):
            wrapper.size_from_ir({"resolution":"2K","ratio":"16:9"})

    def test_model_set_aggregates_existing_fa3_artifact_admissions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);ckpt=root/"ckpt";ckpt.mkdir()
            artifact=ckpt/"model.safetensors";artifact.write_bytes(b"wan-model")
            digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
            ar=root/"artifact-admission.json"
            ar.write_text(json.dumps({
                "schema":"fa3.model-artifact-admission-receipt.v1",
                "admitted":True,
                "artifact_sha256":digest,
                "malware_security_admission":"PASS"
            }))
            manifest=root/"set.json"
            manifest.write_text(json.dumps({
                "schema":"fa3.wan22-model-set-manifest.v1",
                "provider_id":"FA3-PROVIDER-WAN22-001",
                "upstream_revision":modelset.UPSTREAM_REV,
                "checkpoint_dir":str(ckpt),
                "artifacts":[{"relative_path":"model.safetensors","admission_receipt":str(ar)}]
            }))
            out=root/"out.json"
            r=modelset.admit(manifest,out)
            self.assertEqual(r["status"],"PASS")
            self.assertTrue(r["all_artifacts_individually_security_admitted"])
            self.assertFalse(r["aggregator_is_security_authority"])
            self.assertEqual(r["artifact_count"],1)
            self.assertEqual(len(r["artifact_set_sha256"]),64)

    def test_model_set_rejects_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);ckpt=root/"ckpt";ckpt.mkdir()
            artifact=ckpt/"model.safetensors";artifact.write_bytes(b"wan-model")
            ar=root/"artifact-admission.json"
            ar.write_text(json.dumps({
                "schema":"fa3.model-artifact-admission-receipt.v1",
                "admitted":True,
                "artifact_sha256":"0"*64,
                "malware_security_admission":"PASS"
            }))
            manifest=root/"set.json"
            manifest.write_text(json.dumps({
                "schema":"fa3.wan22-model-set-manifest.v1",
                "provider_id":"FA3-PROVIDER-WAN22-001",
                "upstream_revision":modelset.UPSTREAM_REV,
                "checkpoint_dir":str(ckpt),
                "artifacts":[{"relative_path":"model.safetensors","admission_receipt":str(ar)}]
            }))
            with self.assertRaises(modelset.ModelSetDenied):
                modelset.admit(manifest,root/"out.json")

if __name__=="__main__":
    unittest.main()
