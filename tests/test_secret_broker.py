import base64,json,os,pwd,tempfile,unittest
from pathlib import Path
from src import fa3_secret_broker as b

class SecretBrokerTests(unittest.TestCase):
    def test_store_rotation_and_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            s=b.SecretStore(root)
            m1=s.put("provider/api","alpha".encode(),"MACHINE_SERVICE_SECRET","API_TOKEN")
            m2=s.put("provider/api","beta".encode(),"MACHINE_SERVICE_SECRET","API_TOKEN")
            self.assertEqual(1,m1["version"]);self.assertEqual(2,m2["version"])
            meta,value=s.get("provider/api")
            self.assertEqual(b"beta",value)
            obj=root/"objects"/meta["object"]
            self.assertEqual(0,obj.stat().st_mode & 0o077)
    def test_policy_authorization_and_audit_redaction(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);vault=root/"vault";pol=root/"policy";audit=root/"audit.jsonl";pol.mkdir()
            broker=b.Broker(vault,pol,audit)
            broker.store.put("github/token",b"TOP-SECRET-CANARY","MACHINE_SERVICE_SECRET","API_TOKEN")
            user=pwd.getpwuid(os.getuid()).pw_name
            policy={"schema":"fa3.secret-projection-policy.v1","secret_id":"github/token","classification":"MACHINE_SERVICE_SECRET","secret_kind":"API_TOKEN",
                    "allowed_consumers":[{"consumer_id":"TEST-CONSUMER","allowed_unix_users":[user],"allowed_executables":[],"allowed_systemd_units":[]}],
                    "allowed_projections":["UDS_SINGLE_SECRET"],"exportable":False}
            (pol/"github.json").write_text(json.dumps(policy))
            ok=broker.handle({"op":"get","secret_id":"github/token","consumer_id":"TEST-CONSUMER","projection":"UDS_SINGLE_SECRET"},os.getuid(),os.getgid(),os.getpid())
            self.assertTrue(ok["ok"]);self.assertEqual(b"TOP-SECRET-CANARY",base64.b64decode(ok["secret_b64"]))
            denied=broker.handle({"op":"get","secret_id":"github/token","consumer_id":"OTHER","projection":"UDS_SINGLE_SECRET"},os.getuid(),os.getgid(),os.getpid())
            self.assertFalse(denied["ok"])
            log=audit.read_text()
            self.assertNotIn("TOP-SECRET-CANARY",log)
            self.assertIn("secret_ref_sha256",log)
            self.assertIn('"secret_values_collected":false',log)
    def test_bulk_export_has_no_operation(self):
        with tempfile.TemporaryDirectory() as td:
            br=b.Broker(Path(td)/"v",Path(td)/"p",Path(td)/"a")
            r=br.handle({"op":"bulk"},os.getuid(),os.getgid(),os.getpid())
            self.assertFalse(r["ok"])
    def test_non_credential_kind_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            s=b.SecretStore(Path(td))
            with self.assertRaises(ValueError):s.put("cache/item",b"x","MACHINE_SERVICE_SECRET","CACHE")

    def test_policy_metadata_kind_mismatch_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);vault=root/"vault";pol=root/"policy";audit=root/"audit.jsonl";pol.mkdir()
            broker=b.Broker(vault,pol,audit)
            broker.store.put("provider/token",b"VALUE","MACHINE_SERVICE_SECRET","API_TOKEN")
            user=pwd.getpwuid(os.getuid()).pw_name
            policy={"schema":"fa3.secret-projection-policy.v1","secret_id":"provider/token","classification":"MACHINE_SERVICE_SECRET","secret_kind":"SERVICE_PASSWORD",
                    "allowed_consumers":[{"consumer_id":"TEST-CONSUMER","allowed_unix_users":[user],"allowed_executables":[],"allowed_systemd_units":[]}],
                    "allowed_projections":["UDS_SINGLE_SECRET"],"exportable":False}
            (pol/"provider.json").write_text(json.dumps(policy))
            r=broker.handle({"op":"get","secret_id":"provider/token","consumer_id":"TEST-CONSUMER","projection":"UDS_SINGLE_SECRET"},os.getuid(),os.getgid(),os.getpid())
            self.assertFalse(r["ok"])

    def test_invalid_secret_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            s=b.SecretStore(Path(td))
            with self.assertRaises(ValueError):s.put("../../escape",b"x","MACHINE_SERVICE_SECRET","API_TOKEN")

if __name__=="__main__":unittest.main()
