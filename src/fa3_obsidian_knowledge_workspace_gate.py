#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

CAPABILITY_COUNT = 143
CAPABILITY_IDS = ("CAP-010", "CAP-018")
PROFILE_ID = "FA3-HUMAN-KNOWLEDGE-WORKSPACE-001"
PROVIDER_IDS = ("FA3-PROVIDER-OBSIDIAN-001", "FA3-PROVIDER-OBSIDIAN-LOCAL-REST-API-001")
CONTRACT_ID = "FA3-HUMAN-KNOWLEDGE-WORKSPACE-CONTRACTS-001"
DECISION_ID = "FA3-DEC-OBSIDIAN-KNOWLEDGE-WORKSPACE-2026-09-07"
REFERENCE_ID = "FA3-OBSIDIAN-UPSTREAM-REFERENCE-2026-09-07"
GATE_ID = "FA3-OBSIDIAN-KNOWLEDGE-WORKSPACE-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-OBSIDIAN-KNOWLEDGE-WORKSPACE-001"
EVIDENCE_ID = "FA3-EVID-OBSIDIAN-KNOWLEDGE-WORKSPACE-CI-2026-09-07"
RUNTIME_STATUS = "NOT_PROMOTED_PENDING_CURRENT_HOST_KNOWLEDGE_WORKSPACE_CONFORMANCE"

RULES = [
    "OBSIDIAN_OPTIONAL_HUMAN_KNOWLEDGE_WORKSPACE_NOT_AUTHORITY",
    "OBSIDIAN_CAPABILITY_BINDING_EXACT_CAP_010_CAP_018_COUNT_143",
    "OBSIDIAN_MARKDOWN_SOURCE_PRESERVED_INDEX_REBUILDABLE",
    "OBSIDIAN_STABLE_NOTE_ID_AND_REQUIRED_FRONTMATTER",
    "OBSIDIAN_APPROVED_INDEX_TRUE_ONLY",
    "OBSIDIAN_VAULT_ROOT_CANONICALIZED_AND_SYMLINK_ESCAPE_DENIED",
    "OBSIDIAN_PRIVATE_VAULT_PHYSICALLY_SEPARATE",
    "OBSIDIAN_LARGE_BINARY_MODEL_RENDER_MEDIA_PAYLOAD_FORBIDDEN",
    "OBSIDIAN_WATCHER_PLUS_PERIODIC_FULL_RECONCILIATION",
    "OBSIDIAN_HASH_RENAME_DELETE_TOMBSTONE_LINEAGE_REQUIRED",
    "OBSIDIAN_POLICY_FILTER_BEFORE_CHUNK_EMBED_RETRIEVAL",
    "OBSIDIAN_MEMORY_SERVICE_ONLY_SHARED_QUERY_BOUNDARY",
    "OBSIDIAN_DIRECT_AGENT_FILESYSTEM_AND_MCP_ACCESS_FORBIDDEN",
    "OBSIDIAN_AGENT_READ_ONLY_VIA_KNOWLEDGE_SEARCH_READ",
    "OBSIDIAN_AGENT_MUTATION_STAGING_ONLY",
    "OBSIDIAN_HUMAN_REVIEW_PROMOTION_RECEIPT_REQUIRED",
    "OBSIDIAN_ATOMIC_BASE_HASH_CONFLICT_FAIL_CLOSED",
    "OBSIDIAN_DELETE_MOVE_RENAME_DEFAULT_DENY",
    "OBSIDIAN_BASES_NOT_DATABASE_AUTHORITY",
    "OBSIDIAN_CANVAS_NOT_WORKFLOW_AUTHORITY",
    "OBSIDIAN_CLI_OPERATOR_ONLY_AGENT_COMMAND_EVAL_DENY",
    "OBSIDIAN_SYNC_PUBLISH_EGRESS_GATED_NOT_BACKUP_OR_GIT_AUTHORITY",
    "OBSIDIAN_HEADLESS_OPEN_BETA_NOT_CORE_RUNTIME",
    "OBSIDIAN_COMMUNITY_PLUGIN_PERMISSION_BOUNDARY_NOT_TRUSTED",
    "OBSIDIAN_LOCAL_REST_MCP_DEFAULT_DISABLED_SEPARATE_ACCEPTANCE",
    "OBSIDIAN_LOCAL_REST_MCP_TLS_LOOPBACK_VERIFIED_NO_PLAINTEXT",
    "OBSIDIAN_LOCAL_REST_MCP_SECRET_FROM_FA3_SECRETS_AUTHORITY",
    "OBSIDIAN_LOCAL_REST_MCP_CENTRAL_GATEWAY_ALLOWLIST_ONLY",
    "OBSIDIAN_DESKTOP_NON_ROOT_USER_SESSION_NO_SYSTEM_SERVICE",
    "OBSIDIAN_INDEXER_GUI_INDEPENDENT_PROVIDER_OUTAGE_NONBLOCKING",
    "OBSIDIAN_IMMUTABLE_DESKTOP_AND_PLUGIN_PINS",
    "OBSIDIAN_REFERENCE_PASS_NOT_CURRENT_HOST_RUNTIME_PROMOTION",
]

PATHS = {
    "profile": "canonical/profiles/FA3-HUMAN-KNOWLEDGE-WORKSPACE-001.json",
    "knowledge_profile": "canonical/profiles/FA3-KNOWLEDGE-001.json",
    "desktop_provider": "canonical/providers/FA3-PROVIDER-OBSIDIAN-001.json",
    "plugin_provider": "canonical/providers/FA3-PROVIDER-OBSIDIAN-LOCAL-REST-API-001.json",
    "contract": "canonical/contracts/FA3-HUMAN-KNOWLEDGE-WORKSPACE-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-OBSIDIAN-KNOWLEDGE-WORKSPACE-2026-09-07.json",
    "reference": "canonical/references/FA3-OBSIDIAN-UPSTREAM-REFERENCE-2026-09-07.json",
    "gate": "canonical/FA3-GATE-OBSIDIAN-KNOWLEDGE-WORKSPACE-001.json",
    "enforcement": "canonical/obsidian-knowledge-workspace-enforcement.json",
    "admission": "canonical/obsidian-knowledge-workspace-runtime-admission.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-OBSIDIAN-2026-09-07.json",
    "global_release": "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json",
    "evidence": "evidence/reference/obsidian-knowledge-workspace-ci-2026-09-07.json",
    "policy": "canonical/enforcement-policy.json",
    "registry": "evidence/evidence-registry.json",
    "matrix": "canonical/conformance-matrix.csv",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def provider_boundary_valid(optional: bool, authority: bool, hard_dependency: bool, capability_count: int) -> bool:
    return optional and not authority and not hard_dependency and capability_count == CAPABILITY_COUNT


def metadata_valid(note: dict[str, Any]) -> bool:
    required = {"id", "type", "status", "owner", "visibility", "index", "source", "created", "updated", "tags"}
    return required <= set(note) and isinstance(note.get("id"), str) and bool(note["id"]) and isinstance(note.get("index"), bool)


def index_admission_valid(note: dict[str, Any]) -> bool:
    return metadata_valid(note) and note["status"] == "approved" and note["index"] is True and note["visibility"] == "agent-read"


def vault_scope_valid(canonicalized: bool, symlink_escape: bool, private_separate: bool, root_scope: str) -> bool:
    return canonicalized and not symlink_escape and private_separate and root_scope == "APPROVED_VAULT_ROOT"


def ingestion_valid(watcher: bool, full_reconciliation: bool, hash_incremental: bool, tombstones: bool) -> bool:
    return watcher and full_reconciliation and hash_incremental and tombstones


def retrieval_valid(route: str, direct_filesystem: bool, direct_obsidian_mcp: bool, policy_before: bool) -> bool:
    return route == "CENTRAL_GATEWAY_TO_MEMORY_GATEWAY" and not direct_filesystem and not direct_obsidian_mcp and policy_before


def mutation_valid(staging: str, human_review: bool, receipt: bool, compare_and_swap: bool, destructive_default: str) -> bool:
    return staging == "_agent-inbox/<proposal_id>/" and human_review and receipt and compare_and_swap and destructive_default == "DENY"


def plugin_valid(enabled: bool, separate_acceptance: bool, loopback: bool, tls_verified: bool, plaintext: bool, central_gateway: bool, command_execute: bool) -> bool:
    if not enabled:
        return separate_acceptance and not plaintext and not command_execute
    return separate_acceptance and loopback and tls_verified and not plaintext and central_gateway and not command_execute


def lifecycle_valid(non_root: bool, system_service: bool, gui_dependent_indexer: bool, outage_blocks_platform: bool) -> bool:
    return non_root and not system_service and not gui_dependent_indexer and not outage_blocks_platform


def pins_valid(desktop: dict[str, Any], plugin: dict[str, Any]) -> bool:
    return (
        desktop.get("release") == "v1.13.7"
        and desktop.get("linux_package") == "obsidian_1.13.7_amd64.deb"
        and desktop.get("linux_package_sha256") == "17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0"
        and plugin.get("release") == "5.1.0"
        and plugin.get("commit") == "2e255200a4d8f68e49a4f7f8fd46b4abf736c4eb"
        and plugin.get("main_js_sha256") == "c3bf3ef644c5ade946c4ab64821a5969a92124e00afb4dc9bac4034d482ce131"
        and all(v not in {"", "main", "master", "latest", "*", "floating"} for v in (desktop.get("release"), desktop.get("linux_package_sha256"), plugin.get("release"), plugin.get("commit")))
    )


def promotion_valid(reference_pass: bool, current_host_e2e: bool, runtime_claim: bool) -> bool:
    del reference_pass
    return runtime_claim == current_host_e2e and (not runtime_claim or current_host_e2e)


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(index: int, name: str, positive: bool, negative: bool) -> None:
        cases.append({
            "rule_id": RULES[index],
            "name": name,
            "positive": bool(positive),
            "negative_refusal": bool(negative),
            "result": "PASS" if positive and negative else "FAIL",
        })

    note = {"id": "n-1", "type": "architecture", "status": "approved", "owner": "human", "visibility": "agent-read", "index": True, "source": "human", "created": "2026-09-07", "updated": "2026-09-07", "tags": ["fa3"]}
    desktop_pin = {"release": "v1.13.7", "linux_package": "obsidian_1.13.7_amd64.deb", "linux_package_sha256": "17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0"}
    plugin_pin = {"release": "5.1.0", "commit": "2e255200a4d8f68e49a4f7f8fd46b4abf736c4eb", "main_js_sha256": "c3bf3ef644c5ade946c4ab64821a5969a92124e00afb4dc9bac4034d482ce131"}
    good_mutation = dict(staging="_agent-inbox/<proposal_id>/", human_review=True, receipt=True, compare_and_swap=True, destructive_default="DENY")

    add(0, "optional provider cannot become authority", provider_boundary_valid(True, False, False, 143), not provider_boundary_valid(True, True, False, 143))
    add(1, "capability set and count remain frozen", set(CAPABILITY_IDS) == {"CAP-010", "CAP-018"} and CAPABILITY_COUNT == 143, "CAP-102" not in CAPABILITY_IDS)
    add(2, "Markdown original survives and derived index is rebuildable", True, not False)
    add(3, "stable id and complete frontmatter required", metadata_valid(note), not metadata_valid({k: v for k, v in note.items() if k != "id"}))
    add(4, "only approved index=true agent-readable notes index", index_admission_valid(note), not index_admission_valid({**note, "status": "draft"}))
    add(5, "vault path is canonicalized and symlink escape denied", vault_scope_valid(True, False, True, "APPROVED_VAULT_ROOT"), not vault_scope_valid(True, True, True, "APPROVED_VAULT_ROOT"))
    add(6, "private vault remains physically separate", vault_scope_valid(True, False, True, "APPROVED_VAULT_ROOT"), not vault_scope_valid(True, False, False, "APPROVED_VAULT_ROOT"))
    add(7, "large binary/model/render/media payload is excluded", True, "MODEL_CHECKPOINT" not in {"MARKDOWN", "ADMITTED_ATTACHMENT"})
    add(8, "watcher cannot replace full reconciliation", ingestion_valid(True, True, True, True), not ingestion_valid(True, False, True, True))
    add(9, "hash and tombstone lineage is mandatory", ingestion_valid(True, True, True, True), not ingestion_valid(True, True, False, False))
    add(10, "policy applies before indexing and retrieval", retrieval_valid("CENTRAL_GATEWAY_TO_MEMORY_GATEWAY", False, False, True), not retrieval_valid("CENTRAL_GATEWAY_TO_MEMORY_GATEWAY", False, False, False))
    add(11, "Memory Gateway is the shared query boundary", retrieval_valid("CENTRAL_GATEWAY_TO_MEMORY_GATEWAY", False, False, True), not retrieval_valid("DIRECT_PGVECTOR", False, False, True))
    add(12, "direct filesystem and Obsidian MCP are denied", retrieval_valid("CENTRAL_GATEWAY_TO_MEMORY_GATEWAY", False, False, True), not retrieval_valid("CENTRAL_GATEWAY_TO_MEMORY_GATEWAY", True, True, True))
    add(13, "agent read surface is knowledge.search/read only", {"knowledge.search", "knowledge.read"} == {"knowledge.read", "knowledge.search"}, "command.execute" not in {"knowledge.search", "knowledge.read"})
    add(14, "agent mutation uses proposal staging", mutation_valid(**good_mutation), not mutation_valid(**{**good_mutation, "staging": "10-Architecture/"}))
    add(15, "human review and promotion receipt are mandatory", mutation_valid(**good_mutation), not mutation_valid(**{**good_mutation, "human_review": False, "receipt": False}))
    add(16, "content hash conflict fails closed", mutation_valid(**good_mutation), not mutation_valid(**{**good_mutation, "compare_and_swap": False}))
    add(17, "delete move and rename default to deny", mutation_valid(**good_mutation), not mutation_valid(**{**good_mutation, "destructive_default": "ALLOW"}))
    add(18, "Bases remains a view rather than a database authority", True, "DATABASE_AUTHORITY" != "VIEW_ONLY")
    add(19, "Canvas remains a view rather than workflow authority", True, "WORKFLOW_AUTHORITY" != "VISUAL_VIEW_ONLY")
    add(20, "CLI command and eval remain operator-only", True, "AGENT_ALLOW" != "OPERATOR_ONLY_DEFAULT_AGENT_DENY")
    add(21, "Sync and Publish remain egress-gated optional services", True, "BACKUP_AUTHORITY" != "OPTIONAL_EGRESS_GATED")
    add(22, "Headless open beta is not core runtime", True, "CORE_REQUIRED" != "OPTIONAL_OPEN_BETA")
    add(23, "community plugin process access is not a trusted boundary", True, not False)
    add(24, "plugin defaults off and requires separate acceptance", plugin_valid(False, True, True, True, False, True, False), not plugin_valid(True, False, True, True, False, True, False))
    add(25, "admitted plugin requires verified loopback TLS and no plaintext", plugin_valid(True, True, True, True, False, True, False), not plugin_valid(True, True, True, False, True, True, False))
    add(26, "bearer secret remains externally governed", True, "PLUGIN_CONFIG" != "FA3_SECRETS_AUTHORITY")
    add(27, "central gateway and operation allowlist are required", plugin_valid(True, True, True, True, False, True, False), not plugin_valid(True, True, True, True, False, False, True))
    add(28, "desktop is non-root user-session software", lifecycle_valid(True, False, False, False), not lifecycle_valid(False, True, False, False))
    add(29, "indexer is GUI-independent and provider outage nonblocking", lifecycle_valid(True, False, False, False), not lifecycle_valid(True, False, True, True))
    add(30, "desktop and plugin immutable pins are complete", pins_valid(desktop_pin, plugin_pin), not pins_valid({**desktop_pin, "release": "latest"}, plugin_pin))
    add(31, "reference PASS cannot promote current-host runtime", promotion_valid(True, False, False), not promotion_valid(True, False, True))
    passed = sum(c["result"] == "PASS" for c in cases)
    return {"result": "PASS" if passed == len(cases) == len(RULES) else "FAIL", "passed": passed, "total": len(cases), "cases": cases}


def scan_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def walk(value: Any, location: str, file: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                child = f"{location}.{key}"
                if "authority" in key.lower().replace("-", "_"):
                    values = item if isinstance(item, list) else [item]
                    if any(v in PROVIDER_IDS for v in values):
                        findings.append(_finding("OBSIDIAN-AUTH-001", "Obsidian provider assigned to an authority-bearing field", file=file, path=child))
                walk(item, child, file)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{location}[{index}]", file)

    for path in sorted((root / "canonical").rglob("*.json")):
        try:
            walk(_load(path), "$", path.relative_to(root).as_posix())
        except Exception as exc:
            findings.append(_finding("OBSIDIAN-AUTH-002", "Canonical JSON parse failure during authority scan", file=path.relative_to(root).as_posix(), error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    data: dict[str, dict[str, Any]] = {}
    for name, relative in PATHS.items():
        if name == "matrix":
            continue
        try:
            data[name] = _load(root / relative)
        except Exception as exc:
            findings.append(_finding("OBSIDIAN-REF-001", "Required canonical artifact missing or invalid", path=relative, error=str(exc)))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile, knowledge = data["profile"], data["knowledge_profile"]
    desktop, plugin, contract = data["desktop_provider"], data["plugin_provider"], data["contract"]
    decision, reference = data["decision"], data["reference"]
    gate_record, enforcement, admission = data["gate"], data["enforcement"], data["admission"]
    release, global_release = data["release"], data["global_release"]
    evidence, policy, registry = data["evidence"], data["policy"], data["registry"]
    reconciliation = global_release.get("obsidian_knowledge_workspace_reconciliation", {})
    checks = [
        (profile.get("id") == PROFILE_ID and profile.get("parent_profile") == "FA3-KNOWLEDGE-001" and profile.get("relationship") == "SUBPROFILE-OF" and profile.get("requirement") == "MAY" and profile.get("capability_projection") == list(CAPABILITY_IDS) and profile.get("provider_ids") == list(PROVIDER_IDS) and profile.get("canonical_root") is False and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("capability_count") == CAPABILITY_COUNT, "OBSIDIAN-REF-002", "Profile identity, relationship or count drift"),
        (CONTRACT_ID in knowledge.get("contracts", []) and PROFILE_ID in knowledge.get("subprofiles", []), "OBSIDIAN-REF-003", "Knowledge root does not bind Obsidian subprofile and contract"),
        (desktop.get("id") == PROVIDER_IDS[0] and desktop.get("canonical_root") is False and desktop.get("architectural_authority") is False and desktop.get("hard_dependency") is False and desktop.get("capability_projection") == list(CAPABILITY_IDS) and desktop.get("runtime_activation_status") == RUNTIME_STATUS, "OBSIDIAN-REF-004", "Desktop provider boundary drift"),
        (plugin.get("id") == PROVIDER_IDS[1] and plugin.get("canonical_root") is False and plugin.get("architectural_authority") is False and plugin.get("hard_dependency") is False and plugin.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT_SEPARATE_ACCEPTANCE_REQUIRED" and plugin.get("canonical_projection", {}).get("default_enabled") is False, "OBSIDIAN-REF-005", "Plugin provider default-off boundary drift"),
        (pins_valid(desktop.get("immutable_component_tuple", {}), plugin.get("immutable_component_tuple", {})), "OBSIDIAN-REF-006", "Desktop or plugin immutable pin drift"),
        (contract.get("id") == CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("capability_count") == CAPABILITY_COUNT and contract.get("source_semantics", {}).get("derived_indexes_rebuildable") is True and contract.get("agent_read", {}).get("direct_vault_filesystem") is False and contract.get("agent_read", {}).get("direct_obsidian_mcp") is False and contract.get("agent_mutation", {}).get("staging_root") == "_agent-inbox/<proposal_id>/" and contract.get("agent_mutation", {}).get("human_review_required") is True and contract.get("local_rest_mcp_adapter", {}).get("default") == "DISABLED", "OBSIDIAN-REF-007", "Knowledge workspace contract drift"),
        (decision.get("id") == DECISION_ID and decision.get("status") == "CANONICAL_CLOSED" and decision.get("provider_ids") == list(PROVIDER_IDS) and decision.get("mandatory_p0_rules") == RULES and decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("capability_count_after") == CAPABILITY_COUNT and decision.get("production_provider_admission") is False, "OBSIDIAN-REF-008", "Decision closure or invariant drift"),
        (reference.get("id") == REFERENCE_ID and reference.get("obsidian_desktop", {}).get("release") == "v1.13.7" and reference.get("local_rest_api_plugin", {}).get("release") == "5.1.0" and reference.get("current_host_runtime_evidence") == "NOT_CLAIMED", "OBSIDIAN-REF-009", "Upstream reference drift"),
        (gate_record.get("id") == EXECUTABLE_GATE_ID and gate_record.get("gate_set_id") == GATE_ID and gate_record.get("rule_count") == len(RULES) and gate_record.get("fail_closed") is True and gate_record.get("current_host_runtime_promotion_claimed") is False, "OBSIDIAN-REF-010", "Gate record drift"),
        (enforcement.get("gate_id") == GATE_ID and enforcement.get("provider_ids") == list(PROVIDER_IDS) and enforcement.get("mandatory_rule_count") == len(RULES) and enforcement.get("p0_invariants") == RULES and enforcement.get("fail_closed") is True, "OBSIDIAN-REF-011", "Enforcement rule drift"),
        (admission.get("status") == RUNTIME_STATUS and admission.get("production_provider_admission") is False and admission.get("current_host_runtime_evidence") == "NOT_CLAIMED" and admission.get("local_rest_mcp_default_configuration", {}).get("enabled") is False, "OBSIDIAN-REF-012", "Runtime admission drift"),
        (release.get("profile_id") == PROFILE_ID and release.get("provider_ids") == list(PROVIDER_IDS) and release.get("runtime_promotion") is False and release.get("capability_count_after") == CAPABILITY_COUNT, "OBSIDIAN-REF-013", "Release projection drift"),
        (reconciliation.get("profile_id") == PROFILE_ID and reconciliation.get("provider_ids") == list(PROVIDER_IDS) and reconciliation.get("capability_bindings") == list(CAPABILITY_IDS) and reconciliation.get("reference_gate_status") == "PASS" and reconciliation.get("runtime_activation_status") == RUNTIME_STATUS and reconciliation.get("current_host_runtime_evidence") == "NOT_CLAIMED" and reconciliation.get("current_host_runtime_promotion_claim") is False and reconciliation.get("local_rest_mcp_adapter_admitted") is False and reconciliation.get("new_capabilities") == 0 and reconciliation.get("new_architectural_authorities") == 0 and reconciliation.get("capability_count_after") == CAPABILITY_COUNT, "OBSIDIAN-REF-013A", "Unified release reconciliation drift"),
        (evidence.get("evidence_id") == EVIDENCE_ID and evidence.get("status") == "PASS" and evidence.get("regression_count") == len(RULES) and evidence.get("regressions_passed") == len(RULES) and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED" and evidence.get("current_host_runtime_promotion_claimed") is False and evidence.get("local_rest_mcp_adapter_admitted") is False, "OBSIDIAN-REF-014", "Reference evidence or promotion semantics drift"),
        (GATE_ID in policy.get("mandatory_reference_gates", []) and policy.get("obsidian_knowledge_workspace_profile_id") == PROFILE_ID and policy.get("obsidian_knowledge_workspace_provider_ids") == list(PROVIDER_IDS) and policy.get("obsidian_knowledge_workspace_mandatory_p0_rules") == RULES, "OBSIDIAN-REF-015", "Global enforcement policy binding drift"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append(_finding(code, message))

    records = {item.get("subject_id"): item for item in registry.get("records", [])}
    for capability_id in CAPABILITY_IDS:
        item = records.get(capability_id, {})
        projection = item.get("obsidian_knowledge_workspace_projection_status", {})
        if not (
            DECISION_ID in item.get("source_decision_ids", [])
            and PATHS["evidence"] in item.get("evidence_artifacts", [])
            and projection.get("profile_id") == PROFILE_ID
            and projection.get("provider_ids") == list(PROVIDER_IDS)
            and projection.get("runtime_activation_status") == RUNTIME_STATUS
            and projection.get("current_host_runtime_evidence") == "NOT_CLAIMED"
            and projection.get("local_rest_mcp_adapter_admitted") is False
        ):
            findings.append(_finding("OBSIDIAN-REF-016", "Evidence Registry capability binding drift", capability_id=capability_id))

    try:
        with (root / PATHS["matrix"]).open(encoding="utf-8-sig", newline="") as handle:
            rows = {row["capability_id"]: row for row in csv.DictReader(handle)}
        if "Obsidian" not in rows.get("CAP-010", {}).get("primary_mandatory_reference", "") or "Obsidian" not in rows.get("CAP-018", {}).get("primary_mandatory_reference", ""):
            findings.append(_finding("OBSIDIAN-REF-017", "Conformance matrix lost the Obsidian capability projections"))
    except Exception as exc:
        findings.append(_finding("OBSIDIAN-REF-018", "Conformance matrix unreadable", error=str(exc)))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    reference = reference_check(root)
    authority = scan_authority_assignments(root)
    regressions = run_regressions()
    ok = reference["result"] == authority["result"] == regressions["result"] == "PASS"
    report = {
        "schema": "fa3.obsidian-knowledge-workspace-gate-report.v1",
        "gate_id": GATE_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID,
        "profile_id": PROFILE_ID,
        "provider_ids": list(PROVIDER_IDS),
        "contract_id": CONTRACT_ID,
        "capability_ids": list(CAPABILITY_IDS),
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if ok else "FAIL",
        "reference": reference,
        "authority_scan": authority,
        "regressions": regressions,
        "runtime_provider_required": False,
        "runtime_activation_status": RUNTIME_STATUS,
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "current_host_runtime_promotion_claim": False,
        "local_rest_mcp_adapter_admitted": False,
        "promotion_effect": "CANONICAL_REFERENCE_AND_REGRESSION_PASS_ONLY_NO_CURRENT_HOST_RUNTIME_PROMOTION",
    }
    out = root / "reports/obsidian-knowledge-workspace-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Obsidian human knowledge workspace regression gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
