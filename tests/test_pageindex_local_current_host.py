from __future__ import annotations
import json,tempfile,threading,unittest
from pathlib import Path
from fa3_pageindex_local_current_host_gate import gate
from fa3_pageindex_local_gateway_adapter import build_adapters
from fa3_pageindex_local_evidence import write_fixture_pdf,TOKEN
ROOT=Path(__file__).resolve().parents[1]
class PageIndexLocalCurrentHostTests(unittest.TestCase):
    def test_static_gate_admitted_or_pending(self):
        report=gate(ROOT); self.assertEqual("PASS",report["result"],json.dumps(report,indent=2))
    def test_admission_wiring_is_consistent(self):
        conf=json.loads((ROOT/"canonical/FA3-PAGEINDEX-LOCAL-RUNTIME-CONFORMANCE-001.json").read_text())
        provider=json.loads((ROOT/"canonical/providers/FA3-PROVIDER-PAGEINDEX-LOCAL-001.json").read_text())
        reg=json.loads((ROOT/"canonical/mcp-capability-registry.json").read_text())
        if conf["status"]=="CURRENT_HOST_ADMITTED":
            self.assertTrue(conf["production_binding_connected"])
            self.assertTrue(conf["evidence_present"])
            self.assertEqual("CURRENT_HOST_ADMITTED",provider["status"])
            self.assertTrue((ROOT/conf["evidence_ref"]).is_file())
            rows=[]
            for cap in reg["capabilities"]:
                if cap["capability_id"] in {"fa3.document.index","fa3.document.retrieve"}:
                    rows += [p for p in cap["providers"] if p.get("provider_id")=="FA3-PROVIDER-PAGEINDEX-LOCAL-001"]
            self.assertEqual(2,len(rows))
            self.assertTrue(all(x["state"]=="CONNECTED" and x["evidence_ref"]==conf["evidence_ref"] for x in rows))

    def test_fixture_pdf_contains_token(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.pdf"; sha=write_fixture_pdf(p)
            self.assertTrue(p.read_bytes().startswith(b"%PDF")); self.assertIn(TOKEN.encode(),p.read_bytes()); self.assertEqual(64,len(sha))
    def test_registry_uses_unix_user_service(self):
        reg=json.loads((ROOT/"canonical/mcp-capability-registry.json").read_text())
        rows=[]
        for cap in reg["capabilities"]:
            if cap["capability_id"] in {"fa3.document.index","fa3.document.retrieve"}:
                rows += [p for p in cap["providers"] if p.get("provider_id")=="FA3-PROVIDER-PAGEINDEX-LOCAL-001"]
        self.assertEqual(2,len(rows)); self.assertTrue(all(x["transport"]=="unix-user-service" for x in rows))
    def test_systemd_egress_hardening_declared(self):
        unit=(ROOT/"deployment/pageindex-local/fa3-pageindex-local.service.in").read_text()
        router=(ROOT/"deployment/pageindex-local/fa3-pageindex-model-router.service.in").read_text()
        for text in (unit,router):
            self.assertIn("IPAddressDeny=any",text); self.assertIn("IPAddressAllow=localhost",text)
    def test_runtime_directory_and_restart_are_isolated(self):
        unit=(ROOT/"deployment/pageindex-local/fa3-pageindex-local.service.in").read_text()
        router=(ROOT/"deployment/pageindex-local/fa3-pageindex-model-router.service.in").read_text()
        installer=(ROOT/"bin/fa3-pageindex-local-install").read_text()
        self.assertIn("RuntimeDirectory=fa3-pageindex-local",unit)
        self.assertNotIn("RuntimeDirectory=fa3\n",unit)
        self.assertNotIn("After=default.target",router)
        self.assertIn('PAGEINDEX_SOCKET="$PAGEINDEX_RUNTIME_DIR/pageindex-local.sock"',installer)
        self.assertIn('FA3_PAGEINDEX_LOCAL_SOCKET=$PAGEINDEX_SOCKET',installer)
        self.assertIn('BindReadOnlyPaths="$PAGEINDEX_RUNTIME_DIR"',installer)
        self.assertIn("Gateway PageIndex socket environment mismatch",installer)
        self.assertNotIn("%t/fa3/pageindex-local.sock",installer)
        self.assertIn("restart fa3-pageindex-local.service",installer)
    def test_gateway_adapter_requires_absolute_socket(self):
        with self.assertRaises(Exception): build_adapters(Path("relative.sock"))
    def test_gateway_adapter_unavailable_reports_namespace_visibility(self):
        adapter=build_adapters(Path("/tmp/fa3-pageindex-missing/socket.sock"))[0]
        with self.assertRaises(Exception) as ctx:
            adapter.handler({"source":"/tmp/no.pdf"})
        msg=str(ctx.exception)
        self.assertIn("socket_exists=False",msg)
        self.assertIn("parent_exists=False",msg)
if __name__=="__main__": unittest.main()
