from __future__ import annotations
import unittest
from fa3_change_projector import classify_scope, project_canonical_document, project_git_change

class ChangeProjectorTests(unittest.TestCase):
    def test_projectors_emit_fact_records(self):
        can=project_canonical_document({"schema":"x","id":"P1","status":"CANONICAL"},"canonical/p1.json")
        git=project_git_change({"commit":"a"*40,"path":"src/x.py","status":"M","timestamp":"2026-10-02T00:00:00Z"})
        self.assertEqual(can["truth_class"],"FACT")
        self.assertEqual(git["object_id"],"src/x.py")

    def test_scope_classification(self):
        out=classify_scope(["src/a.py","docs/a.md","other/x"],["src/**"],["docs/**"])
        self.assertEqual(out["src/a.py"],"EXPECTED")
        self.assertEqual(out["docs/a.md"],"JUSTIFICATION_REQUIRED")
        self.assertEqual(out["other/x"],"OUT_OF_SCOPE")

if __name__=="__main__": unittest.main()
