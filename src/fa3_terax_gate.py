#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import ipaddress
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-TERAX-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v0.8.6"
REFERENCE_COMMIT = "1fdbc50e53b3ac53db3ba80057805a2d54258545"
REFERENCE_TAG_OBJECT = "0165b39c2e52760316aa3202b6acf0f25fad0551"
LOCAL_CONTROL_REFERENCE_COMMIT = "e9b489c5d50cb9e654fc9a61f901c0eb9f341be3"
LOCAL_CONTROL_BLOB = "2c997c54be458e146cb35bbfb93351cb04853bcb"

P0_INVARIANTS = [
    "READ_BEFORE_EDIT",
    "DIFF_BEFORE_APPLY",
    "TYPED_AUTHENTICATED_LOCAL_CONTROL",
    "SECURITY_INVARIANT_EXECUTABLE_EVIDENCE",
    "DISABLED_CAPABILITY_ZERO_RUNTIME_COST",
]

RULES = [
    (1, "boundary-first host access"),
    (2, "explicit workspace authorization"),
    (3, "capability-scoped tool execution"),
    (4, "mutations require authorization/approval"),
    (5, "read-before-edit"),
    (6, "diff-before-apply"),
    (7, "canonical-path/symlink revalidation"),
    (8, "SSRF + DNS-rebinding resistant egress"),
    (9, "provider-neutral model projection"),
    (10, "project instruction manifests are untrusted scoped context"),
    (11, "subagent capability narrowing"),
    (12, "bounded agent execution"),
    (13, "typed authenticated local-control contracts"),
    (14, "explicit delegated caller context"),
    (15, "security invariant -> executable regression evidence"),
    (16, "unsupported/unverified path -> fail closed"),
    (17, "disabled capability -> effectively zero runtime resource cost"),
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _contains(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def boundary_first_allowed(*, native_boundary: bool, authorized: bool) -> bool:
    return bool(native_boundary and authorized)


def workspace_authorized(root: Path, candidate: Path) -> bool:
    return _contains(root, candidate)


def capability_scoped(granted: set[str], requested: set[str]) -> bool:
    return requested.issubset(granted)


def mutation_authorized(decision: str, approval_present: bool) -> bool:
    decision = decision.upper()
    if decision == "DENY":
        return False
    if decision == "ASK_HUMAN":
        return bool(approval_present)
    return decision == "ALLOW"


def read_before_edit(*, read_seen: bool, read_version: str | None, current_version: str | None) -> bool:
    return bool(read_seen and read_version and current_version and read_version == current_version)


def diff_before_apply(*, proposal: bool, diff: bool, approved: bool, governed_mutation: bool = True) -> bool:
    if not governed_mutation:
        return bool(proposal)
    return bool(proposal and diff and approved)


def egress_allowed(addresses: list[str], *, explicit_local_authorization: bool = False, pinned_addresses: list[str] | None = None) -> bool:
    if not addresses:
        return False
    parsed = []
    for raw in addresses:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            return False
        if ip.is_unspecified or ip.is_multicast or ip.is_link_local:
            return False
        if str(ip) in {"169.254.169.254", "fd00:ec2::254"}:
            return False
        if (ip.is_private or ip.is_loopback) and not explicit_local_authorization:
            return False
        parsed.append(str(ip))
    if pinned_addresses is not None and sorted(parsed) != sorted(pinned_addresses):
        return False
    return True


def provider_projection_valid(routing_authority: str) -> bool:
    return routing_authority == "FA3-AUTH-MODEL-ROUTER-001"


def project_instruction_valid(trust: str, can_override_policy: bool) -> bool:
    return trust == "UNTRUSTED_SCOPED_PROJECT_CONTEXT" and not can_override_policy


def subagent_narrowed(parent: set[str], child: set[str]) -> bool:
    return child.issubset(parent)


def execution_budget_valid(budget: dict[str, int]) -> bool:
    required = ("max_steps", "max_tool_calls", "max_wall_time", "max_processes")
    return all(isinstance(budget.get(k), int) and budget[k] > 0 for k in required)


def local_control_valid(request: dict[str, Any], *, expected_token: str, granted: set[str]) -> bool:
    required = {
        "protocol_version", "request_id", "caller_identity", "caller_context",
        "method", "parameters", "capability_scope", "authorization_token", "target", "deadline_ms",
    }
    if not required.issubset(request):
        return False
    if request["protocol_version"] != 1 or request["authorization_token"] != expected_token:
        return False
    if not request["request_id"] or not request["caller_identity"] or not request["target"]:
        return False
    if not isinstance(request["deadline_ms"], int) or request["deadline_ms"] <= 0:
        return False
    caps = request["capability_scope"]
    if not isinstance(caps, list) or not set(caps).issubset(granted):
        return False
    encoded = json.dumps(request, separators=(",", ":")).encode("utf-8")
    return len(encoded) <= 65536


def delegation_valid(context: dict[str, Any], now_epoch: int) -> bool:
    required = {
        "caller_identity", "parent_execution_id", "workspace_id", "allowed_capabilities",
        "expires_at_epoch", "policy_ref", "evidence_chain",
    }
    return required.issubset(context) and isinstance(context["expires_at_epoch"], int) and context["expires_at_epoch"] > now_epoch


def invariant_evidence_valid(evidence: list[dict[str, Any]]) -> bool:
    return bool(evidence) and all(x.get("executable") is True and x.get("status") == "PASS" for x in evidence)


def unsupported_disposition(state: str) -> str:
    if state.upper() in {"UNKNOWN", "UNSUPPORTED", "UNVERIFIED", "AMBIGUOUS_TARGET", "INVALID_CONTEXT", "MISSING_AUTHORIZATION"}:
        return "DENY"
    return "ALLOW"


def disabled_zero_cost(metrics: dict[str, Any]) -> bool:
    numeric_zero = (
        "resident_process_count", "worker_thread_count", "ram_resident_bytes",
        "gpu_memory_bytes", "network_session_count", "accelerator_reservation_count",
    )
    if any(metrics.get(k) != 0 for k in numeric_zero):
        return False
    return metrics.get("active_polling") is False and metrics.get("background_inference") is False


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    policy_path = root / "canonical/terax-enforcement.json"
    provider_path = root / "canonical/providers/FA3-PROVIDER-TERAX-001.json"
    evidence_path = root / "evidence/reference/terax-v0.8.6.json"
    for path, code in ((policy_path, "TERAX-REF-001"), (provider_path, "TERAX-REF-002"), (evidence_path, "TERAX-REF-003")):
        if not path.exists():
            findings.append(_finding(code, f"Missing required Terax canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    policy, provider, evidence = _load(policy_path), _load(provider_path), _load(evidence_path)
    if policy.get("provider_id") != PROVIDER_ID or policy.get("mandatory_rule_count") != 17:
        findings.append(_finding("TERAX-REF-004", "Terax enforcement rule/provider invariant mismatch"))
    if policy.get("p0_invariants") != P0_INVARIANTS:
        findings.append(_finding("TERAX-REF-005", "Terax P0 invariant set drift"))
    if policy.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("TERAX-REF-006", "Floating main was enabled as Terax promotion evidence"))
    if provider.get("id") != PROVIDER_ID or provider.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("TERAX-REF-007", "Terax provider identity/capability-count invariant mismatch"))
    if any(provider.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability")):
        findings.append(_finding("TERAX-REF-008", "Terax provider was promoted to forbidden authority/root/capability"))
    stable = evidence.get("stable_reference", {})
    if stable.get("release") != REFERENCE_RELEASE or stable.get("commit_sha") != REFERENCE_COMMIT or stable.get("tag_object_sha") != REFERENCE_TAG_OBJECT:
        findings.append(_finding("TERAX-REF-009", "Stable Terax immutable reference drift"))
    lc = evidence.get("local_control_reference", {})
    if lc.get("commit_sha") != LOCAL_CONTROL_REFERENCE_COMMIT or lc.get("blob_sha") != LOCAL_CONTROL_BLOB:
        findings.append(_finding("TERAX-REF-010", "Terax local-control immutable reference drift"))
    if evidence.get("floating_main_allowed") is not False:
        findings.append(_finding("TERAX-REF-011", "Terax evidence permits floating main"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(rule_id: int, passed: bool, negative_passed: bool, detail: str) -> None:
        name = dict(RULES)[rule_id]
        cases.append({"rule_id": rule_id, "name": name, "status": "PASS" if passed and negative_passed else "FAIL", "positive_case": passed, "negative_case": negative_passed, "detail": detail})

    add(1, boundary_first_allowed(native_boundary=True, authorized=True), not boundary_first_allowed(native_boundary=False, authorized=True), "native boundary is mandatory")

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        workspace = base / "workspace"; workspace.mkdir()
        inside = workspace / "a.txt"; inside.write_text("x")
        outside = base / "outside"; outside.mkdir(); secret = outside / "secret"; secret.write_text("x")
        link = workspace / "link"; link.symlink_to(secret)
        add(2, workspace_authorized(workspace, inside), not workspace_authorized(workspace, outside / "x"), "workspace root is explicit")
        add(7, workspace_authorized(workspace, inside), not workspace_authorized(workspace, link), "resolved symlink cannot escape workspace")

    add(3, capability_scoped({"read", "edit"}, {"read"}), not capability_scoped({"read"}, {"read", "shell"}), "requested capabilities must be subset of grant")
    add(4, mutation_authorized("ASK_HUMAN", True), not mutation_authorized("ASK_HUMAN", False), "ASK_HUMAN cannot silently become ALLOW")
    add(5, read_before_edit(read_seen=True, read_version="v1", current_version="v1"), not read_before_edit(read_seen=True, read_version="v1", current_version="v2"), "stale read is rejected")
    add(6, diff_before_apply(proposal=True, diff=True, approved=True), not diff_before_apply(proposal=True, diff=False, approved=True), "governed direct write is rejected")
    add(8, egress_allowed(["8.8.8.8"], pinned_addresses=["8.8.8.8"]), not egress_allowed(["169.254.169.254"], pinned_addresses=["169.254.169.254"]), "metadata/unsafe resolution is fail-closed")
    add(9, provider_projection_valid("FA3-AUTH-MODEL-ROUTER-001"), not provider_projection_valid("TERAX"), "Terax cannot become model-routing authority")
    add(10, project_instruction_valid("UNTRUSTED_SCOPED_PROJECT_CONTEXT", False), not project_instruction_valid("TRUSTED_POLICY", True), "project instructions cannot override policy")
    add(11, subagent_narrowed({"read", "grep"}, {"read"}), not subagent_narrowed({"read"}, {"read", "shell"}), "child capability set cannot widen")
    budget = {"max_steps": 20, "max_tool_calls": 40, "max_wall_time": 300, "max_processes": 4}
    add(12, execution_budget_valid(budget), not execution_budget_valid({"max_steps": 0, "max_tool_calls": 1, "max_wall_time": 1, "max_processes": 1}), "agent execution is bounded")
    req = {"protocol_version":1,"request_id":"r1","caller_identity":"agent","caller_context":{"workspace":"w1"},"method":"open","parameters":{},"capability_scope":["ui.open"],"authorization_token":"token","target":"pane-1","deadline_ms":1000}
    add(13, local_control_valid(req, expected_token="token", granted={"ui.open"}), not local_control_valid({**req, "authorization_token":"bad"}, expected_token="token", granted={"ui.open"}), "local control is typed, bounded and authenticated")
    now = 1_800_000_000
    ctx = {"caller_identity":"a","parent_execution_id":"p","workspace_id":"w","allowed_capabilities":["read"],"expires_at_epoch":now+10,"policy_ref":"POL-1","evidence_chain":["E1"]}
    add(14, delegation_valid(ctx, now), not delegation_valid({**ctx,"expires_at_epoch":now-1}, now), "delegation context expires and is explicit")
    ev = [{"id":"T1","executable":True,"status":"PASS"}]
    add(15, invariant_evidence_valid(ev), not invariant_evidence_valid([{"id":"T1","executable":False,"status":"PASS"}]), "documentation-only evidence is rejected")
    add(16, unsupported_disposition("SUPPORTED") == "ALLOW", unsupported_disposition("UNVERIFIED") == "DENY", "unsupported/unverified states fail closed")
    zero = {"resident_process_count":0,"worker_thread_count":0,"ram_resident_bytes":0,"gpu_memory_bytes":0,"network_session_count":0,"accelerator_reservation_count":0,"active_polling":False,"background_inference":False}
    add(17, disabled_zero_cost(zero), not disabled_zero_cost({**zero,"resident_process_count":1}), "disabled provider has effectively zero runtime cost")

    passed = sum(x["status"] == "PASS" for x in cases)
    return {"schema":"fa3.terax-regression-report.v1","result":"PASS" if passed == 17 else "FAIL","passed":passed,"total":17,"cases":cases}


def current_host_check(root: Path) -> dict[str, Any]:
    p = root / "evidence/receipts/terax-current-host.json"
    if not p.exists():
        return {"result":"FAIL","findings":[_finding("TERAX-HOST-001","Missing current-host Terax receipt")],"receipt":None}
    try:
        receipt = _load(p)
    except Exception as exc:
        return {"result":"FAIL","findings":[_finding("TERAX-HOST-002",f"Unreadable current-host Terax receipt: {exc}")],"receipt":None}
    findings: list[dict[str, Any]] = []
    if receipt.get("schema") != "fa3.terax-current-host.v1" or receipt.get("provider_id") != PROVIDER_ID:
        findings.append(_finding("TERAX-HOST-003","Current-host receipt schema/provider mismatch"))
    if receipt.get("host_scope") != "CURRENT_HOST" or receipt.get("provider_state") != "DISABLED_REFERENCE_ONLY":
        findings.append(_finding("TERAX-HOST-004","Terax current-host receipt is not explicit disabled-reference current-host evidence"))
    if receipt.get("status") != "PASS":
        findings.append(_finding("TERAX-HOST-005","Terax current-host receipt is not PASS",status=receipt.get("status")))
    metrics = receipt.get("metrics", {})
    if not disabled_zero_cost(metrics):
        findings.append(_finding("TERAX-HOST-006","Disabled Terax provider consumed runtime resources",metrics=metrics))
    if receipt.get("gpu_telemetry") != "AVAILABLE":
        findings.append(_finding("TERAX-HOST-007","GPU telemetry unavailable; zero-VRAM claim cannot be current-host PASS"))
    expires_at = receipt.get("expires_at")
    try:
        if not expires_at or datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            findings.append(_finding("TERAX-HOST-008","Terax current-host receipt expired or has no expiry"))
    except ValueError:
        findings.append(_finding("TERAX-HOST-009","Invalid Terax current-host receipt expiry"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings,"receipt":receipt}


def gate(root: Path, *, require_current_host: bool = True) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    host = current_host_check(root) if require_current_host else {"result":"NOT_REQUIRED_IN_CI","findings":[],"receipt":None}
    ok = reference["result"] == "PASS" and regressions["result"] == "PASS" and (not require_current_host or host["result"] == "PASS")
    report = {
        "schema":"fa3.terax-gate-report.v1",
        "provider_id":PROVIDER_ID,
        "capability_count":CAPABILITY_COUNT,
        "result":"PASS" if ok else "FAIL",
        "mode":"CURRENT_HOST" if require_current_host else "CI_REFERENCE_ONLY",
        "reference":reference,
        "regressions":regressions,
        "current_host":host,
        "promotion_effect":"REQUIRED_PASS" if require_current_host else "CI_REFERENCE_EVIDENCE_ONLY",
    }
    _write(root / "reports/terax-gate-report.json", report)
    return report


def canonical_digest(root: Path) -> str:
    h = hashlib.sha256()
    for rel in [
        "canonical/terax-enforcement.json",
        "canonical/providers/FA3-PROVIDER-TERAX-001.json",
        "evidence/reference/terax-v0.8.6.json",
    ]:
        h.update((root / rel).read_bytes())
    return h.hexdigest()
