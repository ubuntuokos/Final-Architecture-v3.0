import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import fa3_terax_gate as t


class TeraxGateTests(unittest.TestCase):
    def test_01_boundary_first(self):
        self.assertTrue(t.boundary_first_allowed(native_boundary=True, authorized=True))
        self.assertFalse(t.boundary_first_allowed(native_boundary=False, authorized=True))

    def test_02_workspace_authorization(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "w"; root.mkdir()
            inside = root / "x"; inside.write_text("x")
            outside = Path(d) / "o"; outside.mkdir()
            self.assertTrue(t.workspace_authorized(root, inside))
            self.assertFalse(t.workspace_authorized(root, outside / "x"))

    def test_03_capability_scope(self):
        self.assertTrue(t.capability_scoped({"read", "edit"}, {"read"}))
        self.assertFalse(t.capability_scoped({"read"}, {"shell"}))

    def test_04_mutation_approval(self):
        self.assertTrue(t.mutation_authorized("ASK_HUMAN", True))
        self.assertFalse(t.mutation_authorized("ASK_HUMAN", False))
        self.assertFalse(t.mutation_authorized("DENY", True))

    def test_05_read_before_edit(self):
        self.assertTrue(t.read_before_edit(read_seen=True, read_version="1", current_version="1"))
        self.assertFalse(t.read_before_edit(read_seen=True, read_version="1", current_version="2"))

    def test_06_diff_before_apply(self):
        self.assertTrue(t.diff_before_apply(proposal=True, diff=True, approved=True))
        self.assertFalse(t.diff_before_apply(proposal=True, diff=False, approved=True))

    def test_07_symlink_revalidation(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "w"; root.mkdir()
            outside = base / "secret"; outside.write_text("s")
            link = root / "link"; link.symlink_to(outside)
            self.assertFalse(t.workspace_authorized(root, link))

    def test_08_ssrf_and_pinning(self):
        self.assertTrue(t.egress_allowed(["8.8.8.8"], pinned_addresses=["8.8.8.8"]))
        self.assertFalse(t.egress_allowed(["169.254.169.254"], pinned_addresses=["169.254.169.254"]))
        self.assertFalse(t.egress_allowed(["127.0.0.1"], pinned_addresses=["127.0.0.1"]))
        self.assertTrue(t.egress_allowed(["127.0.0.1"], explicit_local_authorization=True, pinned_addresses=["127.0.0.1"]))
        self.assertFalse(t.egress_allowed(["8.8.8.8"], pinned_addresses=["1.1.1.1"]))

    def test_09_provider_neutral(self):
        self.assertTrue(t.provider_projection_valid("FA3-AUTH-MODEL-ROUTER-001"))
        self.assertFalse(t.provider_projection_valid("TERAX"))

    def test_10_project_manifest_untrusted(self):
        self.assertTrue(t.project_instruction_valid("UNTRUSTED_SCOPED_PROJECT_CONTEXT", False))
        self.assertFalse(t.project_instruction_valid("TRUSTED_POLICY", True))

    def test_11_subagent_narrowing(self):
        self.assertTrue(t.subagent_narrowed({"read", "grep"}, {"read"}))
        self.assertFalse(t.subagent_narrowed({"read"}, {"read", "shell"}))

    def test_12_bounded_execution(self):
        self.assertTrue(t.execution_budget_valid({"max_steps":1,"max_tool_calls":1,"max_wall_time":1,"max_processes":1}))
        self.assertFalse(t.execution_budget_valid({"max_steps":0,"max_tool_calls":1,"max_wall_time":1,"max_processes":1}))

    def test_13_local_control(self):
        req = {
            "protocol_version":1, "request_id":"r", "caller_identity":"a", "caller_context":{},
            "method":"open", "parameters":{}, "capability_scope":["ui.open"],
            "authorization_token":"tok", "target":"pane", "deadline_ms":1000
        }
        self.assertTrue(t.local_control_valid(req, expected_token="tok", granted={"ui.open"}))
        self.assertFalse(t.local_control_valid({**req, "authorization_token":"bad"}, expected_token="tok", granted={"ui.open"}))
        self.assertFalse(t.local_control_valid({**req, "target":""}, expected_token="tok", granted={"ui.open"}))

    def test_14_delegation_context(self):
        now = 100
        ctx = {
            "caller_identity":"a", "parent_execution_id":"p", "workspace_id":"w",
            "allowed_capabilities":["read"], "expires_at_epoch":101, "policy_ref":"P", "evidence_chain":["E"]
        }
        self.assertTrue(t.delegation_valid(ctx, now))
        self.assertFalse(t.delegation_valid({**ctx, "expires_at_epoch":99}, now))

    def test_15_executable_evidence(self):
        self.assertTrue(t.invariant_evidence_valid([{"executable":True, "status":"PASS"}]))
        self.assertFalse(t.invariant_evidence_valid([{"executable":False, "status":"PASS"}]))

    def test_16_fail_closed(self):
        self.assertEqual(t.unsupported_disposition("UNVERIFIED"), "DENY")
        self.assertEqual(t.unsupported_disposition("SUPPORTED"), "ALLOW")

    def test_17_zero_cost_disabled(self):
        z = {
            "resident_process_count":0, "worker_thread_count":0, "ram_resident_bytes":0,
            "gpu_memory_bytes":0, "network_session_count":0, "accelerator_reservation_count":0,
            "active_polling":False, "background_inference":False
        }
        self.assertTrue(t.disabled_zero_cost(z))
        self.assertFalse(t.disabled_zero_cost({**z, "gpu_memory_bytes":1}))

    def test_regression_matrix_17_of_17(self):
        r = t.run_regressions()
        self.assertEqual(r["result"], "PASS")
        self.assertEqual(r["passed"], 17)
        self.assertEqual(r["total"], 17)

    def test_reference_pin(self):
        root = Path(__file__).resolve().parents[1]
        r = t.reference_check(root)
        self.assertEqual(r["result"], "PASS", r)


if __name__ == "__main__":
    unittest.main()
