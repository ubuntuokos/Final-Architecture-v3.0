"""Independent negative tests for the non-current-host screenplay gate."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_screenplay_gate import gate

CONTRACT = "canonical/contracts/FA3-STORY-SCREENPLAY-IMPLEMENTATION-CONTRACTS-001.json"
SCHEMA = "canonical/contracts/FA3-SCREENPLAY-DOCUMENT-001.schema.json"
REGISTRY = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
LINKS = "canonical/FA3-APPLICATION-DONOR-LINKS-001.json"
GUI = "apps/fa3-control-center/qml/Main.qml"
CMAKE = "apps/fa3-control-center/CMakeLists.txt"


class ScreenplayGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        sources = {CONTRACT: (ROOT / CONTRACT).read_text(encoding="utf-8"),
                   SCHEMA: (ROOT / SCHEMA).read_text(encoding="utf-8"),
                   REGISTRY: json.dumps({"id": "FA3-DONOR-REFERENCE-REGISTRY-001", "backfill": {"entry_count": 3},
                                         "entries": [{"source": {"normalized_key": value}} for value in (
                                             "github:wildwinter/screenplay-tools",
                                             "github:wassermanproductions/scriptbreak",
                                             "github:proteus-technologies-private-limited/opendraft")]}, ensure_ascii=False),
                   LINKS: json.dumps({"applications": [{"application_id": "fa3.story-screenplay"}]}),
                   GUI: 'routeTable: {"create.story-screenplay": 39}',
                   CMAKE: 'qml/StoryScreenplayPage.qml'}
        for relative, content in sources.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def replace_json(self, relative, mutate):
        file = self.root / relative
        value = json.loads(file.read_text(encoding="utf-8"))
        mutate(value)
        file.write_text(json.dumps(value), encoding="utf-8")

    def test_static_gate_reference_only_pass(self):
        result = gate(self.root)
        self.assertEqual("PASS", result["result"], result)
        self.assertEqual("REFERENCE_ONLY_NOT_CURRENT_HOST", result["evidence_level"])
        self.assertEqual("PENDING", result["current_host_status"])

    def test_fake_current_host_evidence_rejected(self):
        self.replace_json(CONTRACT, lambda a: a["current_host"].update(status="PASS"))
        result = gate(self.root)
        self.assertIn("FABRICATED_HOST_EVIDENCE", result["findings"])
        self.assertEqual("FAIL", result["result"])

    def test_office_one_way_promotion_rejected(self):
        self.replace_json(CONTRACT, lambda a: a["interchange"].update(office_family_codec_admission="IMPORT_ONLY"))
        self.assertIn("FALSE_OFFICE_ADMISSION", gate(self.root)["findings"])

    def test_registry_entry_count_drift_rejected(self):
        self.replace_json(REGISTRY, lambda a: a["backfill"].update(entry_count=2))
        self.assertIn("DONOR_REGISTRY_DRIFT", gate(self.root)["findings"])

    def test_no_gui_wiring_rejected(self):
        (self.root / GUI).write_text("missing actual screenplay route", encoding="utf-8")
        self.assertIn("GUI_ROUTE_MISSING", gate(self.root)["findings"])

    def test_provider_and_hardware_authority_bypass_rejected(self):
        def mutate(a):
            a["ai"]["direct_provider_execution"] = True
            a["hardware_audit"]["global_accelerator_requirement"] = True
            a["handoff"]["publish_authority"] = True
        self.replace_json(CONTRACT, mutate)
        findings = gate(self.root)["findings"]
        self.assertIn("AI_AUTHORITY", findings)
        self.assertIn("HARDWARE_DRIFT", findings)
        self.assertIn("HANDOFF_AUTHORITY", findings)


if __name__ == "__main__":
    unittest.main()
