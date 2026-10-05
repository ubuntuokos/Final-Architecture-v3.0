import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fa3_pytorch3d_gate import PATHS, gate
from fa3_pytorch3d_provider import (
    ALLOWED_OPERATIONS,
    admit_job,
    reference_build_candidate,
    reference_job,
    reference_policy_conformance,
    validate_build_candidate,
)


class PyTorch3DGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def copy_gate_fixture(self, target: Path) -> None:
        fixture_paths = list(PATHS.values()) + ["canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"]
        for rel in fixture_paths:
            src = self.root / rel
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())

    def mutate_and_gate(self, key: str, mutation) -> dict:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_gate_fixture(target)
            path = target / PATHS[key]
            data = json.loads(path.read_text())
            mutation(data)
            path.write_text(json.dumps(data))
            return gate(target)

    def test_reference_gate_passes(self):
        report = gate(self.root)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(32, report["rules_checked"])
        self.assertEqual(21, report["provider_executable_conformance"]["case_count"])

    def test_policy_reference_suite_passes(self):
        self.assertEqual("PASS", reference_policy_conformance()["result"])

    def test_all_six_operations_are_admitted(self):
        for operation in ALLOWED_OPERATIONS:
            job = reference_job()
            job["operation"] = operation
            self.assertEqual("PASS", admit_job(job)["result"], operation)

    def test_build_cuda_mismatch_fails_closed(self):
        candidate = reference_build_candidate()
        candidate["build_toolkit_version"] = "13.2"
        self.assertEqual("FAIL", validate_build_candidate(candidate)["result"])

    def test_unverified_community_wheel_fails_closed(self):
        candidate = reference_build_candidate()
        candidate["distribution"] = "COMMUNITY_WHEEL"
        self.assertEqual("FAIL", validate_build_candidate(candidate)["result"])

    def test_missing_stable_accelerator_identity_fails_closed(self):
        job = reference_job()
        job["accelerator_lease"]["device_uuid"] = ""
        self.assertEqual("FAIL", admit_job(job)["result"])

    def test_silent_cpu_fallback_fails_closed(self):
        job = reference_job()
        job["fallback_policy"] = "CPU"
        self.assertEqual("FAIL", admit_job(job)["result"])

    def test_build_candidate_uses_current_host_admission_sources(self):
        candidate = reference_build_candidate()
        self.assertEqual(
            "CURRENT_HOST_ADMISSION_HRB_BOUND_COMPUTE_PROFILE",
            candidate["target_architectures_source"],
        )
        self.assertEqual(
            "CURRENT_HOST_ADMISSION_COMPUTE_PROFILE",
            candidate["build_parallelism_source"],
        )
        self.assertEqual("PASS", validate_build_candidate(candidate)["result"])

    def test_legacy_manual_hrb_build_source_fails_closed(self):
        candidate = reference_build_candidate()
        candidate["target_architectures_source"] = "HRB_DISCOVERY"
        candidate["build_parallelism_source"] = "HRB_LEASE"
        self.assertEqual("FAIL", validate_build_candidate(candidate)["result"])

    def test_build_and_e2e_scripts_require_canonical_admission_receipt(self):
        builder = (self.root / "bin/fa3-pytorch3d-source-build.sh").read_text(encoding="utf-8")
        collector = (self.root / "evidence/collect-pytorch3d-current-host.py").read_text(encoding="utf-8")
        self.assertIn("--admission-receipt", builder)
        self.assertIn("fa3_resource_admission_current_host_gate", builder)
        self.assertNotIn("--hrb-receipt", builder)
        self.assertIn("--admission-receipt", collector)
        self.assertIn("validate_resource_admission_receipt", collector)
        self.assertNotIn("--hrb-receipt", collector)

    def test_negative_authority_claim_fails(self):
        report = self.mutate_and_gate("provider", lambda data: data["authority_boundaries"].update(geometry_semantics=True))
        self.assertEqual("FAIL", report["result"])

    def test_negative_source_build_policy_drift_fails(self):
        report = self.mutate_and_gate("provider", lambda data: data["binary_channel_policy"].update(conda_channel_admissible=True))
        self.assertEqual("FAIL", report["result"])

    def test_negative_runtime_promotion_claim_fails(self):
        report = self.mutate_and_gate("runtime", lambda data: data.update(production_admitted=True))
        self.assertEqual("FAIL", report["result"])

    def test_negative_upstream_pin_drift_fails(self):
        report = self.mutate_and_gate("reference", lambda data: data.update(immutable_revision="0" * 40))
        self.assertEqual("FAIL", report["result"])

    def test_negative_global_reconciliation_drift_fails(self):
        report = self.mutate_and_gate("global_release", lambda data: data["pytorch3d_reconciliation"].update(runtime_activation_status="ADMITTED"))
        self.assertEqual("FAIL", report["result"])


if __name__ == "__main__":
    unittest.main()
