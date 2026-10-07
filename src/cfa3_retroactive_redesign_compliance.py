#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from fa3_donor_registry import _normalized_key

POLICY_REL = "canonical/CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001.json"
REGISTRY_REL = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
REAL_RECORD_ROOT = "canonical/retroactive-redesign-records"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required: " + str(path))
    return value


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + " failed: " + proc.stderr.strip())
    return proc.stdout.strip()


def _published_main_sha(root: Path) -> str:
    override = os.environ.get("CFA3_PUBLISHED_MAIN_SHA", "").strip()
    if _valid_sha(override):
        return override

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        try:
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            if isinstance(event, dict):
                pr_base = event.get("pull_request", {}).get("base", {}).get("sha")
                if _valid_sha(pr_base):
                    return pr_base
                if event.get("ref") == "refs/heads/main" and _valid_sha(event.get("after")):
                    return event["after"]
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    for ref in ("refs/remotes/origin/main", "refs/heads/main"):
        value = _git(root, "rev-parse", "--verify", ref, check=False)
        if _valid_sha(value):
            return value

    branch = _git(root, "branch", "--show-current", check=False)
    head = _git(root, "rev-parse", "HEAD", check=False)
    if branch == "main" and _valid_sha(head):
        return head
    raise RuntimeError("PUBLISHED_CANONICAL_MAIN_UNAVAILABLE")


def _ensure_commit(root: Path, sha: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", sha + "^{commit}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return
    fetch = subprocess.run(
        ["git", "-C", str(root), "fetch", "--no-tags", "--depth=1", "origin", sha],
        capture_output=True,
        check=False,
    )
    if fetch.returncode != 0:
        raise RuntimeError("PUBLISHED_MAIN_FETCH_FAILED")
    verify = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", sha + "^{commit}"],
        capture_output=True,
        check=False,
    )
    if verify.returncode != 0:
        raise RuntimeError("PUBLISHED_MAIN_COMMIT_UNAVAILABLE")


def _git_show_bytes(root: Path, sha: str, rel: str) -> bytes:
    _ensure_commit(root, sha)
    proc = subprocess.run(
        ["git", "-C", str(root), "show", f"{sha}:{rel}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("PUBLISHED_MAIN_FILE_UNAVAILABLE:" + rel)
    return proc.stdout


def _published_registry(root: Path, main_sha: str) -> tuple[dict[str, Any], bytes]:
    raw = _git_show_bytes(root, main_sha, REGISTRY_REL)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or value.get("id") != "FA3-DONOR-REFERENCE-REGISTRY-001":
        raise ValueError("PUBLISHED_MAIN_DONOR_REGISTRY_INVALID")
    return value, raw


def _is_ancestor(root: Path, older: str, newer: str) -> bool:
    _ensure_commit(root, older)
    _ensure_commit(root, newer)
    proc = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", older, newer],
        capture_output=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError("CANONICAL_MAIN_ANCESTRY_CHECK_FAILED")
    return proc.returncode == 0


def _report(findings: list[dict[str, str]], *, final: bool, disposition: str | None = None) -> dict[str, Any]:
    return {
        "schema": "cfa3.retroactive-redesign-compliance-report.v1",
        "result": "PASS" if not findings else "FAIL",
        "disposition": disposition or (
            "REDESIGN_FINAL"
            if final and not findings
            else "REDESIGN_ALLOWED"
            if not final and not findings
            else "BLOCKED"
        ),
        "findings": findings,
        "current_host_runtime_promotion_claim": False,
    }


def canonical_record_path(root: Path, path: Path) -> bool:
    candidate = path if path.is_absolute() else root / path
    try:
        candidate.resolve().relative_to((root / REAL_RECORD_ROOT).resolve())
        return True
    except ValueError:
        return False


def evaluate_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    policy = _load(root / POLICY_REL)

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "message": message})

    if record.get("schema") != "cfa3.retroactive-redesign-record.v1":
        fail("RR-001", "record schema mismatch")
    if record.get("capability_baseline") != 175 or record.get("capability_delta") != 0:
        fail("RR-002", "capability baseline/delta mismatch")
    if record.get("architectural_authority_delta") != 0:
        fail("RR-003", "architectural authority delta must remain zero")

    component = record.get("component")
    if not isinstance(component, dict):
        fail("RR-004", "component object missing")
        component = {}
    evidence = component.get("trigger_evidence_refs")
    if not isinstance(evidence, list) or not evidence:
        fail("RR-005", "trigger evidence required")

    designed_before = component.get("designed_before_mandatory_donor_policy")
    if designed_before is not True:
        normal_case = (
            designed_before is False
            and component.get("donor_policy_applicable_at_original_design") is True
            and isinstance(evidence, list)
            and bool(evidence)
        )
        if normal_case:
            return _report(
                findings,
                final=False,
                disposition="NOT_APPLICABLE_NORMAL_DONOR_RULES" if not findings else "BLOCKED",
            )
        fail("RR-006", "legacy pre-donor trigger not proven")

    phase = record.get("phase")
    lifecycle = policy.get("lifecycle", [])
    if phase not in lifecycle:
        fail("RR-007", "invalid lifecycle phase")
    final = phase == policy.get("finalization_gate", {}).get("final_state")

    if record.get("legacy_source_discovery_complete") is not True:
        fail("RR-008", "legacy source discovery incomplete")

    published_main: str | None = None
    registry: dict[str, Any] = {"entries": []}
    registry_raw = b""
    try:
        published_main = _published_main_sha(root)
        registry, registry_raw = _published_registry(root, published_main)
    except Exception as exc:
        fail("RR-031", "published canonical-main donor snapshot unavailable: " + str(exc))

    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        fail("RR-009", "canonical donor registry entries invalid")
        entries = []
    by_key = {
        row.get("source", {}).get("normalized_key"): row
        for row in entries
        if isinstance(row, dict) and isinstance(row.get("source"), dict)
    }

    legacy_sources = record.get("legacy_sources")
    if not isinstance(legacy_sources, list):
        fail("RR-032", "legacy_sources must be an explicit list")
        legacy_sources = []

    allowed_states = set(policy.get("legacy_source_policy", {}).get("canonical_acceptable_states", []))
    temporary_states = set(policy.get("legacy_source_policy", {}).get("temporary_use_states", []))
    for index, source in enumerate(legacy_sources):
        if not isinstance(source, dict):
            fail("RR-010", f"legacy source {index} invalid")
            continue
        locator = source.get("locator")
        key = source.get("normalized_key")
        if not isinstance(key, str) or not key:
            fail("RR-011", f"legacy source {index} normalized key missing")
            continue
        if not isinstance(locator, str) or not locator.strip():
            fail("RR-033", f"legacy source {index} locator missing")
            continue
        derived_key = _normalized_key("WEBSITE", locator)
        if derived_key != key:
            fail("RR-033", f"legacy source locator/key mismatch: {key}")
            continue
        if not isinstance(source.get("origin_refs"), list) or not source.get("origin_refs"):
            fail("RR-012", f"legacy source {key} provenance missing")

        donor = by_key.get(key)
        canonical = isinstance(donor, dict) and donor.get("status") in allowed_states
        if not canonical:
            if final:
                fail("RR-013", f"legacy source not canonical at finalization: {key}")
            elif source.get("temporary_planning_use") is not True:
                fail("RR-014", f"unregistered legacy source lacks temporary planning-use declaration: {key}")
            elif phase not in temporary_states:
                fail("RR-034", f"temporary planning use not allowed in phase {phase}: {key}")
        elif source.get("canonical_donor_id") != donor.get("donor_id"):
            fail("RR-015", f"canonical donor id mismatch: {key}")

    baseline = record.get("current_rule_baseline")
    if not isinstance(baseline, dict):
        fail("RR-016", "current rule baseline missing")
        baseline = {}
    if baseline.get("captured_from_canonical_main") is not True:
        fail("RR-017", "rule baseline must come from canonical main")
    main_sha = baseline.get("captured_main_sha")
    if not _valid_sha(main_sha):
        fail("RR-018", "captured main SHA invalid")
    elif published_main is not None:
        try:
            if not _is_ancestor(root, main_sha, published_main):
                fail("RR-035", "captured main SHA is not canonical-main lineage")
            if final and main_sha != published_main:
                fail("RR-036", "finalization requires exact current canonical-main SHA")
        except Exception as exc:
            fail("RR-035", "captured main SHA cannot be verified: " + str(exc))
    refs = baseline.get("mandatory_rule_refs")
    if not isinstance(refs, list) or not refs:
        fail("RR-019", "mandatory rule references missing")

    required_categories = set(policy.get("current_rule_delta_review", {}).get("required_categories", []))
    deltas = record.get("rule_delta")
    if not isinstance(deltas, list):
        fail("RR-020", "rule delta list missing")
        deltas = []
    seen: set[str] = set()
    for item in deltas:
        if not isinstance(item, dict):
            fail("RR-021", "invalid rule delta entry")
            continue
        category = item.get("category")
        status = item.get("status")
        if category in seen:
            fail("RR-022", "duplicate rule delta category: " + str(category))
        seen.add(category)
        if category not in required_categories:
            fail("RR-023", "unknown rule delta category: " + str(category))
        if status not in policy.get("current_rule_delta_review", {}).get("allowed_review_statuses", []):
            fail("RR-024", "invalid rule delta status: " + str(status))
        if status == "NOT_APPLICABLE" and not str(item.get("rationale", "")).strip():
            fail("RR-025", "NOT_APPLICABLE requires rationale: " + str(category))
        if final and status not in policy.get("current_rule_delta_review", {}).get("final_resolved_statuses", []):
            fail("RR-026", "unresolved rule delta at finalization: " + str(category))
    missing_categories = sorted(required_categories - seen)
    if missing_categories:
        fail("RR-027", "missing rule delta categories: " + ",".join(missing_categories))

    checks = record.get("finalization_checks")
    if not isinstance(checks, dict):
        fail("RR-028", "finalization checks missing")
        checks = {}
    if final:
        for name in policy.get("finalization_gate", {}).get("required_checks", []):
            if checks.get(name) != "PASS":
                fail("RR-029", "finalization check not PASS: " + name)
        digest = record.get("donor_registry_sha256")
        expected_digest = hashlib.sha256(registry_raw).hexdigest() if registry_raw else None
        if expected_digest is None or digest != expected_digest:
            fail("RR-030", "donor registry digest mismatch against published canonical main")

    return _report(findings, final=final)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one CFA3 retroactive redesign compliance record.")
    parser.add_argument("record", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    record = _load(args.record if args.record.is_absolute() else root / args.record)
    report = evaluate_record(root, record)
    if record.get("phase") == "REDESIGN_FINAL" and not canonical_record_path(root, args.record):
        report["result"] = "FAIL"
        report["disposition"] = "BLOCKED"
        report["findings"].append({
            "code": "RR-037",
            "message": "REDESIGN_FINAL record must be stored under " + REAL_RECORD_ROOT,
        })
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
