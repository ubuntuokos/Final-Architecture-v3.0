from __future__ import annotations
import json
import unittest
from fa3_change_history import REDACTED, build_record, redact

class ChangeSecurityTests(unittest.TestCase):
    def test_secret_keys_are_recursively_redacted(self):
        value=redact({"api_key":"abc","nested":{"password":"def"},"ok":"yes"})
        self.assertEqual(value["api_key"],REDACTED)
        self.assertEqual(value["nested"]["password"],REDACTED)
        self.assertEqual(value["ok"],"yes")

    def test_secret_does_not_survive_record_serialization(self):
        row=build_record(record_id="r",timestamp="t",source_kind="T",source_ref="s",
            object_type="O",object_id="i",operation="U",
            payload={"credential":"super-secret"},details={"token":"raw-token"})
        serialized=json.dumps(row)
        self.assertNotIn("super-secret",serialized)
        self.assertNotIn("raw-token",serialized)

if __name__=="__main__": unittest.main()
