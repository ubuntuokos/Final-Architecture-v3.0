from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fa3_prompt_dispatch import (
    DispatchDenied, MeshDirectory, ReceptionHub, WorkflowProjection,
    addressed_message, build_prompt, canonical, digest, load_admitted_applications,
)
from fa3_mcp_gateway import McpGateway, Adapter
from fa3_uaf import (
    ActionContract, ActionDispatcher, ActionRegistry, CallableProvider,
    ProviderDescriptor, ProviderRegistry,
)

ROOT = Path(__file__).resolve().parents[1]
AUDIT = {"result": "PASS", "vendor_neutral": True, "cpu_only_viable": True,
         "accelerator_cardinality": "0..N", "evidence_ref": "evidenceref:test"}
KEYS = {"alpha": b"a" * 32, "beta": b"b" * 32, "gamma": b"c" * 32}


def mesh(host, others=None):
    allowed = set(others or KEYS)
    return MeshDirectory(host, "https://" + host + ".example", allowed_hosts=allowed,
                         key_resolver=lambda h: KEYS[h])


def prompt(app="fa3.video-editor", action="fa3.test.echo"):
    return build_prompt({"project_id": "project-1", "prompt": "Create scene",
                         "target_application": app, "capability_id": "fa3.test",
                         "action_id": action, "arguments": {"value": "hello"}})


def uaf():
    contract = ActionContract.from_dict({
        "schema": "fa3.uaf.action-contract.v1", "id": "fa3.test.echo",
        "version": "1", "description": "Test bounded FA3 action",
        "input_schema": {"type": "object", "required": ["value"],
                         "properties": {"value": {"type": "string"}}},
        "output_schema": {"type": "object", "required": ["echo"],
                          "properties": {"echo": {"type": "string"}}},
        "semantics": {}, "exposure": {}, "security": {"approval": "policy"},
        "resources": {"hrb_required": False}, "provider": {},
        "evidence": {"required": False},
    })
    registry = ProviderRegistry()
    registry.register(CallableProvider(
        ProviderDescriptor("test-uaf", ("fa3.test.echo",), priority=1),
        lambda request, lease, secrets: {"echo": request.arguments["value"]}))
    return ActionDispatcher(ActionRegistry([contract]), registry,
                            authorize=lambda request, contract: True)


class PromptTest(unittest.TestCase):
    def test_build_typed_without_provider_or_model(self):
        value = prompt()
        self.assertEqual(value["authorities"]["model"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertIsNone(value["logical_model_route"])
        self.assertEqual(len(value["prompt_sha256"]), 64)

    def test_forbids_pin_and_secrets(self):
        for extra in ({"provider_id": "direct"}, {"physical_model": "pin"},
                      {"arguments": {"password": "bad"}}):
            data = {"project_id": "p", "prompt": "x", "target_application": "a",
                    "capability_id": "c", "action_id": "act", **extra}
            with self.assertRaises(DispatchDenied):
                build_prompt(data)

    def test_unmerged_profile_is_fail_closed(self):
        with patch.dict(sys.modules, {"fa3_creative_project_workflow": None}):
            with self.assertRaises(DispatchDenied) as e:
                build_prompt({"project_id": "p", "prompt": "x",
                              "target_application": "a", "capability_id": "c",
                              "action_id": "act", "changed_node_ids": ["shot"]},
                             creative_project={"nodes": []})
            self.assertEqual(e.exception.code, "CREATIVE_PROFILE_NOT_MERGED")
        with patch.dict(sys.modules, {"fa3_visual_style": None}):
            with self.assertRaises(DispatchDenied) as e:
                build_prompt({"project_id": "p", "prompt": "x",
                              "target_application": "a", "capability_id": "c",
                              "action_id": "act"}, visual_recipe={})
            self.assertEqual(e.exception.code, "VISUAL_STYLE_PROFILE_NOT_MERGED")


class MeshTest(unittest.TestCase):
    def test_signed_transitive_discovery(self):
        a, b, c = mesh("alpha"), mesh("beta"), mesh("gamma")
        a.register("fa3.video-editor", ["fa3.test"], ["fa3.test.echo"])
        b.register("fa3.music-studio", ["fa3.audio"], ["fa3.audio.mix"])
        c.register("fa3.story-screenplay", ["fa3.story"], ["fa3.story.write"])
        for node in (a, b, c):
            node.own_snapshot(now=1000, hardware_audit=AUDIT)
        b.exchange(a.export(now=1000), now=1000)
        b.exchange(c.export(now=1000), now=1000)
        self.assertEqual(a.exchange(b.export(now=1000), now=1000), 2)
        self.assertEqual(c.exchange(a.export(now=1000), now=1000), 2)
        route = c.locate("fa3.video-editor", "fa3.test", "fa3.test.echo", now=1001)
        self.assertEqual(route["host_id"], "alpha")
        self.assertEqual({x["data"]["host_id"] for x in a.export(now=1001)},
                         {"alpha", "beta", "gamma"})

    def test_forgeries_replay_expiry_and_untrusted_hosts_fail(self):
        a, b = mesh("alpha"), mesh("beta")
        snap = a.own_snapshot(now=1000, hardware_audit=AUDIT)
        b.ingest(snap, now=1000)
        tampered = json.loads(canonical(snap))
        tampered["data"]["endpoint"] = "https://evil.example"
        with self.assertRaises(DispatchDenied) as e:
            b.ingest(tampered, now=1000)
        self.assertEqual(e.exception.code, "MESH_SIGNATURE_INVALID")
        with self.assertRaises(DispatchDenied) as e:
            b.ingest(snap, now=1400)
        self.assertEqual(e.exception.code, "MESH_SNAPSHOT_EXPIRED")
        newer = a.own_snapshot(now=1001, hardware_audit=AUDIT)
        b.ingest(newer, now=1001)
        with self.assertRaises(DispatchDenied) as e:
            b.ingest(snap, now=1001)
        self.assertEqual(e.exception.code, "MESH_REPLAY_DENIED")
        unknown = mesh("gamma").own_snapshot(now=1000, hardware_audit=AUDIT)
        restricted = mesh("beta", others={"alpha", "beta"})
        with self.assertRaises(DispatchDenied) as e:
            restricted.ingest(unknown, now=1000)
        self.assertEqual(e.exception.code, "MESH_PEER_NOT_ADMITTED")

    def test_host_ambiguity_requires_external_hrb(self):
        a, b, c = mesh("alpha"), mesh("beta"), mesh("gamma")
        for node in (a, b):
            node.register("fa3.video-editor", ["fa3.test"], ["fa3.test.echo"])
            node.own_snapshot(now=1000, hardware_audit=AUDIT)
        c.own_snapshot(now=1000, hardware_audit=AUDIT)
        c.exchange(a.export(now=1000) + b.export(now=1000), now=1000)
        with self.assertRaises(DispatchDenied) as e:
            c.locate("fa3.video-editor", "fa3.test", "fa3.test.echo", now=1000)
        self.assertEqual(e.exception.code, "HRB_PLACEMENT_REQUIRED")
        chosen = c.locate("fa3.video-editor", "fa3.test", "fa3.test.echo",
                          choose_host=lambda candidates: "beta", now=1000)
        self.assertEqual(chosen["host_id"], "beta")
        with self.assertRaises(DispatchDenied) as e:
            c.locate("fa3.video-editor", "fa3.test", "fa3.test.echo",
                     choose_host=lambda candidates: "unadmitted", now=1000)
        self.assertEqual(e.exception.code, "HRB_PLACEMENT_DENIED")

    def test_hardware_audit_required(self):
        a = mesh("alpha")
        with self.assertRaises(DispatchDenied) as e:
            a.own_snapshot(now=1000, hardware_audit={})
        self.assertEqual(e.exception.code, "HARDWARE_AUDIT_REQUIRED")


class ReceptionTest(unittest.TestCase):
    def setUp(self):
        self.directory = mesh("alpha")
        self.allowed = load_admitted_applications(ROOT)
        self.hub = ReceptionHub(self.allowed, self.directory,
                                lambda message, peer: peer.get("authenticated") is True)
        self.hub.bind("fa3.video-editor", ["fa3.test"], ["fa3.test.echo"], uaf())
        self.directory.own_snapshot(now=1000, hardware_audit=AUDIT)

    def test_catalog_adapter_factory_and_real_uaf(self):
        self.assertIn("reference.krita", self.allowed)
        self.assertIn("comfyui", self.allowed)
        self.assertIn("fa3.quickclip", self.allowed)
        route = self.directory.locate("fa3.video-editor", "fa3.test",
                                      "fa3.test.echo", now=1000)
        msg = addressed_message(prompt(), {"id": "human:test"},
                                destination=route, session_id="session-1")
        result = self.hub.receive(msg, {"authenticated": True})
        self.assertEqual(result["output"]["echo"], "hello")
        self.assertEqual(result["provider_id"], "test-uaf")
        self.assertEqual(self.hub.receive(msg, {"authenticated": True}), result)

    def test_denies_unconnected_and_wrong_host_and_policy(self):
        route = self.directory.locate("fa3.video-editor", "fa3.test",
                                      "fa3.test.echo", now=1000)
        msg = addressed_message(prompt(), {"id": "human:test"},
                                destination=route, session_id="session-1")
        with self.assertRaises(DispatchDenied):
            self.hub.receive(msg, {"authenticated": False})
        msg["to"]["host"] = "beta"
        with self.assertRaises(DispatchDenied) as e:
            self.hub.receive(msg, {"authenticated": True})
        self.assertEqual(e.exception.code, "MESSAGE_WRONG_HOST")
        with self.assertRaises(DispatchDenied):
            self.hub.bind("rogue-app", ["x"], ["x"], uaf())

    def test_mcp_gateway_is_actual_invocation_boundary(self):
        gateway = McpGateway({
            "policy_authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
            "capabilities": [{"capability_id": "fa3.prompt.dispatch", "approval": "policy",
                              "hrb_required": False,
                              "providers": [{"state": "CONNECTED", "priority": 1,
                                             "adapter_id": "fa3-receiver",
                                             "provider_id": "FA3-UAF-RECEPTION"}]}],
        })
        gateway.register_adapter(Adapter(
            "fa3-receiver", "FA3-UAF-RECEPTION",
            lambda args: self.hub.receive(args["message"], {"authenticated": True})))
        route = self.directory.locate("fa3.video-editor", "fa3.test",
                                      "fa3.test.echo", now=1000)
        msg = addressed_message(prompt(), {"id": "human:test"},
                                destination=route, session_id="session-1")
        result = gateway.invoke({
            "actor_id": "human:test", "client_id": "fa3-production",
            "session_id": "session-1", "capability_id": "fa3.prompt.dispatch",
            "arguments": {"message": msg},
            "policy_decision": {"authority": "SECURITY_GOVERNANCE_POLICY_PLANE",
                                "status": "ALLOW", "decision_id": "policy-123",
                                "capability_id": "fa3.prompt.dispatch"},
        })
        self.assertEqual(result["result_status"], "success")
        self.assertEqual(result["result"]["output"]["echo"], "hello")


class WorkflowTest(unittest.TestCase):
    def test_intermediate_handoff_and_final_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = WorkflowProjection(str(Path(tmp) / "workflows.sqlite"))
            stages = [
                {"stage_id": "story", "application": "fa3.story-screenplay",
                 "capability": "story", "action_id": "write"},
                {"stage_id": "frames", "application": "fa3.video-editor",
                 "capability": "image", "action_id": "render",
                 "dependencies": [{"stage_id": "story", "kind": "INTERMEDIATE"}]},
                {"stage_id": "export", "application": "fa3.quickclip",
                 "capability": "video", "action_id": "export",
                 "dependencies": [{"stage_id": "frames", "kind": "FINAL"}],
                 "not_before_epoch": 1020},
            ]
            db.submit("job", stages)
            self.assertEqual([s["stage_id"] for s in db.ready("job", now=1000)], ["story"])
            first = db.publish("job", "story", "INTERMEDIATE", "artifactref:story/beat1",
                               {"evidence_ref": "evidenceref:story"}, event_id="e1")
            self.assertTrue(first)
            self.assertFalse(db.publish("job", "story", "INTERMEDIATE",
                                        "artifactref:story/beat1",
                                        {"evidence_ref": "evidenceref:story"}, event_id="e1"))
            pending = db.ready("job", now=1001)
            self.assertEqual([s["stage_id"] for s in pending], ["story", "frames"])
            self.assertEqual(pending[1]["input_artifacts"][0]["artifact_ref"],
                             "artifactref:story/beat1")
            db.publish("job", "frames", "FINAL", "artifactref:frames/final",
                       {"evidence_ref": "evidenceref:frames"}, event_id="e2")
            self.assertEqual([s["stage_id"] for s in db.ready("job", now=1010)], ["story"])
            self.assertIn("export", [s["stage_id"] for s in db.ready("job", now=1020)])
            restored = WorkflowProjection(str(Path(tmp) / "workflows.sqlite"))
            self.assertIn("export", [s["stage_id"] for s in restored.ready("job", now=1021)])

    def test_cycle_and_unscoped_artifact_denied(self):
        db = WorkflowProjection()
        with self.assertRaises(DispatchDenied) as e:
            db.submit("bad", [
                {"stage_id": "a", "application": "x", "capability": "x", "action_id": "x",
                 "dependencies": [{"stage_id": "b"}]},
                {"stage_id": "b", "application": "x", "capability": "x", "action_id": "x",
                 "dependencies": [{"stage_id": "a"}]},
            ])
        self.assertEqual(e.exception.code, "WORKFLOW_CYCLE_DENIED")
        db.submit("good", [{"stage_id": "x", "application": "x",
                             "capability": "x", "action_id": "x"}])
        with self.assertRaises(DispatchDenied):
            db.publish("good", "x", "FINAL", "/tmp/private.txt", {},
                       event_id="bad")


if __name__ == "__main__":
    unittest.main()
