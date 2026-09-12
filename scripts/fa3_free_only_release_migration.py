#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_ID = "FA3-FREE-SELF-HOSTED-ONLY-001"
FREE_GATE = "FA3-FREE-ONLY-GATESET-001"
CODEX_PROVIDER = "FA3-PROVIDER-CODEX-001"
CODEX_GATE = "FA3-CODEX-GATESET-001"
CODEX_DECISION_HISTORY = "FA3-DEC-CODEX-ADAPTER-2026-08-31"


def write_if_changed(path: Path, content: str) -> bool:
    old = path.read_text(encoding="utf-8")
    if old == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def patch_between(path: Path, start: str, end: str, replacement: str) -> bool:
    text = path.read_text(encoding="utf-8")
    i = text.find(start)
    j = text.find(end, i + len(start)) if i >= 0 else -1
    if i < 0 or j < 0:
        raise RuntimeError(f"patch markers not found in {path}: {start!r} -> {end!r}")
    return write_if_changed(path, text[:i] + replacement + text[j:])


def patch_release_gate() -> bool:
    path = ROOT / "src/fa3_release_projection_gate.py"
    start = '    codex = projection.get("codex_reconciliation", {})\n'
    end = '    aisec = projection.get("ai_infra_guard_reconciliation", {})\n'
    replacement = '''    codex = projection.get("codex_reconciliation", {})
    required_codex_manifest_paths = {
        CODEX_PROVIDER_PATH,
        CODEX_ENFORCEMENT_PATH,
        CODEX_GATE_PATH,
        "canonical/policies/FA3-FREE-SELF-HOSTED-ONLY-001.json",
        "canonical/contracts/FA3-PROVIDER-ECONOMICS-CONTRACTS-001.json",
        "canonical/FA3-GATE-FREE-ONLY-001.json",
        "src/fa3_free_only_gate.py",
    }
    codex_manifest_missing = sorted(required_codex_manifest_paths - manifest_paths)
    codex_provider = loadj(root / CODEX_PROVIDER_PATH) if (root / CODEX_PROVIDER_PATH).is_file() else {}
    cap028_codex = next((item for item in records if item.get("subject_id") == CODEX_CAPABILITY_ID), {})
    codex_projection_status = cap028_codex.get("codex_provider_projection_status", {})
    if (
        codex.get("provider_id") != CODEX_PROVIDER_ID
        or codex.get("gate_id") != CODEX_GATE_ID
        or codex.get("capability_id") != CODEX_CAPABILITY_ID
        or codex.get("classification") != "REMOVED_PAID_PROVIDER_TOMBSTONE"
        or codex.get("reconciliation_status") != "DECOMMISSIONED_FREE_ONLY_POLICY"
        or codex.get("runtime_activation_status") != "REMOVED_NOT_ADMITTED"
        or codex.get("current_host_production_e2e") != "NOT_APPLICABLE_REMOVED"
        or codex.get("economics_policy") != "FA3-FREE-SELF-HOSTED-ONLY-001"
        or codex.get("provider_runtime_required_for_global_promotion_when_disabled") is not False
        or codex.get("new_capabilities") != 0
        or codex.get("new_architectural_authorities") != 0
        or codex.get("capability_count_after") != CAPABILITY_COUNT
        or CODEX_GATE_ID not in projection_gates
        or CODEX_GATE_ID not in policy_gates
        or "FA3-FREE-ONLY-GATESET-001" not in projection_gates
        or "FA3-FREE-ONLY-GATESET-001" not in policy_gates
        or codex_manifest_missing
        or codex_provider.get("id") != CODEX_PROVIDER_ID
        or not str(codex_provider.get("status", "")).startswith("REMOVED_")
        or codex_provider.get("active") is not False
        or codex_provider.get("routing_eligible") is not False
        or codex_provider.get("production_admission") != "DENY"
        or codex_provider.get("runtime_surface") != "ABSENT"
        or codex_provider.get("canonical_root") is not False
        or codex_provider.get("architectural_authority") is not False
        or codex_provider.get("new_capability") is not False
        or codex_provider.get("capability_count") != CAPABILITY_COUNT
        or "FA3-DEC-CODEX-ADAPTER-2026-08-31" not in cap028_codex.get("source_decision_ids", [])
        or codex_projection_status.get("provider_id") != CODEX_PROVIDER_ID
        or codex_projection_status.get("classification") != "REMOVED_PAID_PROVIDER_TOMBSTONE"
        or codex_projection_status.get("reconciliation_status") != "DECOMMISSIONED_FREE_ONLY_POLICY"
        or codex_projection_status.get("runtime_activation_status") != "REMOVED_NOT_ADMITTED"
        or codex_projection_status.get("current_host_runtime_evidence") != "NOT_APPLICABLE_REMOVED"
        or codex_projection_status.get("economics_policy") != "FA3-FREE-SELF-HOSTED-ONLY-001"
    ):
        findings.append(
            finding(
                "FA3-RELEASE-PROJECTION-025",
                "Codex paid-provider decommission/free-only reconciliation invariant mismatch",
                reconciliation_status=codex.get("reconciliation_status"),
                runtime_activation_status=codex.get("runtime_activation_status"),
                current_host_production_e2e=codex.get("current_host_production_e2e"),
                missing_manifest_paths=codex_manifest_missing,
                cap028_codex_projection_status=codex_projection_status,
            )
        )

'''
    return patch_between(path, start, end, replacement)


def codex_reconciliation_literal(indent: str = "    ") -> str:
    return f'''{indent}projection["codex_reconciliation"] = {{
{indent}    "provider_id": "FA3-PROVIDER-CODEX-001",
{indent}    "gate_id": "FA3-CODEX-GATESET-001",
{indent}    "capability_id": "CAP-028",
{indent}    "classification": "REMOVED_PAID_PROVIDER_TOMBSTONE",
{indent}    "reconciliation_status": "DECOMMISSIONED_FREE_ONLY_POLICY",
{indent}    "runtime_activation_status": "REMOVED_NOT_ADMITTED",
{indent}    "current_host_production_e2e": "NOT_APPLICABLE_REMOVED",
{indent}    "provider_runtime_required_for_global_promotion_when_disabled": False,
{indent}    "economics_policy": "FA3-FREE-SELF-HOSTED-ONLY-001",
{indent}    "new_capabilities": 0,
{indent}    "new_architectural_authorities": 0,
{indent}    "capability_count_after": 143,
{indent}}}
{indent}projection["free_only_reconciliation"] = {{
{indent}    "policy_id": "FA3-FREE-SELF-HOSTED-ONLY-001",
{indent}    "gate_id": "FA3-FREE-ONLY-GATESET-001",
{indent}    "status": "CANONICAL_FAIL_CLOSED",
{indent}    "paid_provider_fallback": False,
{indent}    "capability_count_after": 143,
{indent}}}
'''


def patch_reconciler() -> bool:
    path = ROOT / "scripts/fa3_reconcile_release_projection.py"
    text = path.read_text(encoding="utf-8")
    if 'projection["codex_reconciliation"] = {' in text:
        return False
    marker = '    ls = run(root, "ls-tree", "-r", "--full-tree", snapshot)\n'
    if marker not in text:
        raise RuntimeError("release reconciler insertion marker missing")
    return write_if_changed(path, text.replace(marker, codex_reconciliation_literal() + "\n" + marker, 1))


def patch_regenerator() -> bool:
    path = ROOT / "src/fa3_release_projection_regenerate.py"
    text = path.read_text(encoding="utf-8")
    if 'projection["codex_reconciliation"] = {' in text:
        return False
    marker = '    manifest = []\n'
    if marker not in text:
        raise RuntimeError("release regenerator insertion marker missing")
    return write_if_changed(path, text.replace(marker, codex_reconciliation_literal() + "\n" + marker, 1))


def patch_evidence_registry() -> bool:
    path = ROOT / "evidence/evidence-registry.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    cap028 = next(x for x in obj.get("records", []) if x.get("subject_id") == "CAP-028")
    status = {
        "provider_id": CODEX_PROVIDER,
        "classification": "REMOVED_PAID_PROVIDER_TOMBSTONE",
        "reconciliation_status": "DECOMMISSIONED_FREE_ONLY_POLICY",
        "runtime_activation_status": "REMOVED_NOT_ADMITTED",
        "current_host_runtime_evidence": "NOT_APPLICABLE_REMOVED",
        "global_runtime_promotion_effect": "NONE_DECOMMISSIONED",
        "decommission_gate": CODEX_GATE,
        "economics_policy": POLICY_ID,
    }
    changed = cap028.get("codex_provider_projection_status") != status
    cap028["codex_provider_projection_status"] = status
    # Retain the historical decision ID as provenance only; the active decision is the free-only decision.
    src = cap028.setdefault("source_decision_ids", [])
    if CODEX_DECISION_HISTORY not in src:
        src.append(CODEX_DECISION_HISTORY)
        changed = True
    if "FA3-DEC-FREE-ONLY-2026-09-12" not in src:
        src.append("FA3-DEC-FREE-ONLY-2026-09-12")
        changed = True
    old_evidence = "evidence/reference/codex-adapter-ci-2026-08-31.json"
    if old_evidence in cap028.get("evidence_artifacts", []):
        cap028["evidence_artifacts"].remove(old_evidence)
        changed = True
    if changed:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def patch_policy() -> bool:
    path = ROOT / "canonical/enforcement-policy.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    gates = obj.setdefault("mandatory_reference_gates", [])
    changed = False
    if FREE_GATE not in gates:
        gates.append(FREE_GATE)
        changed = True
    if obj.get("provider_economics_policy") != POLICY_ID:
        obj["provider_economics_policy"] = POLICY_ID
        changed = True
    if obj.get("paid_provider_fallback") is not False:
        obj["paid_provider_fallback"] = False
        changed = True
    if changed:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def patch_global_enforce() -> bool:
    path = ROOT / "src/fa3_enforce.py"
    text = path.read_text(encoding="utf-8")
    original = text
    import_anchor = 'from fa3_codex_gate import gate as codex_gate, current_host_gate as codex_current_host_gate\n'
    if 'from fa3_free_only_gate import gate as free_only_gate\n' not in text:
        text = text.replace(import_anchor, import_anchor + 'from fa3_free_only_gate import gate as free_only_gate\n', 1)
    if '"release-projection","free-only","runtime"' not in text:
        text = text.replace('"static","release-projection","runtime"', '"static","release-projection","free-only","runtime"', 1)
    dispatch_anchor = '        if a.command=="release-projection":\n            x=release_projection_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED\n'
    if 'if a.command=="free-only":' not in text:
        text = text.replace(dispatch_anchor, dispatch_anchor + '        if a.command=="free-only":\n            x=free_only_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED\n', 1)
    static_anchor = '    if projection_ref["result"]!="PASS":\n        fs.append(finding("FA3-STATIC-039","Unified post-v3.0.11 canonical release projection gate failed",release_projection_gate=projection_ref))\n'
    if 'FA3-STATIC-101' not in text:
        text = text.replace(static_anchor, static_anchor + '\n    free_only_ref=free_only_gate(root)\n    if free_only_ref["result"]!="PASS":\n        fs.append(finding("FA3-STATIC-101","Free/self-hosted-only provider economics gate failed",free_only_gate=free_only_ref))\n', 1)
    codex_anchor = '    if "FA3-CODEX-GATESET-001" not in pol.get("mandatory_reference_gates",[]):\n        fs.append(finding("FA3-STATIC-048","Codex adapter gate is not bound into global enforcement policy"))\n'
    if 'FA3-STATIC-102' not in text:
        text = text.replace(codex_anchor, '    if "FA3-CODEX-GATESET-001" not in pol.get("mandatory_reference_gates",[]):\n        fs.append(finding("FA3-STATIC-048","Codex decommission guard is not bound into global enforcement policy"))\n    if "FA3-FREE-ONLY-GATESET-001" not in pol.get("mandatory_reference_gates",[]):\n        fs.append(finding("FA3-STATIC-102","Free/self-hosted-only economics gate is not bound into global enforcement policy"))\n', 1)
    if text == original:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    changes = {
        "release_gate": patch_release_gate(),
        "reconciler": patch_reconciler(),
        "regenerator": patch_regenerator(),
        "evidence_registry": patch_evidence_registry(),
        "enforcement_policy": patch_policy(),
        "global_enforce": patch_global_enforce(),
    }
    print(json.dumps(changes, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
