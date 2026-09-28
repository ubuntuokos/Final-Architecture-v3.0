import copy
import unittest

from fa3_agent_resume_preflight import assess_resume, event_digest, ResumeDenied

def events():
    e1 = {"event_id":"e1","session_id":"s","sequence":1,
          "event_type":"SESSION_STARTED","previous_sha256":"0"*64}
    e1["event_sha256"] = event_digest(e1)
    e2 = {"event_id":"e2","session_id":"s","sequence":2,
          "event_type":"EXTERNAL_EFFECT_COMMITTED","effect_key":"once",
          "evidence_ref":"journal:immutable-001","previous_sha256":e1["event_sha256"]}
    e2["event_sha256"] = event_digest(e2)
    e3 = {"event_id":"e3","session_id":"s","sequence":3,
          "event_type":"APPROVAL_PENDING","effect_key":"requires-human",
          "previous_sha256":e2["event_sha256"]}
    e3["event_sha256"] = event_digest(e3)
    return [e1,e2,e3]

def run(history=None, requests=None, **changes):
    history = history if history is not None else events()
    opts = dict(session_id="s", events=history,
         requested=requests if requests is not None else [
             {"effect_key":"once"},{"effect_key":"requires-human"},{"effect_key":"new"}],
         verify_authenticated_ledger=lambda session,terminal: session=="s" and terminal==history[-1]["event_sha256"],
         expected_terminal_digest=history[-1]["event_sha256"],
         attempted_retries=0,max_retries=2,max_tool_calls=4)
    opts.update(changes)
    return assess_resume(**opts)

class ResumePreflightTests(unittest.TestCase):
    def test_never_replay_committed_effect_or_auto_approve(self):
        result=run()
        self.assertEqual([x["state"] for x in result["effects"]],[
            "VERIFY_EXISTING_EFFECT_NO_REEXECUTION",
            "PAUSED_AWAITING_EXISTING_APPROVAL",
            "REQUIRE_FRESH_SECURITY_UAF_HRB_AND_MODEL_ROUTE_ADMISSION"])
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["authority"])

    def test_tamper_different_session_and_stale_checkpoint_fail_closed(self):
        h=events()
        h[1]["evidence_ref"]="changed"
        with self.assertRaises(ResumeDenied):run(history=h)
        with self.assertRaises(ResumeDenied):run(session_id="foreign")
        with self.assertRaises(ResumeDenied):run(expected_terminal_digest="0"*64)
        with self.assertRaises(ResumeDenied):run(verify_authenticated_ledger=lambda *_:False)

    def test_duplicate_event_and_effect_fail_closed(self):
        h=events()
        h[1]["event_id"]="e1"
        h[1]["event_sha256"]=event_digest(h[1])
        h[2]["previous_sha256"]=h[1]["event_sha256"]
        h[2]["event_sha256"]=event_digest(h[2])
        with self.assertRaises(ResumeDenied):run(history=h)
        with self.assertRaises(ResumeDenied):run(requests=[{"effect_key":"x"},{"effect_key":"x"}])

    def test_exhausted_retry_budget_escalates_but_does_not_replay(self):
        result=run(attempted_retries=2)
        self.assertEqual(result["effects"][0]["state"],"VERIFY_EXISTING_EFFECT_NO_REEXECUTION")
        self.assertEqual(result["effects"][2]["state"],"ESCALATE_RETRY_BUDGET_EXHAUSTED")
        self.assertEqual(result["remaining_retry_budget"],0)
        with self.assertRaises(ResumeDenied):
            run(max_tool_calls=1)

if __name__=="__main__":
    unittest.main()
