from __future__ import annotations

import json
import datetime as dt
import math
import os
import stat
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_model_router_materialize import (
    MaterializationDenied, render_litellm, select_bindings, sha256_file,
)
from fa3_model_router_system_one_admit import NativeAdmissionDenied, _cpu_masks_are_explicitly_empty, _exact_cli_value, _probe
from fa3_model_router_system_one_live_gate import NativeRouterE2EDenied, verify_live_router
from fa3_model_router_system_one_native_bridge import (
    NativeBridge, NativeBridgeDenied, read_projected_credential, server,
    verify_designation_approval,
)
from fa3_model_router_system_one_transport import (
    NativeRouterTransport, RouterNativeDenied,
)


def designation():
    return {
        "schema": "fa3.system-one-model-designation.v1",
        "result": "PASS",
        "router_authority": "FA3-AUTH-MODEL-ROUTER-001",
        "provider_id": "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001",
        "logical_route": "fa3-decision-system-one",
        "approved_by_primary_model": True,
        "upstream": "openrouter",
        "approved_models": ["native-a"],
        "served_model_aliases": {"native-a": ["native-a-version"]},
    }


def fake_upstream(method, url, payload, key, timeout):
    if method == "GET":
        return {"data": [{"id": "native-a"}, {"id": "unapproved-native-b"}]}
    if method == "POST":
        return {
            "model": "native-a-version", "id": "native-probe-id",
            "answers": {
                name: (
                    {"type": "choice", "choice": "observe", "probabilities": {"observe": 0.9, "handoff": 0.1}, "confidence": 0.9}
                    if name == "native_admission_probe" else
                    {"type": "choice", "choice": "a", "probabilities": {"a": 0.9, "b": 0.1}, "confidence": 0.9}
                ) for name in payload["questions"]
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
    raise AssertionError("unexpected request")


class ModelRouterNativeMaterializationTests(unittest.TestCase):
    def test_missing_native_provider_keeps_existing_routes_without_fake_activation(self):
        routes = [{"route": "fa3-text-primary", "required_runtime_api": "OPENAI_COMPATIBLE_CHAT"},
                  {"route": "fa3-decision-system-one", "required_runtime_api": "SYSTEM_ONE_DECISIONS_V1", "optional": True}]
        rows = [{"provider_id": "FA3-PROVIDER-DECISION-LOCAL-001", "runtime_id": "chat", "api_base": "http://127.0.0.1:1234/v1"}]
        selected = select_bindings(routes, rows, {"chat": ["chat-model"]})
        self.assertEqual(set(selected), {"fa3-text-primary"})
        self.assertNotIn("pass_through_endpoints:", render_litellm(selected))

    def test_native_provider_selects_only_explicitly_approved_live_model(self):
        routes = [{"route": "fa3-decision-system-one", "required_runtime_api": "SYSTEM_ONE_DECISIONS_V1", "optional": True}]
        row = {"provider_id": "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001", "runtime_id": "native-runtime",
               "api_base": "http://127.0.0.1:43210/v1",
               "runtime_apis": ["SYSTEM_ONE_DECISIONS_V1"], "routes": ["fa3-decision-system-one"],
               "approved_models": ["native-a"],
               "native_bridge_auth_env": "FA3_SYSTEM_ONE_BRIDGE_TOKEN"}
        selected = select_bindings(routes, [row], {"native-runtime": ["unapproved-native-b", "native-a"]})
        self.assertEqual(selected["fa3-decision-system-one"]["model"], "native-a")
        rendered = render_litellm(selected)
        self.assertIn('path: "/fa3/system-one/decisions"', rendered)
        self.assertIn('target: "http://127.0.0.1:43210/v1/decisions"', rendered)
        self.assertIn("auth: true", rendered)
        self.assertIn("forward_headers: false", rendered)
        self.assertIn("FA3_SYSTEM_ONE_BRIDGE_TOKEN", rendered)
        self.assertNotIn("unapproved-native-b", rendered)
        self.assertNotIn('model_name: "fa3-decision-system-one"', rendered)

    def test_native_route_fails_closed_on_missing_designation_or_external_target(self):
        route = [{"route": "fa3-decision-system-one", "required_runtime_api": "SYSTEM_ONE_DECISIONS_V1", "optional": False}]
        row = {"provider_id": "P", "runtime_id": "r", "api_base": "http://127.0.0.1:43210/v1",
               "runtime_apis": ["SYSTEM_ONE_DECISIONS_V1"]}
        with self.assertRaises(MaterializationDenied):
            select_bindings(route, [row], {"r": ["model"]})
        row["approved_models"] = ["model"]
        row["native_bridge_auth_env"] = "FA3_SYSTEM_ONE_BRIDGE_TOKEN"
        selected = select_bindings(route, [row], {"r": ["model"]})
        selected["fa3-decision-system-one"]["api_base"] = "https://api.example.org/v1"
        with self.assertRaises(MaterializationDenied):
            render_litellm(selected)


class NativeProviderBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = NativeBridge(upstream="openrouter", designation=designation(),
                                   upstream_key="upstream-test", bridge_token="bridge-test",
                                   fetch=fake_upstream)

    def test_finite_model_catalogue_and_response(self):
        self.assertEqual(self.bridge.models(), ["native-a"])
        wire = self.bridge.decide({
            "model": "native-a", "state": {"goal": "observe"},
            "questions": {"test_question": {"type": "choice", "instructions": "test",
                                           "criteria": {"a": "a", "b": "b"}}},
        })
        self.assertEqual(wire["model"], "native-a-version")
        self.assertEqual(set(wire["answers"]), {"test_question"})
        with self.assertRaises(NativeBridgeDenied):
            self.bridge.decide({
                "model": "unapproved-native-b", "state": {}, "questions": {
                    "test_question": {"type": "choice", "criteria": {"a": "a"}}
                },
            })

    def test_bridge_never_promotes_fake_catalogue_or_redirectable_url(self):
        other = NativeBridge(upstream="openrouter", designation=designation(),
                             upstream_key="a", bridge_token="b",
                             fetch=lambda *args: {"data": [{"id": "unapproved"}]})
        with self.assertRaises(NativeBridgeDenied):
            other.models()
        bad = designation()
        bad["upstream"] = "evil"
        with self.assertRaises(NativeBridgeDenied):
            NativeBridge(upstream="evil", designation=bad, upstream_key="a", bridge_token="b")

    def test_loopback_http_rejects_invalid_and_missing_bearer(self):
        httpd = server(self.bridge, 0)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{httpd.server_port}/v1/models"
            for key in ("wrong", ""):
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(req, timeout=2)
                self.assertEqual(caught.exception.code, 401)
            req = urllib.request.Request(url, headers={"Authorization": "Bearer bridge-test"})
            with urllib.request.urlopen(req, timeout=2) as res:
                response = json.loads(res.read())
            self.assertEqual([row["id"] for row in response["data"]], ["native-a"])
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)


    def test_typesafe_catalogue_uses_official_models_name_schema(self):
        selected = designation()
        selected["upstream"] = "typesafe"

        def typesafe_fetch(method, url, payload, key, timeout):
            if method == "GET":
                return {"models": [{"name": "native-a", "description": "approved"},
                                   {"name": "undesignated", "description": "not selected"}]}
            return fake_upstream(method, url, payload, key, timeout)

        bridge = NativeBridge(
            upstream="typesafe", designation=selected, upstream_key="upstream-test",
            bridge_token="bridge-test", fetch=typesafe_fetch,
        )
        self.assertEqual(bridge.models(), ["native-a"])
        self.assertEqual(bridge.decide({
            "model": "native-a", "state": {"goal": "observe"},
            "questions": {"test_question": {"type": "choice", "criteria": {"a": "a", "b": "b"}}},
        })["model"], "native-a-version")
        for invalid in ({"data": [{"id": "native-a"}]}, {"models": [{"id": "native-a"}]},
                        {"models": [{"name": "native-a"}, {"name": ""}]}):
            other = NativeBridge(
                upstream="typesafe", designation=selected, upstream_key="a", bridge_token="b",
                fetch=lambda *args, item=invalid: item,
            )
            with self.assertRaises(NativeBridgeDenied):
                other.models()

    def test_cpu_mask_proof_rejects_nonempty_and_duplicate_values(self):
        empty = [f"{name}=".encode() for name in (
            "CUDA_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "ZE_AFFINITY_MASK"
        )]
        self.assertTrue(_cpu_masks_are_explicitly_empty(empty))
        self.assertFalse(_cpu_masks_are_explicitly_empty(empty[:-1]))
        self.assertFalse(_cpu_masks_are_explicitly_empty(empty + [b"CUDA_VISIBLE_DEVICES=0"]))
        self.assertFalse(_cpu_masks_are_explicitly_empty([
            b"CUDA_VISIBLE_DEVICES=0", *empty[1:]
        ]))
        self.assertEqual(_exact_cli_value(["--designation", "/private/designation"], "--designation"), "/private/designation")
        self.assertIsNone(_exact_cli_value(["--designation", "/a", "--designation", "/b"], "--designation"))

    def test_signed_designation_required_and_exactly_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "designation.json"
            approval = Path(directory) / "approval.json"
            target.write_text(json.dumps(designation()), encoding="utf-8")
            target.chmod(0o600)
            from fa3_model_router_materialize import sha256_file as sha
            signed = {"schema": "fa3.authenticated-approval-receipt.v2", "payload": {
                "model_designation_sha256": sha(target),
                "provider_id": "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001",
                "logical_route": "fa3-decision-system-one",
                "upstream": "openrouter",
                "approved_models": ["native-a"],
            }}
            approval.write_text(json.dumps(signed), encoding="utf-8")
            approval.chmod(0o600)
            seen = []
            def verified(receipt, **kwargs):
                seen.append(kwargs)
                return {"qualified": True}
            digest = verify_designation_approval(
                root=ROOT, designation=target, approval_receipt=approval,
                expected_source_commit="a" * 40, verifier=verified,
            )
            self.assertEqual(digest, sha(approval))
            self.assertEqual(seen[0]["required_role"], "PRIMARY_MODEL_DESIGNATOR")
            self.assertEqual(seen[0]["required_grant_scope"], "FA3_MODEL_ROUTER_MODEL_DESIGNATION")
            self.assertEqual(seen[0]["expected_receipt_type"], "MODEL_ROUTER_PRIMARY_MODEL_DESIGNATION")
            with self.assertRaisesRegex(NativeBridgeDenied, "authenticated"):
                verify_designation_approval(
                    root=ROOT, designation=target, approval_receipt=approval,
                    expected_source_commit="a" * 40, verifier=lambda *a, **k: {"qualified": False},
                )
            signed["payload"]["approved_models"] = ["unapproved"]
            approval.write_text(json.dumps(signed), encoding="utf-8")
            with self.assertRaisesRegex(NativeBridgeDenied, "exact model designation"):
                verify_designation_approval(
                    root=ROOT, designation=target, approval_receipt=approval,
                    expected_source_commit="a" * 40, verifier=verified,
                )
            approval.chmod(0o644)
            with self.assertRaisesRegex(NativeBridgeDenied, "protected"):
                verify_designation_approval(
                    root=ROOT, designation=target, approval_receipt=approval,
                    expected_source_commit="a" * 40, verifier=verified,
                )

    def test_credential_file_projection_rejects_unprotected_and_symlinked_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fa3-system-one-bridge-token"
            path.write_text("credential", encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(read_projected_credential(Path(directory), path.name), "credential")
            path.chmod(0o644)
            with self.assertRaises(NativeBridgeDenied):
                read_projected_credential(Path(directory), path.name)


class NativeProviderAdmissionProbeTests(unittest.TestCase):
    def test_bounded_live_probe_and_invalid_bearer_are_mandatory(self):
        def request(url, method, token, payload):
            if url.endswith("/models"):
                return 200, {"data": [{"id": "native-a"}]}
            if token != "bridge-test":
                return 401, {}
            return 200, fake_upstream("POST", "", payload, "upstream-test", 1.0)
        served, request_id = _probe("http://127.0.0.1:12345/v1", "bridge-test",
                                    "native-a", ["native-a-version"], request)
        self.assertEqual(served, "native-a-version")
        self.assertEqual(request_id, "native-probe-id")

    def test_bearer_bypass_and_missing_distribution_deny_admission(self):
        def open_server(url, method, token, payload):
            if url.endswith("/models"):
                return 200, {"data": [{"id": "native-a"}]}
            return 200, fake_upstream("POST", "", payload, "test", 1.0)
        with self.assertRaises(NativeAdmissionDenied):
            _probe("http://127.0.0.1:12345/v1", "bridge-test",
                   "native-a", ["native-a-version"], open_server)


class NativeRouterTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.registry = folder / "routes.json"
        self.registry.write_text('{"routes":["fa3-decision-system-one"]}', encoding="utf-8")
        self.config = folder / "generated.yaml"
        self.config.write_text('model_list: []\n', encoding="utf-8")
        self.config.chmod(0o600)
        self.selection = folder / "selection.json"
        self.receipt = {
            "schema": "fa3.model-router-runtime-selection.v1",
            "result": "PASS", "authority": "FA3-AUTH-MODEL-ROUTER-001",
            "runtime_selected": True, "physical_backend_pinned": False, "physical_model_pinned": False,
            "route_registry_sha256": sha256_file(self.registry),
            "generated_config": str(self.config), "generated_config_sha256": sha256_file(self.config),
            "route_bindings": {"fa3-decision-system-one": {
                "route": "fa3-decision-system-one",
                "runtime_api": "SYSTEM_ONE_DECISIONS_V1",
                "selection": "RUNTIME_DISCOVERED",
                "provider_id": "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001",
                "runtime_id": "native-test",
                "api_base": "http://127.0.0.1:43210/v1",
                "native_bridge_auth_env": "FA3_SYSTEM_ONE_BRIDGE_TOKEN",
                "model": "native-a",
            }},
            "admission_receipt_sha256": {"FA3-PROVIDER-SYSTEM-ONE-NATIVE-001": "a" * 64},
        }
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.selection.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.selection.chmod(0o600)

    def test_exact_selection_and_data_plane_provenance(self):
        calls = []
        def request(url, payload, key, timeout):
            calls.append((url, payload, key))
            return {"answers": {"q": {"type": "noul", "noul": 0.95}},
                    "model": "native-a-version", "id": "native-request-id"}
        transport = NativeRouterTransport(
            selection_receipt=self.selection, route_registry=self.registry,
            router_origin="http://127.0.0.1:40001", master_key="broker-test", request=request,
        )
        response = transport({
            "schema": "fa3.model-router.native-decision-request.v1",
            "authority": "FA3-AUTH-MODEL-ROUTER-001",
            "logical_route": "fa3-decision-system-one",
            "protocol": "system-one-decision-v1",
            "request": {"state": {"goal": "observe"}, "questions": {"q": {"type": "noul"}}},
        })
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "http://127.0.0.1:40001/fa3/system-one/decisions")
        self.assertEqual(calls[0][1]["model"], "native-a")
        self.assertEqual(response["_fa3_routing"]["data_plane"], "LITELLM_AUTHENTICATED_PASS_THROUGH")
        self.assertEqual(response["_fa3_routing"]["served_model_id"], "native-a-version")

    def test_fake_http_cannot_satisfy_live_e2e_without_real_provider_receipt(self):
        native = Path(self.tmp.name) / "native-admission.json"
        native.write_text(json.dumps({
            "schema": "fa3.system-one-native-current-host-receipt.v1",
            "result": "PASS", "provider_id": "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001",
            "selected_model": "native-a", "served_model": "native-a-version",
            "api_base": "http://127.0.0.1:43210/v1",
            "real_upstream_response": False,
            "invalid_bearer_rejected": True,
            "secret_broker_admission_verified": True,
        }), encoding="utf-8")
        native.chmod(0o600)
        self.receipt["admission_receipt_sha256"]["FA3-PROVIDER-SYSTEM-ONE-NATIVE-001"] = sha256_file(native)
        self.save()
        with self.assertRaises(NativeRouterE2EDenied):
            verify_live_router(
                root=ROOT, selection=self.selection, native_admission=native,
                origin="http://127.0.0.1:40001", master_key="test",
                http=lambda *a: self.fail("fake provider cannot be used"),
            )

    def test_e2e_proof_requires_real_native_and_litellm_bearer_rejection(self):
        native = Path(self.tmp.name) / "native-admission.json"
        native.write_text(json.dumps({
            "schema": "fa3.system-one-native-current-host-receipt.v1",
            "result": "PASS", "provider_id": "FA3-PROVIDER-SYSTEM-ONE-NATIVE-001",
            "selected_model": "native-a", "served_model": "native-a-version",
            "api_base": "http://127.0.0.1:43210/v1",
            "real_upstream_response": True,
            "invalid_bearer_rejected": True,
            "secret_broker_admission_verified": True,
        }), encoding="utf-8")
        native.chmod(0o600)
        self.receipt["admission_receipt_sha256"]["FA3-PROVIDER-SYSTEM-ONE-NATIVE-001"] = sha256_file(native)
        self.receipt["route_registry_sha256"] = sha256_file(ROOT / "deployment/model-router/routes.json")
        self.save()
        def fake_http(url, method, key, body):
            if key != "broker-test":
                return 401, {}
            return 200, {
                "model": "native-a-version",
                "answers": {"e2e_noop_choice": {
                    "type": "choice", "choice": "observe",
                    "probabilities": {"observe": 0.92, "handoff": 0.08},
                }},
            }
        proof = verify_live_router(
            root=ROOT, selection=self.selection, native_admission=native,
            origin="http://127.0.0.1:40001", master_key="broker-test",
            http=fake_http,
        )
        self.assertEqual(proof["result"], "PASS")
        self.assertTrue(proof["invalid_and_missing_master_key_rejected"])
        self.assertFalse(proof["execution_performed"])
        e2e = Path(self.tmp.name) / "e2e.json"
        e2e.write_text(json.dumps(proof), encoding="utf-8")
        e2e.chmod(0o600)
        transport = NativeRouterTransport(
            selection_receipt=self.selection, route_registry=ROOT / "deployment/model-router/routes.json",
            router_origin="http://127.0.0.1:40001", master_key="broker-test",
            request=lambda *a: {"model": "native-a-version",
                                "answers": {"q": {"type": "noul", "noul": 0.9}}},
        )
        # Prove stale/scope mismatch is rejected (a mock test is never an admission).
        proof["captured_at"] = "2020-01-01T00:00:00+00:00"
        e2e.write_text(json.dumps(proof), encoding="utf-8")
        with self.assertRaises(RouterNativeDenied):
            transport.validate_live_e2e(e2e, root=ROOT)
        # Incorrect LiteLLM authentication must fail independently of native provider authentication.
        def bad_http(url, method, key, body):
            return 200, {"model": "native-a-version", "answers": {}}
        with self.assertRaises(NativeRouterE2EDenied):
            verify_live_router(
                root=ROOT, selection=self.selection, native_admission=native,
                origin="http://127.0.0.1:40001", master_key="broker-test",
                http=bad_http,
            )

    def test_missing_receipt_drift_and_missing_admission_fail_closed(self):
        transport = NativeRouterTransport(
            selection_receipt=self.selection, route_registry=self.registry,
            router_origin="http://127.0.0.1:40001", master_key="broker-test",
            request=lambda *args: self.fail("request must never be sent"),
        )
        self.receipt["admission_receipt_sha256"] = {}
        self.save()
        with self.assertRaises(RouterNativeDenied):
            transport.binding()
        self.receipt["admission_receipt_sha256"] = {"FA3-PROVIDER-SYSTEM-ONE-NATIVE-001": "a" * 64}
        self.save()
        self.config.write_text("mutated config", encoding="utf-8")
        with self.assertRaises(RouterNativeDenied):
            transport.binding()
        with self.assertRaises(RouterNativeDenied):
            NativeRouterTransport(
                selection_receipt=self.selection, route_registry=self.registry,
                router_origin="https://provider.example.org", master_key="x",
            )


if __name__ == "__main__":
    unittest.main()
