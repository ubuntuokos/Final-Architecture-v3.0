#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/fa3-dev-policy.json"
EVIDENCE_DIR = ROOT / "evidence/development/current"
STATE_DIR = ROOT / "state/development"
CANDIDATE_DIR = ROOT / "state/promotion-candidates"
SELF_EXCLUDES = (
    "evidence/development/current/**",
    "state/development/**",
    "state/promotion-candidates/**",
)


def _run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _load_policy() -> dict[str, Any]:
    try:
        return json.loads(POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FA3 dev policy unavailable/invalid: {exc}")


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _excluded(path: str, policy: dict[str, Any]) -> bool:
    patterns = list(policy.get("snapshot", {}).get("exclude", [])) + list(SELF_EXCLUDES)
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def _index_paths() -> list[str]:
    raw = _run_git("ls-files", "-z").stdout
    return sorted(p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p)


def _index_blob(path: str) -> bytes:
    result = _run_git("show", f":{path}", check=False)
    if result.returncode == 0:
        return result.stdout
    # A clean tracked file can still be read from HEAD if an unusual index state exists.
    result = _run_git("show", f"HEAD:{path}", check=False)
    if result.returncode != 0:
        raise RuntimeError(f"cannot read tracked Git blob: {path}")
    return result.stdout


def build_index_manifest() -> dict[str, Any]:
    policy = _load_policy()
    artifacts: list[dict[str, Any]] = []
    for path in _index_paths():
        if _excluded(path, policy):
            continue
        blob = _index_blob(path)
        artifacts.append({"path": path, "sha256": _sha256(blob), "size_bytes": len(blob)})
    payload = {
        "schema": "fa3.dev-index-manifest.v1",
        "source": "GIT_INDEX",
        "hash_algorithm": "sha256",
        "evidence_self_excluded": True,
        "artifacts": artifacts,
    }
    payload["manifest_digest"] = "sha256:" + _sha256(_canonical_bytes(payload))
    return payload


def snapshot(extra_taint: list[str] | None = None) -> dict[str, Any]:
    policy = _load_policy()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_index_manifest()
    taint = sorted(set(extra_taint or []))
    receipt = {
        "schema": "fa3.dev-snapshot-receipt.v1",
        "environment": "development",
        "status": "DEV_TAINTED" if taint else "DEV_DRAFT",
        "authoritative": False,
        "production_eligible": False,
        "manifest_digest": manifest["manifest_digest"],
        "tainted": bool(taint),
        "taint_reasons": taint,
        "maker_checker": policy.get("workspace", {}).get("maker_checker", "DEFERRED"),
        "canonical_write": "DENY",
        "created_unix": int(time.time()),
    }
    (EVIDENCE_DIR / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (EVIDENCE_DIR / "receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (EVIDENCE_DIR / "hashes.sha256").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in manifest["artifacts"]), encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2))
    return receipt


def verify_snapshot(source: str = "index") -> bool:
    manifest_path = EVIDENCE_DIR / "artifact-manifest.json"
    receipt_path = EVIDENCE_DIR / "receipt.json"
    if not manifest_path.exists() or not receipt_path.exists():
        raise SystemExit("FA3 development snapshot missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    claimed = manifest.get("manifest_digest")
    manifest_copy = dict(manifest)
    manifest_copy.pop("manifest_digest", None)
    expected = "sha256:" + _sha256(_canonical_bytes(manifest_copy))
    if claimed != expected or receipt.get("manifest_digest") != expected:
        raise SystemExit("FA3 development snapshot digest mismatch")
    if receipt.get("authoritative") is not False or receipt.get("production_eligible") is not False:
        raise SystemExit("development evidence illegally claims production authority")
    if source == "index":
        regenerated = build_index_manifest()
        if regenerated.get("manifest_digest") != expected:
            raise SystemExit("development snapshot does not match Git index")
    print("FA3 DEV SNAPSHOT PASS")
    return True


def enter() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    session = {
        "schema": "fa3.dev-session.v1",
        "session_id": f"dev-{int(time.time())}-{os.getpid()}",
        "environment": "development",
        "policy_id": "FA3-DEV-POLICY-001",
        "production_eligible": False,
        "canonical_write": "DENY",
        "tainted": False,
        "created_unix": int(time.time()),
    }
    (STATE_DIR / "session.json").write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(session, indent=2))


def status(field: str | None = None) -> None:
    path = STATE_DIR / "session.json"
    if not path.exists():
        value: Any = {"environment": "production", "active_dev_session": False}
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["active_dev_session"] = True
    if field:
        print(value.get(field, ""))
    else:
        print(json.dumps(value, indent=2))


def freeze() -> None:
    verify_snapshot("index")
    manifest = json.loads((EVIDENCE_DIR / "artifact-manifest.json").read_text(encoding="utf-8"))
    receipt = json.loads((EVIDENCE_DIR / "receipt.json").read_text(encoding="utf-8"))
    candidate_id = f"dev-{int(time.time())}-{manifest['manifest_digest'].split(':', 1)[1][:12]}"
    target = CANDIDATE_DIR / candidate_id
    target.mkdir(parents=True, exist_ok=False)
    candidate = {
        "schema": "fa3.promotion-candidate.v1",
        "candidate_id": candidate_id,
        "source_environment": "development",
        "source_manifest_digest": manifest["manifest_digest"],
        "source_tainted": bool(receipt.get("tainted")),
        "immutable": True,
        "canonical": False,
        "production_eligible": False,
        "status": "CANDIDATE_FROZEN",
        "promotion_status": "VALIDATION_REQUIRED",
    }
    candidate["candidate_digest"] = "sha256:" + _sha256(_canonical_bytes(candidate))
    for name in ("artifact-manifest.json", "receipt.json", "hashes.sha256"):
        (target / name).write_bytes((EVIDENCE_DIR / name).read_bytes())
    (target / "candidate.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(candidate, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Development Mode control")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("enter")
    p_status = sub.add_parser("status")
    p_status.add_argument("--field")
    p_snap = sub.add_parser("snapshot")
    p_snap.add_argument("--taint", action="append", default=[])
    p_verify = sub.add_parser("verify-snapshot")
    p_verify.add_argument("--source", choices=["index", "none"], default="index")
    sub.add_parser("freeze")
    args = parser.parse_args()
    if args.command == "enter":
        enter()
    elif args.command == "status":
        status(args.field)
    elif args.command == "snapshot":
        snapshot(args.taint)
    elif args.command == "verify-snapshot":
        verify_snapshot("index" if args.source == "index" else "none")
    elif args.command == "freeze":
        freeze()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
