import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fa3_openfx_interop import reference_execution, run_reference_conformance, validate_execution
from fa3_openfx_interop_gate import PATHS, gate


class OpenFXInteropGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def copy_gate_fixture(self, target: Path) -> None:
        for rel in PATHS.values():
            src = self.root / rel
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        for rel in (
            "src/fa3_openfx_interop.py",
            "src/fa3_openfx_interop_gate.py",
            "tests/test_openfx_interop_gate.py",
            ".github/workflows/openfx-reference-gate.yml",
            "src/fa3_enforce.py",
            ".github/workflows/fa3-permanent-enforcement.yml",
            "README.md",
        ):
            src = self.root / rel
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())

    def mutate_and_gate(self, key: str, mutation) -> dict:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_gate_fixture(target)
            path = target / PATHS[key]
            data = json.loads(path.read_text(encoding="utf-8"))
            mutation(data)
            path.write_text(json.dumps(data), encoding="utf-8")
            return gate(target)

    def test_reference_gate_passes(self):
        report = gate(self.root)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(30, report["rules_checked"])

    def test_typed_reference_suite_has_positive_and_negative_coverage(self):
        report = run_reference_conformance()
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(21, report["case_count"])
        self.assertEqual(21, report["cases_passed"])

    def test_valid_reference_execution_passes(self):
        self.assertEqual("PASS", validate_execution(reference_execution())["result"])

    def test_native_plugin_without_allowlist_fails_closed(self):
        candidate = reference_execution()
        candidate["plugin"]["allowlisted"] = False
        self.assertEqual("FAIL", validate_execution(candidate)["result"])

    def test_host_api_and_suite_mismatch_fail_closed(self):
        candidate = reference_execution()
        candidate["host"]["observed_openfx_api_version"] = "1.4"
        candidate["host"]["observed_suites"].remove("cuda_render")
        report = validate_execution(candidate)
        self.assertEqual("FAIL", report["result"])
        self.assertGreaterEqual(report["blocking_findings"], 2)

    def test_silent_backend_fallback_fails_closed(self):
        candidate = reference_execution()
        candidate["resource"]["observed_backend"] = "CPU"
        self.assertEqual("FAIL", validate_execution(candidate)["result"])

    def test_display_accelerator_fails_closed(self):
        candidate = reference_execution()
        candidate["resource"]["hrb_lease"]["role"] = "DISPLAY"
        self.assertEqual("FAIL", validate_execution(candidate)["result"])

    def test_missing_ocio_identity_fails_closed(self):
        candidate = reference_execution()
        candidate["color"]["ocio_config_sha256"] = ""
        self.assertEqual("FAIL", validate_execution(candidate)["result"])

    def test_provider_authority_claim_fails(self):
        report = self.mutate_and_gate("provider", lambda data: data.update(architectural_authority=True))
        self.assertEqual("FAIL", report["result"])

    def test_natron_openfx_15_overclaim_fails(self):
        report = self.mutate_and_gate("provider", lambda data: data["openfx_host_capability"].update(openfx_1_5_specific_suites_attested=True))
        self.assertEqual("FAIL", report["result"])

    def test_upstream_standard_pin_drift_fails(self):
        report = self.mutate_and_gate("reference", lambda data: data["sources"][0].update(immutable_commit="0" * 40))
        self.assertEqual("FAIL", report["result"])

    def test_current_host_promotion_overclaim_fails(self):
        report = self.mutate_and_gate("runtime", lambda data: data.update(production_admitted=True))
        self.assertEqual("FAIL", report["result"])

    def test_global_policy_unbinding_fails(self):
        report = self.mutate_and_gate("global_policy", lambda data: data["mandatory_reference_gates"].remove("FA3-OPENFX-INTEROPERABILITY-GATESET-001"))
        self.assertEqual("FAIL", report["result"])

    def test_evidence_registry_unbinding_fails(self):
        def mutation(data):
            cap = next(item for item in data["records"] if item["subject_id"] == "CAP-071")
            cap["source_decision_ids"].remove("FA3-DEC-OPENFX-INTEROPERABILITY-2026-09-11")
        report = self.mutate_and_gate("registry", mutation)
        self.assertEqual("FAIL", report["result"])

    def test_global_release_reconciliation_drift_fails(self):
        report = self.mutate_and_gate("global_release", lambda data: data["openfx_interoperability_reconciliation"].update(production_promotion_claimed=True))
        self.assertEqual("FAIL", report["result"])


if __name__ == "__main__":
    unittest.main()
