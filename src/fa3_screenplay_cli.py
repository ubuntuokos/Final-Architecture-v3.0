#!/usr/bin/env python3
"""Local, explicit FA3 screenplay interchange and derived-proposal CLI."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from fa3_screenplay import (ScreenplayError, FORMATS, PROFILES, derive_breakdown,
                            edit_scene, export_screenplay, fork_branch, import_screenplay,
                            project_handoff, review_candidate, validate_document)


def _read(path: str) -> str:
    # Never implicitly read a URL or send data over the network.
    src = Path(path).expanduser()
    if not src.is_file() or src.is_symlink():
        raise ScreenplayError(f"input must be a regular local file: {src}")
    return src.read_text(encoding="utf-8")


def _json(path: str) -> dict:
    value = json.loads(_read(path))
    if not isinstance(value, dict):
        raise ScreenplayError("expected JSON object")
    return value


def _write(path: str, content: str, *, replace: bool = False) -> None:
    dest = Path(path).expanduser()
    if dest.exists() and (not replace or dest.is_symlink()):
        raise ScreenplayError("destination exists: use --replace only for an owned regular file")
    if not dest.parent.is_dir():
        raise ScreenplayError("output directory does not exist")
    fd, temp_path = tempfile.mkstemp(prefix=".fa3-screenplay-", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_path, dest)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _dump(value: dict) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("formats", help="List implemented bounded bidirectional subset codecs")
    p = sub.add_parser("import", help="Local text -> canonical screenplay JSON")
    p.add_argument("--format", choices=tuple(FORMATS), required=True)
    p.add_argument("--profile", choices=sorted(PROFILES), default="FEATURE")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--allow-loss", action="store_true")
    p = sub.add_parser("export", help="Canonical screenplay JSON -> local text")
    p.add_argument("--format", choices=tuple(FORMATS), required=True)
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--allow-loss", action="store_true")
    p = sub.add_parser("validate", help="Validate a canonical screenplay document; no mutation")
    p.add_argument("--input", required=True)
    p = sub.add_parser("breakdown", help="Derive source-linked proposals, never an approved schedule")
    p.add_argument("--input", required=True)
    p.add_argument("--previous")
    p.add_argument("--refresh-affected", action="store_true")
    p.add_argument("--output", required=True)
    p = sub.add_parser("review", help="Record a LOCAL_UNVERIFIED_REVIEW, not UAF authorization")
    p.add_argument("--input", required=True)
    p.add_argument("--candidate-id", required=True)
    p.add_argument("--decision", choices=["APPROVED", "REJECTED"], required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("branch", help="Fork an independently versioned story branch")
    p.add_argument("--input", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("edit-scene", help="Edit only an existing scene, preserving stable scene IDs")
    p.add_argument("--input", required=True)
    p.add_argument("--scene", required=True)
    p.add_argument("--heading", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("handoff", help="Generate a non-authoritative, blocker-aware handoff preview")
    p.add_argument("--input", required=True)
    p.add_argument("--breakdown", required=True)
    p.add_argument("--output", required=True)
    for p in sub.choices.values():
        if "--output" in [x.option_strings[0] for x in p._actions if x.option_strings]:
            p.add_argument("--replace", action="store_true", help="Explicitly replace an owned regular output file")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "formats":
            print(_dump({"codecs": FORMATS, "office_codecs": "NOT_ADMITTED",
                         "current_host_evidence": "NOT_RUN"}), end="")
            return 0
        if args.cmd == "import":
            value, receipt = import_screenplay(_read(args.input), args.format, profile=args.profile,
                                                allow_loss=args.allow_loss)
        elif args.cmd == "export":
            value, receipt = export_screenplay(_json(args.input), args.format, allow_loss=args.allow_loss)
        elif args.cmd == "validate":
            value = _json(args.input)
            validate_document(value)
            print(_dump({"result": "PASS", "schema": value["schema"], "scenes": len(value["scenes"])}), end="")
            return 0
        elif args.cmd == "breakdown":
            value = derive_breakdown(_json(args.input), _json(args.previous) if args.previous else None,
                                     refresh_affected=args.refresh_affected)
            receipt = {"status": "NON_CANONICAL_DERIVED_PROPOSAL", "source_revision": value["source_revision"]}
        elif args.cmd == "review":
            value = review_candidate(_json(args.input), args.candidate_id, args.decision, args.actor)
            receipt = {"status": "LOCAL_UNVERIFIED_REVIEW", "candidate_id": args.candidate_id,
                       "decision": args.decision}
        elif args.cmd == "branch":
            value = fork_branch(_json(args.input), args.branch)
            receipt = {"status": "BRANCHED", "branch_id": value["branch_id"]}
        elif args.cmd == "edit-scene":
            value = edit_scene(_json(args.input), args.scene, heading=args.heading)
            receipt = {"status": "REVISION_CREATED", "scene_id": args.scene, "revision": value["revision"]}
        elif args.cmd == "handoff":
            value = project_handoff(_json(args.input), _json(args.breakdown))
            receipt = {"status": value["status"], "blockers": value["blockers"]}
        else:
            parser.error("unreachable command")
        _write(args.output, value if isinstance(value, str) else _dump(value), replace=args.replace)
        print(_dump(receipt), end="")
        return 3 if args.cmd == "handoff" and value["status"] == "BLOCKED" else 0
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(_dump({"result": "FAIL", "error": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
