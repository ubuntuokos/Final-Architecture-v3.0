import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_demucs_gate import (
    class_allowlist_valid,
    gate,
    model_loading_trust_valid,
    placement_authority_valid,
    run_regressions,
    stem_request_valid,
)

class DemucsGateTests(unittest.TestCase):
    def test_regression_suite_passes_all_twenty_invariants(self):
        report = run_regressions()
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["passed"], 20)
        self.assertEqual(report["total"], 20)

    def test_unsupported_stem_is_rejected(self):
        self.assertFalse(stem_request_valid({"vocals","drums","bass","other"}, {"piano"}))

    def test_accelerator_without_hrb_lease_is_rejected(self):
        self.assertFalse(placement_authority_valid(True, None, False))

    def test_safe_container_alone_does_not_authorize_execution(self):
        self.assertFalse(model_loading_trust_valid(container_safe=True, provenance_pass=False, admitted=False, legacy_pickle=False, explicit_legacy_trust=False))

    def test_arbitrary_metadata_class_is_rejected(self):
        self.assertFalse(class_allowlist_valid("evil.module.Class", {"HTDemucs":"fa3.impl.htdemucs"}))

    def test_reference_gate_passes_with_canonical_artifacts(self):
        report = gate(ROOT)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["reference"]["result"], "PASS")
        self.assertEqual(report["regressions"]["passed"], 20)
        self.assertFalse(report["runtime_provider_required"])

    def test_optional_provider_cannot_be_promoted_to_authority(self):
        provider_path = ROOT / "canonical/providers/FA3-PROVIDER-DEMUCS-001.json"
        original = provider_path.read_text()
        try:
            provider = json.loads(original)
            provider["architectural_authority"] = True
            provider_path.write_text(json.dumps(provider))
            report = gate(ROOT)
            self.assertEqual(report["result"], "FAIL")
            self.assertTrue(any(x["code"] == "DEMUCS-REF-013" for x in report["reference"]["findings"]))
        finally:
            provider_path.write_text(original)

if __name__ == "__main__":
    unittest.main()
