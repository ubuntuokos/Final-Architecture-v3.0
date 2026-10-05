#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

REGISTRY_REL = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
REJECTION_AUDIT_REL = "canonical/FA3-DONOR-REJECTION-AUDIT-001.json"
ALLOWED_STATES = {"CANDIDATE", "ANALYZED", "ACCEPTED_REFERENCE", "SUPERSEDED"}
APPROVED_OWNER_DONOR_COMMANDS = ("donornak", "vedd fel donornak", "add a donorlistához")

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

def _committed_bytes(root: Path, rel_value: str, *, allowed_roots: tuple[str, ...]) -> bytes:
    rel = Path(rel_value)
    if (
        rel.is_absolute()
        or ".." in rel.parts
        or rel.as_posix() != rel_value
        or not rel.parts
        or rel.parts[0] not in allowed_roots
    ):
        raise ValueError("INVALID_COMMITTED_PATH")
    path = root.resolve() / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError("COMMITTED_SOURCE_UNAVAILABLE")
    raw = path.read_bytes()
    result = subprocess.run(
        ["git", "-C", str(root.resolve()), "show", "HEAD:" + rel_value],
        capture_output=True,
        check=False,
    )
    if result.returncode or result.stdout != raw:
        raise ValueError("DIRTY_OR_NONCOMMITTED_SOURCE")
    return raw


def _approved_plan_registration(root: Path, approval_ref: str | None, normalized_key: str) -> dict[str, Any] | None:
    """Bound donor registration to committed owner-approved plan evidence."""
    if not approval_ref:
        return None
    raw = _committed_bytes(root, approval_ref, allowed_roots=("canonical",))
    decision = json.loads(raw)
    approved_keys = decision.get("approved_processed_donor_keys")
    approved_plan_path = decision.get("approved_plan_path")
    approved_plan_sha256 = decision.get("approved_plan_sha256")
    assessment_path = decision.get("approved_donor_assessment_path")
    assessment_sha256 = decision.get("approved_donor_assessment_sha256")
    lineage_ref = decision.get("conversation_lineage_ref")
    if (
        not approval_ref.startswith("canonical/decisions/")
        or decision.get("status") != "APPROVED"
        or decision.get("explicit_user_approval") is not True
        or decision.get("donor_registration_authorization") != "APPROVED_PLAN_PROCESSED_DONORS_ONLY"
        or not isinstance(approved_keys, list)
        or not approved_keys
        or any(not isinstance(key, str) or not key for key in approved_keys)
        or len(set(approved_keys)) != len(approved_keys)
        or not isinstance(approved_plan_path, str)
        or not isinstance(approved_plan_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", approved_plan_sha256)
        or not isinstance(assessment_path, str)
        or not isinstance(assessment_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", assessment_sha256)
        or not isinstance(lineage_ref, str)
        or not lineage_ref
        or not isinstance(decision.get("user_request_ref"), str)
        or not decision.get("user_request_ref")
    ):
        raise ValueError("INVALID_PLAN_APPROVAL_FOR_DONOR_REGISTRATION")
    plan_raw = _committed_bytes(root, approved_plan_path, allowed_roots=("canonical", "docs"))
    if hashlib.sha256(plan_raw).hexdigest() != approved_plan_sha256:
        raise ValueError("APPROVED_PLAN_HASH_MISMATCH")
    assessment_raw = _committed_bytes(root, assessment_path, allowed_roots=("canonical",))
    if hashlib.sha256(assessment_raw).hexdigest() != assessment_sha256:
        raise ValueError("APPROVED_DONOR_ASSESSMENT_HASH_MISMATCH")
    assessment = json.loads(assessment_raw)
    exception = assessment.get("planning_donor_analysis_exception")
    if (
        not isinstance(exception, dict)
        or exception.get("scope") != "ORIGINATING_CONVERSATION_AND_DIRECT_CONTINUATIONS_ONLY"
        or exception.get("planning_only") is not True
        or exception.get("cross_conversation_reuse") is not False
        or exception.get("lineage_ref") != lineage_ref
    ):
        raise ValueError("APPROVED_PLAN_CONVERSATION_LINEAGE_MISMATCH")
    processed = assessment.get("planning_processed_donors")
    if not isinstance(processed, list):
        raise ValueError("APPROVED_DONOR_ASSESSMENT_PROCESSED_SET_MISSING")
    assessment_keys = [
        item.get("normalized_key") for item in processed if isinstance(item, dict)
    ]
    if (
        len(assessment_keys) != len(processed)
        or any(not isinstance(key, str) or not key for key in assessment_keys)
        or len(set(assessment_keys)) != len(assessment_keys)
        or set(assessment_keys) != set(approved_keys)
    ):
        raise ValueError("APPROVED_PROCESSED_DONOR_SET_MISMATCH")
    if normalized_key not in approved_keys:
        raise ValueError("DONOR_NOT_IN_APPROVED_PLAN_PROCESSED_SET")
    return decision


def _merge_strings(existing: Any, incoming: list[str]) -> list[str]:
    base = [str(x) for x in existing] if isinstance(existing, list) else []
    return sorted(set(base + [x for x in incoming if x]))

def refresh_donor_count(registry: dict[str, Any]) -> int:
    """Recalculate the canonical count after an authorized donor mutation.

    The count is derived, never incremented by a hard-coded delta. Refuse to
    mask malformed entries, duplicate identities or changes to the fixed
    capability baseline. The readiness gate separately detects unreviewed
    edits or stale counts; it must not repair evidence on read.
    """
    if registry.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        raise ValueError("unexpected donor registry id")
    if "capability_count" in registry and registry["capability_count"] != 175:
        raise ValueError("CAPABILITY_BASELINE_NOT_175")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise ValueError("donor entries must be a list")
    ids, keys = set(), set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("source"), dict):
            raise ValueError(f"MALFORMED_DONOR_ENTRY:{index}")
        donor_id, key = entry.get("donor_id"), entry["source"].get("normalized_key")
        if entry.get("status") not in ALLOWED_STATES:
            raise ValueError(f"INVALID_ACTIVE_DONOR_STATE:{index}")
        if not isinstance(donor_id, str) or not donor_id or donor_id in ids:
            raise ValueError(f"DUPLICATE_OR_INVALID_DONOR_ID:{index}")
        if not isinstance(key, str) or not key or key in keys:
            raise ValueError(f"DUPLICATE_OR_INVALID_SOURCE_KEY:{index}")
        ids.add(donor_id)
        keys.add(key)
    backfill = registry.setdefault("backfill", {})
    if not isinstance(backfill, dict):
        raise ValueError("invalid donor backfill metadata")
    backfill["entry_count"] = len(entries)
    return len(entries)


def _rejection_audit(root: Path) -> dict[str, Any]:
    path = root.resolve() / REJECTION_AUDIT_REL
    if not path.is_file():
        raise ValueError("REJECTION_AUDIT_MISSING")
    value = _load(path)
    if value.get("id") != "FA3-DONOR-REJECTION-AUDIT-001" or not isinstance(value.get("entries"), list):
        raise ValueError("REJECTION_AUDIT_INVALID")
    return value


def _security_reentry_verified(row: dict[str, Any]) -> bool:
    proof = row.get("security_reentry_evidence")
    return (
        isinstance(proof, dict)
        and proof.get("status") == "VERIFIED_SAFE"
        and isinstance(proof.get("evidence_refs"), list)
        and bool(proof["evidence_refs"])
        and row.get("code_reuse_policy") != "FORBIDDEN"
    )


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    # Single write boundary for direct capture, staged batch import and
    # maintenance reconciliation: count and data go into one atomic replace.
    if path.name == Path(REGISTRY_REL).name:
        refresh_donor_count(value)
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
    owner_submitted_link: bool = False,
    explicit_donor_marker: bool = False,
    owner_donor_command: str | None = None,
    plan_approval_ref: str | None = None,
) -> dict[str, Any]:
    key = _normalized_key(source_kind, source_locator)
    approved_plan = _approved_plan_registration(root, plan_approval_ref, key) if plan_approval_ref else None
    if owner_donor_command is not None and owner_donor_command not in APPROVED_OWNER_DONOR_COMMANDS:
        raise ValueError("UNAPPROVED_OWNER_DONOR_COMMAND")
    direct_authorized = explicit_donor_marker and owner_submitted_link
    if not direct_authorized and approved_plan is None:
        raise ValueError("DONOR_INTAKE_AUTHORIZATION_REQUIRED: explicit owner donor command or approved-plan registration")
    if owner_submitted_link and not source_locator.strip().lower().startswith(("https://", "http://")):
        raise ValueError("owner donor registration requires a link")
    path = root.resolve() / REGISTRY_REL
    registry = _load(path)
    if registry.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        raise ValueError("unexpected donor registry id")
    if owner_submitted_link and not source_locator.strip().lower().startswith(("https://", "http://")):
        raise ValueError("owner pre-reviewed registration requires a submitted source link")
    today = seen_date or dt.date.today().isoformat()
    entries = registry.get("entries")
    backfill = registry.get("backfill")
    if not isinstance(entries, list) or (backfill is not None and not isinstance(backfill, dict)):
        raise ValueError("INVALID_EXISTING_DONOR_REGISTRY")
    # Historical snapshots may lack backfill metadata entirely, including
    # small alias-migration fixtures. Bootstrap from actual entries only when
    # metadata is absent; a present but stale count still fails closed.
    if backfill is None:
        registry["backfill"] = {"entry_count": len(entries)}
    elif backfill.get("entry_count") != len(entries):
        raise ValueError("BACKFILL_COUNT_DRIFT_BEFORE_MUTATION")
    # Source identity wins. Equal display names with different source keys must
    # not silently merge unrelated GitHub repositories or research projects.
    match = next((row for row in entries if isinstance(row, dict)
                  and (row.get("source", {}).get("normalized_key") == key
                       or key in row.get("legacy_source_keys", []))), None)
    audit = _rejection_audit(root)
    audited = {
        item.get("donor", {}).get("source", {}).get("normalized_key")
        for item in audit.get("entries", [])
        if isinstance(item, dict) and isinstance(item.get("donor"), dict)
    }
    if key in audited and (match is None or not _security_reentry_verified(match)):
        raise ValueError("REJECTED_DONOR_REENTRY_REQUIRES_VERIFIED_SAFE_MAINTENANCE")
    created = match is None
    if match is None and not (
        (direct_authorized and source_locator.lower().startswith(("https://", "http://")))
        or approved_plan is not None
    ):
        raise ValueError("NEW_DONOR_REQUIRES_EXPLICIT_OWNER_COMMAND_OR_APPROVED_PLAN")
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
            "status": "ACCEPTED_REFERENCE" if (direct_authorized or approved_plan is not None) else "CANDIDATE",
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
    # Both intake paths authorize reference registration only. They never approve
    # source copying, dependency adoption, provider/model admission or runtime use.
    if direct_authorized or approved_plan is not None:
        if match.get("status") == "SUPERSEDED":
            raise ValueError("superseded source needs explicit conflict reconciliation")
        match["status"] = "ACCEPTED_REFERENCE"
        if approved_plan is not None:
            match["submission_review"] = {
                "basis": "OWNER_APPROVED_IMPLEMENTATION_PLAN_PROCESSED_DONOR_SET",
                "scope": "REFERENCE_REGISTRATION_ONLY",
                "approval_ref": plan_approval_ref,
                "conversation_lineage_ref": approved_plan["conversation_lineage_ref"],
                "second_donornak_marker_required": False,
                "second_registry_approval_required": False,
            }
        else:
            match["submission_review"] = {
                "basis": "OWNER_PRE_REVIEWED_DIRECT_DONOR_LINK",
                "scope": "REFERENCE_REGISTRATION_ONLY",
                "owner_donor_command": owner_donor_command or "donornak",
                "second_registry_approval_required": False,
            }
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
    refresh_donor_count(registry)
    if not dry_run:
        _atomic_write(path, registry)
    return {"created": created, "donor_id": match["donor_id"], "status": match["status"], "normalized_key": match["source"]["normalized_key"], "dry_run": dry_run}

_DONOR_COMMAND_PATTERNS = (
    ("vedd fel donornak", re.compile(r"(?i)(?<![\w])vedd[ \t]+fel[ \t]+donornak\b")),
    ("add a donorlistához", re.compile(r"(?i)(?<![\w])add[ \t]+a[ \t]+donorlistához\b")),
    ("donornak", re.compile(r"(?i)(?<![\w])donornak\b")),
)
_LINK_URL = re.compile(r'https?://[^\s<>\[\]()"]+', re.I)
_NEGATION = re.compile(r"(?i)\b(?:nem|ne|not|don['’]t|do\s+not)\b")


def _owner_command_matches(text: str) -> list[tuple[str, re.Match[str]]]:
    url_spans = [(m.start(), m.end()) for m in _LINK_URL.finditer(text)]
    found: list[tuple[str, re.Match[str]]] = []
    for command, pattern in _DONOR_COMMAND_PATTERNS:
        for match in pattern.finditer(text):
            if any(start <= match.start() < end for start, end in url_spans):
                continue
            clause_start = max(
                text.rfind("\n", 0, match.start()),
                text.rfind(".", 0, match.start()),
                text.rfind("!", 0, match.start()),
                text.rfind("?", 0, match.start()),
                text.rfind(";", 0, match.start()),
            ) + 1
            if _NEGATION.search(text[clause_start:match.start()]):
                continue
            if any(not (match.end() <= existing.start() or match.start() >= existing.end())
                   for _, existing in found):
                continue
            found.append((command, match))
    return sorted(found, key=lambda item: item[1].start())


def _explicit_owner_marker(text: str):
    matches = _owner_command_matches(text)
    return matches[0][1] if matches else None


def _explicit_owner_command(text: str) -> str | None:
    matches = _owner_command_matches(text)
    return matches[0][0] if matches else None


def parse_donor_mention(text: str, *, name: str | None = None, source: str | None = None) -> tuple[str, str, str]:
    """Accept only the three approved explicit commands and bind them to the supplied URL."""
    command = _explicit_owner_command(text)
    if command is None:
        raise ValueError("EXPLICIT_OWNER_DONOR_COMMAND_REQUIRED")
    found = sorted(set(
        match.group(0).rstrip(".,;:!?}\\").removesuffix(".git")
        for match in _LINK_URL.finditer(text)
    ))
    normalized_source = source.removesuffix(".git") if isinstance(source, str) else None
    if len(found) > 1 and not normalized_source:
        raise ValueError("multiple commanded source URLs: capture each separately")
    if normalized_source and not found:
        raise ValueError("link-free follow-up targeting requires conversation importer context")
    if normalized_source and normalized_source not in found:
        raise ValueError("supplied source contradicts the owner-commanded URL")
    locator = normalized_source or (found[0] if found else None)
    if not locator or not locator.lower().startswith(("https://", "http://")):
        raise ValueError("an explicitly commanded donor link is required")
    if not name:
        name = "/".join(locator.split("/")[3:5]) if locator.lower().startswith("https://github.com/") else locator
    kind = "GITHUB" if locator.lower().startswith("https://github.com/") else "REFERENCE"
    return name.strip(), kind, locator

def main() -> int:
    p = argparse.ArgumentParser(description="Capture or merge a potential FA3 donor candidate.")
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--name")
    p.add_argument("--source", dest="source_locator")
    p.add_argument("--mention", help="One tentative-donor conversation mention. Raw text is not stored.")
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
    p.add_argument("--refresh-count", action="store_true",
                   help="Explicit maintenance-only reconciliation after reviewed external JSON edits")
    p.add_argument("--owner-submitted-link", action="store_true",
                   help="Owner explicitly issued an approved donor-intake command for this link")
    p.add_argument("--owner-donor-marker", choices=["donornak"],
                   help="Backward-compatible attestation for the canonical donornak command")
    p.add_argument("--owner-donor-command", choices=list(APPROVED_OWNER_DONOR_COMMANDS),
                   help="Operator attests the exact approved owner donor-intake command")
    p.add_argument("--approved-plan-registration", action="store_true",
                   help="Register one exact processed donor from an owner-approved implementation plan")
    p.add_argument("--plan-approval-record",
                   help="Committed canonical approval record binding plan, assessment, lineage and processed donor set")
    args = p.parse_args()
    if args.refresh_count:
        path = Path(args.root).resolve() / REGISTRY_REL
        registry = _load(path)
        previous = registry.get("backfill", {}).get("entry_count")
        updated = refresh_donor_count(registry)
        if updated != previous and not args.dry_run:
            _atomic_write(path, registry)
        print(json.dumps({"result": "DONOR_COUNT_REFRESH",
                          "previous_count": previous, "entry_count": updated,
                          "changed": updated != previous and not args.dry_run,
                          "dry_run": args.dry_run}, ensure_ascii=False))
        return 0
    owner_command = args.owner_donor_command or args.owner_donor_marker
    direct_mode = args.owner_submitted_link and owner_command in APPROVED_OWNER_DONOR_COMMANDS
    approved_plan_mode = args.approved_plan_registration and bool(args.plan_approval_record)
    if args.plan_approval_record and not args.approved_plan_registration:
        p.error("--plan-approval-record requires --approved-plan-registration")
    # A dry run on an unauthorized link is analysis only and never mutates the registry.
    if args.dry_run and not direct_mode and not approved_plan_mode:
        print(json.dumps({"result": "ANALYSIS_ONLY_UNMARKED_LINK",
                          "created": False, "registry_mutated": False,
                          "dry_run": True}, ensure_ascii=False))
        return 0
    if args.approved_plan_registration:
        if not args.plan_approval_record:
            p.error("--plan-approval-record is required for approved-plan registration")
        if not args.name or not args.source_locator:
            p.error("--name and --source are required for approved-plan registration")
        name, kind, locator = args.name, args.source_kind, args.source_locator
    elif args.mention:
        if not direct_mode:
            p.error("mention intake requires trusted owner role and an approved donor command attestation")
        parsed_command = _explicit_owner_command(args.mention)
        if parsed_command is None or parsed_command != owner_command:
            p.error("owner command attestation must exactly match the mention")
        name, kind, locator = parse_donor_mention(args.mention, name=args.name, source=args.source_locator)
    else:
        if not direct_mode:
            p.error("an approved explicit owner donor-intake command is required")
        if not args.name or not args.source_locator:
            p.error("--name and --source are required for direct donor intake")
        name, kind, locator = args.name, args.source_kind, args.source_locator
    result = capture_candidate(
        Path(args.root), name=name, source_kind=kind,
        source_locator=locator, tags=args.tag, capabilities=args.capability,
        domains=args.domain, targets=args.target, problems=args.problem,
        note=args.note, discovered_from=args.discovered_from,
        seen_date=args.seen_date, dry_run=args.dry_run,
        owner_submitted_link=args.owner_submitted_link,
        explicit_donor_marker=direct_mode,
        owner_donor_command=owner_command if direct_mode else None,
        plan_approval_ref=args.plan_approval_record if approved_plan_mode else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
