#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fa3_donor_registry import resolve_donor_reference

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
OLD = "FA3-DONOR-ASCEND-TRITON-ASCEND-LEGACY-001"
NEW = "FA3-DONOR-TRITON-LANG-TRITON-ASCEND-001"


class DonorSupersededResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_triton_legacy_id_redirects_to_current_accepted_reference(self):
        result = resolve_donor_reference(self.registry, OLD)
        self.assertTrue(result["redirected"])
        self.assertEqual(result["resolved_donor_id"], NEW)
        self.assertEqual(result["replacement_chain"], [OLD, NEW])
        self.assertEqual(result["record"]["status"], "ACCEPTED_REFERENCE")

    def test_triton_legacy_url_redirects_to_current_accepted_reference(self):
        result = resolve_donor_reference(
            self.registry, "https://github.com/Ascend/triton-ascend"
        )
        self.assertTrue(result["redirected"])
        self.assertEqual(result["resolved_donor_id"], NEW)

    def test_current_reference_does_not_redirect(self):
        result = resolve_donor_reference(self.registry, NEW)
        self.assertFalse(result["redirected"])
        self.assertEqual(result["replacement_chain"], [NEW])

    def test_missing_replacement_fails_closed(self):
        registry = copy.deepcopy(self.registry)
        old = next(row for row in registry["entries"] if row["donor_id"] == OLD)
        old["donor_replacement_reference_id"] = "FA3-DONOR-NOT-THERE-001"
        with self.assertRaisesRegex(ValueError, "SUPERSEDED_DONOR_REPLACEMENT_NOT_FOUND"):
            resolve_donor_reference(registry, OLD)

    def test_replacement_cycle_fails_closed(self):
        registry = copy.deepcopy(self.registry)
        target = next(row for row in registry["entries"] if row["donor_id"] == NEW)
        target["status"] = "SUPERSEDED"
        target["donor_replacement_reference_id"] = OLD
        with self.assertRaisesRegex(ValueError, "DONOR_REPLACEMENT_CYCLE"):
            resolve_donor_reference(registry, OLD)

    def test_redirect_must_end_at_accepted_reference(self):
        registry = copy.deepcopy(self.registry)
        target = next(row for row in registry["entries"] if row["donor_id"] == NEW)
        target["status"] = "CANDIDATE"
        with self.assertRaisesRegex(ValueError, "DONOR_REPLACEMENT_NOT_ACCEPTED"):
            resolve_donor_reference(registry, OLD)


if __name__ == "__main__":
    unittest.main()
