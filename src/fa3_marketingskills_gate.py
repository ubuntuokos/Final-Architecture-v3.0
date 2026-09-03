#!/usr/bin/env python3
from __future__ import annotations
import argparse
import copy
import json
import posixpath
import re
from pathlib import Path

PROVIDER_ID = "FA3-PROVIDER-MARKETINGSKILLS-001"
CONTRACT_ID = "FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001"
DECISION_ID = "FA3-DEC-MARKETINGSKILLS-SKILL-ADMISSION-2026-09-03"
GATE_ID = "FA3-GATE-MARKETINGSKILLS-SKILL-ADMISSION-001"
GATESET_ID = "FA3-MARKETINGSKILLS-SKILL-ADMISSION-GATESET-001"
REFERENCE_ID = "FA3-MARKETINGSKILLS-UPSTREAM-REFERENCE-2026-09-03"
UPSTREAM_PIN = "5cd4a7eae3a9a7b5d2aceb0613f7d1f7c4b65968"
EVIDENCE_PATH = "evidence/reference/marketingskills-skill-admission-ci-2026-09-03.json"
CAPABILITY_IDS = ["CAP-003","CAP-004","CAP-010","CAP-011","CAP-018","CAP-019","CAP-040","CAP-049","CAP-103","CAP-112","CAP-125"]
RULES = ["MARKETINGSKILLS_PROVIDER_NOT_AUTHORITY","MARKETINGSKILLS_CAPABILITY_AUTHORITY_COUNT_INVARIANT","MARKETINGSKILLS_IMMUTABLE_UPSTREAM_PIN_REQUIRED","SKILL_PACKAGE_UNTRUSTED_BY_DEFAULT","SKILL_PACKAGE_DESCRIPTOR_AND_MANIFEST_DIGEST_REQUIRED","SKILL_PACKAGE_LICENSE_SNAPSHOT_REQUIRED","SKILL_PACKAGE_AUTO_UPDATE_FORBIDDEN","NEW_UPSTREAM_COMMIT_REQUIRES_READMISSION","SKILL_DEPENDENCY_GRAPH_EXPLICIT_AND_ACYCLIC","SKILL_ENTRYPOINT_NAME_VERSION_SOURCE_EXPLICIT","SKILL_CONTENT_ON_DEMAND_SCOPE_BOUND","GLOBAL_CORPUS_AUTO_INJECTION_FORBIDDEN","EXECUTABLE_DIRECTIVES_INERT_BY_DEFAULT","SHELL_INTERPOLATION_IMPLICIT_EXECUTION_FORBIDDEN","SCRIPT_ASSET_AUTO_EXECUTION_FORBIDDEN","SYMLINK_PATH_TRAVERSAL_ESCAPE_FORBIDDEN","REMOTE_INCLUDE_OR_FETCH_DURING_ADMISSION_FORBIDDEN","TOOL_DISCOVERY_NOT_TOOL_AUTHORIZATION","TOOL_INTENT_ROUTES_THROUGH_CENTRAL_MCP","DIRECT_CREDENTIAL_ACCESS_FROM_SKILL_FORBIDDEN","DIRECT_EXTERNAL_MUTATION_FROM_SKILL_FORBIDDEN","MUTATION_REQUIRES_EXPLICIT_AUTHORIZATION_AND_APPLICABLE_HITL","BEHAVIORAL_EVAL_REQUIRED_BEFORE_ADMISSION","ADVERSARIAL_INJECTION_AND_NEGATIVE_EVAL_REQUIRED","EVAL_PASS_BOUND_TO_PACKAGE_DIGEST","SPONSORSHIP_AFFILIATION_PROVENANCE_ONLY","SPONSORSHIP_CANNOT_CHANGE_RANKING_OR_AUTHORIZATION","USE_RECEIPT_BINDS_SKILL_VERSION_DIGEST_DEPENDENCIES","DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST","REFERENCE_CI_NOT_RUNTIME_OR_MUTATION_ADMISSION","PORTABLE_HARDWARE_NO_STATIC_HOST_SKU_ASSUMPTION","EXECUTABLE_HELPER_REQUIRES_EXISTING_SANDBOX_POLICY_AND_RESOURCE_BOUNDARY"]
CASE_IDS = [f"MSA-{i:03d}" for i in range(1, 33)]
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

def loadj(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def writej(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def finding(code, message, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}

def _safe_relpath(path):
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    norm = posixpath.normpath(path)
    if norm in (".", "..") or norm.startswith("../") or "/../" in f"/{norm}/":
        return False
    return not norm.startswith("/")

def _safe_symlink(path, target):
    if not _safe_relpath(path) or not isinstance(target, str) or not target or target.startswith("/"):
        return False
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
    return resolved not in ("..", ".") and not resolved.startswith("../") and not resolved.startswith("/")

def _acyclic(nodes, edges):
    graph = {n: [] for n in nodes}
    for edge in edges:
        if not isinstance(edge, dict):
            return False
        a, b = edge.get("from"), edge.get("to")
        if a not in graph or b not in graph:
            return False
        graph[a].append(b)
    state = {}
    def visit(n):
        s = state.get(n, 0)
        if s == 1:
            return False
        if s == 2:
            return True
        state[n] = 1
        for m in graph[n]:
            if not visit(m):
                return False
        state[n] = 2
        return True
    return all(visit(n) for n in nodes)

def package_admission_allowed(pkg):
    try:
        source = pkg["source"]
        digests = pkg["digests"]
        license_ = pkg["license"]
        dep = pkg["dependencies"]
        execution = pkg["execution"]
        scope = pkg["scope"]
        tool = pkg["tool_boundary"]
        evaluation = pkg["evaluation"]
        commercial = pkg["commercial"]
        hardware = pkg["hardware"]
        files = pkg["files"]
        symlinks = pkg.get("symlinks", [])
        if pkg.get("trust_default") != "UNTRUSTED":
            return False
        if not SHA40.fullmatch(source.get("commit", "")) or source.get("floating_ref_allowed") is not False:
            return False
        if source.get("auto_update") is not False or source.get("new_commit_requires_readmission") is not True:
            return False
        if not SHA256.fullmatch(digests.get("content_sha256", "")) or not SHA256.fullmatch(digests.get("manifest_sha256", "")):
            return False
        if not license_.get("name") or license_.get("snapshot_present") is not True:
            return False
        if dep.get("explicit") is not True or not _acyclic(dep.get("nodes", []), dep.get("edges", [])):
            return False
        if scope.get("on_demand") is not True or scope.get("global_auto_injection") is not False or not scope.get("task_scope"):
            return False
        if execution.get("mode") != "INERT_DATA":
            return False
        if execution.get("shell_interpolation_exec_allowed") is not False:
            return False
        if execution.get("script_auto_execute") is not False:
            return False
        if execution.get("remote_fetch_during_admission") is not False:
            return False
        if execution.get("direct_credential_access") is not False or execution.get("direct_external_mutation") is not False:
            return False
        if tool.get("discovery_is_authorization") is not False or tool.get("central_mcp_required") is not True:
            return False
        if evaluation.get("required") is not True or evaluation.get("behavioral") is not True:
            return False
        if evaluation.get("negative") is not True or evaluation.get("adversarial_injection") is not True:
            return False
        if evaluation.get("result") != "PASS" or evaluation.get("bound_content_sha256") != digests.get("content_sha256"):
            return False
        if commercial.get("sponsorship_affects_ranking") is not False or commercial.get("sponsorship_affects_authorization") is not False:
            return False
        if hardware.get("portable") is not True or hardware.get("exact_host_model_required") is not False:
            return False
        if any(not _safe_relpath(p) for p in files):
            return False
        if any(not _safe_symlink(s.get("path"), s.get("target")) for s in symlinks):
            return False
        return True
    except (KeyError, TypeError):
        return False

def skill_use_allowed(receipt):
    try:
        if receipt.get("package_admission_status") != "PASS":
            return False
        if not receipt.get("skill_name") or not receipt.get("skill_version"):
            return False
        if not SHA256.fullmatch(receipt.get("content_sha256", "")) or not SHA256.fullmatch(receipt.get("dependency_digest_sha256", "")):
            return False
        if not receipt.get("task_scope") or receipt.get("unsandboxed_execution") is not False:
            return False
        ti = receipt.get("tool_intent")
        if ti:
            if ti.get("via_central_mcp") is not True:
                return False
            if ti.get("mutating") is True and ti.get("authorization_receipt") is not True:
                return False
            if ti.get("hitl_required") is True and ti.get("human_approved") is not True:
                return False
        if receipt.get("sponsorship_changed_ranking") is not False:
            return False
        return True
    except TypeError:
        return False

def good_package():
    content = "a" * 64
    return {
        "trust_default": "UNTRUSTED",
        "source": {
            "repository": "coreyhaines31/marketingskills",
            "commit": UPSTREAM_PIN,
            "floating_ref_allowed": False,
            "auto_update": False,
            "new_commit_requires_readmission": True,
        },
        "digests": {"content_sha256": content, "manifest_sha256": "b" * 64},
        "license": {"name": "MIT", "snapshot_present": True},
        "entrypoints": [{"name": "copywriting", "version": "2.0.2", "path": "skills/copywriting/SKILL.md"}],
        "dependencies": {
            "explicit": True,
            "nodes": ["copywriting", "product-marketing"],
            "edges": [{"from": "copywriting", "to": "product-marketing"}],
        },
        "execution": {
            "mode": "INERT_DATA",
            "shell_interpolation_exec_allowed": False,
            "script_auto_execute": False,
            "remote_fetch_during_admission": False,
            "direct_credential_access": False,
            "direct_external_mutation": False,
        },
        "scope": {"on_demand": True, "global_auto_injection": False, "task_scope": "marketing.copywriting"},
        "tool_boundary": {"discovery_is_authorization": False, "central_mcp_required": True},
        "evaluation": {
            "required": True,
            "behavioral": True,
            "negative": True,
            "adversarial_injection": True,
            "result": "PASS",
            "bound_content_sha256": content,
        },
        "commercial": {"sponsorship_affects_ranking": False, "sponsorship_affects_authorization": False},
        "hardware": {"portable": True, "exact_host_model_required": False},
        "files": ["skills/copywriting/SKILL.md", "skills/copywriting/references/example.md"],
        "symlinks": [],
    }

def good_use_receipt():
    return {
        "package_admission_status": "PASS",
        "skill_name": "copywriting",
        "skill_version": "2.0.2",
        "content_sha256": "a" * 64,
        "dependency_digest_sha256": "c" * 64,
        "task_scope": "marketing.copywriting",
        "unsandboxed_execution": False,
        "tool_intent": {"via_central_mcp": True, "mutating": False},
        "sponsorship_changed_ranking": False,
    }

def _mutate(obj, fn):
    x = copy.deepcopy(obj)
    fn(x)
    return x

def run_regressions():
    g = good_package()
    u = good_use_receipt()
    tests = [
        package_admission_allowed(g),
        not package_admission_allowed(_mutate(g, lambda x: x["source"].update(floating_ref_allowed=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["source"].update(commit="main"))),
        not package_admission_allowed(_mutate(g, lambda x: x["source"].update(auto_update=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["digests"].update(content_sha256=""))),
        not package_admission_allowed(_mutate(g, lambda x: x["evaluation"].update(bound_content_sha256="d"*64))),
        not package_admission_allowed(_mutate(g, lambda x: x["license"].update(snapshot_present=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["dependencies"].update(explicit=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["dependencies"].update(edges=[{"from":"copywriting","to":"product-marketing"},{"from":"product-marketing","to":"copywriting"}]))),
        not package_admission_allowed(_mutate(g, lambda x: x["scope"].update(global_auto_injection=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["scope"].update(on_demand=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["execution"].update(mode="ACTIVE_EXECUTION"))),
        not package_admission_allowed(_mutate(g, lambda x: x["execution"].update(shell_interpolation_exec_allowed=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["execution"].update(script_auto_execute=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["execution"].update(remote_fetch_during_admission=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["execution"].update(direct_credential_access=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["execution"].update(direct_external_mutation=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["tool_boundary"].update(central_mcp_required=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["tool_boundary"].update(discovery_is_authorization=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["files"].append("../escape"))),
        not package_admission_allowed(_mutate(g, lambda x: x["files"].append("/absolute"))),
        not package_admission_allowed(_mutate(g, lambda x: x["symlinks"].append({"path":"skills/x/link","target":"../../../etc/passwd"}))),
        not package_admission_allowed(_mutate(g, lambda x: x["evaluation"].update(required=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["evaluation"].update(behavioral=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["evaluation"].update(adversarial_injection=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["evaluation"].update(result="FAIL"))),
        not package_admission_allowed(_mutate(g, lambda x: x["commercial"].update(sponsorship_affects_ranking=True))),
        not package_admission_allowed(_mutate(g, lambda x: x["commercial"].update(sponsorship_affects_authorization=True))),
        skill_use_allowed(u),
        not skill_use_allowed(_mutate(u, lambda x: x["tool_intent"].update(via_central_mcp=False))),
        not skill_use_allowed(_mutate(u, lambda x: x["tool_intent"].update(mutating=True, authorization_receipt=False))),
        not package_admission_allowed(_mutate(g, lambda x: x["hardware"].update(exact_host_model_required=True))),
    ]
    cases = [{"case_id": cid, "status": "PASS" if ok else "FAIL"} for cid, ok in zip(CASE_IDS, tests)]
    return {
        "result": "PASS" if len(cases) == 32 and all(c["status"] == "PASS" for c in cases) else "FAIL",
        "total": len(cases),
        "passed": sum(c["status"] == "PASS" for c in cases),
        "case_ids_exact": [c["case_id"] for c in cases] == CASE_IDS,
        "cases": cases,
    }

def canonical_check(root):
    root = Path(root)
    findings = []
    provider = loadj(root / "canonical/providers/FA3-PROVIDER-MARKETINGSKILLS-001.json")
    contract = loadj(root / "canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json")
    decision = loadj(root / "canonical/decisions/FA3-DEC-MARKETINGSKILLS-SKILL-ADMISSION-2026-09-03.json")
    reference = loadj(root / "canonical/references/FA3-MARKETINGSKILLS-UPSTREAM-REFERENCE-2026-09-03.json")
    enforcement = loadj(root / "canonical/marketingskills-skill-admission-enforcement.json")
    gate_rec = loadj(root / "canonical/FA3-GATE-MARKETINGSKILLS-SKILL-ADMISSION-001.json")
    evidence = loadj(root / EVIDENCE_PATH)
    profile = loadj(root / "canonical/profiles/FA3-MARKETING-001.json")
    marketing_contract = loadj(root / "canonical/contracts/FA3-MARKETING-CONTRACTS-001.json")
    policy = loadj(root / "canonical/enforcement-policy.json")

    if not (
        provider.get("id") == PROVIDER_ID
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("new_architectural_authority") is False
        and provider.get("capability_count") == 143
        and provider.get("upstream", {}).get("immutable_commit") == UPSTREAM_PIN
        and provider.get("runtime_activation_status") == "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"
        and provider.get("package_admission", {}).get("entire_upstream_repo_is_not_implicitly_admitted") is True
        and provider.get("package_admission", {}).get("auto_update") is False
        and provider.get("package_admission", {}).get("executable_directives_policy") == "INERT_DATA_ONLY"
    ):
        findings.append(finding("MSA-CANON-001", "MarketingSkills provider identity/trust/runtime boundary drift"))

    boundaries = provider.get("authority_boundaries", {})
    if any(boundaries.get(k) is not False for k in (
        "identity","authorization","secrets","durable_workflow","canonical_customer_data",
        "canonical_campaign_state","evidence","mcp_gateway","tool_execution","provider_ranking",
        "recommendation_authority"
    )):
        findings.append(finding("MSA-CANON-002", "MarketingSkills crossed an architectural authority boundary"))

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("provider_neutral") is True
        and contract.get("new_capability") is False
        and contract.get("new_architectural_authority") is False
        and contract.get("capability_count") == 143
        and contract.get("mandatory_rules") == RULES
        and contract.get("execution_safety", {}).get("executable_directives_inert_by_default") is True
        and contract.get("tool_governance", {}).get("central_mcp_gateway_required") is True
        and contract.get("evaluation", {}).get("adversarial_prompt_injection_eval_required") is True
    ):
        findings.append(finding("MSA-CANON-003", "Provider-neutral skill-package admission contract drift"))

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("provider_id") == PROVIDER_ID
        and decision.get("contract_id") == CONTRACT_ID
        and decision.get("upstream_pin") == UPSTREAM_PIN
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == 143
        and decision.get("current_host_runtime_claim") is False
    ):
        findings.append(finding("MSA-CANON-004", "MarketingSkills decision/capability/authority invariant drift"))

    obs = reference.get("observed_at_commit", {})
    if not (
        reference.get("id") == REFERENCE_ID
        and reference.get("immutable_commit") == UPSTREAM_PIN
        and obs.get("skill_md_count") == 50
        and obs.get("eval_file_count") == 50
        and obs.get("cli_js_count") == 64
        and "CLAUDE.md" in obs.get("symlinks", [])
        and reference.get("security_interpretation", {}).get("full_repo_skill_package_admission_performed") is False
    ):
        findings.append(finding("MSA-CANON-005", "Pinned upstream reference observation drift"))

    if not (
        enforcement.get("gate_id") == GATE_ID
        and enforcement.get("gateset_id") == GATESET_ID
        and enforcement.get("provider_id") == PROVIDER_ID
        and enforcement.get("contract_id") == CONTRACT_ID
        and enforcement.get("upstream_pin") == UPSTREAM_PIN
        and enforcement.get("fail_closed") is True
        and enforcement.get("regression_case_count") == 32
        and enforcement.get("executable_case_ids") == CASE_IDS
        and enforcement.get("rules") == RULES
    ):
        findings.append(finding("MSA-CANON-006", "Marketingskills enforcement matrix drift"))

    if not (
        gate_rec.get("id") == GATE_ID
        and gate_rec.get("gateset_id") == GATESET_ID
        and gate_rec.get("case_ids") == CASE_IDS
        and gate_rec.get("mandatory_rules") == RULES
        and gate_rec.get("current_host_provider_runtime_evidence") is False
    ):
        findings.append(finding("MSA-CANON-007", "Executable gate record drift"))

    if not (
        evidence.get("status") == "PASS"
        and evidence.get("provider_id") == PROVIDER_ID
        and evidence.get("contract_id") == CONTRACT_ID
        and evidence.get("gate_id") == GATE_ID
        and evidence.get("upstream_pin") == UPSTREAM_PIN
        and evidence.get("full_upstream_skill_package_admission") == "NOT_PERFORMED_BY_REFERENCE_GATE"
        and evidence.get("current_host_runtime_evidence") == "NOT_CLAIMED"
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("capability_count_after") == 143
    ):
        findings.append(finding("MSA-CANON-008", "Reference evidence overclaims admission/runtime or drifted"))

    if not (
        profile.get("id") == "FA3-MARKETING-001"
        and CONTRACT_ID in profile.get("contracts", [])
        and profile.get("providers", {}).get("skill_package_knowledge") == [PROVIDER_ID]
        and "coreyhaines31/marketingskills" in profile.get("knowledge_pattern_sources", [])
    ):
        findings.append(finding("MSA-CANON-009", "Marketing profile is not bound to skill-package provider/contract"))

    if marketing_contract.get("skill_package_admission", {}).get("contract_id") != CONTRACT_ID:
        findings.append(finding("MSA-CANON-010", "Marketing contract is not bound to provider-neutral skill admission"))

    if not (
        GATESET_ID in policy.get("mandatory_reference_gates", [])
        and policy.get("marketingskills_provider_id") == PROVIDER_ID
        and policy.get("skill_package_admission_contract_id") == CONTRACT_ID
        and policy.get("marketingskills_gate_id") == GATESET_ID
        and policy.get("marketingskills_upstream_pin") == UPSTREAM_PIN
        and policy.get("marketingskills_capability_bindings") == CAPABILITY_IDS
        and policy.get("marketingskills_runtime_status") == "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY"
        and policy.get("marketingskills_mandatory_p0_rules") == RULES
    ):
        findings.append(finding("MSA-CANON-011", "Global enforcement policy Marketingskills binding drift"))

    return {"result":"PASS" if not findings else "FAIL","findings":findings}

def gate(root):
    canonical = canonical_check(root)
    regressions = run_regressions()
    result = "PASS" if canonical["result"] == "PASS" and regressions["result"] == "PASS" else "FAIL"
    report = {
        "schema":"fa3.marketingskills-skill-admission-gate-report.v1",
        "gate_id":GATE_ID,
        "gateset_id":GATESET_ID,
        "provider_id":PROVIDER_ID,
        "contract_id":CONTRACT_ID,
        "upstream_pin":UPSTREAM_PIN,
        "result":result,
        "canonical":canonical,
        "regressions":regressions,
        "full_upstream_skill_package_admission":"NOT_PERFORMED_BY_REFERENCE_GATE",
        "current_host_runtime_claim":False,
    }
    writej(Path(root) / "reports/marketingskills-skill-admission-gate-report.json", report)
    return report

def main():
    ap = argparse.ArgumentParser(description="FA3 Marketingskills skill-package admission regression gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
