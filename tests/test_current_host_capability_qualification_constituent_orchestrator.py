import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_current_host_capability_qualification_constituent_orchestrator import (
    _structured_rejection_findings,
    orchestrate,
)

QID = "FA3-QUAL-CAP-001-POS-001"
CID = "CAP001-POS-ALL"
PID = "FA3-QUAL-PRODUCER-CAP001-POS-ALL"


class QualificationConstituentOrchestratorTests(unittest.TestCase):
    @staticmethod
    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _root(self, *, mode="pass"):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "evidence").mkdir(parents=True)
        (root / "canonical").mkdir(parents=True)
        (root / "src").mkdir(parents=True)
        shutil.copy(ROOT / "evidence/evidence-registry.json", root / "evidence/evidence-registry.json")
        shutil.copy(
            ROOT / "canonical/current-host-capability-test-qualifications.json",
            root / "canonical/current-host-capability-test-qualifications.json",
        )
        shutil.copy(
            ROOT / "canonical/current-host-capability-qualification-constituent-producers.json",
            root / "canonical/current-host-capability-qualification-constituent-producers.json",
        )
        for rel in (
            "canonical/current-host-capability-test-qualifications.json",
            "canonical/current-host-capability-qualification-constituent-producers.json",
        ):
            path = root / rel
            registry = json.loads(path.read_text())
            registry["entries"] = []
            path.write_text(json.dumps(registry))
        rec = next(
            row for row in json.loads((root / "evidence/evidence-registry.json").read_text())["records"]
            if row["subject_id"] == "CAP-001"
        )
        qpath = root / "canonical/current-host-capability-test-qualifications.json"
        qreg = json.loads(qpath.read_text())
        qreg["entries"].append({
            "qualification_id": QID,
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "coverage_semantics": "COMPLETE_CAPABILITY_OBLIGATION",
            "evidence_authority_id": "FA3-AUTH-OBS-EVIDENCE-001",
            "runtime_constituent_schema": "fa3.capability-current-host-qualification-constituent.v2",
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "max_constituent_ttl_seconds": 3600,
            "completeness_basis": {
                "type": "EXACT_EVIDENCE_REGISTRY_SOURCE_DECISION_COVERAGE",
                "source_decision_ids": rec["source_decision_ids"],
            },
            "required_constituents": [{
                "constituent_id": CID,
                "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION",
                "covers_source_decision_ids": rec["source_decision_ids"],
            }],
        })
        qpath.write_text(json.dumps(qreg))

        adapter = root / "src/cap001_positive_producer.py"
        if mode == "exit-fail":
            adapter.write_text("raise SystemExit(7)\n")
        elif mode == "structured-reject":
            adapter.write_text(
                "import json,sys\n"
                f"print(json.dumps({{'schema':'fa3.qualification-producer-rejection.v1','status':'REJECTED','producer_id':'{PID}','qualification_id':'{QID}','constituent_id':'{CID}','subject_id':'CAP-001','stage':'COLLECTOR','reason_codes':['CAP006_CGROUP_V2_UNPROVEN'],'summary':{{'cgroup_v2_pass':False}}}}), file=sys.stderr)\n"
                "raise SystemExit(2)\n"
            )
        else:
            outside = mode == "outside"
            wrong = mode == "wrong-status"
            adapter.write_text(f'''import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["FA3_REPOSITORY_ROOT"])
scope = Path(os.environ["FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR"])
if {outside!r}:
    artifact = root / ".fa3-current-host/outside-source.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
else:
    artifact = scope / "evidence.json"
artifact.write_text(json.dumps({{"status":"PASS"}}) + "\\n")
verdict = {{
    "schema": "fa3.capability-current-host-qualification-constituent-verdict.v1",
    "producer_id": "{PID}",
    "qualification_id": os.environ["FA3_QUALIFICATION_ID"],
    "constituent_id": os.environ["FA3_CONSTITUENT_ID"],
    "subject_id": os.environ["FA3_CAPABILITY_ID"],
    "test_kind": os.environ["FA3_TEST_KIND"],
    "test_id": os.environ["FA3_TEST_ID"],
    "status": {"'FAIL'" if wrong else "'PASS'"},
    "execution_scope": "CURRENT_HOST",
    "current_host": True,
    "synthetic": False,
    "ci_reference_only": False,
    "provider_receipt_only": False,
    "component_receipt_only": False,
    "generic_host_collection_only": False,
    "global_promotion_claim": False,
    "source_evidence_class": os.environ["FA3_SOURCE_EVIDENCE_CLASS"],
    "covers_source_decision_ids": json.loads(os.environ["FA3_COVERS_SOURCE_DECISION_IDS_JSON"]),
    "source_artifact_path": artifact.relative_to(root).as_posix(),
    "source_artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
}}
print(json.dumps(verdict))
''')

        ppath = root / "canonical/current-host-capability-qualification-constituent-producers.json"
        preg = json.loads(ppath.read_text())
        preg["entries"].append({
            "producer_id": PID,
            "qualification_id": QID,
            "constituent_id": CID,
            "subject_id": "CAP-001",
            "test_kind": "positive",
            "test_id": rec["required_positive_test"],
            "source_evidence_class": "CROSS_CUTTING_CURRENT_HOST_EXECUTION",
            "covers_source_decision_ids": rec["source_decision_ids"],
            "adapter_path": "src/cap001_positive_producer.py",
            "adapter_sha256": self._sha(adapter),
            "execution_mode": "REAL_CURRENT_HOST_EXECUTION",
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "argv": [],
            "timeout_seconds": 30,
            "ttl_seconds": 1800,
        })
        ppath.write_text(json.dumps(preg))
        return td, root

    def _host(self, root):
        host = root / ".fa3-current-host/global-closure/host/host-fingerprint.json"
        host.parent.mkdir(parents=True, exist_ok=True)
        host.write_text('{"host":"fixture"}\n')
        return host

    def test_dry_run_does_not_materialize_current_host_constituent(self):
        td, root = self._root()
        try:
            report = orchestrate(root, execute=False)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["status"], "REGISTERED_CONSTITUENT_PRODUCERS_NOT_EXECUTED")
            self.assertEqual(report["registered_producer_count"], 1)
            self.assertEqual(report["constituents_materialized"], 0)
            self.assertFalse((root / ".fa3-current-host/qualification-constituents").exists())
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_real_execution_materializes_v2_host_hash_bound_manifest(self):
        td, root = self._root()
        try:
            host = self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "PASS")
            self.assertEqual(report["constituents_materialized"], 1)
            path = root / f".fa3-current-host/qualification-constituents/{QID}/{CID}.json"
            manifest = json.loads(path.read_text())
            self.assertEqual(manifest["schema"], "fa3.capability-current-host-qualification-constituent.v2")
            self.assertEqual(manifest["host_fingerprint_sha256"], self._sha(host))
            self.assertEqual(manifest["producer"]["producer_id"], PID)
            self.assertEqual(
                manifest["producer"]["orchestrator_id"],
                "FA3-CURRENT-HOST-QUALIFICATION-CONSTITUENT-ORCHESTRATOR-001",
            )
            artifact = root / manifest["source_artifact_path"]
            self.assertTrue(artifact.is_file())
            self.assertEqual(self._sha(artifact), manifest["source_artifact_sha256"])
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_source_artifact_outside_exact_scope_is_rejected(self):
        td, root = self._root(mode="outside")
        try:
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["constituents_materialized"], 0)
            self.assertFalse((root / ".fa3-current-host/qualification-constituents").exists())
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_typed_pass_verdict_is_required(self):
        td, root = self._root(mode="wrong-status")
        try:
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["constituents_materialized"], 0)
            self.assertTrue(any(
                "status mismatch" in detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ))
        finally:
            td.cleanup()

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_structured_registered_producer_rejection_is_preserved(self):
        td, root = self._root(mode="structured-reject")
        try:
            self._host(root)
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            details = [
                detail
                for finding in report["blocking_findings"]
                for detail in finding.get("findings", [])
            ]
            self.assertIn("producer adapter returncode 2", details)
            self.assertIn("producer rejection: producer stage: COLLECTOR", details)
            self.assertIn("producer rejection: producer reason code: CAP006_CGROUP_V2_UNPROVEN", details)
            self.assertFalse((root / ".fa3-current-host/qualification-constituents").exists())
        finally:
            td.cleanup()

    def test_rejection_channel_rejects_free_text_and_wrong_binding(self):
        entry={"producer_id":PID,"qualification_id":QID,"constituent_id":CID,"subject_id":"CAP-001"}
        free_text=json.dumps({"status":"REJECTED","findings":["secret=hunter2"]})
        self.assertEqual(_structured_rejection_findings(free_text,entry),[])
        wrong=json.dumps({
            "schema":"fa3.qualification-producer-rejection.v1","status":"REJECTED",
            "producer_id":"OTHER","qualification_id":QID,"constituent_id":CID,
            "subject_id":"CAP-001","stage":"COLLECTOR",
            "reason_codes":["CAP006_CGROUP_V2_UNPROVEN"],"summary":{},
        })
        self.assertEqual(_structured_rejection_findings(wrong,entry),[])

    def test_rejection_channel_rejects_unknown_code_and_summary_field(self):
        entry={"producer_id":PID,"qualification_id":QID,"constituent_id":CID,"subject_id":"CAP-001"}
        base={
            "schema":"fa3.qualification-producer-rejection.v1","status":"REJECTED",
            **entry,"stage":"COLLECTOR","reason_codes":["CAP006_CGROUP_V2_UNPROVEN"],"summary":{},
        }
        self.assertEqual(_structured_rejection_findings(json.dumps({**base,"reason_codes":["UNKNOWN"]}),entry),[])
        self.assertEqual(_structured_rejection_findings(json.dumps({**base,"summary":{"secret":"hunter2"}}),entry),[])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "real current-host execution must be non-root")
    def test_missing_host_fingerprint_blocks_execution(self):
        td, root = self._root()
        try:
            report = orchestrate(root, execute=True)
            self.assertEqual(report["orchestrator_integrity"], "FAIL")
            self.assertEqual(report["constituents_materialized"], 0)
            self.assertTrue(any(item["code"] == "QCPO-004" for item in report["blocking_findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
