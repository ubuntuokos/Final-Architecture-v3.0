import datetime
import getpass
import socket
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import fa3_terax_host_observation as obs

class TeraxHostObservationTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.datetime.now(datetime.timezone.utc)
        self.doc={
          "schema":"fa3.current-host-runner-doctor-receipt.v1","result":"PASS",
          "repository":"ubuntuokos/Final-Architecture-v3.0","runner_status":"online",
          "labels":["self-hosted","linux","x64","fa3-current-host"],
          "host":socket.gethostname(),"user":getpass.getuser(),
          "required_labels_present":True,"systemd_user_service_active":True,
          "hrb_validator_bridge_ready":True,"hrb_acquire_bridge_ready":True,
          "observed_at":self.now.isoformat()}
        self.rec={
          "schema":"fa3.terax-current-host.v2","provider_id":"FA3-PROVIDER-TERAX-001",
          "status":"OBSERVATIONAL_ONLY","physical_attestation":False,
          "host_scope":"CURRENT_HOST","provider_state":"DISABLED_REFERENCE_ONLY",
          "host_fingerprint_sha256":obs.fingerprint(),
          "workload_execution_requested":False,"requested_resource_classes":[],
          "accelerator_discovery_performed":False,"accelerator_lease_required":False,
          "gpu_telemetry":"NOT_APPLICABLE_NO_ACCELERATOR_RESOURCE_CLASS",
          "provider_receipt_substitution_allowed":False,"capability_promotion_claim":False,
          "global_promotion_claim":False,
          "metrics":{"resident_process_count":0,"worker_thread_count":0,"ram_resident_bytes":0,
                     "network_session_count":0,"active_polling":False,"background_inference":False},
          "collected_at":self.now.isoformat(),
          "expires_at":(self.now+datetime.timedelta(days=1)).isoformat()}
    def result(self):
        return obs.validate(self.doc,self.rec,source_sha="a"*40,expected_sha="a"*40,
                            now=self.now,effective_uid=1000)
    def test_positive_fixture_is_observation_not_physical_pass(self):
        v=self.result()
        self.assertEqual(v["result"],"OBSERVATIONAL_ONLY",v)
        self.assertFalse(v["physical_current_host_pass_claim"])
        self.assertFalse(v["global_promotion_claim"])
        self.assertEqual(v["coexistence_current_host_status"],"PENDING_CURRENT_HOST")
        self.assertIn("AUTHORITATIVE_HRB_LEASE_AND_RESERVATION_INVENTORY",v["missing_for_physical_pass"])
    def test_forged_physical_pass_denied(self):
        self.rec["status"]="PASS";self.rec["physical_attestation"]=True
        self.assertEqual(self.result()["result"],"FAIL")
    def test_missing_runner_labels_denied(self):
        self.doc["labels"]=["ubuntu-latest"]
        self.assertEqual(self.result()["result"],"FAIL")
    def test_wrong_host_denied(self):
        self.doc["host"]="other-host"
        self.assertEqual(self.result()["result"],"FAIL")
    def test_boolean_zero_not_accepted_as_metric(self):
        self.rec["metrics"]["resident_process_count"]=False
        self.assertEqual(self.result()["result"],"FAIL")
    def test_resource_leak_denied(self):
        self.rec["metrics"]["worker_thread_count"]=1
        self.assertEqual(self.result()["result"],"FAIL")
    def test_disabled_reference_cannot_probe_accelerator(self):
        self.rec["accelerator_discovery_performed"]=True
        self.assertEqual(self.result()["result"],"FAIL")
    def test_stale_runner_doctor_denied(self):
        self.doc["observed_at"]=(self.now-datetime.timedelta(days=1)).isoformat()
        self.assertEqual(self.result()["result"],"FAIL")
    def test_wrong_checkout_denied(self):
        v=obs.validate(self.doc,self.rec,source_sha="a"*40,expected_sha="b"*40,
                       now=self.now,effective_uid=1000)
        self.assertEqual(v["result"],"FAIL")
    def test_collector_no_nvidia_discovery(self):
        s=(ROOT/"evidence/collect-terax-current-host.py").read_text()
        self.assertNotIn("nvidia-smi",s)
        self.assertIn('"physical_attestation": False',s)

if __name__=="__main__":
    unittest.main()
