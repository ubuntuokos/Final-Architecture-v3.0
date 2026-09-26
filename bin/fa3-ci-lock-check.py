#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_release_baseline import load_active_release_baseline

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"[FA3-CI][FAIL-CLOSED] {message}", file=sys.stderr)
    raise SystemExit(2)


def git_tracked(prefix: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", prefix],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return [line for line in proc.stdout.splitlines() if line]


def main() -> int:
    required = [
        ROOT / "canonical/FA3-DEV-MODE-001.json",
        ROOT / "canonical/FA3-UPDATE-FABRIC-001.json",
        ROOT / "canonical/FA3-SECURITY-UPDATE-001.json",
        ROOT / "canonical/FA3-UPDATE-RESTART-001.json",
        ROOT / "config/fa3-dev-policy.json",
        ROOT / "config/fa3-update-policy.json",
    ]
    for path in required:
        if not path.exists():
            fail(f"required control file missing: {path.relative_to(ROOT)}")

    dev = json.loads((ROOT / "canonical/FA3-DEV-MODE-001.json").read_text(encoding="utf-8"))
    baseline = load_active_release_baseline(ROOT)
    if dev.get("capability_count") != baseline.capability_count:
        fail("canonical capability count changed")
    if dev.get("trust_domains", {}).get("development", {}).get("canonical_write") != "DENY":
        fail("development domain gained canonical write authority")

    legacy = ROOT / "canonical/conversation-reconciliation-enforcement.json"
    if legacy.exists():
        data = json.loads(legacy.read_text(encoding="utf-8"))
        if "frozen_dev_artifacts" in data:
            fail("legacy frozen_dev_artifacts contamination detected in canonical SSOT")

    tracked_candidates = git_tracked("state/promotion-candidates")
    if tracked_candidates:
        fail("mutable/frozen local promotion candidates must not be committed: " + ", ".join(tracked_candidates[:8]))

    evidence_dir = Path(
        os.environ.get("FA3_DEV_EVIDENCE_DIR", str(ROOT / "evidence/development/current"))
    ).resolve()
    receipt_path = evidence_dir / "receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("authoritative") is not False or receipt.get("production_eligible") is not False:
            fail("development receipt illegally claims production authority")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "src/fa3_dev_mode.py"), "verify-snapshot", "--source", "index"],
            cwd=ROOT,
        )
        if proc.returncode != 0:
            fail("development snapshot does not match checked-out Git tree/index")

    gate = subprocess.run([sys.executable, str(ROOT / "src/fa3_dev_update_gate.py")], cwd=ROOT)
    if gate.returncode != 0:
        fail("canonical Dev/Update gate failed")

    print("[FA3-CI] Development boundary lock: PASS")
    print(f"[FA3-CI] capability_delta=0 authority_delta=0 capability_count={baseline.capability_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
