#!/usr/bin/env python3
"""FA3 non-authoritative prompt builder, addressed reception and peer directory.

The central MCP Gateway mediates invocation; UAF owns execution; Temporal owns
durable scheduling; Security Governance, Model Router and HRB retain authority.
This module owns only validated messages, routing metadata and local projections.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import ssl
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA = "fa3.prompt-dispatch.v1"
SNAPSHOT_SCHEMA = "fa3.mesh-snapshot.v1"
MAX_CLOCK_SKEW = 120
MAX_MESSAGE_BYTES = 1_048_576


class DispatchDenied(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise DispatchDenied(code)


def _no_inline_secrets(value: Any) -> None:
    forbidden = {"api_key", "password", "secret", "secrets", "credential",
                 "credentials", "bearer_token", "private_key"}
    if isinstance(value, dict):
        for key, item in value.items():
            _require(str(key).lower() not in forbidden, "INLINE_SECRET_FORBIDDEN")
            _no_inline_secrets(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _no_inline_secrets(item)


def load_admitted_applications(root: Path) -> set[str]:
    """Every known application has a possible receiver, never implicit admission."""
    internal = json.loads((root / "canonical/FA3-APPLICATION-DONOR-LINKS-001.json").read_text())
    curated = json.loads((root / "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json").read_text())
    _require(internal.get("id") == "FA3-APPLICATION-DONOR-LINKS-001", "APP_CATALOG_INVALID")
    _require(curated.get("id") == "FA3-AI-STUDIO-APP-CATALOG-001", "APP_CATALOG_INVALID")
    return {row["application_id"] for row in internal["applications"]} | {
        row["id"] for row in curated["applications"] if row.get("admission") == "APPROVED"
    }


def build_prompt(spec: dict[str, Any], *, creative_project: dict[str, Any] | None = None,
                 visual_recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Deterministic, typed prompt construction; never picks a model/provider."""
    _require(isinstance(spec, dict), "PROMPT_SCHEMA_INVALID")
    _no_inline_secrets(spec)
    for field in ("project_id", "prompt", "target_application", "capability_id", "action_id"):
        _require(nonempty(spec.get(field)), "PROMPT_FIELD_REQUIRED")
    _require(isinstance(spec.get("arguments", {}), dict), "PROMPT_ARGUMENTS_INVALID")
    _require(isinstance(spec.get("dependencies", []), list), "PROMPT_DEPENDENCIES_INVALID")
    _require(spec.get("physical_model") is None and spec.get("provider_id") is None,
             "MODEL_ROUTER_BYPASS")
    result = {
        "schema": SCHEMA, "prompt_id": spec.get("prompt_id") or str(uuid.uuid4()),
        "project_id": spec["project_id"], "prompt": spec["prompt"],
        "to": {"application": spec["target_application"],
               "host": spec.get("target_host"), "capability": spec["capability_id"]},
        "action_id": spec["action_id"], "arguments": dict(spec.get("arguments", {})),
        "dependencies": list(spec.get("dependencies", [])),
        "not_before_epoch": int(spec.get("not_before_epoch", 0)),
        "deadline_epoch": spec.get("deadline_epoch"),
        "logical_model_route": spec.get("logical_model_route"),
        "authorities": {
            "tool": "FA3-AUTH-MCP-GATEWAY-001",
            "execution": "FA3-UNIFIED-ACTION-FABRIC-001",
            "model": "FA3-AUTH-MODEL-ROUTER-001",
            "resources": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "durable": "EXISTING_FA3_TEMPORAL_AUTHORITY",
        },
    }
    if creative_project is not None:
        try:
            from fa3_creative_project_workflow import plan_scoped_revision, project_context_slice
        except ImportError as exc:
            raise DispatchDenied("CREATIVE_PROFILE_NOT_MERGED") from exc
        changed = spec.get("changed_node_ids")
        _require(isinstance(changed, list) and changed, "SCOPED_REVISION_REQUIRED")
        revision = plan_scoped_revision(creative_project, changed)
        _require(not revision["approval_required"] or spec.get("approval_ref"),
                 "HUMAN_APPROVAL_REQUIRED")
        result["scoped_revision"] = revision
        result["project_context"] = project_context_slice(creative_project, revision)
    if visual_recipe is not None:
        try:
            from fa3_visual_style import build_visual_intent
        except ImportError as exc:
            raise DispatchDenied("VISUAL_STYLE_PROFILE_NOT_MERGED") from exc
        result["visual_intent"] = build_visual_intent(
            visual_recipe, values=spec.get("visual_values", {}),
            scope=spec.get("visual_scope", "ASSET"), target_id=spec.get("target_id"),
        )
    _no_inline_secrets(result)
    result["prompt_sha256"] = digest(result)
    return result


def _sign(value: dict[str, Any], key: bytes) -> str:
    _require(isinstance(key, bytes) and len(key) >= 32, "PEER_KEY_UNAVAILABLE")
    return hmac.new(key, canonical(value), hashlib.sha256).hexdigest()


def _valid_endpoint(endpoint: str) -> bool:
    parsed = urllib.parse.urlparse(endpoint)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username \
        and not parsed.password and not parsed.fragment and parsed.path in ("", "/")


class MeshDirectory:
    """Verified, expiring, transitive host inventory. Peer keys come from Secret Broker.

    A seed/allowlist of peer identities and their key resolvers is required:
    gossip never creates a new trust relationship or expands policy scope.
    """
    def __init__(self, host_id: str, endpoint: str, *, allowed_hosts: set[str],
                 key_resolver: Callable[[str], bytes], ttl_seconds: int = 90):
        _require(nonempty(host_id) and _valid_endpoint(endpoint), "MESH_HOST_INVALID")
        _require(host_id in allowed_hosts and ttl_seconds > 0, "MESH_TRUST_INVALID")
        self.host_id, self.endpoint = host_id, endpoint.rstrip("/")
        self.allowed_hosts, self.key_resolver = frozenset(allowed_hosts), key_resolver
        self.ttl_seconds = ttl_seconds
        self._sequence = 0
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._local_apps: dict[str, dict[str, Any]] = {}

    def register(self, app_id: str, capabilities: list[str], action_ids: list[str],
                 *, state: str = "READY") -> None:
        _require(nonempty(app_id) and state in {"READY", "DRAINING", "OFFLINE"},
                 "APP_REGISTRATION_INVALID")
        _require(capabilities and action_ids and all(map(nonempty, capabilities + action_ids)),
                 "APP_REGISTRATION_INVALID")
        self._local_apps[app_id] = {"app_id": app_id, "capabilities": sorted(set(capabilities)),
                                    "action_ids": sorted(set(action_ids)), "state": state}

    def own_snapshot(self, *, now: int | None = None, hardware_audit: dict[str, Any]) -> dict[str, Any]:
        now = int(time.time()) if now is None else int(now)
        _require(hardware_audit.get("result") == "PASS"
                 and hardware_audit.get("vendor_neutral") is True
                 and hardware_audit.get("cpu_only_viable") is True
                 and hardware_audit.get("accelerator_cardinality") == "0..N",
                 "HARDWARE_AUDIT_REQUIRED")
        self._sequence += 1
        data = {"schema": SNAPSHOT_SCHEMA, "host_id": self.host_id,
                "endpoint": self.endpoint, "sequence": self._sequence,
                "issued_epoch": now, "expires_epoch": now + self.ttl_seconds,
                "hardware_audit_ref": hardware_audit.get("evidence_ref"),
                "apps": [self._local_apps[k] for k in sorted(self._local_apps)]}
        _require(nonempty(data["hardware_audit_ref"]), "HARDWARE_AUDIT_REQUIRED")
        signed = {"data": data, "signature": _sign(data, self.key_resolver(self.host_id))}
        self._snapshots[self.host_id] = signed
        return signed

    def ingest(self, snapshot: dict[str, Any], *, now: int | None = None) -> bool:
        now = int(time.time()) if now is None else int(now)
        _require(isinstance(snapshot, dict) and isinstance(snapshot.get("data"), dict),
                 "MESH_SNAPSHOT_INVALID")
        data = snapshot["data"]
        host = data.get("host_id")
        _require(host in self.allowed_hosts and data.get("schema") == SNAPSHOT_SCHEMA,
                 "MESH_PEER_NOT_ADMITTED")
        _require(_valid_endpoint(data.get("endpoint", "")), "MESH_ENDPOINT_INVALID")
        _require(isinstance(data.get("sequence"), int) and data["sequence"] >= 1,
                 "MESH_SEQUENCE_INVALID")
        _require(isinstance(data.get("issued_epoch"), int)
                 and isinstance(data.get("expires_epoch"), int)
                 and abs(now - data["issued_epoch"]) <= MAX_CLOCK_SKEW
                 and now < data["expires_epoch"]
                 and data["expires_epoch"] - data["issued_epoch"] <= self.ttl_seconds,
                 "MESH_SNAPSHOT_EXPIRED")
        _require(isinstance(data.get("apps"), list) and nonempty(data.get("hardware_audit_ref")),
                 "MESH_SNAPSHOT_INVALID")
        seen_apps: set[str] = set()
        for app in data["apps"]:
            _require(isinstance(app, dict) and nonempty(app.get("app_id"))
                     and app["app_id"] not in seen_apps
                     and app.get("state") in {"READY", "DRAINING", "OFFLINE"}
                     and isinstance(app.get("capabilities"), list)
                     and isinstance(app.get("action_ids"), list), "MESH_APP_INVALID")
            seen_apps.add(app["app_id"])
        signature = snapshot.get("signature")
        expected = _sign(data, self.key_resolver(host))
        _require(isinstance(signature, str) and hmac.compare_digest(signature, expected),
                 "MESH_SIGNATURE_INVALID")
        old = self._snapshots.get(host)
        if old is not None:
            prior = old["data"]["sequence"]
            _require(data["sequence"] >= prior, "MESH_REPLAY_DENIED")
            if data["sequence"] == prior:
                _require(signature == old["signature"], "MESH_EQUIVOCATION_DENIED")
                return False
        self._snapshots[host] = snapshot
        return True

    def exchange(self, bundle: list[dict[str, Any]], *, now: int | None = None) -> int:
        _require(isinstance(bundle, list), "MESH_BUNDLE_INVALID")
        count = 0
        for snapshot in bundle:
            if self.ingest(snapshot, now=now):
                count += 1
        return count

    def export(self, *, now: int | None = None) -> list[dict[str, Any]]:
        now = int(time.time()) if now is None else int(now)
        return [self._snapshots[k] for k in sorted(self._snapshots)
                if self._snapshots[k]["data"]["expires_epoch"] > now]

    def locate(self, application: str, capability: str, action_id: str,
               *, host: str | None = None, now: int | None = None,
               choose_host: Callable[[list[dict[str, str]]], str] | None = None) -> dict[str, str]:
        now = int(time.time()) if now is None else int(now)
        candidates = []
        for snap in self.export(now=now):
            data = snap["data"]
            if host and data["host_id"] != host:
                continue
            for app in data["apps"]:
                if (app["app_id"] == application and app["state"] == "READY"
                        and capability in app["capabilities"] and action_id in app["action_ids"]):
                    candidates.append({"host_id": data["host_id"], "endpoint": data["endpoint"],
                                       "application": application, "capability": capability,
                                       "action_id": action_id})
        _require(bool(candidates), "MESH_TARGET_UNAVAILABLE")
        if len(candidates) > 1:
            _require(choose_host is not None, "HRB_PLACEMENT_REQUIRED")
            selected = choose_host(candidates)
            candidates = [c for c in candidates if c["host_id"] == selected]
            _require(len(candidates) == 1, "HRB_PLACEMENT_DENIED")
        return candidates[0]


@dataclass
class ReceptionAdapter:
    application_id: str
    admitted_actions: frozenset[str]
    uaf_dispatcher: Any
    principal_validator: Callable[[dict[str, Any], dict[str, Any]], bool]

    def receive(self, message: dict[str, Any], *, peer: dict[str, Any]) -> dict[str, Any]:
        from fa3_uaf import ActionRequest, ExecutionContext
        _require(message.get("to", {}).get("application") == self.application_id,
                 "RECEIVER_ADDRESS_MISMATCH")
        action_id = message.get("action_id")
        _require(action_id in self.admitted_actions, "RECEIVER_ACTION_NOT_ADMITTED")
        _require(self.principal_validator(message, peer) is True, "RECEIVER_POLICY_DENIED")
        principal = message.get("principal")
        _require(isinstance(principal, dict), "RECEIVER_PRINCIPAL_INVALID")
        context = ExecutionContext(context_id=message["message_id"],
                                   application=self.application_id,
                                   project=message.get("project_id"),
                                   session_id=message.get("session_id"))
        request = ActionRequest(action_id=action_id, arguments=message.get("arguments", {}),
                                principal=principal, context=context,
                                request_id=message["message_id"],
                                approval=message.get("approval"))
        outcome = self.uaf_dispatcher.execute(request)
        return outcome.as_dict()


class ReceptionHub:
    """Generic receiver factory for every admitted app; unbound apps never execute."""
    def __init__(self, admitted: set[str], directory: MeshDirectory,
                 principal_validator: Callable[[dict[str, Any], dict[str, Any]], bool],
                 *, receipt_store: str = ":memory:"):
        import threading
        self.admitted, self.directory = frozenset(admitted), directory
        self.principal_validator = principal_validator
        self.adapters: dict[str, ReceptionAdapter] = {}
        self._replay_lock = threading.RLock()
        self._receipts = sqlite3.connect(receipt_store, check_same_thread=False)
        self._receipts.execute("CREATE TABLE IF NOT EXISTS inbox (message_id TEXT PRIMARY KEY, "
                               "message_hash TEXT NOT NULL, status TEXT NOT NULL, receipt TEXT)")
        self._receipts.commit()

    def bind(self, app_id: str, capabilities: list[str], action_ids: list[str],
             uaf_dispatcher: Any) -> ReceptionAdapter:
        _require(app_id in self.admitted and app_id not in self.adapters,
                 "RECEIVER_APP_NOT_ADMITTED")
        _require(uaf_dispatcher is not None, "RECEIVER_UAF_REQUIRED")
        adapter = ReceptionAdapter(app_id, frozenset(action_ids), uaf_dispatcher,
                                   self.principal_validator)
        self.adapters[app_id] = adapter
        self.directory.register(app_id, capabilities, action_ids)
        return adapter

    def receive(self, message: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
        _require(message.get("schema") == SCHEMA, "MESSAGE_SCHEMA_INVALID")
        _no_inline_secrets(message)
        _require(nonempty(message.get("message_id")) and nonempty(message.get("project_id")),
                 "MESSAGE_ID_INVALID")
        destination = message.get("to")
        _require(isinstance(destination, dict)
                 and destination.get("host") == self.directory.host_id, "MESSAGE_WRONG_HOST")
        app_id = destination.get("application")
        _require(app_id in self.adapters, "RECEIVER_NOT_CONNECTED")
        _require(peer.get("authenticated") is True
                 and self.principal_validator(message, peer) is True, "RECEIVER_POLICY_DENIED")
        request_hash = digest(message)
        with self._replay_lock:
            row = self._receipts.execute(
                "SELECT message_hash,status,receipt FROM inbox WHERE message_id=?",
                (message["message_id"],)).fetchone()
            if row is not None:
                _require(row[0] == request_hash, "MESSAGE_ID_COLLISION")
                _require(row[1] == "DONE", "MESSAGE_IN_DOUBT_RECONCILIATION_REQUIRED")
                return json.loads(row[2])
            self._receipts.execute(
                "INSERT INTO inbox(message_id,message_hash,status) VALUES(?,?,?)",
                (message["message_id"], request_hash, "PENDING"))
            self._receipts.commit()
            # Never auto-repeat an uncertain side effect after a crash/failure.
            result = self.adapters[app_id].receive(message, peer=peer)
            self._receipts.execute(
                "UPDATE inbox SET status='DONE',receipt=? WHERE message_id=?",
                (canonical(result).decode(), message["message_id"]))
            self._receipts.commit()
            return result


def addressed_message(prompt: dict[str, Any], principal: dict[str, Any],
                      *, destination: dict[str, str], session_id: str,
                      approval: dict[str, Any] | None = None) -> dict[str, Any]:
    _require(prompt.get("schema") == SCHEMA, "PROMPT_SCHEMA_INVALID")
    _require(nonempty(session_id) and isinstance(principal, dict), "MESSAGE_PRINCIPAL_INVALID")
    _require(destination["application"] == prompt["to"]["application"]
             and destination["capability"] == prompt["to"]["capability"]
             and destination["action_id"] == prompt["action_id"], "MESSAGE_ROUTE_MISMATCH")
    return {"schema": SCHEMA, "message_id": str(uuid.uuid4()),
            "prompt_id": prompt["prompt_id"], "project_id": prompt["project_id"],
            "session_id": session_id, "principal": principal,
            "to": {"host": destination["host_id"], "application": destination["application"],
                   "capability": destination["capability"]},
            "action_id": prompt["action_id"], "arguments": dict(prompt["arguments"]),
            "prompt_sha256": prompt["prompt_sha256"], "approval": approval}


class WorkflowProjection:
    """SQLite reference projection, not a replacement for Temporal workflow history.

    In production Temporal invokes ready() and publish() as existing durable
    activities. Only opaque artifact references cross application boundaries.
    """
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, spec TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (job TEXT, stage TEXT, event_id TEXT, "
                        "kind TEXT, artifact_ref TEXT, receipt TEXT, PRIMARY KEY (job,stage,event_id))")
        self.db.commit()

    def submit(self, job_id: str, stages: list[dict[str, Any]]) -> None:
        _require(nonempty(job_id) and isinstance(stages, list) and stages, "WORKFLOW_INVALID")
        ids = [s.get("stage_id") for s in stages]
        _require(all(map(nonempty, ids)) and len(set(ids)) == len(ids), "WORKFLOW_INVALID")
        nodes = {s["stage_id"]: s for s in stages}
        _no_inline_secrets(stages)
        for s in stages:
            _require(nonempty(s.get("application")) and nonempty(s.get("capability"))
                     and nonempty(s.get("action_id")), "WORKFLOW_STAGE_INVALID")
            deps = s.get("dependencies", [])
            _require(isinstance(deps, list), "WORKFLOW_DEPENDENCIES_INVALID")
            for dep in deps:
                _require(isinstance(dep, dict) and dep.get("stage_id") in nodes
                         and dep.get("kind", "FINAL") in {"INTERMEDIATE", "FINAL"},
                         "WORKFLOW_DEPENDENCIES_INVALID")
        def visit(node: str, stack: set[str], seen: set[str]) -> None:
            _require(node not in stack, "WORKFLOW_CYCLE_DENIED")
            if node in seen:
                return
            stack.add(node)
            for dep in nodes[node].get("dependencies", []):
                visit(dep["stage_id"], stack, seen)
            stack.remove(node)
            seen.add(node)
        seen: set[str] = set()
        for stage_id in ids:
            visit(stage_id, set(), seen)
        self.db.execute("INSERT INTO jobs VALUES (?, ?)", (job_id, canonical(stages).decode()))
        self.db.commit()

    def publish(self, job_id: str, stage_id: str, kind: str, artifact_ref: str,
                receipt: dict[str, Any], *, event_id: str) -> bool:
        _require(kind in {"INTERMEDIATE", "FINAL"} and nonempty(event_id)
                 and nonempty(artifact_ref) and artifact_ref.startswith("artifactref:")
                 and isinstance(receipt, dict) and nonempty(receipt.get("evidence_ref")),
                 "WORKFLOW_EVENT_INVALID")
        stages = self._stages(job_id)
        _require(stage_id in {s["stage_id"] for s in stages}, "WORKFLOW_STAGE_UNKNOWN")
        before = self.db.total_changes
        self.db.execute("INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?, ?)",
                        (job_id, stage_id, event_id, kind, artifact_ref,
                         canonical(receipt).decode()))
        self.db.commit()
        return self.db.total_changes > before

    def _stages(self, job_id: str) -> list[dict[str, Any]]:
        row = self.db.execute("SELECT spec FROM jobs WHERE id=?", (job_id,)).fetchone()
        _require(row is not None, "WORKFLOW_UNKNOWN")
        return json.loads(row[0])

    def ready(self, job_id: str, *, now: int | None = None) -> list[dict[str, Any]]:
        now = int(time.time()) if now is None else int(now)
        events = self.db.execute("SELECT stage,kind,artifact_ref,receipt FROM events WHERE job=?",
                                 (job_id,)).fetchall()
        complete = {stage for stage, kind, *_ in events if kind == "FINAL"}
        available = {(stage, kind) for stage, kind, *_ in events}
        result = []
        for stage in self._stages(job_id):
            if stage["stage_id"] in complete or now < int(stage.get("not_before_epoch", 0)):
                continue
            if stage.get("deadline_epoch") is not None and now > int(stage["deadline_epoch"]):
                continue
            deps = stage.get("dependencies", [])
            if not all((d["stage_id"], d.get("kind", "FINAL")) in available
                       or (d.get("kind", "FINAL") == "INTERMEDIATE"
                           and (d["stage_id"], "FINAL") in available) for d in deps):
                continue
            artifacts = [{"source_stage": st, "kind": kind, "artifact_ref": ref,
                          "evidence_ref": json.loads(rec)["evidence_ref"]}
                         for st, kind, ref, rec in events if st in {d["stage_id"] for d in deps}
                         and (st, kind) in available]
            result.append({**stage, "input_artifacts": artifacts})
        return result


def https_exchange(endpoint: str, snapshots: list[dict[str, Any]], *,
                   tls: ssl.SSLContext, timeout: float = 5.0) -> list[dict[str, Any]]:
    """mTLS-required outbound peer sync; a server adapter must verify the client cert."""
    _require(_valid_endpoint(endpoint) and isinstance(tls, ssl.SSLContext)
             and tls.verify_mode == ssl.CERT_REQUIRED
             and tls.check_hostname, "MESH_MTLS_REQUIRED")
    payload = canonical({"snapshots": snapshots})
    _require(len(payload) < MAX_MESSAGE_BYTES, "MESH_BUNDLE_TOO_LARGE")
    req = urllib.request.Request(endpoint.rstrip("/") + "/v1/mesh/sync", payload,
                                 {"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, context=tls, timeout=timeout) as response:
        raw = response.read(MAX_MESSAGE_BYTES + 1)
    _require(len(raw) <= MAX_MESSAGE_BYTES, "MESH_BUNDLE_TOO_LARGE")
    result = json.loads(raw)
    _require(isinstance(result, dict) and isinstance(result.get("snapshots"), list),
             "MESH_BUNDLE_INVALID")
    return result["snapshots"]


MCP_RECEPTION_CAPABILITY = "fa3.prompt.dispatch"
MCP_RECEPTION_PROVIDER = "FA3-PROMPT-RECEPTION-001"
MCP_RECEPTION_ADAPTER = "fa3-prompt-reception"


def sign_delivery(message: dict[str, Any], *, sender: MeshDirectory,
                  now: int | None = None) -> dict[str, Any]:
    """HMAC integrity binding: host, address, principal, action and artifact refs."""
    now = int(time.time()) if now is None else int(now)
    _require(message.get("schema") == SCHEMA and message.get("to", {}).get("host")
             in sender.allowed_hosts, "MESSAGE_SCHEMA_INVALID")
    data = {"sender_host": sender.host_id, "issued_epoch": now,
            "message": message}
    return {"data": data, "signature": _sign(data, sender.key_resolver(sender.host_id))}


def verify_delivery(signed: dict[str, Any], *, directory: MeshDirectory,
                    authenticated_peer_host: str | None = None,
                    now: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    now = int(time.time()) if now is None else int(now)
    _require(isinstance(signed, dict) and isinstance(signed.get("data"), dict),
             "MESSAGE_SIGNATURE_INVALID")
    data = signed["data"]
    sender_host = data.get("sender_host")
    _require(sender_host in directory.allowed_hosts
             and (authenticated_peer_host is None or sender_host == authenticated_peer_host),
             "MESSAGE_SENDER_NOT_ADMITTED")
    _require(isinstance(data.get("issued_epoch"), int)
             and abs(now - data["issued_epoch"]) <= MAX_CLOCK_SKEW,
             "MESSAGE_EXPIRED")
    sig = signed.get("signature")
    _require(isinstance(sig, str)
             and hmac.compare_digest(sig, _sign(data, directory.key_resolver(sender_host))),
             "MESSAGE_SIGNATURE_INVALID")
    message = data.get("message")
    _require(isinstance(message, dict)
             and message.get("schema") == SCHEMA
             and message.get("to", {}).get("host") == directory.host_id,
             "MESSAGE_WRONG_HOST")
    return message, {"authenticated": True, "host_id": sender_host,
                     "signature_verified": True}


def admitted_mcp_adapter(hub: ReceptionHub):
    """The only inbound action bridge: signed envelope -> Central MCP -> UAF."""
    from fa3_mcp_gateway import Adapter, GatewayDenied
    from fa3_uaf import UafError

    def handle(arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            signed = arguments.get("signed_envelope")
            message, peer = verify_delivery(signed, directory=hub.directory)
            return hub.receive(message, peer)
        except DispatchDenied as exc:
            raise GatewayDenied(exc.code, "Receiver denied message") from exc
        except UafError as exc:
            raise GatewayDenied(exc.code, "UAF denied receiver action") from exc

    return Adapter(MCP_RECEPTION_ADAPTER, MCP_RECEPTION_PROVIDER, handle)


def mcp_adapter_factory():
    """Host-owned factory: FA3_PROMPT_RECEPTION_HUB_FACTORY=module:function.

    The factory must instantiate real UAF dispatchers, Secret Broker key
    resolvers and Security Governance principal validation for admitted apps.
    """
    import importlib
    import os
    raw = os.environ.get("FA3_PROMPT_RECEPTION_HUB_FACTORY", "").strip()
    _require(raw.count(":") == 1, "RECEIVER_HOST_FACTORY_REQUIRED")
    module, method = raw.split(":")
    hub = getattr(importlib.import_module(module), method)()
    _require(isinstance(hub, ReceptionHub), "RECEIVER_HOST_FACTORY_INVALID")
    return admitted_mcp_adapter(hub)


def _verify_mtls_context(context: ssl.SSLContext) -> None:
    _require(isinstance(context, ssl.SSLContext)
             and context.verify_mode == ssl.CERT_REQUIRED,
             "MESH_MTLS_REQUIRED")


def https_dispatch(endpoint: str, mcp_request: dict[str, Any], *,
                   tls: ssl.SSLContext, timeout: float = 10.0) -> dict[str, Any]:
    """Remote transport to host's Central MCP Gateway bridge; no direct UAF HTTP."""
    _require(_valid_endpoint(endpoint) and tls.check_hostname, "MESH_ENDPOINT_INVALID")
    _verify_mtls_context(tls)
    payload = canonical(mcp_request)
    _require(len(payload) < MAX_MESSAGE_BYTES, "MESSAGE_TOO_LARGE")
    req = urllib.request.Request(endpoint.rstrip("/") + "/v1/dispatch", payload,
                                 {"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, context=tls, timeout=timeout) as response:
        raw = response.read(MAX_MESSAGE_BYTES + 1)
    _require(len(raw) <= MAX_MESSAGE_BYTES, "MESSAGE_TOO_LARGE")
    result = json.loads(raw)
    _require(isinstance(result, dict), "RECEPTION_RESULT_INVALID")
    return result


def create_mesh_http_server(bind: tuple[str, int], *, directory: MeshDirectory,
                            gateway: Any, tls: ssl.SSLContext,
                            certificate_host: Callable[[dict[str, Any]], str]):
    """A host supplies a step-ca issued mTLS server context and cert mapping.

    Every action enters the existing Central MCP Gateway. No default port and
    no plaintext listener. Host-owned policy resolver is mandatory.
    """
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    _verify_mtls_context(tls)
    _require(callable(certificate_host) and gateway.policy_resolver is not None,
             "MESH_POLICY_RESOLVER_REQUIRED")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_POST(self):
            try:
                peer_cert = self.connection.getpeercert()
                _require(bool(peer_cert), "MESH_CLIENT_CERT_REQUIRED")
                peer_host = certificate_host(peer_cert)
                _require(peer_host in directory.allowed_hosts, "MESH_PEER_NOT_ADMITTED")
                length = int(self.headers.get("Content-Length", -1))
                _require(0 <= length <= MAX_MESSAGE_BYTES
                         and self.headers.get("Content-Type", "").split(";")[0]
                         == "application/json", "MESSAGE_SCHEMA_INVALID")
                body = json.loads(self.rfile.read(length))
                _require(isinstance(body, dict), "MESSAGE_SCHEMA_INVALID")
                if self.path == "/v1/mesh/sync":
                    snapshots = body.get("snapshots")
                    _require(isinstance(snapshots, list)
                             and any(s.get("data", {}).get("host_id") == peer_host
                                     for s in snapshots), "MESH_PEER_SNAPSHOT_REQUIRED")
                    directory.exchange(snapshots)
                    result = {"snapshots": directory.export()}
                elif self.path == "/v1/dispatch":
                    args = body.get("arguments", {})
                    _require(isinstance(args, dict), "MESSAGE_SCHEMA_INVALID")
                    verify_delivery(args.get("signed_envelope"), directory=directory,
                                    authenticated_peer_host=peer_host)
                    _require(body.get("capability_id") == MCP_RECEPTION_CAPABILITY,
                             "MESH_CAPABILITY_DENIED")
                    result = gateway.invoke(body, peer_context={
                        "client_certificate": peer_cert, "authenticated_host": peer_host})
                else:
                    raise DispatchDenied("MESH_PATH_DENIED")
                raw = canonical(result)
                self.send_response(200)
            except (DispatchDenied, ValueError, KeyError, TypeError):
                raw = canonical({"error": "MESH_REQUEST_DENIED"})
                self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(bind, Handler)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    return server
