#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

PROFILE = "canonical/profiles/FA3-SKILL-FABRIC-001.json"
ADMISSION = "canonical/contracts/FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001.json"
INTERFACE = "canonical/contracts/FA3-SKILL-INTERFACE-CONTEXT-PREVIEW-CONTRACTS-001.json"
PROJECTION = "canonical/contracts/FA3-SKILL-HOST-PROJECTION-CONTRACTS-001.json"
ATTESTATION = "canonical/contracts/FA3-SKILL-PROVENANCE-ATTESTATION-CONTRACTS-001.json"
BROWSER_CONTRACT = "canonical/contracts/FA3-BROWSER-SESSION-INTERACTION-CONTRACTS-001.json"
BROWSER_PROFILE = "canonical/profiles/FA3-BROWSER-SESSION-INTERACTION-001.json"
BROWSER_INTENT = "canonical/intents/FA3-BROWSER-SESSION-INTERACTION-APPLICATION-INTENT-001.json"
BROWSER_REUSE = "canonical/assessments/FA3-BROWSER-SESSION-INTERACTION-REUSE-ASSESSMENT-001.json"
BROWSERSKILL_REF = "canonical/references/FA3-BROWSERSKILL-UPSTREAM-REFERENCE-2026-09-25.json"
DECISION = "canonical/decisions/FA3-DEC-SKILL-FABRIC-UNIFIED-RECONCILIATION-2026-09-25.json"
RADAR = "canonical/FA3-EXTERNAL-SKILL-RADAR-001.json"
ENFORCEMENT = "canonical/skill-fabric-enforcement.json"


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level object required")
    return value


def _safe_relpath(path: str) -> bool:
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    norm = posixpath.normpath(path)
    return norm not in (".", "..") and not norm.startswith("../") and "/../" not in f"/{norm}/"


def interface_allowed(record: dict[str, Any]) -> bool:
    try:
        if record.get("typed") is not True:
            return False
        for key in ("inputs", "outputs", "preconditions", "postconditions"):
            if not isinstance(record.get(key), list):
                return False
        for row in record["inputs"] + record["outputs"]:
            if not isinstance(row, dict) or not row.get("name") or not row.get("type"):
                return False
        return record.get("grants_authority") is False
    except (TypeError, KeyError):
        return False


def context_budget_allowed(record: dict[str, Any]) -> bool:
    keys = (
        "metadata_max_tokens", "instructions_max_tokens", "references_max_tokens",
        "metadata_used_tokens", "instructions_used_tokens", "references_used_tokens",
    )
    if any(not isinstance(record.get(k), int) or record[k] < 0 for k in keys):
        return False
    if any(record[k] == 0 for k in ("metadata_max_tokens", "instructions_max_tokens", "references_max_tokens")):
        return False
    pairs = (
        ("metadata_used_tokens", "metadata_max_tokens"),
        ("instructions_used_tokens", "instructions_max_tokens"),
        ("references_used_tokens", "references_max_tokens"),
    )
    return all(record[used] <= record[maximum] for used, maximum in pairs) and record.get("overflow_policy") == "FAIL_CLOSED"


def activation_preview_allowed(record: dict[str, Any]) -> bool:
    if record.get("result") != "PASS" or record.get("side_effects_performed") is not False:
        return False
    if record.get("authority_expansion") is not False or record.get("allowed_tools_is_authorization") is not False:
        return False
    admitted = record.get("admitted_permissions")
    requested = record.get("requested_permissions")
    if not isinstance(admitted, dict) or not isinstance(requested, dict):
        return False
    for key, value in requested.items():
        if value is True and admitted.get(key) is not True:
            return False
        if value not in (True, False):
            return False
    routes = record.get("routes", {})
    expected = {
        "tool": "FA3-AUTH-MCP-GATEWAY-001",
        "model": "FA3-AUTH-MODEL-ROUTER-001",
        "resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "secret": "FA3-AUTH-SECRETS",
    }
    return all(routes.get(k) == v for k, v in expected.items())


def provenance_attestation_allowed(record: dict[str, Any]) -> bool:
    if record.get("present") is not True:
        return record.get("required") is False
    if record.get("signature_verified") is not True:
        return False
    if record.get("signature_is_sufficient_for_admission") is not False:
        return False
    if not SHA40.fullmatch(str(record.get("source_commit", ""))):
        return False
    if not SHA256.fullmatch(str(record.get("content_sha256", ""))):
        return False
    if not SHA256.fullmatch(str(record.get("manifest_sha256", ""))):
        return False
    if not record.get("source_repository") or record.get("expected_source_match") is not True:
        return False
    if record.get("build_attestation") is True and record.get("expected_builder_match") is not True:
        return False
    return record.get("security_authority") == "FA3-SCS-001"


def host_projection_allowed(record: dict[str, Any], allowed_targets: set[str]) -> bool:
    if record.get("admission_status") != "ADMITTED":
        return False
    if not SHA256.fullmatch(str(record.get("content_sha256", ""))):
        return False
    if not record.get("skill_name") or not record.get("skill_version"):
        return False
    target = record.get("target_root")
    if target not in allowed_targets or not _safe_relpath(target):
        return False
    if record.get("global_install") is True or record.get("global_config_mutation") is True:
        return False
    if record.get("symlink_escape") is True:
        return False
    collision = record.get("collision", {})
    if collision.get("present") is True:
        return collision.get("same_content_digest") is True and collision.get("explicit_exact_digest_reuse") is True
    return True


def browser_tab_lease_allowed(record: dict[str, Any]) -> bool:
    required = ("session_id", "tab_ref", "origin_scope", "action_scope", "issued_at_epoch", "expires_at_epoch")
    if any(record.get(k) in (None, "", []) for k in required):
        return False
    if record.get("approved") is not True or record.get("return_required") is not True:
        return False
    if not isinstance(record.get("action_scope"), list) or not record["action_scope"]:
        return False
    if not isinstance(record.get("issued_at_epoch"), int) or not isinstance(record.get("expires_at_epoch"), int):
        return False
    if record["expires_at_epoch"] <= record["issued_at_epoch"]:
        return False
    if record.get("credential_access") is True or record.get("cookie_export") is True or record.get("token_export") is True:
        return False
    if record.get("sibling_tab_authority_inheritance") is not False or record.get("popup_authority_inheritance") is not False:
        return False
    return True


def _mut(value: dict[str, Any], fn) -> dict[str, Any]:
    result = copy.deepcopy(value)
    fn(result)
    return result


def run_regressions() -> dict[str, Any]:
    interface = {
        "typed": True,
        "inputs": [{"name": "diff", "type": "text/diff"}],
        "outputs": [{"name": "findings", "type": "application/fa3.findings+json"}],
        "preconditions": ["task_scope_bound"],
        "postconditions": ["acceptance_checked"],
        "grants_authority": False,
    }
    budget = {
        "metadata_max_tokens": 256, "instructions_max_tokens": 2048, "references_max_tokens": 4096,
        "metadata_used_tokens": 64, "instructions_used_tokens": 900, "references_used_tokens": 800,
        "overflow_policy": "FAIL_CLOSED",
    }
    preview = {
        "result": "PASS", "side_effects_performed": False, "authority_expansion": False,
        "allowed_tools_is_authorization": False,
        "admitted_permissions": {"network": False, "filesystem_write": True, "exec": False, "secrets": False},
        "requested_permissions": {"network": False, "filesystem_write": True, "exec": False, "secrets": False},
        "routes": {
            "tool": "FA3-AUTH-MCP-GATEWAY-001", "model": "FA3-AUTH-MODEL-ROUTER-001",
            "resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001", "secret": "FA3-AUTH-SECRETS",
        },
    }
    attestation = {
        "present": True, "required": False, "signature_verified": True,
        "signature_is_sufficient_for_admission": False,
        "source_repository": "example/skill", "source_commit": "1" * 40,
        "content_sha256": "a" * 64, "manifest_sha256": "b" * 64,
        "expected_source_match": True, "build_attestation": True, "expected_builder_match": True,
        "security_authority": "FA3-SCS-001",
    }
    projection = {
        "admission_status": "ADMITTED", "skill_name": "example", "skill_version": "1.0.0",
        "content_sha256": "a" * 64, "target_root": ".agents/skills",
        "global_install": False, "global_config_mutation": False, "symlink_escape": False,
        "collision": {"present": False},
    }
    lease = {
        "session_id": "s1", "tab_ref": "tab-1", "origin_scope": "https://example.invalid",
        "action_scope": ["CLICK"], "issued_at_epoch": 100, "expires_at_epoch": 200,
        "approved": True, "return_required": True, "credential_access": False,
        "cookie_export": False, "token_export": False,
        "sibling_tab_authority_inheritance": False, "popup_authority_inheritance": False,
    }
    allowed_targets = {".agents/skills", ".github/skills"}
    checks = [
        ("interface-valid", interface_allowed(interface)),
        ("interface-untyped-denied", not interface_allowed(_mut(interface, lambda x: x.update(typed=False)))),
        ("budget-valid", context_budget_allowed(budget)),
        ("budget-overflow-denied", not context_budget_allowed(_mut(budget, lambda x: x.update(references_used_tokens=5000)))),
        ("preview-valid", activation_preview_allowed(preview)),
        ("preview-side-effect-denied", not activation_preview_allowed(_mut(preview, lambda x: x.update(side_effects_performed=True)))),
        ("preview-permission-expansion-denied", not activation_preview_allowed(_mut(preview, lambda x: x["requested_permissions"].update(network=True)))),
        ("attestation-valid", provenance_attestation_allowed(attestation)),
        ("attestation-signature-alone-denied", not provenance_attestation_allowed(_mut(attestation, lambda x: x.update(expected_source_match=False)))),
        ("attestation-unsigned-optional", provenance_attestation_allowed({"present": False, "required": False})),
        ("projection-valid", host_projection_allowed(projection, allowed_targets)),
        ("projection-unadmitted-denied", not host_projection_allowed(_mut(projection, lambda x: x.update(admission_status="PENDING")), allowed_targets)),
        ("projection-collision-denied", not host_projection_allowed(_mut(projection, lambda x: x.update(collision={"present": True, "same_content_digest": False, "explicit_exact_digest_reuse": False})), allowed_targets)),
        ("projection-exact-digest-reuse", host_projection_allowed(_mut(projection, lambda x: x.update(collision={"present": True, "same_content_digest": True, "explicit_exact_digest_reuse": True})), allowed_targets)),
        ("browser-lease-valid", browser_tab_lease_allowed(lease)),
        ("browser-lease-no-approval-denied", not browser_tab_lease_allowed(_mut(lease, lambda x: x.update(approved=False)))),
        ("browser-lease-credential-denied", not browser_tab_lease_allowed(_mut(lease, lambda x: x.update(credential_access=True)))),
        ("browser-popup-inheritance-denied", not browser_tab_lease_allowed(_mut(lease, lambda x: x.update(popup_authority_inheritance=True)))),
    ]
    cases = [{"case_id": f"SKF13-{i:03d}", "name": name, "status": "PASS" if ok else "FAIL"} for i, (name, ok) in enumerate(checks, 1)]
    return {"result": "PASS" if all(ok for _, ok in checks) else "FAIL", "total": len(cases), "passed": sum(c["status"] == "PASS" for c in cases), "cases": cases}


def canonical_check(root: Path) -> list[str]:
    findings: list[str] = []
    required = [PROFILE, ADMISSION, INTERFACE, PROJECTION, ATTESTATION, BROWSER_CONTRACT, BROWSER_PROFILE, BROWSER_INTENT, BROWSER_REUSE, BROWSERSKILL_REF, DECISION, RADAR, ENFORCEMENT]
    missing = [p for p in required if not (root / p).is_file()]
    if missing:
        return [f"missing v1.3 artifacts: {missing}"]
    profile = loadj(root / PROFILE)
    admission = loadj(root / ADMISSION)
    interface = loadj(root / INTERFACE)
    projection = loadj(root / PROJECTION)
    attestation = loadj(root / ATTESTATION)
    browser_contract = loadj(root / BROWSER_CONTRACT)
    browser_profile = loadj(root / BROWSER_PROFILE)
    browser_reuse = loadj(root / BROWSER_REUSE)
    radar = loadj(root / RADAR)
    enforcement = loadj(root / ENFORCEMENT)
    decision = loadj(root / DECISION)

    if profile.get("version") != "1.3.0" or admission.get("version") != "1.3.0":
        findings.append("Skill Fabric/admission 1.3 not active")
    expected = {INTERFACE.split("/")[-1][:-5], PROJECTION.split("/")[-1][:-5], ATTESTATION.split("/")[-1][:-5]}
    if not expected.issubset(set(admission.get("extension_contracts", []))):
        findings.append("Skill Fabric 1.3 extension contract binding missing")
    if not expected.issubset(set(enforcement.get("extension_contract_ids", []))):
        findings.append("Skill Fabric enforcement missing 1.3 contracts")
    if interface.get("context_budget", {}).get("used_must_not_exceed_max") is not True:
        findings.append("context budget fail-closed invariant missing")
    if projection.get("coexistence", {}).get("collision_policy") != "FAIL_CLOSED":
        findings.append("host projection collision policy weakened")
    if attestation.get("semantics", {}).get("signature_alone_never_sufficient_for_admission") is not True:
        findings.append("attestation signature incorrectly sufficient")
    if browser_profile.get("parent_profile") != "FA3-BROWSER-ACTION-RUNTIME-001":
        findings.append("browser session profile bypasses Browser Action Runtime")
    if browser_profile.get("evidence_boundary", {}).get("current_host_runtime_claim") is not False:
        findings.append("browser session static profile overclaims current-host runtime")
    if browser_reuse.get("result") != "PASS":
        findings.append("browser session Reuse Assessment not PASS")
    if browser_contract.get("security", {}).get("credential_extraction") != "DENY":
        findings.append("browser credential extraction boundary weakened")
    repos = {row.get("repository"): row for row in radar.get("sources", [])}
    required_repos = {
        "mattpocock/skills": "c55ee46073ed923f86ce59a5eb3b6d895095d1b7",
        "microsoft/skills": "23d0dac5f83f268166a17f0bc7dc6c73dc348a33",
        "dotnet/skills": "a55fbf42c36a37b94ec07291bd79cb6b6bf3a04d",
        "emilkowalski/skills": "d16ebe60d09a5ba2afcb7054ede9d0a10c9f6128",
        "awesome-skills/code-review-skill": "4850184dfd7765ea7b3c5c4e9b6cf8e0815ee7cb",
        "Tencent/BrowserSkill": "147727a0e2ded65a7d0f364beea8cc2ebcdec8af",
    }
    for repo, commit in required_repos.items():
        row = repos.get(repo)
        if not row or row.get("commit") != commit or row.get("classification") != "REFERENCE_ONLY":
            findings.append(f"external radar pin/classification missing: {repo}")
    effect = decision.get("authority_effect", {})
    if effect != {"new_capability": False, "new_architectural_authority": False, "capability_count_after": module_active_capability_count(__file__)}:
        findings.append("1.3 decision capability/authority invariant drift")
    hw = decision.get("hardware_audit", {})
    if not (hw.get("vendor_neutral") and hw.get("cpu_only_viable") and hw.get("global_accelerator_requirement") is False):
        findings.append("1.3 Hardware Audit invariant failed")
    return findings


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings = canonical_check(root)
    regressions = run_regressions()
    result = "PASS" if not findings and regressions["result"] == "PASS" else "FAIL"
    report = {
        "schema": "fa3.skill-fabric-v13-gate-report.v1",
        "result": result,
        "findings": findings,
        "regressions": regressions,
        "provider_specific": False,
        "capability_count": module_active_capability_count(__file__),
        "new_architectural_authority": False,
        "current_host_runtime_claim": False,
        "browser_session_current_host_claim": False,
    }
    out = root / "reports/skill-fabric-v13-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = evaluate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
