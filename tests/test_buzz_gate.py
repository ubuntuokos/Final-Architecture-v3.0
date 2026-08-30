import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_buzz_gate import (
    CAPABILITY_COUNT,
    GATE_ID,
    PROVIDER_ID,
    gate,
    run_regressions,
    scan_canonical_authority_assignments,
)


class BuzzGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        return td, root

    def _write_json(self, path: Path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["gate_id"], GATE_ID)
        self.assertEqual(report["provider_id"], PROVIDER_ID)
        self.assertEqual(report["capability_count"], CAPABILITY_COUNT)
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["authority_scan"]["result"], "PASS")
        self.assertEqual(report["regressions"]["result"], "PASS")
        self.assertFalse(report["runtime_provider_required"])

    def test_executable_regressions_cover_eight_authorities_plus_root_and_count(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 10)
        self.assertEqual(report["total"], 10)
        names = {case["name"] for case in report["cases"]}
        for domain in (
            "identity",
            "authorization",
            "mcp",
            "workflow",
            "evidence",
            "secrets",
            "host_resource",
            "developer_execution",
        ):
            self.assertIn(f"{domain} authority escalation denial", names)
        self.assertIn("canonical-root promotion denial", names)
        self.assertIn("capability/authority count drift denial", names)

    def test_each_prohibited_authority_assignment_is_rejected_by_canonical_scan(self):
        fields = {
            "identity": "identity_authority",
            "authorization": "authorization_authority",
            "mcp": "mcp_authority",
            "workflow": "workflow_authority",
            "evidence": "evidence_authority",
            "secrets": "secrets_authority",
            "host_resource": "host_resource_authority",
            "developer_execution": "developer_execution_authority",
        }
        for domain, field in fields.items():
            with self.subTest(domain=domain):
                td, root = self._copy_root()
                try:
                    self._write_json(
                        root / "canonical" / f"buzz-escalation-{domain}.json",
                        {
                            "schema": "fa3.test-mutation.v1",
                            "id": f"FA3-BUZZ-MUTATION-{domain.upper()}",
                            "provider_id": PROVIDER_ID,
                            field: PROVIDER_ID,
                        },
                    )
                    report = scan_canonical_authority_assignments(root)
                    self.assertEqual(report["result"], "FAIL")
                    self.assertTrue(
                        any(finding.get("domain") in (domain, "generic") for finding in report["findings"]),
                        report,
                    )
                finally:
                    td.cleanup()

    def test_authority_boundary_owner_escalation_is_rejected(self):
        td, root = self._copy_root()
        try:
            provider_path = root / "canonical/providers/FA3-PROVIDER-BUZZ-001.json"
            provider = json.loads(provider_path.read_text(encoding="utf-8"))
            provider["authority_boundaries"]["identity"] = PROVIDER_ID
            self._write_json(provider_path, provider)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(
                any(x["code"] == "BUZZ-AUTH-006" for x in report["authority_scan"]["findings"])
            )
        finally:
            td.cleanup()

    def test_canonical_root_promotion_is_rejected(self):
        td, root = self._copy_root()
        try:
            provider_path = root / "canonical/providers/FA3-PROVIDER-BUZZ-001.json"
            provider = json.loads(provider_path.read_text(encoding="utf-8"))
            provider["canonical_root"] = True
            self._write_json(provider_path, provider)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REF-005" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_architectural_authority_promotion_is_rejected(self):
        td, root = self._copy_root()
        try:
            provider_path = root / "canonical/providers/FA3-PROVIDER-BUZZ-001.json"
            provider = json.loads(provider_path.read_text(encoding="utf-8"))
            provider["architectural_authority"] = True
            self._write_json(provider_path, provider)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-AUTH-003" for x in report["authority_scan"]["findings"]))
        finally:
            td.cleanup()

    def test_capability_count_drift_is_rejected(self):
        td, root = self._copy_root()
        try:
            provider_path = root / "canonical/providers/FA3-PROVIDER-BUZZ-001.json"
            provider = json.loads(provider_path.read_text(encoding="utf-8"))
            provider["capability_count"] = CAPABILITY_COUNT + 1
            provider["new_capability"] = True
            self._write_json(provider_path, provider)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REF-005" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_missing_decision_record_fails_closed(self):
        td, root = self._copy_root()
        try:
            (root / "canonical/decisions/FA3-DEC-BUZZ-2026-08-30.json").unlink()
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REF-002" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_enforcement_constraint_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/buzz-enforcement.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["rules"][0]["requirement"] = "Buzz may become MCP authority."
            self._write_json(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REF-009" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_global_policy_binding_is_required(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/enforcement-policy.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["mandatory_reference_gates"] = [
                item for item in obj["mandatory_reference_gates"] if item != GATE_ID
            ]
            self._write_json(path, obj)
            report = gate(root)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "BUZZ-REF-010" for x in report["reference"]["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
