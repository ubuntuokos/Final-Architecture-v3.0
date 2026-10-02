from __future__ import annotations
import json
import unittest
from pathlib import Path
from fa3_change_history import ChangeHistoryError, build_record, validate_record

ROOT=Path(__file__).resolve().parents[1]

class ChangeRecordTests(unittest.TestCase):
    def test_schema_and_fact_provenance(self):
        schema=json.loads((ROOT/"canonical/schemas/FA3-CHANGE-RECORD-SCHEMA-001.json").read_text())
        self.assertIn("provenance",schema["required"])
        row=build_record(record_id="r1",timestamp="2026-10-02T00:00:00Z",
            source_kind="TEST",source_ref="test:1",object_type="PROFILE",object_id="p",
            operation="UPDATED",payload={"x":1})
        self.assertRegex(row["provenance"]["source_sha256"],r"^[0-9a-f]{64}$")
        validate_record(row)

    def test_fact_without_digest_fails_closed(self):
        row={"id":"r","timestamp":"t","truth_class":"FACT","source_kind":"T",
             "source_ref":"s","object_type":"P","object_id":"p","operation":"O","provenance":{}}
        with self.assertRaises(ChangeHistoryError): validate_record(row)

if __name__=="__main__": unittest.main()
