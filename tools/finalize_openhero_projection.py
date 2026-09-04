#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_PATH = "canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json"
GATESET_ID = "FA3-WEB-CREATIVE-ASSET-GATESET-001"
PROVIDER_ID = "FA3-PROVIDER-OPENHERO-001"
CONTRACT_ID = "FA3-WEB-CREATIVE-ASSET-PACKAGING-DELIVERY-CONTRACTS-001"
DECISION_ID = "FA3-DEC-OPENHERO-WEB-CREATIVE-ASSET-2026-09-04"
EVIDENCE_PATH = "evidence/reference/openhero-web-creative-asset-ci-2026-09-04.json"
UPSTREAM_PIN = "d599548dd09fce4aff66e076c4ab87d73e1e8a3d"
CAPABILITIES = ["CAP-003", "CAP-004", "CAP-011", "CAP-016", "CAP-019", "CAP-038", "CAP-047", "CAP-049", "CAP-103", "CAP-125"]
TEMP_PATHS = {
    ".github/workflows/fa3-openhero-reconcile.yml",
    "tools/reconcile_openhero_materialization.py",
    "tools/apply_openhero_nonworkflow.py",
    "tools/finalize_openhero_projection.py",
}
MUTABLE_TOP_LEVEL = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache", ".fa3-current-host"}


def run(*args: str) -> str:
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{p.stdout}\n{p.stderr}")
    return p.stdout.strip()


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def mutable(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts or parts[0] in MUTABLE_TOP_LEVEL or "__pycache__" in parts:
        return True
    return rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep"


def main() -> None:
    path = ROOT / PROJECTION_PATH
    projection = json.loads(path.read_text(encoding="utf-8"))
    gates = projection.setdefault("mandatory_reference_gates", [])
    if GATESET_ID not in gates:
        gates.append(GATESET_ID)
    projection["openhero_web_creative_asset_reconciliation"] = {
        "provider_id": PROVIDER_ID,
        "contract_id": CONTRACT_ID,
        "decision_id": DECISION_ID,
        "gate_id": GATESET_ID,
        "upstream_pin": UPSTREAM_PIN,
        "capability_ids": CAPABILITIES,
        "classification": "OPTIONAL_REFERENCE_WEB_CREATIVE_ASSET_PROVIDER",
        "reconciliation_status": "GLOBAL_PROJECTION_RECONCILED_REFERENCE_ADMISSION_GATE_PASS_RUNTIME_NOT_DEPENDENCY",
        "runtime_activation_status": "REFERENCE_ONLY_NOT_RUNTIME_DEPENDENCY",
        "current_host_runtime_evidence": "NOT_CLAIMED",
        "reference_evidence": EVIDENCE_PATH,
        "reference_evidence_status": "PASS",
        "provider_runtime_required_for_global_promotion_when_disabled": False,
        "code_license_media_rights_separate": True,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    files = []
    for item in ROOT.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(ROOT).as_posix()
        if rel == PROJECTION_PATH or rel in TEMP_PATHS or mutable(rel):
            continue
        files.append(rel)
    files.sort()
    projection["manifest"] = [{"path": rel, "git_blob_sha": blob_sha(ROOT / rel)} for rel in files]
    projection["manifest_entry_count"] = len(files)
    path.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", PROJECTION_PATH)
    run("git", "commit", "-m", "FA3: finalize OpenHero unified release projection")
    branch = os.environ.get("GITHUB_REF_NAME") or run("git", "branch", "--show-current")
    run("git", "push", "origin", f"HEAD:{branch}")
    print(json.dumps({"status": "PASS", "manifest_entry_count": len(files), "head": run("git", "rev-parse", "HEAD")}, indent=2))


if __name__ == "__main__":
    main()
