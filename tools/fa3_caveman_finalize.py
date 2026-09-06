#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "1d8a3ffaa2b4d11abcc6003250ff66b4798eef60"
PROJECTION_PATH = Path("canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")
TEMP_PATHS = [Path("tools/fa3_caveman_finalize.py"), Path(".github/workflows/fa3-caveman-finalize.yml")]
GATE_ID = "FA3-CAVEMAN-GATESET-001"
PROVIDER_ID = "FA3-PROVIDER-CAVEMAN-001"
CONTRACT_ID = "FA3-CONTEXT-TRANSFORM-CONTRACTS-001"
DECISION_ID = "FA3-DEC-CAVEMAN-2026-08-30"
CAPABILITY_ID = "CAP-010"
P0_RULES = [
    "CAVEMAN_RECOVERY_BEFORE_LOSSY_TRANSFORM",
    "CAVEMAN_CANONICAL_ORIGINAL_IMMUTABLE",
    "CAVEMAN_FAILURE_UNSUPPORTED_EXACT_PASS_THROUGH",
    "CAVEMAN_MEASURABLE_BENEFIT_GATE_REQUIRED",
    "CAVEMAN_SEMANTIC_FIDELITY_AND_TASK_SUCCESS_GATE_REQUIRED",
    "CAVEMAN_MEASUREMENT_PROVENANCE_CLASS_REQUIRED",
    "CAVEMAN_RECORD_BASELINE_BEFORE_OPTIMIZE",
    "CAVEMAN_UNKNOWN_UNSUPPORTED_NO_TRANSFORM",
    "CAVEMAN_SOURCE_HASH_RECOVERY_LINEAGE_REQUIRED",
    "CAVEMAN_RECOVERY_STORE_SENSITIVE_AND_HARDENED",
    "CAVEMAN_BOUNDED_INPUT_RECOVERY_AND_RETENTION",
    "CAVEMAN_CACHE_STABILITY_VOLATILITY_EXPLICIT",
    "CAVEMAN_SEMANTIC_DEGRADATION_ROLLBACK_REQUIRED",
    "CAVEMAN_TELEMETRY_OFF_UNLESS_EXPLICITLY_AUTHORIZED",
    "CAVEMAN_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
]


def run(*args: str, capture: bool = True) -> str:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=capture, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.strip() if capture else ""


def loadj(path: Path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def writej(path: Path, obj) -> None:
    (ROOT / path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def insert_after_once(text: str, anchor: str, addition: str, label: str) -> str:
    if addition.strip() in text:
        return text
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(anchor, anchor + addition, 1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def update_policy() -> None:
    path = Path("canonical/enforcement-policy.json")
    obj = loadj(path)
    gates = obj.setdefault("mandatory_reference_gates", [])
    if GATE_ID not in gates:
        gates.append(GATE_ID)
    obj["caveman_provider_id"] = PROVIDER_ID
    obj["caveman_context_transform_contract_id"] = CONTRACT_ID
    obj["caveman_mandatory_p0_rules"] = P0_RULES
    writej(path, obj)


def update_registry() -> None:
    path = Path("evidence/evidence-registry.json")
    obj = loadj(path)
    rec = next((x for x in obj.get("records", []) if x.get("subject_id") == CAPABILITY_ID), None)
    if rec is None:
        raise RuntimeError("CAP-010 missing from Evidence Registry")
    decisions = rec.setdefault("source_decision_ids", [])
    if DECISION_ID not in decisions:
        decisions.append(DECISION_ID)
    evidence = rec.setdefault("evidence_artifacts", [])
    for item in (
        "evidence/reference/caveman-ci-2026-08-31.json",
        "evidence/reference/caveman-global-reconciliation-ci-2026-08-31.json",
    ):
        if item not in evidence:
            evidence.append(item)
    rec["caveman_provider_projection_status"] = {
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "reference_gate_status": "PASS",
        "runtime_activation_status": "NOT_PROMOTED_REFERENCE_ONLY",
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "provider_runtime_required_for_global_promotion_when_disabled": False,
    }
    if rec.get("runtime_conformance") != "EVIDENCE-PENDING":
        raise RuntimeError("CAP-010 runtime_conformance must remain EVIDENCE-PENDING")
    if rec.get("status") != "PENDING_CURRENT_HOST":
        raise RuntimeError("CAP-010 status must remain PENDING_CURRENT_HOST")
    if rec.get("promotion_state") != "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE":
        raise RuntimeError("CAP-010 promotion state changed unexpectedly")
    writej(path, obj)


def update_enforcer() -> None:
    path = ROOT / "src/fa3_enforce.py"
    text = path.read_text(encoding="utf-8")
    text = insert_after_once(
        text,
        "from fa3_autogpt_gate import gate as autogpt_gate\n",
        "from fa3_caveman_gate import gate as caveman_gate\n",
        "Caveman import",
    )
    text = insert_after_once(
        text,
        '    if "FA3-AUTOGPT-GATESET-001" not in pol.get("mandatory_reference_gates",[]):\n        fs.append(finding("FA3-STATIC-037","AutoGPT agentic-workflow boundary gate is not bound into global enforcement policy"))\n',
        '    if "FA3-CAVEMAN-GATESET-001" not in pol.get("mandatory_reference_gates",[]):\n        fs.append(finding("FA3-STATIC-091","Caveman recoverable context-transformation gate is not bound into global enforcement policy"))\n',
        "Caveman policy binding",
    )
    text = insert_after_once(
        text,
        '    autogpt_ref=autogpt_gate(root)\n    if autogpt_ref["result"]!="PASS":\n        fs.append(finding("FA3-STATIC-038","AutoGPT mandatory agentic workflow/boundary regression gate failed",autogpt_gate=autogpt_ref))\n',
        '    caveman_ref=caveman_gate(root)\n    if caveman_ref["result"]!="PASS":\n        fs.append(finding("FA3-STATIC-092","Caveman recoverable context-transformation regression gate failed",caveman_gate=caveman_ref))\n',
        "Caveman static execution",
    )
    text = replace_once(
        text,
        '"autogpt_gate_status":autogpt_ref["result"],',
        '"autogpt_gate_status":autogpt_ref["result"],"caveman_gate_status":caveman_ref["result"],',
        "Caveman static report detail",
    )
    text = replace_once(
        text,
        '"external-api-discovery","autogpt","ai-infra-guard"',
        '"external-api-discovery","autogpt","caveman","ai-infra-guard"',
        "Caveman CLI choice",
    )
    text = insert_after_once(
        text,
        '        if a.command=="autogpt":\n            x=autogpt_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED\n',
        '        if a.command=="caveman":\n            x=caveman_gate(root); print(json.dumps(x,indent=2)); return OK if x["result"]=="PASS" else BLOCKED\n',
        "Caveman CLI dispatch",
    )
    path.write_text(text, encoding="utf-8")


def parse_delta(snapshot: str):
    raw = run("git", "diff", "--name-status", "--find-renames", BASE_COMMIT, snapshot)
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith(("R", "C")):
            if len(parts) < 3:
                raise RuntimeError(f"invalid rename/copy row: {line}")
            path = parts[-1]
        else:
            if len(parts) < 2:
                raise RuntimeError(f"invalid delta row: {line}")
            path = parts[1]
        rows.append((status, path))
    return rows


def mutable_release_path(path: str) -> bool:
    parts = Path(path).parts
    if not parts:
        return True
    if parts[0] in {"reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache"}:
        return True
    if "__pycache__" in parts:
        return True
    if path.startswith("evidence/receipts/") and path != "evidence/receipts/.gitkeep":
        return True
    return False


def manifest_for(snapshot: str, delta_rows):
    status_map = {path: status for status, path in delta_rows}
    raw = run("git", "ls-tree", "-r", "--full-tree", snapshot)
    out = []
    for line in raw.splitlines():
        meta, path = line.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind != "blob" or path == PROJECTION_PATH.as_posix() or mutable_release_path(path):
            continue
        status = status_map.get(path, "UNCHANGED")
        if status.startswith("A"):
            delta_status = "added"
        elif status.startswith("M"):
            delta_status = "modified"
        elif status.startswith("R"):
            delta_status = "renamed"
        elif status.startswith("C"):
            delta_status = "copied"
        elif status == "UNCHANGED":
            delta_status = "unchanged"
        else:
            delta_status = status.lower()
        out.append({"path": path, "git_blob_sha": sha, "baseline_delta_status": delta_status})
    out.sort(key=lambda x: x["path"])
    return out


def regenerate_projection(snapshot: str) -> None:
    path = PROJECTION_PATH
    obj = loadj(path)
    policy = loadj(Path("canonical/enforcement-policy.json"))
    registry = loadj(Path("evidence/evidence-registry.json"))
    delta = parse_delta(snapshot)
    paths = [p for _, p in delta]

    def pref(prefix: str):
        return sorted(p for p in paths if p.startswith(prefix))

    root_tree = run("git", "rev-parse", f"{snapshot}^{{tree}}")
    canonical_tree = run("git", "rev-parse", f"{snapshot}:canonical")
    commit_count = int(run("git", "rev-list", "--count", f"{BASE_COMMIT}..{snapshot}"))
    added = sum(s.startswith("A") for s, _ in delta)
    modified = sum(s.startswith("M") for s, _ in delta)
    removed = sum(s.startswith("D") for s, _ in delta)
    other = len(delta) - added - modified - removed
    manifest = manifest_for(snapshot, delta)

    obj["source_snapshot"] = {
        "snapshot_semantics": "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR",
        "baseline_commit_sha": BASE_COMMIT,
        "pre_projection_head_sha": snapshot,
        "pre_projection_root_tree_sha": root_tree,
        "pre_projection_canonical_tree_sha": canonical_tree,
        "commits_ahead_of_v3_0_11_conformance_commit": commit_count,
        "total_post_baseline_commits": commit_count,
        "delta_file_count": len(delta),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
    }
    obj["overlay_inventory"] = {
        "canonical_files_in_post_baseline_delta": len(pref("canonical/")),
        "evidence_files_in_post_baseline_delta": len(pref("evidence/")),
        "source_files_in_post_baseline_delta": len(pref("src/")),
        "test_files_in_post_baseline_delta": len(pref("tests/")),
        "workflow_files_in_post_baseline_delta": len(pref(".github/workflows/")),
        "provider_records": pref("canonical/providers/"),
        "profile_records": pref("canonical/profiles/"),
        "contract_records": pref("canonical/contracts/"),
        "decision_records": pref("canonical/decisions/"),
        "upstream_reference_records": pref("canonical/references/"),
        "reference_evidence_records": pref("evidence/reference/"),
    }
    obj["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))
    obj["manifest"] = manifest
    obj["manifest_entry_count"] = len(manifest)
    scope = obj.setdefault("manifest_scope", {})
    scope.update({
        "repository_release_surface_complete": True,
        "self_excluded_path": PROJECTION_PATH.as_posix(),
        "mutable_runtime_evidence_receipts_excluded": True,
        "source_snapshot_anchor": snapshot,
        "regenerated_from_branch_head": snapshot,
    })
    obj["caveman_reconciliation"] = {
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "gate_id": GATE_ID,
        "capability_id": CAPABILITY_ID,
        "classification": "OPTIONAL_CONTEXT_TRANSFORMATION_REFERENCE_PROVIDER",
        "reconciliation_status": "GLOBAL_PROJECTION_RECONCILED_REFERENCE_RUNTIME_NOT_PROMOTED",
        "runtime_activation_status": "NOT_PROMOTED_REFERENCE_ONLY",
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "provider_runtime_required_for_global_promotion_when_disabled": False,
        "upstream_release": "v2.4.0",
        "upstream_commit": "df2ccd85c94ec3c8289cb62ac020d241ccfb0c60",
        "reference_gate_status": "PASS",
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    ev = obj.setdefault("evidence_registry", {})
    ev["caveman_capability_binding"] = {
        "subject_id": CAPABILITY_ID,
        "provider_id": PROVIDER_ID,
        "decision_id": DECISION_ID,
        "reference_evidence": [
            "evidence/reference/caveman-ci-2026-08-31.json",
            "evidence/reference/caveman-global-reconciliation-ci-2026-08-31.json",
        ],
        "runtime_status": "PENDING_CURRENT_HOST",
        "provider_runtime_status": "NOT_PROMOTED_REFERENCE_ONLY",
    }
    notes = obj.setdefault("projection_notes", [])
    note = (
        "FA3-PROVIDER-CAVEMAN-001 materialized under FA3-KNOWLEDGE-001 with a provider-neutral "
        "recoverable context-transformation contract, 15-rule executable fail-closed regression gate, "
        "PASS reference evidence and CAP-010/global inventory reconciliation; capability count remains "
        "143 and Caveman receives no architectural authority or runtime promotion."
    )
    if note not in notes:
        notes.append(note)

    cap = next(x for x in registry.get("records", []) if x.get("subject_id") == CAPABILITY_ID)
    if cap.get("status") != "PENDING_CURRENT_HOST" or cap.get("runtime_conformance") != "EVIDENCE-PENDING":
        raise RuntimeError("CAP-010 runtime state was unexpectedly promoted")
    writej(path, obj)


def configure_git() -> None:
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")


def main() -> int:
    branch = os.environ.get("GITHUB_REF_NAME", "")
    if branch and branch != "fa3/caveman-finalize-2026-09-06":
        raise RuntimeError(f"unexpected branch: {branch}")
    configure_git()
    update_policy()
    update_registry()
    update_enforcer()

    for temp in TEMP_PATHS:
        p = ROOT / temp
        if p.exists():
            p.unlink()

    run("git", "add", "-A")
    status = run("git", "status", "--porcelain")
    if not status:
        raise RuntimeError("phase-1 global reconciliation produced no changes")
    run("git", "commit", "-m", "FA3 Caveman: bind global policy and evidence reconciliation")
    snapshot = run("git", "rev-parse", "HEAD")

    regenerate_projection(snapshot)
    run("git", "add", PROJECTION_PATH.as_posix())
    changed = run("git", "diff", "--cached", "--name-only").splitlines()
    if changed != [PROJECTION_PATH.as_posix()]:
        raise RuntimeError(f"phase-2 must change only projection, got: {changed}")
    run("git", "commit", "-m", "FA3 Caveman: reconcile unified release projection [caveman-finalized]")

    run("python", "-m", "py_compile", "src/fa3_caveman_gate.py", "src/fa3_enforce.py")
    run("python", "-m", "unittest", "discover", "-s", "tests", "-v", capture=False)
    run("./bin/fa3-enforce", "caveman", capture=False)
    run("./bin/fa3-enforce", "release-projection", capture=False)
    run("./bin/fa3-enforce", "static", capture=False)

    final_head = run("git", "rev-parse", "HEAD")
    print(json.dumps({
        "result": "PASS",
        "snapshot": snapshot,
        "final_head": final_head,
        "capability_count": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }, indent=2))
    run("git", "push", "origin", f"HEAD:{branch}", capture=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
