#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

REGISTRY_REL = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
ALLOWED_STATES = {"CANDIDATE", "ANALYZED", "ACCEPTED_REFERENCE", "REJECTED", "SUPERSEDED"}

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("donor registry must be a JSON object")
    return value

def _slug(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").upper()
    return out[:56] or "UNNAMED"

def _normalized_key(kind: str, locator: str) -> str:
    text = locator.strip()
    low = text.lower()
    if low.startswith("https://github.com/"):
        body = text[len("https://github.com/"):].strip("/").removesuffix(".git").lower()
        return "github:" + body
    return kind.lower() + ":" + low if ":" not in low else low

def _merge_strings(existing: Any, incoming: list[str]) -> list[str]:
    base = [str(x) for x in existing] if isinstance(existing, list) else []
    return sorted(set(base + [x for x in incoming if x]))

def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".donor-registry-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def capture_candidate(
    root: Path,
    *,
    name: str,
    source_kind: str,
    source_locator: str,
    tags: list[str] | None = None,
    capabilities: list[str] | None = None,
    domains: list[str] | None = None,
    targets: list[str] | None = None,
    problems: list[str] | None = None,
    note: str | None = None,
    discovered_from: str = "conversation",
    seen_date: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    path = root.resolve() / REGISTRY_REL
    registry = _load(path)
    if registry.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        raise ValueError("unexpected donor registry id")
    key = _normalized_key(source_kind, source_locator)
    today = seen_date or dt.date.today().isoformat()
    entries = registry.setdefault("entries", [])
    match = next((row for row in entries if isinstance(row, dict) and (
        row.get("source", {}).get("normalized_key") == key or str(row.get("name", "")).casefold() == name.casefold()
    )), None)
    created = match is None
    if match is None:
        base_id = f"FA3-DONOR-{_slug(name)}-001"
        used = {str(row.get("donor_id")) for row in entries if isinstance(row, dict)}
        donor_id = base_id
        if donor_id in used:
            import hashlib
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:8].upper()
            donor_id = f"FA3-DONOR-{_slug(name)[:44]}-{digest}-001"
        match = {
            "donor_id": donor_id,
            "name": name,
            "source": {"kind": source_kind.upper(), "locator": source_locator, "normalized_key": key},
            "status": "CANDIDATE",
            "discovered_from": [discovered_from],
            "first_seen": today,
            "last_seen": today,
            "donor_modes": ["REFERENCE_IMPLEMENTATION"],
            "capability_hints": [],
            "domain_hints": [],
            "problem_hints": [],
            "target_hints": [],
            "tags": [],
            "license": {"declared": "UNKNOWN", "status": "UNKNOWN"},
            "code_reuse_policy": "SOURCE_COPY_BLOCKED_PENDING_LICENSE_REVIEW",
            "discoverable_for_planning": True,
            "authority": False,
            "automatic_selection": False,
            "automatic_fetch": False,
            "automatic_install": False,
            "automatic_activation": False,
            "automatic_dependency": False,
            "automatic_code_import": False,
            "automatic_provider_admission": False,
            "automatic_model_selection": False,
        }
        entries.append(match)
    match["last_seen"] = today
    match["discovered_from"] = _merge_strings(match.get("discovered_from"), [discovered_from])
    match["tags"] = _merge_strings(match.get("tags"), tags or [])
    match["capability_hints"] = _merge_strings(match.get("capability_hints"), capabilities or [])
    match["domain_hints"] = _merge_strings(match.get("domain_hints"), domains or [])
    match["problem_hints"] = _merge_strings(match.get("problem_hints"), problems or [])
    match["target_hints"] = _merge_strings(match.get("target_hints"), targets or [])
    if note:
        match["notes"] = _merge_strings(match.get("notes"), [note])
    if match.get("status") not in ALLOWED_STATES:
        raise ValueError("invalid donor state")
    entries.sort(key=lambda row: str(row.get("donor_id", "")))
    registry.setdefault("backfill", {})["entry_count"] = len(entries)
    if not dry_run:
        _atomic_write(path, registry)
    return {"created": created, "donor_id": match["donor_id"], "status": match["status"], "normalized_key": key, "dry_run": dry_run}

def main() -> int:
    p = argparse.ArgumentParser(description="Capture or merge a potential FA3 donor candidate.")
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--name", required=True)
    p.add_argument("--source", required=True, dest="source_locator")
    p.add_argument("--source-kind", default="reference")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--capability", action="append", default=[])
    p.add_argument("--domain", action="append", default=[])
    p.add_argument("--problem", action="append", default=[])
    p.add_argument("--target", action="append", default=[])
    p.add_argument("--note")
    p.add_argument("--discovered-from", default="conversation")
    p.add_argument("--date", dest="seen_date")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    result = capture_candidate(
        Path(args.root), name=args.name, source_kind=args.source_kind,
        source_locator=args.source_locator, tags=args.tag, capabilities=args.capability,
        domains=args.domain, targets=args.target, problems=args.problem,
        note=args.note, discovered_from=args.discovered_from,
        seen_date=args.seen_date, dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
