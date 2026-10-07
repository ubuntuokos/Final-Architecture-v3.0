from __future__ import annotations
import importlib.util,json,os,tempfile,time,unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

root_helper=load_module("fa3_hrb_admission_root",ROOT/"libexec/fa3-host-resource-broker-admission-root.py")
client=load_module("fa3_hrb_admission_client",ROOT/"libexec/fa3-host-resource-broker-admission.py")

class HrbAdmissionBridgeTests(unittest.TestCase):
    def test_root_helper_denial_codes_do_not_expose_secret_material(self):
        self.assertEqual("KEYRING_INVALID",root_helper._denial_code(root_helper.AdmissionError("HRB admission keyring scope mismatch")))
        self.assertEqual("WORKLOAD_INVALID",root_helper._denial_code(root_helper.AdmissionError("workload schema mismatch")))
        self.assertEqual("INPUT_INVALID",root_helper._denial_code(root_helper.AdmissionError("input ownership or mode invalid")))

    def workload_bytes(self):
        return json.dumps({"schema":root_helper.WORKLOAD_SCHEMA,"workload_id":"cpu-workload-1","requirements":[{"metric":"cpu.physical_cores","operator":">=","value":1},{"metric":"memory.total_gib","operator":">=","value":1}]}).encode()

    def test_issue_and_validate_are_scope_bound_and_not_lease(self):
        key={"scope":root_helper.HMAC_SCOPE,"active_key_id":"k1","keys":[{"key_id":"k1","secret_hex":"11"*32}]}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"keys.json"; p.write_text(json.dumps(key)); p.chmod(0o600)
            with mock.patch.object(root_helper,"KEY_FILE",p), mock.patch.object(root_helper.os,"geteuid",return_value=0), mock.patch.object(root_helper.Path,"lstat",Path.lstat):
                with mock.patch.object(root_helper,"_load_keyring",return_value=("k1",bytes.fromhex("11"*32))):
                    doc=root_helper.issue_authorization(self.workload_bytes())
                    raw=json.dumps(doc,separators=(",",":")).encode()
                    validated=root_helper.validate_authorization_bytes(raw)
        self.assertEqual(validated["authority"],root_helper.AUTHORITY)
        self.assertEqual(validated["requested_resource_classes"],["cpu","memory"])
        self.assertFalse(validated["accelerator_required"])
        self.assertTrue(validated["semantics"]["authorization_is_not_resource_lease"])
        self.assertNotIn("lease_id",validated)

    def test_client_propagates_bounded_denial_reason(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); workload=td/"workload.json"; out=td/"auth.json"; helper=td/"helper"; helper.write_text("x"); helper.chmod(0o755)
            workload.write_bytes(self.workload_bytes()); workload.chmod(0o600)
            denied=mock.Mock(returncode=2,stdout="",stderr="DENIED:KEYRING_INVALID\n")
            with mock.patch.object(os,"geteuid",return_value=1000), mock.patch.object(client.subprocess,"run",return_value=denied):
                with self.assertRaisesRegex(client.ClientError,"KEYRING_INVALID"):
                    client.authorize(workload,out,helper=helper)

    def test_tampered_authorization_rejected(self):
        with mock.patch.object(root_helper,"_load_keyring",return_value=("k1",bytes.fromhex("22"*32))):
            doc=root_helper.issue_authorization(self.workload_bytes())
            doc["workload_id"]="other"
            with self.assertRaises(root_helper.AdmissionError):
                root_helper.validate_authorization_bytes(json.dumps(doc).encode())

    def test_forbidden_cu_tu_rejected(self):
        bad=json.dumps({"schema":root_helper.WORKLOAD_SCHEMA,"workload_id":"w","requirements":[{"metric":"tu","operator":">=","value":1}]}).encode()
        with self.assertRaises(root_helper.AdmissionError):
            root_helper._parse_workload(bad)

    def test_installer_owner_only_permission_check_has_correct_precedence(self):
        script=(ROOT/"bin/fa3-install-hrb-admission-bridge.sh").read_text(encoding="utf-8")
        self.assertIn('(( (8#$mode & 077) == 0 ))',script)
        self.assertNotIn('(( 8#$mode & 077 == 0 ))',script)

    def test_client_writes_private_authorization_without_shell(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); workload=td/"workload.json"; out=td/"auth.json"; helper=td/"helper"; helper.write_text("x"); helper.chmod(0o755)
            raw=self.workload_bytes(); workload.write_bytes(raw)
            doc={"schema":client.AUTH_SCHEMA,"workload_id":"cpu-workload-1","workload_envelope_sha256":__import__("hashlib").sha256(raw).hexdigest()}
            completed=mock.Mock(returncode=0,stdout=json.dumps(doc),stderr="")
            with mock.patch.object(os,"geteuid",return_value=1000), mock.patch.object(client.subprocess,"run",return_value=completed) as invoked:
                client.authorize(workload,out,helper=helper)
            self.assertEqual(out.stat().st_mode & 0o777,0o600)
            self.assertEqual(invoked.call_args.args[0][:4],["sudo","-n",str(helper),"authorize"])
            self.assertNotIn("shell",invoked.call_args.kwargs)

if __name__=="__main__":
    unittest.main()
