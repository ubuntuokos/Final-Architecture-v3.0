#!/usr/bin/env python3
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

PROVIDER_ID = "FA3-PROVIDER-BUZZ-001"
MCP_AUTHORITY = "FA3-AUTH-MCP-GATEWAY-001"
SECURITY_AUTHORITY = "FA3-AUTH-SECURITY-GOV-001"
WRAPPER_PROTOCOL = "fa3-buzz-wrapper/1"
MAX_COMMAND_BYTES = 16 * 1024
MAX_TIMEOUT_SECONDS = 600
MAX_OUTPUT_BYTES = 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AdmissionDenied(RuntimeError):
    pass


def _deny(message: str) -> None:
    raise AdmissionDenied(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def direct_buzz_dev_mcp_allowed() -> bool:
    return False


def validate_runtime_route(route: dict[str, Any]) -> dict[str, Any]:
    if route.get("mcp_authority") != MCP_AUTHORITY:
        _deny("Central MCP Gateway is required")
    if route.get("fa3_wrapper") is not True:
        _deny("FA3 Buzz wrapper is required")
    if route.get("direct_buzz_dev_mcp") is not False:
        _deny("raw buzz-dev-mcp direct host-tool route is denied")
    if route.get("workspace_containment") is not True:
        _deny("workspace containment is required")
    if route.get("capability_narrowing") is not True:
        _deny("capability narrowing is required")
    return {"status": "ADMITTED_WRAPPED_ROUTE", **route}


def discover_provider_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("discovery_executed_provider") is not False:
            _deny("provider discovery must not execute candidate")
        path = candidate.get("path")
        digest = candidate.get("sha256")
        if not isinstance(path, str) or not Path(path).is_absolute():
            _deny("provider candidate path must be absolute")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            _deny("provider candidate requires lowercase SHA-256")
        out.append({"path": str(Path(path)), "sha256": digest, "discovery_executed_provider": False})
    return out


def select_staged_candidate(candidates: Iterable[dict[str, Any]], *, selected_path: str, staged_path: str, staged_sha256: str) -> dict[str, Any]:
    discovered = discover_provider_candidates(candidates)
    matches = [c for c in discovered if c["path"] == selected_path]
    if len(matches) != 1:
        _deny("provider shadowing, duplicate, or missing candidate")
    chosen = matches[0]
    if chosen["sha256"] != staged_sha256:
        _deny("staged provider digest differs from discovered identity")
    if not Path(staged_path).is_absolute():
        _deny("staged provider path must be absolute")
    return {"provider_id": PROVIDER_ID, "source_path": selected_path, "staged_path": staged_path, "sha256": staged_sha256, "identity_revalidated": True}


def negotiate_provider(staged: dict[str, Any], info: dict[str, Any], *, requested_capabilities: Iterable[str]) -> dict[str, Any]:
    if staged.get("identity_revalidated") is not True:
        _deny("provider identity must be revalidated before negotiation")
    if info.get("protocol") != WRAPPER_PROTOCOL:
        _deny("provider protocol/version mismatch")
    if info.get("provider_id") != PROVIDER_ID:
        _deny("provider identity mismatch during protocol negotiation")
    if info.get("sha256") != staged.get("sha256"):
        _deny("provider digest changed before negotiation")
    supported = set(info.get("capabilities", []))
    requested = set(requested_capabilities)
    if not requested.issubset(supported):
        _deny("requested capability exceeds negotiated provider surface")
    return {"status": "NEGOTIATED", "protocol": WRAPPER_PROTOCOL, "provider_id": PROVIDER_ID, "sha256": staged["sha256"], "capabilities": sorted(requested)}


def validate_delegated_context(*, actor_id: str, owner_id: str, delegated_caller_context: dict[str, Any], capability_grant: dict[str, Any], authorization_lease: dict[str, Any] | None, requested_capabilities: Iterable[str], owner_attestation: dict[str, Any] | None = None) -> dict[str, Any]:
    if not actor_id or not owner_id or actor_id == owner_id:
        _deny("actor identity must remain distinct from owner/delegated authority")
    if delegated_caller_context.get("actor_id") != actor_id:
        _deny("delegated caller context actor mismatch")
    if delegated_caller_context.get("owner_id") != owner_id:
        _deny("delegated caller context owner mismatch")
    granted = set(capability_grant.get("capabilities", []))
    requested = set(requested_capabilities)
    if not requested.issubset(granted):
        _deny("requested capability exceeds CapabilityGrant")
    if authorization_lease is None:
        if owner_attestation:
            _deny("owner attestation is provenance evidence, not an authorization lease")
        _deny("authorization lease required")
    if authorization_lease.get("issuer") != SECURITY_AUTHORITY:
        _deny("authorization lease must be issued by FA3 Security/Governance")
    if authorization_lease.get("decision") != "ALLOW":
        _deny("authorization lease is not ALLOW")
    lease_caps = set(authorization_lease.get("capabilities", []))
    if not requested.issubset(lease_caps):
        _deny("authorization lease does not cover requested capabilities")
    return {"status": "DELEGATED_CONTEXT_ADMITTED", "actor_id": actor_id, "owner_id": owner_id, "capabilities": sorted(requested), "owner_attestation_present": owner_attestation is not None}


def admit_secret_handle(*, negotiation: dict[str, Any] | None, secret: dict[str, Any], requested_capabilities: Iterable[str]) -> dict[str, Any]:
    if not negotiation or negotiation.get("status") != "NEGOTIATED":
        _deny("protocol negotiation must complete before secret transfer")
    secret_type = secret.get("type")
    if secret_type in {"RAW_PRIVATE_KEY", "NSEC", "RAW_SECRET"}:
        _deny("raw private-key/nsec transfer is forbidden")
    if secret_type != "LEASED_SCOPED_SECRET_HANDLE":
        _deny("leased scoped secret handle required")
    scope = set(secret.get("capabilities", []))
    requested = set(requested_capabilities)
    if not requested.issubset(scope):
        _deny("secret handle scope does not cover requested capability")
    if secret.get("expires_at") in (None, "", 0):
        _deny("secret handle must have bounded lifetime")
    return {"status": "SCOPED_SECRET_HANDLE_ADMITTED", "handle_id": secret.get("handle_id"), "capabilities": sorted(requested), "raw_secret_transferred": False}


def resolve_workspace_target(workspace_root: Path | str, relative_path: str) -> Path:
    root = Path(workspace_root).resolve(strict=True)
    rel = Path(relative_path)
    if rel.is_absolute() or ".." in rel.parts:
        _deny("absolute or traversal path denied")
    candidate = root.joinpath(rel)
    try:
        resolved = candidate.resolve(strict=candidate.exists())
    except (OSError, RuntimeError) as exc:
        _deny(f"workspace path resolution failed: {exc}")
    try:
        common = os.path.commonpath([str(root), str(resolved)])
    except ValueError:
        _deny("workspace path crosses filesystem boundary")
    if common != str(root):
        _deny("workspace/symlink escape denied")
    return resolved


def mutation_proposal(workspace_root: Path | str, relative_path: str, *, old_text: str, new_text: str) -> dict[str, Any]:
    target = resolve_workspace_target(workspace_root, relative_path)
    if not target.is_file():
        _deny("mutation target must be an existing regular file")
    before = target.read_text(encoding="utf-8")
    count = before.count(old_text)
    if count != 1:
        _deny("mutation precondition must match exactly once")
    after = before.replace(old_text, new_text, 1)
    diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=f"a/{relative_path}", tofile=f"b/{relative_path}"))
    if not diff:
        _deny("mutation must produce a non-empty proposed diff")
    return {"relative_path": relative_path, "base_sha256": sha256_bytes(before.encode()), "proposed_sha256": sha256_bytes(after.encode()), "proposed_content": after, "proposed_diff": diff, "proposed_diff_sha256": sha256_bytes(diff.encode()), "applied": False}


def apply_authorized_mutation(workspace_root: Path | str, proposal: dict[str, Any], authorization: dict[str, Any]) -> dict[str, Any]:
    if authorization.get("issuer") != SECURITY_AUTHORITY or authorization.get("decision") != "ALLOW":
        _deny("mutation authorization must be ALLOW from Security/Governance")
    if authorization.get("proposed_diff_sha256") != proposal.get("proposed_diff_sha256"):
        _deny("authorization is not bound to the proposed diff")
    target = resolve_workspace_target(workspace_root, str(proposal["relative_path"]))
    current = target.read_bytes()
    if sha256_bytes(current) != proposal.get("base_sha256"):
        _deny("stale mutation base state denied")
    proposed_content = proposal.get("proposed_content")
    if not isinstance(proposed_content, str):
        _deny("proposed content missing")
    if sha256_bytes(proposed_content.encode()) != proposal.get("proposed_sha256"):
        _deny("proposed content hash mismatch")
    tmp_fd, tmp_name = tempfile.mkstemp(prefix=".fa3-buzz-", dir=str(target.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            handle.write(proposed_content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    post_hash = sha256_bytes(target.read_bytes())
    if post_hash != proposal["proposed_sha256"]:
        _deny("post-state verification failed")
    return {"status": "APPLIED_AND_VERIFIED", "relative_path": proposal["relative_path"], "proposed_diff_sha256": proposal["proposed_diff_sha256"], "post_state_sha256": post_hash, "atomic_replace": True}


def validate_execution_budget(spec: dict[str, Any]) -> dict[str, Any]:
    argv = spec.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        _deny("typed argv list required")
    if spec.get("shell") is not False:
        _deny("shell execution is forbidden")
    command_bytes = sum(len(x.encode()) + 1 for x in argv)
    timeout = spec.get("timeout_seconds")
    output_limit = spec.get("output_limit_bytes")
    if command_bytes > MAX_COMMAND_BYTES:
        _deny("command size exceeds bound")
    if not isinstance(timeout, int) or timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
        _deny("timeout exceeds bound")
    if not isinstance(output_limit, int) or output_limit <= 0 or output_limit > MAX_OUTPUT_BYTES:
        _deny("output limit exceeds bound")
    if spec.get("process_tree_cancellation") is not True:
        _deny("process-tree cancellation required")
    return {"status": "BOUNDED_EXECUTION_ADMITTED", "command_bytes": command_bytes, "timeout_seconds": timeout, "output_limit_bytes": output_limit, "process_tree_cancellation": True}


def sanitize_provider_output(data: str, *, output_limit_bytes: int, secrets: Iterable[str] = ()) -> dict[str, Any]:
    if output_limit_bytes <= 0 or output_limit_bytes > MAX_OUTPUT_BYTES:
        _deny("invalid output bound")
    raw = data.encode("utf-8", errors="replace")
    truncated = len(raw) > output_limit_bytes
    clipped = raw[:output_limit_bytes].decode("utf-8", errors="replace")
    redacted = clipped
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return {"text": redacted, "trusted": False, "truncated": truncated, "validated_size_bytes": len(redacted.encode())}


def derive_tenant_context(*, server_tenant: str, client_tenant: str | None = None) -> dict[str, Any]:
    if not server_tenant:
        _deny("server-derived tenant context required")
    if client_tenant is not None and client_tenant != server_tenant:
        _deny("client tenant override/spoof denied")
    return {"tenant_id": server_tenant, "source": "SERVER_DERIVED", "client_override": False}


def rederive_remote_target_path(*, target_root: Path | str, relative_path: str, host_resolved_path: str | None = None) -> Path:
    if host_resolved_path is not None:
        _deny("host-resolved paths must not cross remote substrate boundary")
    return resolve_workspace_target(target_root, relative_path)


def lifecycle_transition(*, event: str, restart_allowed_by_policy: bool = False) -> dict[str, Any]:
    if event == "INTENTIONAL_STOP":
        return {"state": "STOPPED_FINAL", "restart": False}
    if event == "ABNORMAL_EXIT":
        return {"state": "RESTART_ALLOWED" if restart_allowed_by_policy else "STOPPED_POLICY_REQUIRED", "restart": bool(restart_allowed_by_policy)}
    _deny("unsupported lifecycle event")


def run_ci_wrapper_contract_e2e() -> dict[str, Any]:
    digest = "a" * 64
    candidate = [{"path": "/opt/fa3/staged/buzz-backend-reference", "sha256": digest, "discovery_executed_provider": False}]
    staged = select_staged_candidate(candidate, selected_path=candidate[0]["path"], staged_path="/opt/fa3/staged/buzz-backend-reference", staged_sha256=digest)
    negotiated = negotiate_provider(staged, {"protocol": WRAPPER_PROTOCOL, "provider_id": PROVIDER_ID, "sha256": digest, "capabilities": ["workspace.read", "workspace.propose"]}, requested_capabilities=["workspace.read", "workspace.propose"])
    route = validate_runtime_route({"mcp_authority": MCP_AUTHORITY, "fa3_wrapper": True, "direct_buzz_dev_mcp": False, "workspace_containment": True, "capability_narrowing": True})
    delegated = validate_delegated_context(actor_id="agent:test", owner_id="owner:test", delegated_caller_context={"actor_id": "agent:test", "owner_id": "owner:test"}, capability_grant={"capabilities": ["workspace.read", "workspace.propose"]}, authorization_lease={"issuer": SECURITY_AUTHORITY, "decision": "ALLOW", "capabilities": ["workspace.read", "workspace.propose"]}, requested_capabilities=["workspace.read"], owner_attestation={"kind": "REFERENCE_ONLY"})
    secret = admit_secret_handle(negotiation=negotiated, secret={"type": "LEASED_SCOPED_SECRET_HANDLE", "handle_id": "fixture", "expires_at": "2099-01-01T00:00:00Z", "capabilities": ["workspace.read", "workspace.propose"]}, requested_capabilities=["workspace.read"])
    budget = validate_execution_budget({"argv": ["buzz-backend-reference", "info"], "shell": False, "timeout_seconds": 5, "output_limit_bytes": 4096, "process_tree_cancellation": True})
    return {"schema": "fa3.buzz-runtime-wrapper-ci-e2e.v1", "result": "PASS", "synthetic_provider_fixture": True, "current_host_production_claim": False, "route": route["status"], "negotiation": negotiated["status"], "delegation": delegated["status"], "secret_boundary": secret["status"], "execution": budget["status"], "raw_buzz_dev_mcp_direct_provider": "DENIED"}
