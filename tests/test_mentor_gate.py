import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import fa3_mentor_gate as m

class MentorGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        shutil.copytree(ROOT / "evidence/reference", root / "evidence/reference")
        return td, root

    def test_baseline_gate_passes(self):
        r = m.gate(ROOT)
        self.assertEqual("PASS", r["result"], r)
        self.assertEqual((8, 8), (r["regressions"]["passed"], r["regressions"]["total"]))
        self.assertFalse(r["promotion_claimed"])

    def test_provider_authority_drift_fails_closed(self):
        td, root = self._copy_root()
        try:
            path = root / "canonical/providers/FA3-PROVIDER-MENTOR-LOCAL-001.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["architectural_authority"] = True
            path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
            self.assertEqual("FAIL", m.gate(root)["result"])
        finally:
            td.cleanup()

    def test_memory_write_requires_consent(self):
        self.assertTrue(m.memory_write_projection_valid(explicit_consent=True, canonical_write_performed=False, escalation_capability="memory.write"))
        self.assertFalse(m.memory_write_projection_valid(explicit_consent=False, canonical_write_performed=False, escalation_capability="memory.write"))

    def test_mentor_cannot_execute_lab(self):
        self.assertFalse(m.lab_projection_valid({"target_capability":"agent_execution.sandboxed_practice_lab","execute_by_mentor":True,"requires_authorization":True}))

    def test_lab_requires_authenticated_agent_execution_and_bubblewrap(self):
        self.assertFalse(m.delegated_lab_execution_valid(transport_authenticated=False, authority="agent_execution", approved=True, sandbox_backend="bubblewrap", network="deny", writable_host_paths=[]))
        self.assertFalse(m.delegated_lab_execution_valid(transport_authenticated=True, authority="mentor", approved=True, sandbox_backend="bubblewrap", network="deny", writable_host_paths=[]))
        self.assertFalse(m.delegated_lab_execution_valid(transport_authenticated=True, authority="agent_execution", approved=True, sandbox_backend=None, network="deny", writable_host_paths=[]))

    def test_decision_matrix_direct_link(self):
        d=json.loads((ROOT/"canonical/decisions/FA3-DEC-MENTOR-2026-08-30.json").read_text())
        x=json.loads((ROOT/"canonical/FA3-MENTOR-CONFORMANCE-MATRIX-001.json").read_text())
        p=json.loads((ROOT/"canonical/profiles/FA3-MENTOR-001.json").read_text())
        self.assertTrue(m.registry_matrix_link_valid(d,x,p))

if __name__ == "__main__":
    unittest.main()
