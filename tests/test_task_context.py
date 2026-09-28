import copy
import unittest

from fa3_task_context import (
    TaskContextDenied, project_task_context, restore_task_context
)

DATA = [
    {"id": "visible", "kind": "note", "text": "allowed task state"},
    {"id": "secret", "kind": "security_evidence", "text": "protected other task"},
    {"id": "hidden", "kind": "note", "text": "recoverable", "state": "HIDDEN"},
]
GRANT = {"task_id": "T-1", "allowed_item_ids": ["visible", "hidden"]}

def security(grant, task_id, ids):
    return grant["task_id"] == task_id and ids.issubset({"visible", "hidden"})

class TaskContextTests(unittest.TestCase):
    def test_permission_before_relevance_keeps_other_task_out(self):
        projected = project_task_context(DATA, task_id="T-1",
            requested_ids=["visible", "hidden"], grant=GRANT,
            verify_security_grant=security, target_active=1)
        entries = projected["projection"]["items"]
        self.assertEqual({row["id"] for row in entries}, {"visible", "hidden"})
        self.assertNotIn("protected other task", repr(projected))
        self.assertFalse(projected["authority"])
        self.assertFalse(projected["authorization_receipt_claim"])

    def test_missing_or_cross_task_grant_blocks_before_projection(self):
        for grant in ({}, {"task_id":"T-2","allowed_item_ids":["visible"]}):
            with self.subTest(grant=grant), self.assertRaises(TaskContextDenied):
                project_task_context(DATA, task_id="T-1", requested_ids=["visible"],
                    grant=grant, verify_security_grant=security)

    def test_untrusted_grant_fields_do_not_authenticate_themselves(self):
        fake = {"task_id":"T-1", "allowed_item_ids":["visible","secret"],"status":"VALID"}
        with self.assertRaises(TaskContextDenied):
            project_task_context(DATA, task_id="T-1",
                requested_ids=["visible","secret"], grant=fake,
                verify_security_grant=lambda *_: False)

    def test_denied_id_never_enters_ranker(self):
        with self.assertRaises(TaskContextDenied):
            project_task_context(DATA, task_id="T-1", requested_ids=["secret"],
                grant=GRANT, verify_security_grant=security, target_active=1)

    def test_restore_only_authorized_hidden_item(self):
        p = project_task_context(DATA, task_id="T-1", requested_ids=["visible","hidden"],
            grant=GRANT, verify_security_grant=security, target_active=0)
        restored = restore_task_context(p, item_id="hidden")
        self.assertEqual(next(r for r in restored["projection"]["items"] if r["id"]=="hidden")["state"],"ACTIVE")
        with self.assertRaises(TaskContextDenied):
            restore_task_context(restored, item_id="secret")

    def test_provenance_detects_tampering_and_duplicate_source(self):
        with self.assertRaises(TaskContextDenied):
            project_task_context(DATA + [copy.deepcopy(DATA[0])], task_id="T-1",
                requested_ids=["visible"],grant=GRANT,verify_security_grant=security)
        p = project_task_context(DATA, task_id="T-1", requested_ids=["hidden"],
            grant=GRANT,verify_security_grant=security,target_active=0)
        p["projection"]["items"][0]["text"] = "changed"
        with self.assertRaises(ValueError):
            restore_task_context(p,item_id="hidden")

if __name__=="__main__":
    unittest.main()
