#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "1d8a3ffaa2b4d11abcc6003250ff66b4798eef60"
PROJECTION = ROOT / "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
POLICY = ROOT / "canonical/enforcement-policy.json"
REGISTRY = ROOT / "evidence/evidence-registry.json"
AUDIT_DECISION = "FA3-DEC-FFMPEG-AI-CURRENT-HOST-AUDIT-2026-09-03"
CAPS = {"CAP-005", "CAP-006", "CAP-016", "CAP-121", "CAP-126", "CAP-137"}
MUTABLE_TOP = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache", ".fa3-current-host"}


def run(*args: str) -> str:
    p = subprocess.run(["git", "-C", str(ROOT), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout.strip()


def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def write(path: Path, obj): path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def blob_sha(path: Path) -> str:
    data = path.read_bytes(); return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

def mutable(rel: str) -> bool:
    parts = Path(rel).parts
    return (not parts or parts[0] in MUTABLE_TOP or "__pycache__" in parts or (rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep"))


def reconcile_bindings() -> bool:
    changed = False
    policy = load(POLICY)
    updates = {
        "ffmpeg_ai_current_host_conformance_id": "FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001",
        "ffmpeg_ai_current_host_executable_gate_id": "FA3-GATE-FFMPEG-AI-CURRENT-HOST-001",
        "ffmpeg_ai_current_host_gateset_id": "FA3-FFMPEG-AI-CURRENT-HOST-GATESET-001",
        "ffmpeg_ai_current_host_audit_decision_id": AUDIT_DECISION,
        "ffmpeg_ai_current_host_evidence_level": "CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_PASS",
        "ffmpeg_ai_current_host_production_evidence_level": "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS",
        "ffmpeg_ai_current_host_state": "EXECUTION_CONFORMANCE_HARDENED_PRODUCTION_E2E_PENDING",
        "ffmpeg_ai_current_host_global_promotion_claim": False,
    }
    for k, v in updates.items():
        if policy.get(k) != v: policy[k] = v; changed = True
    if changed: write(POLICY, policy)

    reg = load(REGISTRY); reg_changed = False
    parent = {
        "profile_id": "FA3-NEURAL-MEDIA-EXECUTION-001",
        "contract_id": "FA3-NEURAL-MEDIA-EXECUTION-CONTRACTS-001",
        "provider_ids": ["FA3-PROVIDER-FFMPEG-001", "FA3-PROVIDER-VS-MLRT-001"],
        "gate_id": "FA3-FFMPEG-AI-GATESET-001",
        "reference_evidence": "evidence/reference/ffmpeg-ai-ci-2026-09-03.json",
        "runtime_status": "PENDING_REAL_CURRENT_HOST_PRODUCTION_E2E",
        "current_host_runtime_evidence": "PENDING_REAL_CURRENT_HOST_PRODUCTION_E2E",
        "ci_reference_pass_does_not_promote_runtime": True,
    }
    current = {
        "conformance_id": "FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001",
        "gate_id": "FA3-GATE-FFMPEG-AI-CURRENT-HOST-001",
        "workflow": ".github/workflows/fa3-ffmpeg-ai-current-host.yml",
        "state": "EXECUTION_CONFORMANCE_HARDENED_PRODUCTION_E2E_PENDING",
        "execution_conformance_evidence_level_required": "CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_PASS",
        "production_evidence_level_required": "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS",
        "execution_conformance_can_promote_runtime": False,
        "production_e2e_status": "PENDING_REAL_CURRENT_HOST_PRODUCTION_E2E",
        "component_pass_claim": False,
        "global_promotion_claim": False,
    }
    for rec in reg.get("records", []):
        if rec.get("subject_id") not in CAPS: continue
        ids = rec.setdefault("source_decision_ids", [])
        if AUDIT_DECISION not in ids: ids.append(AUDIT_DECISION); reg_changed = True
        if rec.get("ffmpeg_ai_projection_status") != parent: rec["ffmpeg_ai_projection_status"] = parent; reg_changed = True
        if rec.get("ffmpeg_ai_current_host_projection_status") != current: rec["ffmpeg_ai_current_host_projection_status"] = current; reg_changed = True
    top = {
        **current,
        "audit_decision_id": AUDIT_DECISION,
        "capability_bindings": sorted(CAPS),
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    if reg.get("ffmpeg_ai_current_host_reconciliation") != top:
        reg["ffmpeg_ai_current_host_reconciliation"] = top; reg_changed = True
    if reg_changed: write(REGISTRY, reg)
    return changed or reg_changed


def diff_rows(snapshot: str):
    raw = run("diff", "--name-status", "--find-renames", BASE_COMMIT, snapshot)
    rows=[]
    for line in raw.splitlines():
        if not line: continue
        p=line.split("\t"); status=p[0]; path=p[-1] if status.startswith(("R","C")) else p[1]; rows.append((status,path))
    return rows


def reconcile_projection(snapshot: str) -> None:
    p = load(PROJECTION); rows = diff_rows(snapshot); paths=[x[1] for x in rows]
    pref=lambda s: sorted(x for x in paths if x.startswith(s))
    p["source_snapshot"].update({
        "pre_projection_head_sha": run("rev-parse", snapshot),
        "pre_projection_root_tree_sha": run("rev-parse", f"{snapshot}^{{tree}}"),
        "pre_projection_canonical_tree_sha": run("rev-parse", f"{snapshot}:canonical"),
        "commits_ahead_of_v3_0_11_conformance_commit": int(run("rev-list", "--count", f"{BASE_COMMIT}..{snapshot}")),
        "total_post_baseline_commits": int(run("rev-list", "--count", f"{BASE_COMMIT}..{snapshot}")),
        "delta_file_count": len(rows),
        "delta_added_files": sum(s.startswith("A") for s,_ in rows),
        "delta_modified_files": sum(s.startswith("M") for s,_ in rows),
        "delta_removed_files": sum(s.startswith("D") for s,_ in rows),
        "delta_other_files": sum(not s.startswith(("A","M","D")) for s,_ in rows),
    })
    inv=p["overlay_inventory"]
    inv.update({
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
    })
    ff=p.setdefault("ffmpeg_ai_reconciliation", {})
    ff.update({
        "runtime_activation_status": "PENDING_REAL_CURRENT_HOST_PRODUCTION_E2E",
        "current_host_runtime_evidence": "PENDING_REAL_CURRENT_HOST_PRODUCTION_E2E",
        "current_host_runtime_promotion_claim": False,
        "current_host_conformance_id": "FA3-FFMPEG-AI-RUNTIME-CONFORMANCE-001",
        "current_host_executable_gate_id": "FA3-GATE-FFMPEG-AI-CURRENT-HOST-001",
        "current_host_audit_decision_id": AUDIT_DECISION,
        "current_host_workflow": ".github/workflows/fa3-ffmpeg-ai-current-host.yml",
        "current_host_closure_status": "EXECUTION_CONFORMANCE_HARDENED_PRODUCTION_E2E_PENDING",
        "current_host_execution_conformance_evidence_level": "CURRENT_HOST_FFMPEG_EXECUTION_CONFORMANCE_PASS",
        "current_host_required_production_evidence_level": "CURRENT_HOST_FFMPEG_NEURAL_MEDIA_PRODUCTION_E2E_PASS",
        "execution_conformance_can_promote_runtime": False,
    })
    tracked = run("ls-files").splitlines()
    manifest=[]
    for rel in sorted(tracked):
        if rel == str(PROJECTION.relative_to(ROOT)) or mutable(rel): continue
        path=ROOT/rel
        if path.is_file(): manifest.append({"path": rel, "git_blob_sha": blob_sha(path)})
    p["manifest"] = manifest; p["manifest_entry_count"] = len(manifest)
    p["last_reconciled_at"] = "2026-09-03"; p["last_regenerated_at"] = "2026-09-03"
    write(PROJECTION, p)


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("mode", choices=("bindings","projection")); ap.add_argument("--snapshot")
    a=ap.parse_args()
    if a.mode=="bindings": reconcile_bindings()
    else:
        if not a.snapshot: raise SystemExit("--snapshot required")
        reconcile_projection(a.snapshot)
    return 0

if __name__ == "__main__": raise SystemExit(main())
