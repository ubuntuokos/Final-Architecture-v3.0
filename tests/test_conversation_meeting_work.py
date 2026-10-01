from __future__ import annotations
import unittest
from fa3_conversation_meeting_work import WorkPolicyError,approve_for_materialization,emit_draft_intent,normalize_event,project_views,propose,reject,rollback_draft,verify_human

def event(n,t,text,origin="DETERMINISTIC",speaker="p1"):
    return {"event_id":f"evt-{n}","source_id":"meeting-group-1","timestamp":f"2026-10-01T10:{n:02d}:00+02:00","speaker_id":speaker,"speaker_role":"participant","origin":origin,"object_type":t,"text":text,"confidence":0.99}

class TestWorkFabric(unittest.TestCase):
    def test_group_meeting(self):
        xs=[event(1,"DECISION","One graph."),event(2,"DECISION","AI optional."),event(3,"TASK","Adapter."),event(4,"TASK","GUI."),event(5,"TASK","Current host."),event(6,"QUESTION","Which adapter first?")]
        ps=[verify_human(propose(normalize_event(x)),verifier_id="r") for x in xs]
        ps[4]=reject(ps[4],reviewer_id="r",reason="defer")
        for k in (2,3): ps[k]=approve_for_materialization(ps[k],approver_id="a",permissions={"MATERIALIZE_WORK"})
        ds=[emit_draft_intent(ps[k]) for k in (2,3)]
        v=project_views(ps)
        self.assertEqual(2,len(ds)); self.assertTrue(all(x["state"]=="DRAFT_NOT_CANONICAL" for x in ds))
        self.assertEqual(2,len(v["views"]["DECISION_MAP"]["items"])); self.assertEqual(2,len(v["views"]["TASK_LIST"]["items"])); self.assertEqual(1,len(v["views"]["OPEN_QUESTIONS"]["items"]))
    def test_speaker_is_not_authority(self):
        p=verify_human(propose(normalize_event(event(1,"TASK","Do work",speaker="owner-claim"))),verifier_id="r")
        with self.assertRaisesRegex(WorkPolicyError,"APPROVER_NOT_AUTHORIZED"): approve_for_materialization(p,approver_id="owner-claim",permissions=set())
    def test_ai_disabled_manual_remains(self):
        with self.assertRaisesRegex(WorkPolicyError,"AI_DISABLED"): normalize_event(event(1,"TASK","AI",origin="AI_PROPOSAL"),ai_enabled=False)
        self.assertEqual("MANUAL",normalize_event(event(2,"TASK","Manual",origin="MANUAL"),ai_enabled=False).origin)
    def test_missing_provenance(self):
        x=event(1,"TASK","x"); del x["source_id"]
        with self.assertRaisesRegex(WorkPolicyError,"MISSING_PROVENANCE"): normalize_event(x)
    def test_verification_required(self):
        p=propose(normalize_event(event(1,"DECISION","x")))
        with self.assertRaisesRegex(WorkPolicyError,"HUMAN_VERIFICATION_REQUIRED"): approve_for_materialization(p,approver_id="a",permissions={"MATERIALIZE_WORK"})
    def test_rollback(self):
        p=verify_human(propose(normalize_event(event(1,"TASK","x"))),verifier_id="r"); p=approve_for_materialization(p,approver_id="a",permissions={"MATERIALIZE_WORK"}); p=rollback_draft(p)
        self.assertEqual("HUMAN_VERIFIED",p.state); self.assertTrue(p.metadata["draft_retracted"])
if __name__=="__main__": unittest.main()
