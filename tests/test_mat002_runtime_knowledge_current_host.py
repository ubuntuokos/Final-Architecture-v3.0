import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_mat002_runtime_knowledge_current_host import (
    CAPABILITIES,
    agent_task_allowed,
    deliberation_valid,
    expected_source_decisions,
    hrb_failure_summary,
    hrb_gate_failure_codes,
    knowledge_note_allowed,
    validate_exact_coverage,
    workspace_allowed,
)

class Mat002RuntimeKnowledgeCurrentHostTests(unittest.TestCase):
    def _root(self):
        td=tempfile.TemporaryDirectory();root=Path(td.name);(root/"evidence").mkdir(parents=True)
        records=[{"subject_id":cap,"source_decision_ids":[f"DEC-{cap}","FA3-CORE-001"]} for cap in CAPABILITIES]
        (root/"evidence/evidence-registry.json").write_text(json.dumps({"records":records})+"\n",encoding="utf-8")
        return td,root

    def test_exact_coverage_is_ordered_and_fail_closed(self):
        td,root=self._root()
        try:
            exp=expected_source_decisions(root,"CAP-006")
            self.assertEqual(exp,["DEC-CAP-006","FA3-CORE-001"])
            self.assertEqual(validate_exact_coverage(root,"CAP-006",exp),exp)
            with self.assertRaises(RuntimeError):
                validate_exact_coverage(root,"CAP-006",list(reversed(exp)))
        finally:td.cleanup()

    def test_agent_task_policy_rejects_privilege_and_external_network(self):
        good={"execution_scope":"CURRENT_HOST","requires_human_approval":True,"privileged":False,"network_scope":"NONE","argv":[sys.executable,"-c","print(1)"]}
        self.assertTrue(agent_task_allowed(good))
        self.assertFalse(agent_task_allowed({**good,"argv":["sudo","id"]}))
        self.assertFalse(agent_task_allowed({**good,"requires_human_approval":False}))
        self.assertFalse(agent_task_allowed({**good,"network_scope":"INTERNET"}))

    def test_workspace_policy_requires_bounded_child(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);approved=base/"workspace";approved.mkdir();child=approved/"project";child.mkdir();home=base/"home";home.mkdir()
            self.assertTrue(workspace_allowed(child,approved,home,()))
            self.assertFalse(workspace_allowed(approved,approved,home,()))
            self.assertFalse(workspace_allowed(home,approved,home,()))
            self.assertFalse(workspace_allowed(Path("/"),approved,home,()))

    def test_deliberation_requires_unique_actor_quorum(self):
        self.assertTrue(deliberation_valid([{"actor_id":"a","choice":"A"},{"actor_id":"b","choice":"A"},{"actor_id":"c","choice":"B"}]))
        self.assertFalse(deliberation_valid([{"actor_id":"a","choice":"A"},{"actor_id":"a","choice":"A"}]))
        self.assertFalse(deliberation_valid([{"actor_id":"a","choice":"A"},{"actor_id":"b","choice":"B"},{"actor_id":"c","choice":"ABSTAIN"}]))

    def test_knowledge_note_admission_is_fail_closed(self):
        good={"id":"n1","status":"APPROVED","index":True,"visibility":"PRIVATE"}
        self.assertTrue(knowledge_note_allowed(good))
        self.assertFalse(knowledge_note_allowed({**good,"status":"DRAFT"}))
        self.assertFalse(knowledge_note_allowed({**good,"visibility":"UNKNOWN"}))
        self.assertFalse(knowledge_note_allowed({**good,"index":False}))

    def test_mat002_capability_set_is_exact_second_batch(self):
        self.assertEqual(CAPABILITIES,("CAP-006","CAP-007","CAP-008","CAP-009","CAP-010"))

    def test_hrb_failure_summary_is_allowlisted_and_vendor_neutral(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"receipt.json"
            path.write_text(json.dumps({"check_summary":{
                "cpu_baseline_pass":True,"accelerator_inventory_schema_pass":True,
                "accelerator_device_count":0,"failed_check_codes":[],
                "device_uuid":"must-not-leak","vendor":"must-not-leak",
            }})+"\n",encoding="utf-8")
            summary=hrb_failure_summary(path)
            self.assertEqual(summary["accelerator_device_count"],0)
            self.assertTrue(summary["accelerator_inventory_schema_pass"])
            self.assertNotIn("device_uuid",summary)
            self.assertNotIn("vendor",summary)

    def test_hrb_missing_receipt_and_gate_report_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.assertEqual(hrb_failure_summary(root/"missing.json"),{
                "failed_check_codes":["CAP006_RECEIPT_UNAVAILABLE"]
            })
            self.assertEqual(hrb_gate_failure_codes(root),["CAP006_GATE_REPORT_UNAVAILABLE"])

if __name__=="__main__":
    unittest.main()
