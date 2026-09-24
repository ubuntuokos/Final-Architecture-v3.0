#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/fa3-dev-policy.json"
EVIDENCE_DIR = Path(os.environ.get("FA3_DEV_EVIDENCE_DIR", str(ROOT / "evidence/development/current"))).resolve()
STATE_DIR = ROOT / "state/development"
SESSION_PATH = STATE_DIR / "session.json"
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


def _index_entries() -> list[tuple[str, str, str]]:
    """Return sorted (path, git_mode, object_id) entries from stage 0 of the Git index."""
    raw = _run_git("ls-files", "-s", "-z").stdout
    entries: list[tuple[str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_id, stage = metadata.split(b" ", 2)
        except ValueError as exc:
            raise RuntimeError("invalid Git index record") from exc
        if stage != b"0":
            raise RuntimeError("unmerged Git index is not eligible for an FA3 snapshot")
        path = raw_path.decode("utf-8", "surrogateescape")
        entries.append((path, mode.decode("ascii"), object_id.decode("ascii")))
    return sorted(entries, key=lambda item: item[0])


def _read_git_blobs(object_ids: list[str]) -> dict[str, bytes]:
    """Read Git blobs through one request/response cat-file process without pipe deadlock."""
    ordered = list(dict.fromkeys(object_ids))
    if not ordered:
        return {}
    process = subprocess.Popen(
        ["git", "-C", str(ROOT), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    blobs: dict[str, bytes] = {}
    try:
        for requested in ordered:
            # Request one object and consume its complete response before sending the
            # next request. This preserves the single-process optimization while
            # preventing stdin/stdout pipe backpressure from deadlocking large indexes.
            process.stdin.write(f"{requested}\n".encode("ascii"))
            process.stdin.flush()

            header = process.stdout.readline()
            if not header:
                process.kill()
                raise RuntimeError(f"Git cat-file ended before object {requested}")
            fields = header.rstrip(b"\n").split(b" ")
            if len(fields) == 2 and fields[1] == b"missing":
                process.kill()
                raise RuntimeError(f"Git index object missing: {requested}")
            if len(fields) != 3 or fields[1] != b"blob":
                process.kill()
                raise RuntimeError(f"Git index object is not a blob: {requested}")
            size = int(fields[2])
            data = process.stdout.read(size)
            separator = process.stdout.read(1)
            if len(data) != size or separator != b"\n":
                process.kill()
                raise RuntimeError(f"truncated Git blob stream: {requested}")
            blobs[requested] = data

        process.stdin.close()
        stderr = process.stderr.read()
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(f"git cat-file --batch failed: {stderr.decode('utf-8', 'replace')}")
        return blobs
    finally:
        if not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()


def build_index_manifest() -> dict[str, Any]:
    policy = _load_policy()
    entries = [entry for entry in _index_entries() if not _excluded(entry[0], policy)]
    blobs = _read_git_blobs([entry[2] for entry in entries])
    artifacts: list[dict[str, Any]] = []
    for path, git_mode, object_id in entries:
        blob = blobs[object_id]
        artifacts.append(
            {
                "path": path,
                "git_mode": git_mode,
                "sha256": _sha256(blob),
                "size_bytes": len(blob),
            }
        )
    payload = {
        "schema": "fa3.dev-index-manifest.v1",
        "source": "GIT_INDEX",
        "hash_algorithm": "sha256",
        "binds_git_mode": True,
        "evidence_self_excluded": True,
        "artifacts": artifacts,
    }
    payload["manifest_digest"] = "sha256:" + _sha256(_canonical_bytes(payload))
    return payload


def _load_session() -> dict[str, Any] | None:
    if not SESSION_PATH.exists():
        return None
    try:
        value = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FA3 development session invalid: {exc}")
    if value.get("environment") != "development":
        raise SystemExit("FA3 development session has invalid environment")
    return value


def _sticky_taint(extra_taint: list[str]) -> list[str]:
    session = _load_session()
    prior = [] if session is None else list(session.get("taint_reasons", []))
    reasons = sorted(set(prior + list(extra_taint)))
    if session is not None and reasons:
        session["tainted"] = True
        session["taint_reasons"] = reasons
        session["updated_unix"] = int(time.time())
        SESSION_PATH.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    return reasons


def snapshot(extra_taint: list[str] | None = None) -> dict[str, Any]:
    policy = _load_policy()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_index_manifest()
    taint = _sticky_taint(extra_taint or [])
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
        "taint_reasons": [],
        "created_unix": int(time.time()),
    }
    SESSION_PATH.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(session, indent=2))


def status(field: str | None = None) -> None:
    value = _load_session()
    if value is None:
        value = {"environment": "production", "active_dev_session": False}
    else:
        value = dict(value)
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
