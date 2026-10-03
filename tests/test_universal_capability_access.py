from __future__ import annotations

import json
import unittest
from pathlib import Path

from fa3_universal_capability_access import classify_donor, gate, validate_material_usage

ROOT = Path(__file__).resolve().parents[1]


class UniversalCapabilityAccessTests(unittest.TestCase):
    def test_static_gate_passes_current_reference_usage(self):
        result = gate(ROOT)
        self.assertEqual("PASS", result["result"])
        self.assertEqual(1384, result["registry_entry_count"])
        self.assertEqual(0, result["active_material_usage_edge_count"])

    def test_hy_motion_is_geographically_restricted(self):
        registry = json.loads((ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(encoding="utf-8"))
        row = next(x for x in registry["entries"] if x["donor_id"] == "FA3-DONOR-TENCENT-HUNYUAN-HY-MOTION-1-0-001")
        result = classify_donor(row)
        self.assertEqual("KNOWN_ACCESS_BARRIER_SIGNAL", result["classification"])
        self.assertIn("GEOGRAPHIC_OR_FIELD_RESTRICTION", result["reasons"])

    def test_restricted_material_usage_requires_global_substitute(self):
        donor = {
            "source": {"kind": "GITHUB"},
            "license": {"declared": "Example Community License", "status": "REFERENCE_ONLY_GEO_RESTRICTED"},
            "code_reuse_policy": "REFERENCE_ONLY_GEO_RESTRICTED_GLOBAL_SUBSTITUTE_REQUIRED",
            "donor_modes": ["REFERENCE_IMPLEMENTATION"],
            "tags": ["geo-restricted"],
            "notes": ["Territory excludes a region."],
        }
        donor_class = classify_donor(donor)
        usage = {"usage_kind": "RUNTIME_DEPENDENCY"}
        self.assertTrue(validate_material_usage(usage, donor_class))
        usage["universal_access"] = {
            "classification": "OPTIONAL_RESTRICTED_WITH_GLOBAL_SUBSTITUTE",
            "global_substitute_refs": ["FA3-NATIVE-EXAMPLE-001"],
            "restriction_circumvention": False,
        }
        self.assertEqual([], validate_material_usage(usage, donor_class))

    def test_unknown_rights_block_material_adoption(self):
        donor = {
            "source": {"kind": "GITHUB"},
            "license": {"declared": "UNKNOWN", "status": "UNKNOWN"},
            "code_reuse_policy": "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW",
            "donor_modes": ["REFERENCE_IMPLEMENTATION"],
            "tags": [],
            "notes": [],
        }
        donor_class = classify_donor(donor)
        usage = {
            "usage_kind": "CODE_REUSE",
            "universal_access": {
                "classification": "GLOBAL_BASELINE",
                "global_substitute_refs": [],
                "restriction_circumvention": False,
            },
        }
        findings = validate_material_usage(usage, donor_class)
        self.assertTrue(any("UNKNOWN_ACCESS_RIGHTS" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
