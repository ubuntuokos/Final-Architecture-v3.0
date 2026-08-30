import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import fa3_kanboard_gate as k

class KanboardGateTests(unittest.TestCase):
    def _copy_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(ROOT / "canonical", root / "canonical")
        (root / "evidence/reference").mkdir(parents=True, exist_ok=True)
        return td, root

    def _write(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def test_baseline_gate_passes(self):
        r = k.gate(ROOT)
        self.assertEqual(r["result"], "PASS", r)
        self.assertEqual(r["regressions"]["passed"], 12)
        self.assertEqual(r["regressions"]["total"], 12)
        self.assertEqual(r["authority_scan"]["result"], "PASS")
        self.assertFalse(r["runtime_provider_required"])

    def test_event_cannot_self_authorize_action(self):
        self.assertFalse(k.event_action_allowed(
            event_validated=True, event_type="task.moved", action_capability="work_item.update",
            actor_identity="event", project_scope="project:1",
            policy_authority="FA3-AUTH-SECURITY-GOV-001", policy_decision="ALLOW",
            event_implies_authorization=True))

    def test_application_wide_credential_bypass_denied(self):
        self.assertFalse(k.integration_credential_valid(
            global_application_credential=True, actor_scoped_identity="application",
            project_scope="*", permission_checks_enforced=False))

    def test_state_transition_without_scope_denied(self):
        self.assertFalse(k.state_transition_authorized(
            caller_identity="agent:1", project_scope="", capability_scope=["work_item.transition"],
            current_state="READY", requested_state="DONE", policy_authority=k.PROVIDER_ID,
            policy_decision="ALLOW"))

    def test_plugin_without_supply_chain_evidence_denied(self):
        self.assertFalse(k.plugin_admission_valid(
            source_identity="url:random", pinned_version="", digest="",
            provenance_verified=False, license_admitted=False, policy_admitted=False,
            adhoc_web_install=True))

    def test_provider_url_without_egress_controls_denied(self):
        self.assertFalse(k.provider_egress_valid(
            provider_configured_url=True, canonical_egress_authorized=False,
            ssrf_controls=False, dns_rebinding_controls=False))

    def test_external_provider_cannot_own_canonical_work_item_identity(self):
        self.assertFalse(k.work_item_projection_valid(
            canonical_work_item_id="", provider_instance="kb:local", provider_object_id="task:42",
            sync_state="SYNCED", provider_owns_canonical_identity=True))

    def test_webhook_payload_cannot_be_authorization_or_evidence(self):
        self.assertFalse(k.webhook_projection_valid(
            authenticated=True, validated=False, typed_normalized=False, canonical_event_id="",
            webhook_is_authorization=True, webhook_is_canonical_evidence=True))

    def test_authority_assignment_scan_fails_closed(self):
        td, root = self._copy_root()
        try:
            self._write(root / "canonical/kanboard-escalation.json",
                        {"schema":"fa3.test.v1", "id":"T", "workflow_authority":k.PROVIDER_ID})
            r = k.scan_canonical_authority_assignments(root)
            self.assertEqual(r["result"], "FAIL", r)
        finally:
            td.cleanup()

    def test_provider_authority_drift_denied(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/providers/FA3-PROVIDER-KANBOARD-001.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["architectural_authority"] = True
            self._write(p, o)
            r = k.gate(root)
            self.assertEqual(r["result"], "FAIL", r)
        finally:
            td.cleanup()

    def test_policy_binding_required(self):
        td, root = self._copy_root()
        try:
            p = root / "canonical/enforcement-policy.json"
            o = json.loads(p.read_text(encoding="utf-8"))
            o["mandatory_reference_gates"] = [
                x for x in o["mandatory_reference_gates"] if x != k.GATE_ID
            ]
            self._write(p, o)
            r = k.gate(root)
            self.assertEqual(r["result"], "FAIL", r)
            self.assertTrue(any(f["code"] == "KANBOARD-REF-007" for f in r["reference"]["findings"]))
        finally:
            td.cleanup()

    def test_regression_matrix_is_12_of_12(self):
        r = k.run_regressions()
        self.assertEqual(r["result"], "PASS", r)
        self.assertEqual((r["passed"], r["total"]), (12, 12))

if __name__ == "__main__":
    unittest.main()
