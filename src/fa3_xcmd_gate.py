#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-XCMD-001"
DECISION_ID = "FA3-DEC-XCMD-2026-08-30"
REFERENCE_ID = "FA3-XCMD-UPSTREAM-REFERENCE-2026-08-30"
GATE_ID = "FA3-XCMD-GATESET-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v0.10.1"
REFERENCE_COMMIT = "1594d06582bf024d0a71ee108afe06a98629ec9a"
OBSERVED_X_HEAD = "390fa27a231579f1ee493bcd7961bcba4cb85034"
MANDATORY_CONSTRAINT = (
    "X-CMD SHALL NOT become an FA3 identity, authorization, MCP, model-routing, secrets, "
    "network-egress, host-resource, artifact-trust, workflow, evidence, developer-execution "
    "or host-package-mutation authority."
)
P0_INVARIANTS = [
    "XCMD_REMOTE_NETWORK_TO_SHELL_DIRECT_EXECUTION_FORBIDDEN",
    "XCMD_IMMUTABLE_REFERENCE_IDENTITY_REQUIRED",
    "XCMD_CURATED_PACKAGE_NOT_TRANSITIVE_TRUST",
    "XCMD_AGENT_SHELL_CAPABILITY_MEDIATED",
    "XCMD_PROJECT_AGENT_INSTRUCTIONS_UNTRUSTED_SCOPED_CONTEXT",
    "XCMD_SELF_UPDATE_NOT_PRODUCTION_AUTHORITY",
    "XCMD_GLOBAL_HOST_MUTATION_REQUIRES_EXTERNAL_AUTHORIZATION",
    "XCMD_MODEL_SECRET_EGRESS_MCP_BOUNDARIES_PRESERVED",
    "XCMD_ON_DEMAND_MATERIALIZATION_NOT_BACKGROUND_AUTHORITY",
    "XCMD_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
    "XCMD_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
    "XCMD_EXECUTION_EVIDENCE_ATTRIBUTABLE"
]
EXPECTED_EXTERNAL_BOUNDARIES = {
    "authorization_policy": "FA3-AUTH-SECURITY-GOV-001",
    "tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
    "model_routing": "FA3-AUTH-MODEL-ROUTER-001",
    "host_resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "artifact_trust": "FA3-REG-ARTIFACT-MODEL-001",
    "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    "registry": "FA3-REGISTRY-001",
}
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _iter_strings(item)

def _is_xcmd_value(value: Any) -> bool:
    for raw in _iter_strings(value):
        normalized = raw.upper().replace("_", "-")
        if PROVIDER_ID in raw or normalized in {"X-CMD", "XCMD"} or normalized.startswith("FA3-AUTH-XCMD"):
            return True
    return False

def network_to_shell_allowed(*, downloaded_from_network: bool, materialized: bool,
                             immutable_identity: bool, integrity_verified: bool,
                             provenance_verified: bool, policy_admitted: bool,
                             direct_eval_or_pipe: bool) -> bool:
    if direct_eval_or_pipe:
        return False
    if downloaded_from_network:
        return all((materialized, immutable_identity, integrity_verified, provenance_verified, policy_admitted))
    return policy_admitted

def immutable_reference_valid(*, ref: str, commit_sha: str | None) -> bool:
    if ref in {"X", "main", "master", "latest", "HEAD"}:
        return False
    return bool(commit_sha and FULL_SHA_RE.fullmatch(commit_sha))

def package_trust_valid(*, curated: bool, integrity_verified: bool,
                        provenance_verified: bool, license_admitted: bool,
                        policy_admitted: bool) -> bool:
    del curated
    return all((integrity_verified, provenance_verified, license_admitted, policy_admitted))

def agent_shell_execution_valid(*, caller_identity: str, workspace_id: str,
                                capability_scope: list[str], tool_mediation_authority: str,
                                policy_authority: str, policy_admitted: bool) -> bool:
    return bool(caller_identity and workspace_id and capability_scope
                and tool_mediation_authority == "FA3-AUTH-MCP-GATEWAY-001"
                and policy_authority == "FA3-AUTH-SECURITY-GOV-001"
                and policy_admitted)

def project_context_valid(*, trust_class: str, grants_authority: bool) -> bool:
    return trust_class == "UNTRUSTED_SCOPED_CONTEXT" and grants_authority is False

def self_update_allowed(*, production: bool, explicit_external_authorization: bool,
                        immutable_target: bool, post_change_evidence: bool,
                        floating_upgrade: bool) -> bool:
    if floating_upgrade:
        return False
    if production:
        return all((explicit_external_authorization, immutable_target, post_change_evidence))
    return explicit_external_authorization and immutable_target

def global_host_mutation_allowed(*, global_mutation: bool, external_authorization: bool,
                                 change_evidence: bool) -> bool:
    if not global_mutation:
        return True
    return external_authorization and change_evidence

def boundary_projection_valid(boundaries: dict[str, str]) -> bool:
    if any(_is_xcmd_value(v) for v in boundaries.values()):
        return False
    return all(boundaries.get(k) == v for k, v in EXPECTED_EXTERNAL_BOUNDARIES.items())

def lazy_materialization_valid(*, invocation_admitted: bool, fetch_on_demand: bool,
                               background_prefetch: bool, inactive_provider: bool) -> bool:
    if inactive_provider and background_prefetch:
        return False
    if fetch_on_demand and not invocation_admitted:
        return False
    return True

def disabled_zero_cost(metrics: dict[str, Any]) -> bool:
    numeric_zero = ("resident_process_count", "background_worker_count",
                    "network_session_count", "accelerator_reservation_count")
    if any(int(metrics.get(k, 0)) != 0 for k in numeric_zero):
        return False
    return not bool(metrics.get("active_polling", False) or metrics.get("background_fetch", False))

def provider_shape_valid(provider: dict[str, Any]) -> bool:
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("status") == "ACCEPTED_REFERENCE"
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("normative_constraint") == MANDATORY_CONSTRAINT
        and boundary_projection_valid(provider.get("authority_boundaries", {}))
    )

def execution_evidence_valid(evidence: dict[str, Any]) -> bool:
    required = ("caller_identity", "request_id", "workspace_id", "capability_scope",
                "policy_decision_id", "executable_artifact_id", "result_status")
    return all(bool(evidence.get(k)) for k in required)

def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    canonical = root / "canonical"
    if not canonical.exists():
        return {"result": "FAIL", "scanned_json_files": 0,
                "findings": [_finding("XCMD-AUTH-000", "canonical directory is missing")]}
    authority_key_markers = ("authority", "authoritative", "owner", "router", "gateway", "broker", "trust_owner")
    for path in sorted(canonical.rglob("*.json")):
        scanned += 1
        try:
            data = _load(path)
        except Exception as exc:
            findings.append(_finding("XCMD-AUTH-001", "Canonical JSON parse failure during X-CMD scan",
                                     file=str(path.relative_to(root)), error=str(exc)))
            continue
        def walk(value: Any, p: str = "$") -> None:
            if isinstance(value, dict):
                xcmd_scoped = any(_is_xcmd_value(value.get(k)) for k in ("id", "provider_id", "subject", "provider") if k in value)
                for key, item in value.items():
                    kp = f"{p}.{key}"
                    normalized = key.lower().replace("-", "_")
                    if key == "authority_boundaries" and isinstance(item, dict):
                        for domain, owner in item.items():
                            if _is_xcmd_value(owner):
                                findings.append(_finding("XCMD-AUTH-002", "X-CMD assigned as authority boundary owner",
                                                         file=str(path.relative_to(root)), path=f"{kp}.{domain}", domain=domain, value=owner))
                    if xcmd_scoped and key == "architectural_authority" and item is True:
                        findings.append(_finding("XCMD-AUTH-003", "X-CMD architectural_authority enabled",
                                                 file=str(path.relative_to(root)), path=kp))
                    if any(m in normalized for m in authority_key_markers) and _is_xcmd_value(item):
                        findings.append(_finding("XCMD-AUTH-004", "X-CMD assigned to authority-bearing field",
                                                 file=str(path.relative_to(root)), path=kp, value=item))
                    walk(item, kp)
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    walk(item, f"{p}[{idx}]")
        walk(data)
    unique = []
    seen = set()
    for f in findings:
        key = (f.get("code"), f.get("file"), f.get("path"), json.dumps(f.get("value"), sort_keys=True, default=str))
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return {"result": "PASS" if not unique else "FAIL", "scanned_json_files": scanned, "findings": unique}

def reference_check(root: Path) -> dict[str, Any]:
    findings = []
    provider_path = root / "canonical/providers/FA3-PROVIDER-XCMD-001.json"
    decision_path = root / "canonical/decisions/FA3-DEC-XCMD-2026-08-30.json"
    reference_path = root / "canonical/references/FA3-XCMD-UPSTREAM-REFERENCE-2026-08-30.json"
    enforcement_path = root / "canonical/xcmd-enforcement.json"
    policy_path = root / "canonical/enforcement-policy.json"
    for path, code in ((provider_path,"XCMD-REF-001"),(decision_path,"XCMD-REF-002"),
                       (reference_path,"XCMD-REF-003"),(enforcement_path,"XCMD-REF-004"),
                       (policy_path,"XCMD-REF-005")):
        if not path.exists():
            findings.append(_finding(code, f"Missing required X-CMD canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result":"FAIL","findings":findings}
    provider, decision, reference, enforcement, policy = map(_load,
        (provider_path,decision_path,reference_path,enforcement_path,policy_path))
    if not provider_shape_valid(provider):
        findings.append(_finding("XCMD-REF-006","X-CMD provider authority/capability/boundary invariant drift"))
    required_classes = {"OPTIONAL_PROVIDER","TERMINAL_TOOLCHAIN_PROVIDER","AGENT_SHELL_INTEGRATION_PROVIDER",
                        "ON_DEMAND_CLI_PROVISIONING_PROVIDER","ARCHITECTURAL_PATTERN_SOURCE"}
    if not required_classes.issubset(set(provider.get("classification",[]))):
        findings.append(_finding("XCMD-REF-007","X-CMD provider classification drift"))
    if not (decision.get("id")==DECISION_ID and decision.get("status")=="CANONICAL_CLOSED"
            and decision.get("provider_id")==PROVIDER_ID and decision.get("gate_id")==GATE_ID
            and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0
            and decision.get("capability_count_after")==CAPABILITY_COUNT
            and decision.get("mandatory_constraint")==MANDATORY_CONSTRAINT):
        findings.append(_finding("XCMD-REF-008","X-CMD canonical decision invariant drift"))
    disp = reference.get("fa3_disposition",{})
    if not (reference.get("id")==REFERENCE_ID and reference.get("provider_id")==PROVIDER_ID
            and reference.get("repository")=="x-cmd/x-cmd" and reference.get("default_branch")=="X"
            and reference.get("observed_default_branch_head")==OBSERVED_X_HEAD
            and reference.get("immutable_reference_release")==REFERENCE_RELEASE
            and reference.get("immutable_reference_commit")==REFERENCE_COMMIT
            and FULL_SHA_RE.fullmatch(reference.get("immutable_reference_commit",""))
            and disp.get("floating_x_allowed_as_promotion_evidence") is False
            and disp.get("curation_implies_transitive_trust") is False
            and disp.get("direct_remote_eval_allowed_in_canonical_provisioning") is False
            and disp.get("upstream_self_upgrade_allowed_as_production_authority") is False):
        findings.append(_finding("XCMD-REF-009","X-CMD upstream reference pin/security disposition drift"))
    if not (enforcement.get("gate_id")==GATE_ID and enforcement.get("provider_id")==PROVIDER_ID
            and enforcement.get("fail_closed") is True
            and enforcement.get("runtime_provider_required_for_global_promotion") is False
            and enforcement.get("floating_x_allowed_as_promotion_evidence") is False
            and enforcement.get("mandatory_rule_count")==len(P0_INVARIANTS)
            and enforcement.get("p0_invariants")==P0_INVARIANTS
            and enforcement.get("regression_case_count")==12):
        findings.append(_finding("XCMD-REF-010","X-CMD fail-closed enforcement record drift"))
    if GATE_ID not in policy.get("mandatory_reference_gates",[]):
        findings.append(_finding("XCMD-REF-011","X-CMD gate is not bound into mandatory_reference_gates"))
    if policy.get("xcmd_provider_id") != PROVIDER_ID:
        findings.append(_finding("XCMD-REF-012","Global enforcement policy X-CMD provider identity drift"))
    if policy.get("xcmd_mandatory_p0_rules") != P0_INVARIANTS:
        findings.append(_finding("XCMD-REF-013","Global enforcement policy X-CMD P0 invariant drift"))
    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def run_regressions() -> dict[str, Any]:
    cases = []
    def add(rule_id,name,positive,negative):
        cases.append({"rule_id":rule_id,"name":name,"status":"PASS" if positive and negative else "FAIL",
                      "positive_case":positive,"negative_case":negative})
    add("FA3-XCMD-P0-001","remote network-to-shell direct execution denial",
        network_to_shell_allowed(downloaded_from_network=True,materialized=True,immutable_identity=True,
                                 integrity_verified=True,provenance_verified=True,policy_admitted=True,direct_eval_or_pipe=False),
        not network_to_shell_allowed(downloaded_from_network=True,materialized=False,immutable_identity=False,
                                     integrity_verified=False,provenance_verified=False,policy_admitted=False,direct_eval_or_pipe=True))
    add("FA3-XCMD-P0-002","floating X reference denial",
        immutable_reference_valid(ref=REFERENCE_RELEASE,commit_sha=REFERENCE_COMMIT),
        not immutable_reference_valid(ref="X",commit_sha=None))
    add("FA3-XCMD-P0-003","curation is not transitive trust",
        package_trust_valid(curated=True,integrity_verified=True,provenance_verified=True,license_admitted=True,policy_admitted=True),
        not package_trust_valid(curated=True,integrity_verified=False,provenance_verified=False,license_admitted=False,policy_admitted=False))
    add("FA3-XCMD-P0-004","agent shell requires caller/workspace/capability mediation",
        agent_shell_execution_valid(caller_identity="agent:A",workspace_id="ws:1",capability_scope=["tool.jq"],
                                    tool_mediation_authority="FA3-AUTH-MCP-GATEWAY-001",
                                    policy_authority="FA3-AUTH-SECURITY-GOV-001",policy_admitted=True),
        not agent_shell_execution_valid(caller_identity="agent:A",workspace_id="",capability_scope=["shell.*"],
                                        tool_mediation_authority="XCMD",policy_authority="XCMD",policy_admitted=True))
    add("FA3-XCMD-P0-005","project instruction authority escalation denial",
        project_context_valid(trust_class="UNTRUSTED_SCOPED_CONTEXT",grants_authority=False),
        not project_context_valid(trust_class="TRUSTED_POLICY",grants_authority=True))
    add("FA3-XCMD-P0-006","unattended floating self-update denial",
        self_update_allowed(production=True,explicit_external_authorization=True,immutable_target=True,post_change_evidence=True,floating_upgrade=False),
        not self_update_allowed(production=True,explicit_external_authorization=False,immutable_target=False,post_change_evidence=False,floating_upgrade=True))
    add("FA3-XCMD-P0-007","global host mutation authorization denial",
        global_host_mutation_allowed(global_mutation=True,external_authorization=True,change_evidence=True),
        not global_host_mutation_allowed(global_mutation=True,external_authorization=False,change_evidence=False))
    good_boundaries = dict(EXPECTED_EXTERNAL_BOUNDARIES)
    bad_boundaries = dict(good_boundaries); bad_boundaries["model_routing"] = PROVIDER_ID
    add("FA3-XCMD-P0-008","cross-cutting authority bypass denial",
        boundary_projection_valid(good_boundaries), not boundary_projection_valid(bad_boundaries))
    add("FA3-XCMD-P0-009","inactive background prefetch denial",
        lazy_materialization_valid(invocation_admitted=True,fetch_on_demand=True,background_prefetch=False,inactive_provider=False),
        not lazy_materialization_valid(invocation_admitted=False,fetch_on_demand=True,background_prefetch=True,inactive_provider=True))
    zero={"resident_process_count":0,"background_worker_count":0,"network_session_count":0,
          "accelerator_reservation_count":0,"active_polling":False,"background_fetch":False}
    add("FA3-XCMD-P0-010","disabled provider runtime-cost denial",
        disabled_zero_cost(zero), not disabled_zero_cost({**zero,"resident_process_count":1}))
    good_provider={"id":PROVIDER_ID,"status":"ACCEPTED_REFERENCE","canonical_root":False,
                   "architectural_authority":False,"new_capability":False,"capability_count":CAPABILITY_COUNT,
                   "activation_mode":"OPTIONAL_DISABLED_BY_DEFAULT","global_runtime_promotion_required_when_disabled":False,
                   "normative_constraint":MANDATORY_CONSTRAINT,"authority_boundaries":good_boundaries}
    add("FA3-XCMD-P0-011","provider authority/capability drift denial",
        provider_shape_valid(good_provider), not provider_shape_valid({**good_provider,"architectural_authority":True,"capability_count":144}))
    good_evidence={"caller_identity":"agent:A","request_id":"req:1","workspace_id":"ws:1","capability_scope":["tool.jq"],
                   "policy_decision_id":"pol:1","executable_artifact_id":"sha256:abc","result_status":"PASS"}
    bad_evidence={k:v for k,v in good_evidence.items() if k!="executable_artifact_id"}
    add("FA3-XCMD-P0-012","execution evidence attribution denial",
        execution_evidence_valid(good_evidence), not execution_evidence_valid(bad_evidence))
    passed=sum(c["status"]=="PASS" for c in cases)
    return {"schema":"fa3.xcmd-regression-report.v1","result":"PASS" if passed==len(cases) else "FAIL",
            "passed":passed,"total":len(cases),"cases":cases}

def gate(root: Path) -> dict[str, Any]:
    reference=reference_check(root)
    authority_scan=scan_canonical_authority_assignments(root)
    regressions=run_regressions()
    ok=all(x["result"]=="PASS" for x in (reference,authority_scan,regressions))
    report={"schema":"fa3.xcmd-gate-report.v1","gate_id":GATE_ID,"provider_id":PROVIDER_ID,
            "capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL",
            "mode":"CANONICAL_SECURITY_BOUNDARY_AND_EXECUTABLE_REGRESSIONS","reference":reference,
            "authority_scan":authority_scan,"regressions":regressions,"runtime_provider_required":False,
            "promotion_effect":"MANDATORY_CANONICAL_RULES_PROVIDER_RUNTIME_OPTIONAL"}
    _write(root/"reports/xcmd-gate-report.json",report)
    return report

def main() -> int:
    ap=argparse.ArgumentParser(description="FA3 X-CMD fail-closed security/boundary regression gate")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=ap.parse_args()
    result=gate(Path(args.root).resolve())
    print(json.dumps(result,indent=2))
    return 0 if result["result"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
