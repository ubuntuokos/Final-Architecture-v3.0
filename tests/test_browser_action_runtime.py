from __future__ import annotations
import os,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from fa3_browser_action_runtime import BrowserActionDenied,MutationLedger,bind_selected_action,build_action_space,execute_action,normalize_observation,revalidate,type_text_generation_request,verify_outcome

def obs(*,revision=1,occluded=False):
    return {"observation_id":"obs-1","revision":revision,"document_id":"doc-1","page_fingerprint":"page-1",
      "url":"https://example.test/login","elements":[
        {"element_id":"username","role":"textbox","label":"Username","value":"","visible":True,"enabled":True,"occluded":False,"supported_actions":["TYPE_TEXT"]},
        {"element_id":"login","role":"button","label":"Login","visible":True,"enabled":True,"occluded":occluded,"supported_actions":["CLICK"]}
      ],"provenance":{"source":"test-browser"}}

class BrowserActionRuntimeTests(unittest.TestCase):
    def test_page_content_is_always_untrusted(self):
        raw=obs(); raw["trust_class"]="TRUSTED_SYSTEM"
        self.assertEqual("UNTRUSTED_EXTERNAL_CONTENT",normalize_observation(raw)["trust_class"])
    def test_action_space_contains_only_observed_operations(self):
        space=build_action_space(obs()); ids={x["action_id"] for x in space["candidates"]}
        self.assertIn("TYPE_TEXT:username",ids); self.assertIn("CLICK:login",ids); self.assertNotIn("CLICK:username",ids)
        self.assertEqual("DENY",space["candidate_set_expansion"])
    def test_stale_revision_denied(self):
        space=build_action_space(obs()); click=next(x for x in space["candidates"] if x["action_id"]=="CLICK:login")
        with self.assertRaises(BrowserActionDenied) as e: revalidate(bind_selected_action(space,click["id"]),obs(revision=2))
        self.assertEqual("STALE_OBSERVATION",e.exception.code)
    def test_occluded_click_denied(self):
        space=build_action_space(obs()); click=next(x for x in space["candidates"] if x["action_id"]=="CLICK:login")
        with self.assertRaises(BrowserActionDenied) as e: revalidate(bind_selected_action(space,click["id"]),obs(occluded=True))
        self.assertEqual("TARGET_OCCLUDED",e.exception.code)
    def test_done_is_not_success(self):
        current=obs(); space=build_action_space(current); done=next(x for x in space["candidates"] if x["action_id"]=="DONE")
        r=execute_action(bind_selected_action(space,done["id"]),current,lambda c,o:{"unexpected":True})
        self.assertEqual("COMPLETION_CLAIM",r["status"]); self.assertFalse(r["verified_success"])
    def test_type_text_delegates_model_selection(self):
        current=obs(); space=build_action_space(current); row=next(x for x in space["candidates"] if x["action_id"]=="TYPE_TEXT:username")
        r=type_text_generation_request(bind_selected_action(space,row["id"]),purpose="fill")
        self.assertEqual("FA3-AUTH-MODEL-ROUTER-001",r["authority"]); self.assertEqual("fa3-text-primary",r["logical_route"])
        self.assertNotIn("model",r); self.assertNotIn("provider",r)
    def test_blind_mutation_retry_denied(self):
        current=obs(); space=build_action_space(current); row=next(x for x in space["candidates"] if x["action_id"]=="CLICK:login")
        binding=bind_selected_action(space,row["id"]); ledger=MutationLedger(); ex=lambda c,o:{"accepted":True}
        self.assertEqual("EXECUTED",execute_action(binding,current,ex,ledger=ledger)["status"])
        with self.assertRaises(BrowserActionDenied) as e: execute_action(binding,current,ex,ledger=ledger)
        self.assertEqual("BLIND_MUTATION_RETRY_DENIED",e.exception.code)
    def test_independent_verification(self):
        post=obs(); post["url"]="https://example.test/account"
        r=verify_outcome([{"type":"url_contains","value":"/account"},{"type":"element_present","element_id":"login"}],post)
        self.assertEqual("VERIFIED_SUCCESS",r["result"])
    def test_cpu_only(self):
        old={k:os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES","ROCR_VISIBLE_DEVICES","ZE_AFFINITY_MASK")}
        try:
            for k in old: os.environ[k]=""
            self.assertTrue(build_action_space(obs())["candidates"])
        finally:
            for k,v in old.items():
                if v is None: os.environ.pop(k,None)
                else: os.environ[k]=v
if __name__=="__main__": unittest.main()
