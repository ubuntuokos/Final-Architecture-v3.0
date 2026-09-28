#!/usr/bin/env python3
"""Opt-in local inbox for user-supplied ChatGPT exports.

This consumes only files deliberately placed in a private inbox. It never
downloads account data, sends exports over a network or pushes Git changes.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path

from fa3_donor_chat_import import _conversations, ingest

DEFAULT_HOME = Path.home() / ".local/share/fa3/donor-import"
MAX_INBOX_FILES = 512


def _save_private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".donor-inbox-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def process_inbox(root: Path, home: Path = DEFAULT_HOME) -> dict:
    inbox = home / "inbox"
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = home / ".import.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state_path = home / "processed.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or not isinstance(state.get("sha256", []), list):
                raise ValueError("inbox checkpoint is malformed")
        else:
            state = {"schema": "fa3.donor-import-checkpoint.v1", "sha256": []}
        processed = set(state["sha256"])
        files = sorted(
            path for path in inbox.iterdir()
            if path.is_file() and not path.is_symlink()
            and (path.suffix.lower() == ".zip" or
                 (path.suffix.lower() == ".json" and path.name.lower().startswith("conversations")))
        )
        if len(files) > MAX_INBOX_FILES:
            raise ValueError("too many pending export files; review private inbox")
        outcome = {"imports": 0, "previously_seen": 0, "created": 0, "merged": 0, "blocked": 0}
        for file_path in files:
            digest = _file_digest(file_path)
            if digest in processed:
                outcome["previously_seen"] += 1
                continue
            try:
                result = ingest(root, _conversations(file_path, {"user", "assistant"}), origin="chatgpt-export")
            except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
                outcome["blocked"] += 1
                # Never log the raw file name, source path, conversation text, or account data.
                raise ValueError("private donor inbox has a blocked or incomplete export") from exc
            outcome["imports"] += 1
            outcome["created"] += result["created"]
            outcome["merged"] += result["merged"]
            processed.add(digest)
            # Checkpoint only after successful atomic registry write.
            _save_private_json(state_path, {
                "schema": "fa3.donor-import-checkpoint.v1", "sha256": sorted(processed)
            })
        return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description="Import user-supplied ChatGPT exports from a private local inbox.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    args = parser.parse_args()
    try:
        summary = process_inbox(args.root, args.home)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print("Donor inbox BLOCKED: " + str(exc), file=__import__("sys").stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
