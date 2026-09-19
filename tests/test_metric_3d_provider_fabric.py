from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Metric3DProviderFabricTests(unittest.TestCase):
    def test_cap032_core_recipe_is_provider_neutral(self) -> None:
        recipes = load("canonical/current-host-capability-proof-recipes.json")
        cap032 = next(row for row in recipes["recipes"] if row["capability_id"] == "CAP-032")
        self.assertEqual("metric_3d_reconstruction", cap032["primitive"])
        self.assertNotIn("pytorch3d_runtime", recipes["primitive_counts"])
        self.assertEqual(1, recipes["primitive_counts"]["metric_3d_reconstruction"])
        self.assertEqual(
            "PROVIDER_NEUTRAL_CORE_PROOF_SPECIALIZED_PROVIDERS_CONDITIONAL",
            cap032["provider_selection"],
        )

    def test_differentiable_profile_exposes_replaceable_provider_set(self) -> None:
        profile = load("canonical/profiles/FA3-DIFFERENTIABLE-3D-001.json")
        self.assertFalse(profile["provider_selection_policy"]["core_cap032_runtime_hard_dependency"])
        self.assertEqual(
            {
                "FA3-PROVIDER-KAOLIN-001",
                "FA3-PROVIDER-PYTORCH3D-001",
                "FA3-PROVIDER-NVDIFFRAST-001",
            },
            set(profile["providers"]),
        )
        self.assertEqual(
            "FA3-PROVIDER-OPEN3D-001",
            profile["provider_selection_policy"]["open3d_general_metric_reconstruction_provider"],
        )

    def test_open3d_is_preferred_general_provider_not_authority(self) -> None:
        provider = load("canonical/providers/FA3-PROVIDER-OPEN3D-001.json")
        self.assertEqual(["CAP-032"], provider["capability_bindings"])
        self.assertFalse(provider["activation"]["global_current_host_hard_dependency"])
        self.assertEqual("MIT", provider["upstream"]["license"])
        self.assertFalse(provider["architectural_authority"])
        self.assertFalse(provider["production_policy"]["global_promotion_claim"])

    def test_kaolin_default_surface_is_production_eligible_but_noncommercial_namespace_is_not(self) -> None:
        provider = load("canonical/providers/FA3-PROVIDER-KAOLIN-001.json")
        self.assertEqual("Apache-2.0", provider["upstream"]["default_license"])
        self.assertIn("kaolin.non_commercial", provider["license_boundary"]["denied_production_prefixes"])
        self.assertFalse(provider["activation"]["global_current_host_hard_dependency"])
        self.assertFalse(provider["production_policy"]["global_promotion_claim"])

    def test_pytorch3d_is_compatibility_provider_not_core_dependency(self) -> None:
        provider = load("canonical/providers/FA3-PROVIDER-PYTORCH3D-001.json")
        self.assertFalse(provider["activation"]["global_current_host_hard_dependency"])
        self.assertFalse(provider["activation"]["cap032_core_proof_dependency"])
        self.assertFalse(provider["promotion"]["runtime_promotion_required_for_cap032_core_closure"])
        self.assertIn(
            "COMPATIBILITY_PROVIDER_NOT_CAP032_RUNTIME_HARD_DEPENDENCY",
            provider["classification"],
        )

    def test_nvdiffrast_is_research_only_under_current_license(self) -> None:
        provider = load("canonical/providers/FA3-PROVIDER-NVDIFFRAST-001.json")
        self.assertFalse(provider["activation"]["production_admitted"])
        self.assertFalse(provider["activation"]["commercial_workflow_admitted"])
        self.assertTrue(provider["activation"]["separate_license_required_for_commercial_use"])
        self.assertEqual("NOT_PRODUCTION_BASELINE", provider["production_policy"]["role"])

    def test_provider_fabric_decision_and_evidence_registry_are_bound(self) -> None:
        decision = load("canonical/decisions/FA3-DEC-METRIC-3D-PROVIDER-FABRIC-2026-09-19.json")
        self.assertEqual(143, decision["baseline_effect"]["capability_count_after"])
        self.assertEqual(0, decision["baseline_effect"]["new_architectural_authorities"])
        registry = load("evidence/evidence-registry.json")
        cap032 = next(row for row in registry["records"] if row["subject_id"] == "CAP-032")
        self.assertIn(decision["id"], cap032["source_decision_ids"])
        fabric = cap032["metric_3d_provider_fabric_status"]
        self.assertFalse(fabric["global_single_provider_hard_dependency"])
        self.assertFalse(fabric["nvdiffrast_production_admitted"])

    def test_global_preflight_has_no_pytorch3d_runtime_requirement(self) -> None:
        source = (ROOT / "src/fa3_full_current_host_preflight.py").read_text(encoding="utf-8")
        self.assertNotIn('if "pytorch3d_runtime" in primitives', source)
        self.assertNotIn("no approved local Python runtime with torch + pytorch3d available", source)
        self.assertIn("metric_3d_reconstruction", source)


if __name__ == "__main__":
    unittest.main()
