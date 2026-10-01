from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fa3_license_rights_audit import build_inventory

ROOT = Path(__file__).resolve().parents[1]


class RetroactiveLicenseRightsAuditTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        (root / "canonical").mkdir()
        (root / "src").mkdir()
        (root / "assets").mkdir()
        (root / "canonical" / "distribution-manifest.json").write_text(json.dumps({
            "included": [{"subject_id": "FA3-PROVIDER-NATIVE-001", "release_bundle_status": "INCLUDED"}],
            "excluded": [{"subject_id": "FA3-UPSTREAM-REFERENCE-001", "release_bundle_status": "EXCLUDED"}],
        }), encoding="utf-8")
        (root / "REUSE.toml").write_text(
            'version = 1\n[[annotations]]\npath = ["src/native.py"]\n'
            'precedence = "override"\nSPDX-FileCopyrightText = "FA3"\n'
            'SPDX-License-Identifier = "Apache-2.0"\n',
            encoding="utf-8",
        )
        (root / "src" / "native.py").write_text("print('ok')\n", encoding="utf-8")
        (root / "src" / "untagged.py").write_text("print('review')\n", encoding="utf-8")
        (root / "assets" / "font.ttf").write_bytes(b"font")

    def test_inventory_is_fail_closed_not_legal_clearance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            inv = build_inventory(root)
            self.assertEqual("PASS", inv["result"])
            self.assertEqual("BLOCKED", inv["audit_closure_status"])
            self.assertFalse(inv["invariants"]["release_eligible"])
            self.assertTrue(inv["invariants"]["automatic_inventory_is_not_legal_clearance"])
            self.assertGreater(inv["summary"]["work_queue_items"], 0)
            self.assertEqual(1, inv["summary"]["unique_release_blockers"])

    def test_release_included_subject_is_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            inv = build_inventory(root)
            blocking = [x for x in inv["work_queue"] if x.get("severity") == "BLOCKING"]
            self.assertTrue(any(x.get("subject_id") == "FA3-PROVIDER-NATIVE-001" for x in blocking))

    def test_valid_release_descriptor_clears_subject_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            (root / "canonical" / "license-rights-policy.json").write_text(json.dumps({
                "id": "FA3-LICENSE-RIGHTS-POLICY-001"
            }), encoding="utf-8")
            descriptor_dir = root / "canonical" / "license-rights" / "descriptors"
            descriptor_dir.mkdir(parents=True)
            descriptor = {
                "schema": "fa3.license-rights-descriptor.v1",
                "subject": {"id": "FA3-PROVIDER-NATIVE-001", "type": "CODE"},
                "source": {"locator": "src/native.py", "revision": "a" * 40},
                "license": {
                    "declared": "Apache-2.0",
                    "detected": ["Apache-2.0"],
                    "concluded": "Apache-2.0",
                    "effective": "Apache-2.0",
                },
                "rights": {
                    "modification_allowed": True,
                    "redistribution_allowed": True,
                    "commercial_use_allowed": True,
                },
                "obligations": {
                    "attribution_required": True,
                    "source_offer_required": False,
                    "entitlement_required": False,
                    "entitlement_reference": None,
                    "unresolved": [],
                },
                "disposition": "ALLOW_WITH_OBLIGATIONS",
                "evidence": ["fixture"],
            }
            dpath = descriptor_dir / "FA3-PROVIDER-NATIVE-001.json"
            dpath.write_text(json.dumps(descriptor), encoding="utf-8")
            (root / "canonical" / "license-rights-descriptor-registry.json").write_text(json.dumps({
                "entries": [{
                    "subject_id": "FA3-PROVIDER-NATIVE-001",
                    "descriptor": "canonical/license-rights/descriptors/FA3-PROVIDER-NATIVE-001.json",
                }]
            }), encoding="utf-8")
            inv = build_inventory(root)
            self.assertEqual(0, inv["summary"]["unique_release_blockers"])
            self.assertEqual(1, inv["summary"]["rights_descriptor_cleared_release_subjects"])
            self.assertFalse(any(x.get("severity") == "BLOCKING" for x in inv["work_queue"]))

    def test_repository_release_included_subjects_have_descriptors(self):
        inv = build_inventory(ROOT)
        self.assertEqual(0, inv["summary"]["unique_release_blockers"])
        self.assertEqual(
            inv["summary"]["release_included_subjects"],
            inv["summary"]["rights_descriptor_cleared_release_subjects"],
        )
        self.assertFalse(any(x.get("severity") == "BLOCKING" for x in inv["work_queue"]))

    def test_non_code_rights_domains_are_separate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            inv = build_inventory(root)
            fonts = [x for x in inv["subjects"] if x["category"] == "FONT"]
            self.assertEqual(1, len(fonts))
            self.assertFalse(fonts[0]["automatic_legal_clearance"])


if __name__ == "__main__":
    unittest.main()
