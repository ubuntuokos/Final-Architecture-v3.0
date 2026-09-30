import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"evidence/collect-communications-contacts-current-host.py"
SPEC=importlib.util.spec_from_file_location("comm_current_host_collector",PATH)
MOD=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

class CommunicationsCurrentHostCollectorTests(unittest.TestCase):
    def valid_receipt(self):
        return {
            "status":"PASS","current_host":True,"physical_execution":True,"production_e2e":True,
            "synthetic":False,"historical_only":False,"provider_id":"TEST-PROVIDER",
            "protocols":{"smtp":True,"imap_or_jmap":True,"carddav":True,"tls_certificate_validation":True},
            "roundtrips":{"send_receive":True,"contact":True},
            "security":{
                "secret_broker_used":True,"attachment_security_pass":True,"malware_scanner_pass":True,
                "dlp_pass":True,"software_coexistence_pass":True,"hardware_safety_pass":True,
                "authorization_context_pass":True,
            },
            "evidence_refs":["physical-provider-receipt"],
        }

    def test_complete_physical_receipt_is_structurally_admissible(self):
        self.assertEqual([],MOD.validate_provider_receipt(self.valid_receipt()))

    def test_synthetic_receipt_is_rejected(self):
        r=self.valid_receipt(); r["synthetic"]=True
        self.assertIn("synthetic-evidence-forbidden",MOD.validate_provider_receipt(r))

    def test_missing_contact_roundtrip_is_rejected(self):
        r=self.valid_receipt(); r["roundtrips"]["contact"]=False
        self.assertIn("roundtrip:contact",MOD.validate_provider_receipt(r))

    def test_secret_value_field_is_rejected(self):
        r=self.valid_receipt(); r["token_value"]="do-not-store"
        with self.assertRaises(ValueError):
            MOD.validate_provider_receipt(r)

if __name__=="__main__":
    unittest.main()
