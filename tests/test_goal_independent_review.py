import copy
import json
import tempfile
import unittest
from pathlib import Path

from fa3_goal_execution import digest
from fa3_goal_independent_review import (
    EVIDENCE_AUTHORITY, IndependentReviewDenied, review_goal_evidence,
    write_readonly_projection,
)
from test_goal_execution_foundation import fixture, evidence

def verifier(query):
    return {
        "authority": EVIDENCE_AUTHORITY,
        "goal_digest": query["goal_digest"],
        "criterion_id": query["criterion_id"],
        "artifact_digest": query["artifact_digest"],
        "evidence_ref": query["evidence_ref"],
        "verifier_ref": query["verifier_ref"],
        "independent_checker_ref": "canonical-checker:separate-session",
        "status": "REFERENCE_AUTHENTICATED",
    }

class IndependentGoalReviewTests(unittest.TestCase):
    def test_proof_reference_never_completes_goal(self):
        out = review_goal_evidence(fixture(), evidence(), verify_canonical_evidence=verifier)
        self.assertEqual(out["status"], "ALL_REFERENCES_CHECKED_CANONICAL_CLOSURE_REQUIRED")
        self.assertEqual(out["criteria"][0]["status"],
                         "REFERENCE_AUTHENTICATED_PENDING_CANONICAL_CLOSURE")
        self.assertFalse(out["verification_claim"])
        self.assertFalse(out["authority"])
        self.assertTrue(out["canonical_gate_required"])

    def test_self_authored_or_wrong_authority_is_blocked(self):
        def maker(query):
            r = verifier(query)
            r["independent_checker_ref"] = "agent-existing-01"
            return r
        x = review_goal_evidence(fixture(), evidence(), verify_canonical_evidence=maker)
        self.assertEqual(x["status"], "MISSING_OR_BLOCKED")
        self.assertEqual(x["criteria"][0]["reason"], "INDEPENDENT_CHECKER_REQUIRED")
        def forge(query):
            r=verifier(query); r["authority"]="agent-self"; return r
        x = review_goal_evidence(fixture(), evidence(), verify_canonical_evidence=forge)
        self.assertEqual(x["criteria"][0]["reason"], "CANONICAL_EVIDENCE_AUTHENTICATION_MISMATCH")

    def test_missing_evidence_does_not_invoke_checker(self):
        def never_called(_):
            raise AssertionError("unproven observation must not call verifier")
        x=review_goal_evidence(fixture(),[],verify_canonical_evidence=never_called)
        self.assertEqual(x["status"],"MISSING_OR_BLOCKED")
        self.assertEqual(x["criteria"][0]["status"],"MISSING")

    def test_semantic_advisory_needs_distinct_named_checker(self):
        g=fixture()
        c=g["acceptance_criteria"][0]["verification"]
        c["kind"]="SEMANTIC_ADVISORY_WITH_INDEPENDENT_CHECK"
        c["independent_verifier_ref"]="canonical-checker:designated"
        obs=evidence()
        obs[0]["independent_verifier_ref"]=c["independent_verifier_ref"]
        obs[0]["independent_check_status"]="PASS"
        x=review_goal_evidence(g,obs,verify_canonical_evidence=verifier)
        self.assertEqual(x["criteria"][0]["reason"],"INDEPENDENT_VERIFIER_MISMATCH")

    def test_human_signoff_is_checked_by_independent_verifier(self):
        g=fixture();g["acceptance_criteria"][0]["verification"]["kind"]="HUMAN"
        obs=evidence();obs[0]["human_approval_ref"]="approval:unsigned"
        x=review_goal_evidence(g,obs,verify_canonical_evidence=verifier)
        self.assertEqual(x["criteria"][0]["reason"],"HUMAN_APPROVAL_NOT_AUTHENTICATED")

    def test_owner_only_atomic_ui_projection_without_authority(self):
        result=review_goal_evidence(fixture(),evidence(),verify_canonical_evidence=verifier)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"fa3"/"goal-review-projection.json"
            write_readonly_projection(result,target)
            written=json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(written["goal_digest"],digest(fixture()))
            self.assertEqual(target.stat().st_mode & 0o077,0)
            bad={**result,"verification_claim":True}
            with self.assertRaises(IndependentReviewDenied):
                write_readonly_projection(bad,target)

if __name__=="__main__":
    unittest.main()
