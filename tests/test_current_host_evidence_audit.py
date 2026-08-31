import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_current_host_evidence_audit import audit

class CurrentHostEvidenceAuditTests(unittest.TestCase):
    def _root(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        (root/"evidence/receipts/capabilities").mkdir(parents=True)
        (root/"evidence/runtime/CAP-001").mkdir(parents=True)
        shutil.copy(ROOT/"evidence/evidence-registry.json",root/"evidence/evidence-registry.json")
        (root/"evidence/reference").mkdir(parents=True,exist_ok=True)
        shutil.copy(ROOT/"evidence/reference/hrb-cuda-current-host-2026-08-28.json",root/"evidence/reference/hrb-cuda-current-host-2026-08-28.json")
        return td,root

    def _valid_receipt(self,root,record):
        now=datetime.now(timezone.utc)
        runtime=root/"evidence/runtime/CAP-001/runtime.log"; host=root/"evidence/runtime/CAP-001/host-fingerprint.json"
        runtime.write_text("verified current-host executable trace\n"); host.write_text('{"host":"test-current-host"}\n')
        rh=hashlib.sha256(runtime.read_bytes()).hexdigest(); hh=hashlib.sha256(host.read_bytes()).hexdigest()
        return {
          "schema":"fa3.capability-current-host-evidence.v1","subject_id":record["subject_id"],"status":"PASS",
          "execution_scope":"CURRENT_HOST","current_host":True,"synthetic":False,"ci_reference_only":False,
          "host_fingerprint_path":"evidence/runtime/CAP-001/host-fingerprint.json","host_fingerprint_sha256":hh,
          "collected_at":now.isoformat(),"expires_at":(now+timedelta(days=7)).isoformat(),
          "tests":{
            "positive":{"id":record["required_positive_test"],"status":"PASS","artifact_sha256":rh},
            "negative":{"id":record["required_negative_test"],"status":"PASS","artifact_sha256":rh},
            "rollback":{"id":record["rollback_requirement"],"status":"PASS","artifact_sha256":rh}},
          "evidence_artifacts":[
            {"path":"evidence/runtime/CAP-001/runtime.log","sha256":rh},
            {"path":"evidence/runtime/CAP-001/host-fingerprint.json","sha256":hh}]}

    def test_baseline_is_integrity_pass_but_runtime_incomplete(self):
        r=audit(ROOT); self.assertEqual(r["audit_integrity"],"PASS"); self.assertEqual(r["runtime_closure"],"FAIL")
        self.assertEqual(r["registry_pass_count"],0); self.assertEqual(r["registry_pending_count"],143)

    def test_fabricated_registry_pass_without_receipt_fails_integrity(self):
        td,root=self._root()
        try:
            p=root/"evidence/evidence-registry.json"; reg=json.loads(p.read_text()); reg["records"][0]["status"]="PASS"; p.write_text(json.dumps(reg))
            r=audit(root); self.assertEqual(r["audit_integrity"],"FAIL"); self.assertIn("CAP-001",r["blocking_findings"][0]["capability_ids"])
        finally: td.cleanup()

    def test_valid_receipt_can_be_reconciled(self):
        td,root=self._root()
        try:
            reg=json.loads((root/"evidence/evidence-registry.json").read_text()); rec=reg["records"][0]
            (root/"evidence/receipts/capabilities/CAP-001.json").write_text(json.dumps(self._valid_receipt(root,rec)))
            self.assertIn("CAP-001",audit(root)["reconciliation_candidates"])
            r=audit(root,apply_reconciliation=True); self.assertIn("CAP-001",r["reconciliation_applied"])
            self.assertEqual(json.loads((root/"evidence/evidence-registry.json").read_text())["records"][0]["status"],"PASS")
        finally: td.cleanup()

    def test_test_id_mismatch_is_rejected(self):
        td,root=self._root()
        try:
            reg=json.loads((root/"evidence/evidence-registry.json").read_text()); receipt=self._valid_receipt(root,reg["records"][0])
            receipt["tests"]["positive"]["id"]="AT-WRONG"; (root/"evidence/receipts/capabilities/CAP-001.json").write_text(json.dumps(receipt))
            row=audit(root)["capabilities"][0]; self.assertFalse(row["qualified_current_host_receipt"])
            self.assertTrue(any("mismatch" in x for x in row["receipt_findings"]))
        finally: td.cleanup()

    def test_declared_digest_must_match_real_file(self):
        td,root=self._root()
        try:
            reg=json.loads((root/"evidence/evidence-registry.json").read_text()); receipt=self._valid_receipt(root,reg["records"][0])
            receipt["evidence_artifacts"][0]["sha256"]="b"*64; (root/"evidence/receipts/capabilities/CAP-001.json").write_text(json.dumps(receipt))
            row=audit(root)["capabilities"][0]; self.assertFalse(row["qualified_current_host_receipt"])
            self.assertTrue(any("digest mismatch" in x for x in row["receipt_findings"]))
        finally: td.cleanup()

if __name__=="__main__": unittest.main()
