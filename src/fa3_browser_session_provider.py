#!/usr/bin/env python3
from __future__ import annotations
import hashlib,time
from typing import Any,Callable
from fa3_browser_action_runtime import BrowserActionDenied,MutationLedger,execute_action,normalize_observation,verify_outcome
from fa3_browser_session_bridge import BrowserSessionBridgeError,BrowserSessionBridgeServer
from fa3_uaf import ActionRequest,ProviderDescriptor
PROVIDER_ID="FA3-PROVIDER-BROWSER-SESSION-BRIDGE-001"
ACTION_EXECUTE="browser.action.execute"
ACTION_IDS=(ACTION_EXECUTE,"browser.session.start","browser.session.stop","browser.tab.list","browser.tab.borrow","browser.tab.return","browser.human_assistance.request","browser.human_assistance.cancel")
class BrowserSessionProvider:
    descriptor=ProviderDescriptor(provider_id=PROVIDER_ID,action_ids=ACTION_IDS,capabilities=("browser.session.local-native-messaging","browser.session.logical-tab-lease","browser.bounded-action-execution","browser.human-assistance"),priority=45,state="CONNECTED",metadata={"architectural_authority":False,"parent_profile":"FA3-BROWSER-SESSION-INTERACTION-001","action_runtime":"FA3-BROWSER-ACTION-RUNTIME-001","transport":"NATIVE_MESSAGING_TO_NAMESPACED_UNIX_SOCKET","cpu_only_supported":True,"remote_browser":False})
    def __init__(self,bridge:BrowserSessionBridgeServer,*,binding_loader:Callable[[str],dict[str,Any]],receipt_sink:Callable[[str,dict[str,Any]],str]):
        self.bridge=bridge;self.binding_loader=binding_loader;self.receipt_sink=receipt_sink;self.ledger=MutationLedger()
        self._revision_by_tab={};self._fingerprint_by_tab={};self._observation_id_by_tab={}
    def _require_resource(self,resource_lease,secret_leases):
        if resource_lease is None:raise BrowserActionDenied("BROWSER-RESOURCE-DENIED","HRB admission authorization required")
        if secret_leases:raise BrowserActionDenied("BROWSER-SECRET-DENIED","browser session provider accepts no direct secret projection")
    def observe(self,tab_ref:str)->dict[str,Any]:
        try:response=self.bridge.request("page.observe",{"tab_ref":tab_ref})
        except BrowserSessionBridgeError as exc:raise BrowserActionDenied(exc.code,str(exc)) from exc
        raw=response.get("observation")
        if not isinstance(raw,dict):raise BrowserActionDenied("BROWSER-OBSERVATION-FAILED","bridge observation missing")
        raw=dict(raw);html=str(raw.pop("html",""));fingerprint=hashlib.sha256((str(raw.get("url",""))+"\n"+html).encode()).hexdigest()
        if self._fingerprint_by_tab.get(tab_ref)!=fingerprint:
            self._revision_by_tab[tab_ref]=self._revision_by_tab.get(tab_ref,0)+1;self._fingerprint_by_tab[tab_ref]=fingerprint
            self._observation_id_by_tab[tab_ref]=f"obs-{self._revision_by_tab[tab_ref]}-{fingerprint[:12]}"
        document_id=hashlib.sha256(f"{tab_ref}|{raw.get('timeOrigin')}".encode()).hexdigest()
        return normalize_observation({"observation_id":self._observation_id_by_tab[tab_ref],"revision":self._revision_by_tab[tab_ref],"document_id":document_id,"page_fingerprint":fingerprint,"url":str(raw.get("url","")),"elements":raw.get("elements",[]),"provenance":{"provider_id":PROVIDER_ID,"transport":"NATIVE_MESSAGING_UNIX_SOCKET","tab_ref":tab_ref}})
    def _execute_candidate(self,tab_ref,candidate,parameters):
        operation=str(candidate.get("operation",""))
        if operation=="WAIT":
            milliseconds=parameters.get("milliseconds",250)
            if not isinstance(milliseconds,int) or not 0<=milliseconds<=5000:raise BrowserActionDenied("BROWSER-PARAMETERS-INVALID","WAIT outside bounded range")
            time.sleep(milliseconds/1000);return{"operation":"WAIT","transport":"LOCAL_RUNTIME","physical_browser":True}
        if operation not in {"CLICK","TYPE_TEXT","SELECT","SCROLL_INTO_VIEW","PRESS_KEY"}:raise BrowserActionDenied("BROWSER-EXECUTION-INVALID",f"unsupported session operation: {operation}")
        try:result=self.bridge.request("page.execute",{"tab_ref":tab_ref,"operation":operation,"target_id":candidate.get("target_id"),"parameters":parameters})
        except BrowserSessionBridgeError as exc:raise BrowserActionDenied(exc.code,str(exc)) from exc
        return{"operation":operation,"target_id":candidate.get("target_id"),"transport":"NATIVE_MESSAGING_UNIX_SOCKET","physical_browser":True,"dom_event_execution":True,"bridge_result":result.get("status")}
    def _session_action(self,request:ActionRequest)->dict[str,Any]:
        method={"browser.session.start":"session.start","browser.session.stop":"session.stop","browser.tab.list":"tabs.list","browser.tab.borrow":"tab.borrow","browser.tab.return":"tab.return","browser.human_assistance.request":"assist.request","browser.human_assistance.cancel":"assist.cancel"}.get(request.action_id)
        if method is None:raise BrowserActionDenied("BROWSER-EXECUTION-INVALID","unsupported browser session action")
        params=dict(request.arguments)
        if request.approval is not None and request.action_id in {"browser.tab.borrow","browser.human_assistance.request"}:
            params["approval"]={"approved":True,"authority":str(request.approval.get("authority","")),"receipt":str(request.approval.get("approval_id",""))}
        try:result=self.bridge.request(method,params)
        except BrowserSessionBridgeError as exc:raise BrowserActionDenied(exc.code,str(exc)) from exc
        result=dict(result);result["execution_receipt_ref"]=self.receipt_sink(request.action_id,{"schema":"fa3.browser-session-action-receipt.v1","action_id":request.action_id,"result":result,"global_promotion_claim":False});return result
    def execute(self,request:ActionRequest,resource_lease:Any=None,secret_leases:tuple[Any,...]=()):
        self._require_resource(resource_lease,secret_leases)
        if request.action_id!=ACTION_EXECUTE:return self._session_action(request)
        ref=request.arguments.get("binding_ref")
        if not isinstance(ref,str) or not ref:raise BrowserActionDenied("BROWSER-BINDING-INVALID","binding_ref required")
        binding=self.binding_loader(ref);tab_ref=binding.get("tab_ref")
        if not isinstance(tab_ref,str) or not tab_ref:raise BrowserActionDenied("BROWSER-BINDING-INVALID","session tab_ref missing")
        parameters=binding.get("execution_parameters",{})
        execution=execute_action(binding,self.observe(tab_ref),lambda candidate,observation:self._execute_candidate(tab_ref,candidate,parameters),ledger=self.ledger)
        expected=request.arguments.get("expected_postconditions",[])
        if execution.get("status")=="EXECUTED":verification=verify_outcome(expected,self.observe(tab_ref));status=verification["result"]
        else:verification={"schema":"fa3.browser-outcome-verification.v1","result":"INDETERMINATE","checks":[],"global_promotion_claim":False};status=str(execution.get("status"))
        return{"status":status,"execution_receipt_ref":self.receipt_sink("execution",execution),"verification_ref":self.receipt_sink("verification",verification)}
