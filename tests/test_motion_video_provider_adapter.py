import hashlib, json, os, tempfile, unittest
from pathlib import Path
from unittest import mock
import fa3_motion_video_provider_adapter as a

PROVIDER="FA3-PROVIDER-KLING-001"
class AdapterV2Tests(unittest.TestCase):
    def manifest(self,root,topology="REMOTE",requires=False,outputs=None):
        exe=root/"provider.py"; exe.write_text("#!/usr/bin/env python3\nimport pathlib,sys\nout=pathlib.Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b'video')\n"); exe.chmod(0o755)
        admission=root/"admission.json"; admission.write_text(json.dumps({"provider_id":PROVIDER,"status":"PASS","synthetic_or_mock_provider":False}))
        m={
          "schema":"fa3.motion-video-execution-manifest.v2","status":"ADMITTED","provider_id":PROVIDER,"service_provider":"Kling AI","model_family":"Kling","model_id":"test","model_version":"1",
          "capability_snapshot":{"schema":"fa3.video-capability-snapshot.v2","conditioning":["TEXT"],"generation_modes":["TEXT_TO_VIDEO"],"output_modes":outputs or ["VIDEO_ONLY"],"execution_topologies":["REMOTE_PROVIDER" if topology=="REMOTE" else "SINGLE_ACCELERATOR"],"temporal_modes":["FIXED_CLIP"],"backend_family":"TEST"},
          "provider_selection_authority":"FA3-AUTH-MODEL-ROUTER-001","resource_authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001",
          "transport":"FA3_EXECUTOR_COMMAND","cost_class":"FREE_REMOTE","execution_topology":topology,"execution_topology_class":"REMOTE_PROVIDER" if topology=="REMOTE" else "SINGLE_ACCELERATOR",
          "requires_accelerator":requires,"silent_fallback_allowed":False,
          "admission_receipt":str(admission),"admission_receipt_sha256":hashlib.sha256(admission.read_bytes()).hexdigest(),
          "lifecycle_compatibility":{"contract_id":"FA3-VIDEO-PROVIDER-LIFECYCLE-BACKEND-CACHE-CONTRACTS-001","requested_backend":"TEST","observed_backend":"TEST","runtime_version_tuple":"1","model_identity":"test","model_component_tuple":"model+vae+encoder","compatibility_evidence":"unit","fallback_policy":"DENY"},
          "executable":str(exe),"executable_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),"argv":["{ir}","{output}"],"audio_authority_claim":False
        }
        return m

    def files(self,root,m):
        mp=root/"manifest.json"; mp.write_text(json.dumps(m))
        s={"schema":"fa3.motion-video-route-selection-receipt.v2","authority":"FA3-AUTH-MODEL-ROUTER-001","status":"ROUTED","provider_id":PROVIDER,"service_provider":"Kling AI","model_family":"Kling","provider_manifest_sha256":hashlib.sha256(mp.read_bytes()).hexdigest()}
        sp=root/"selection.json"; sp.write_text(json.dumps(s))
        ir=root/"ir.json"; ir.write_text(json.dumps({"schema":"fa3.video-generation-ir.v2","request_id":"x"}))
        return sp,mp,ir

    def test_remote_exec_without_local_resource_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); sp,mp,ir=self.files(root,self.manifest(root)); out=root/"out.bin"
            r=a.execute(sp,mp,ir,workload_path=None,resource_projection_path=None,output_path=out,timeout=10)
            self.assertEqual(r["resource_count"],0); self.assertEqual(r["status"],"PASS")

    def test_local_requires_workload_mode(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); m=self.manifest(root,"LOCAL",True); sp,mp,ir=self.files(root,m)
            with self.assertRaises(a.MotionVideoDenied): a.execute(sp,mp,ir,workload_path=None,resource_projection_path=None,output_path=root/"o",timeout=10)

    def test_backend_mismatch_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); m=self.manifest(root); m["lifecycle_compatibility"]["observed_backend"]="OTHER"
            with self.assertRaises(a.MotionVideoDenied): a.validate_lifecycle(m)

    def test_resource_projection_zero_to_n_and_no_silent_expansion(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            recs=[]
            for i in range(2):
                p=root/f"r{i}.json"; p.write_text(json.dumps({"payload":{"hrb_lease_identity":{"lease_id":f"L{i}","accelerator_uuid":f"U{i}","pci_bus_id":f"0000:0{i}:00.0"}}}))
                recs.append({"receipt_path":str(p),"receipt_sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
            proj={"schema":"fa3.motion-video-hrb-resource-projection.v1","authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","cardinality":2,"resources":recs}
            m=self.manifest(root,"LOCAL",True)
            with mock.patch.object(a,"validate_resource_admission_receipt",return_value=[]):
                resources=a.validate_resource_projection(m,proj)
            self.assertEqual(len(resources),2)
            proj["cardinality"]=3
            with self.assertRaises(a.MotionVideoDenied): a.validate_resource_projection(m,proj)

    def test_synchronized_av_cannot_claim_voice_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); m=self.manifest(root,outputs=["SYNCHRONIZED_AV"]); m["audio_authority_claim"]=True
            sp,mp,ir=self.files(root,m)
            with self.assertRaises(a.MotionVideoDenied): a.execute(sp,mp,ir,workload_path=None,resource_projection_path=None,output_path=root/"o",timeout=10)

if __name__=="__main__": unittest.main()
