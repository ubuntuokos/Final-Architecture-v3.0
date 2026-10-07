from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from fa3_browser_action_runtime import BrowserActionDenied,bind_selected_action,build_action_space
from fa3_browser_cdp_gate import gate
from fa3_browser_cdp_provider import BrowserCdpProvider,CdpProviderError,_loopback_url
from fa3_uaf import ActionRequest,ExecutionContext
def obs(url="http://127.0.0.1/"):return{"observation_id":"obs-1","revision":1,"document_id":"doc-1","page_fingerprint":"fp-1","url":url,"elements":[{"element_id":"el-0000","role":"button","label":"Advance","value":None,"visible":True,"enabled":True,"occluded":False,"supported_actions":["CLICK"],"metadata":{}}],"provenance":{}}
class FakeSession:
    def __init__(self):self.after=False
    def observe(self):
        v=obs("http://127.0.0.1/#clicked" if self.after else "http://127.0.0.1/")
        if self.after:v.update(observation_id="obs-2",revision=2,page_fingerprint="fp-2")
        return v
    def execute_candidate(self,c,p):self.after=True;return{"operation":c["operation"]}
class T(unittest.TestCase):
    def test_remote_denied(self):
        with self.assertRaises(CdpProviderError):_loopback_url("ws://example.com/x",schemes={"ws"})
    def test_execution_verification(self):
        space=build_action_space(obs());click=next(x for x in space["candidates"] if x["operation"]=="CLICK");binding=bind_selected_action(space,click["id"]);binding["execution_parameters"]={};receipts=[];p=BrowserCdpProvider(FakeSession(),binding_loader=lambda ref:binding,receipt_sink=lambda k,v:receipts.append(k) or f"evidence://{k}");r=p.execute(ActionRequest(action_id="browser.action.execute",arguments={"binding_ref":"b","expected_postconditions":[{"type":"url_contains","value":"#clicked"}]},principal={"id":"u"},context=ExecutionContext("c")),resource_lease={"lease_id":"h"});self.assertEqual("VERIFIED_SUCCESS",r["status"]);self.assertEqual(["execution","verification"],receipts)
    def test_hrb_required(self):
        p=BrowserCdpProvider(FakeSession(),binding_loader=lambda ref:{},receipt_sink=lambda k,v:"e")
        with self.assertRaises(BrowserActionDenied):p.execute(ActionRequest(action_id="browser.action.execute",arguments={"binding_ref":"b"},principal={"id":"u"},context=ExecutionContext("c")))
    def test_gate(self):self.assertEqual("PASS",gate(ROOT)["result"])
if __name__=="__main__":unittest.main()
