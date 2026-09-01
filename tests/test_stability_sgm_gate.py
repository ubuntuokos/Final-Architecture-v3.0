from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import fa3_stability_sgm_gate as s

ROOT = Path(__file__).resolve().parents[1]


class StabilitySgmGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence", root / "evidence")
        return td, root

    @staticmethod
    def _write(path: Path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        report = s.gate(ROOT)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual(16, report["regressions"]["passed"])
        self.assertEqual("PASS", report["authority_scan"]["result"])
        self.assertFalse(report["runtime_provider_required"])
        self.assertFalse(report["current_host_runtime_evidence"])

    def test_recipe_identity_is_reproducible_and_tamper_evident(self):
        recipe = {
            "model_artifact_id": "m:1", "model_revision": "r:1", "config_digest": "sha256:c",
            "component_identities": ["c:1"], "sampler": "s:1", "scheduler": "q:1",
            "precision": "fp16", "conditioning_digest": "sha256:d", "runtime_revision": "rt:1",
        }
        identity = s.recipe_identity(recipe)
        self.assertTrue(s.recipe_identity_valid(recipe, identity))
        recipe["precision"] = "fp32"
        self.assertFalse(s.recipe_identity_valid(recipe, identity))

    def test_code_license_does_not_admit_weights_or_outputs(self):
        record = {key: "KNOWN" for key in s.LICENSE_FIELDS}
        record.update({"code_license_admits_weights": False, "code_license_admits_outputs": False})
        self.assertTrue(s.license_separation_valid(record))
        record["code_license_admits_weights"] = True
        self.assertFalse(s.license_separation_valid(record))

    def test_tensor_hash_required_when_format_permits(self):
        self.assertTrue(s.artifact_integrity_valid(container_sha256="a" * 64, tensor_payload_sha256="b" * 64, format_permits_tensor_hash=True))
        self.assertFalse(s.artifact_integrity_valid(container_sha256="a" * 64, tensor_payload_sha256=None, format_permits_tensor_hash=True))

    def test_multiview_observations_are_not_canonical_geometry(self):
        self.assertTrue(s.geometry_boundary_valid(output_type="GENERATED_VISUAL_OBSERVATION_SET", canonical_geometry=False, geometry_authority=None))
        self.assertFalse(s.geometry_boundary_valid(output_type="GENERATED_VISUAL_OBSERVATION_SET", canonical_geometry=True, geometry_authority=None))
        self.assertTrue(s.geometry_boundary_valid(output_type="MESH", canonical_geometry=True, geometry_authority="FA3-3D-GEOM-001"))

    def test_accelerator_placement_requires_verified_hrb_lease(self):
        self.assertTrue(s.hrb_placement_valid(accelerator_requested=True, placement_authority="FA3-AUTH-HOST-RESOURCE-BROKER-001", lease_id="lease:1", lease_verified=True))
        self.assertFalse(s.hrb_placement_valid(accelerator_requested=True, placement_authority=s.PROVIDER_ID, lease_id="lease:1", lease_verified=True))
        self.assertFalse(s.hrb_placement_valid(accelerator_requested=True, placement_authority="FA3-AUTH-HOST-RESOURCE-BROKER-001", lease_id=None, lease_verified=False))

    def test_low_vram_adaptation_cannot_mutate_model_semantics(self):
        self.assertTrue(s.low_vram_policy_valid(adaptation_class="EXECUTION_POLICY", changes_model_semantics=False, recipe_bound=True))
        self.assertFalse(s.low_vram_policy_valid(adaptation_class="MODEL_MUTATION", changes_model_semantics=True, recipe_bound=True))

    def test_disabled_provider_has_no_background_cost(self):
        self.assertTrue(s.disabled_provider_valid(enabled=False, resident_processes=0, active_gpu_leases=0, polling_workers=0))
        self.assertFalse(s.disabled_provider_valid(enabled=False, resident_processes=1, active_gpu_leases=0, polling_workers=0))

    def test_provider_authority_tamper_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json"
            provider = json.loads(path.read_text(encoding="utf-8"))
            provider["architectural_authority"] = True
            self._write(path, provider)
            report = s.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertEqual("FAIL", report["authority_scan"]["result"])
        finally:
            td.cleanup()

    def test_geometry_boundary_tamper_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-STABILITY-SGM-001.json"
            provider = json.loads(path.read_text(encoding="utf-8"))
            provider["output_semantics"]["canonical_geometry"] = True
            self._write(path, provider)
            report = s.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "SGM-REF-003" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_floating_upstream_reference_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/references/FA3-STABILITY-SGM-UPSTREAM-REFERENCE-2026-09-01.json"
            reference = json.loads(path.read_text(encoding="utf-8"))
            reference["resolved_commit"] = "main"
            self._write(path, reference)
            report = s.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "SGM-REF-006" for x in report["findings"]))
        finally:
            td.cleanup()

    def test_reference_evidence_cannot_claim_runtime_promotion(self):
        td, root = self._copy_root()
        try:
            path = root / "evidence/reference/stability-sgm-ci-2026-09-01.json"
            evidence = json.loads(path.read_text(encoding="utf-8"))
            evidence["current_host_runtime_evidence"] = True
            self._write(path, evidence)
            report = s.gate(root)
            self.assertEqual("FAIL", report["result"])
            self.assertTrue(any(x["code"] == "SGM-REF-008" for x in report["findings"]))
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
