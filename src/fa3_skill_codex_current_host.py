#!/usr/bin/env python3
"""Real-host Codex skill-consumer observation using existing signed FA3 authorities.

Only available after independently provisioned source/registry trust pins,
Security Governance role grants, task-bound signed claims, and real pinned
Codex binary/archive. This producer does not self-sign or promote evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_codex_adapter import (
    ADAPTER_ID, ARCHIVE_NAME, ARCHIVE_SHA256,
    CODE_MODE_HOST_ARCHIVE_NAME, CODE_MODE_HOST_ARCHIVE_SHA256, CODEX_VERSION,
    PROVIDER_ID, CodexAdapter, _init_repo, codex_preflight,
)
from fa3_developer_agent_coordination import AgentTask, Coordinator
from fa3_skill_signed_authority import SignedSkillAuthorityVerifier
from fa3_skill_task_binding import SkillTaskBinding
from fa3_skill_task_projection import SkillTaskPreflight

SCHEMA = "fa3.skill-codex-current-host-observation.v1"
TRUST_SCHEMA = "fa3.skill-host-trust-pin.v1"
BUNDLE_SCHEMA = "fa3.skill-codex-host-bundle.v1"
REPORT = "reports/skill-codex-current-host-report.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class SkillHostDenied(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise SkillHostDenied("unsafe or oversized host input")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SkillHostDenied("host input must be a JSON object")
    return value


def load_trust_pin(path: Path, *, strict: bool = True) -> dict[str, Any]:
    """Fail closed unless the production pin is independent and root-managed."""
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise SkillHostDenied("trust pin must be absolute, canonical and nonsymlinked")
    if strict:
        for member in (path, path.parent):
            info = member.stat()
            if info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise SkillHostDenied("trust pin and directory must be root-managed")
    config = _read_json(path)
    if (config.get("schema") != TRUST_SCHEMA
            or not SHA40.fullmatch(str(config.get("source_commit", "")))
            or not SHA256.fullmatch(str(config.get("registry_sha256", "")))
            or config.get("approved_provider_id") != PROVIDER_ID
            or config.get("codex_archive_sha256") != ARCHIVE_SHA256
            or config.get("codex_code_mode_host_archive_sha256") != CODE_MODE_HOST_ARCHIVE_SHA256
            or config.get("trust_profile") != "FA3-TRUST-PKI-001"
            or config.get("security_authority") != "FA3-AUTH-SECURITY-GOV-001"):
        raise SkillHostDenied("host trust pin identity and provider pin mismatch")
    return config


def check_bundle(root: Path, bundle: dict[str, Any], config: dict[str, Any]) -> tuple[str, SkillTaskBinding, dict[str, Any], str]:
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("provider_id") != PROVIDER_ID:
        raise SkillHostDenied("invalid real-host skill bundle")
    task_id = bundle.get("task_id")
    skill_id = bundle.get("skill_id")
    if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id):
        raise SkillHostDenied("invalid task ID in signed host bundle")
    registry_bytes = (root / "canonical/skill-registry.json").read_bytes()
    if hashlib.sha256(registry_bytes).hexdigest() != config["registry_sha256"]:
        raise SkillHostDenied("installed registry differs from root-managed source pin")
    registry = json.loads(registry_bytes)
    candidates = [row for row in registry.get("entries", []) if isinstance(row, dict)
                  and row.get("skill_id") == skill_id]
    if len(candidates) != 1 or bundle.get("registry_entry") != candidates[0]:
        raise SkillHostDenied("signed bundle does not match exactly one canonical skill")
    entry = candidates[0]
    snapshot = entry.get("snapshot", {})
    package = bundle.get("package")
    if (not isinstance(package, dict) or entry.get("admission_status") != "ADMITTED"
            or package.get("package_id") != entry.get("package_id")
            or package.get("source", {}).get("commit") != snapshot.get("source_commit")
            or package.get("digests", {}).get("content_sha256") != snapshot.get("content_sha256")
            or package.get("digests", {}).get("manifest_sha256") != snapshot.get("manifest_sha256")):
        raise SkillHostDenied("bundle package differs from independently admitted native snapshot")
    for field in ("admission", "selection", "lease", "language_context", "intent"):
        if not isinstance(bundle.get(field), dict):
            raise SkillHostDenied("incomplete signed runtime bundle: " + field)
    language = bundle["language_context"]
    if (bundle["selection"].get("task_scope") != "developer"
            or bundle["selection"].get("task_id", task_id) != task_id
            or bundle["lease"].get("task_id") != task_id):
        raise SkillHostDenied("bundle admission or activation scope mismatch")
    if not isinstance(skill_id, str) or not skill_id:
        raise SkillHostDenied("skill ID missing")
    binding = SkillTaskBinding(
        root, package, entry, bundle["admission"],
        bundle["selection"], bundle["lease"], bundle["intent"])
    return task_id, binding, language, skill_id


def _git_head(root: Path) -> str:
    value = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                           text=True, capture_output=True, check=True).stdout.strip()
    if not SHA40.fullmatch(value):
        raise SkillHostDenied("repository HEAD not an immutable 40-char source commit")
    return value


def _verify_installed_codex(root: Path, binary: Path, archive: Path) -> dict[str, Any]:
    collector = root / "evidence/collect-codex-current-host.py"
    spec = importlib.util.spec_from_file_location("fa3_existing_codex_host_collector", collector)
    if spec is None or spec.loader is None:
        raise SkillHostDenied("existing Codex supply-chain collector unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    supply = module.verify_installed_binary_against_archive(binary, archive)
    supply["code_mode_host"] = module.verify_code_mode_host_against_archive(
        binary.with_name("codex-code-mode-host"),
        archive.with_name(CODE_MODE_HOST_ARCHIVE_NAME),
    )
    return supply


def run_observation(
    root: Path, trust_path: Path, bundle_path: Path,
    binary: Path, archive: Path, *, timeout_seconds: int = 600,
) -> dict[str, Any]:
    if (os.environ.get("FA3_CURRENT_HOST") != "1"
            or os.environ.get("FA3_EXECUTION_SCOPE") != "CURRENT_HOST"):
        raise SkillHostDenied("official current-host execution markers required")
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise SkillHostDenied("existing pinned Codex binary requires Linux x86_64")
    if os.geteuid() == 0:
        raise SkillHostDenied("Codex provider must not run as root")
    if timeout_seconds < 60 or timeout_seconds > 1800:
        raise SkillHostDenied("Codex timeout outside admitted bounds")
    root = Path(root).resolve()
    config = load_trust_pin(trust_path)
    if _git_head(root) != config["source_commit"]:
        raise SkillHostDenied("running checkout differs from independently trusted release pin")
    # Existing provider qualification must precede the additional skill test.
    from fa3_codex_gate import validate_current_host_receipt
    prior = validate_current_host_receipt(root)
    if prior.get("result") != "PASS":
        raise SkillHostDenied("existing real Codex current-host provider admission is missing or failed")
    bundle_path = Path(bundle_path)
    if (not bundle_path.is_absolute() or bundle_path.stat().st_mode & 0o077
            or bundle_path.is_symlink()):
        raise SkillHostDenied("signed bundle must be an absolute private nonsymlinked file")
    bundle = _read_json(bundle_path)
    task_id, binding, language, skill_id = check_bundle(root, bundle, config)
    supplied_root = Path("/var/lib/fa3-step-ca/certs/root_ca.crt")
    supplied_governance = Path("/etc/fa3/trust/security-governance-approval.pub")
    verifier = SignedSkillAuthorityVerifier(
        source_commit=config["source_commit"],
        registry_sha256=config["registry_sha256"],
        root_ca=supplied_root, security_public_key=supplied_governance,
        strict_host_permissions=True)
    preflight = SkillTaskPreflight(
        {skill_id: binding}, language, root, authority_verifier=verifier)
    supply = _verify_installed_codex(root, Path(binary), Path(archive))
    runtime = codex_preflight(Path(binary))
    with tempfile.TemporaryDirectory(prefix="fa3-skill-codex-host-") as temp:
        scratch = Path(temp)
        repo = scratch / "repo"
        _init_repo(repo)
        task = AgentTask(task_id, "codex-skill-worker", PROVIDER_ID,
                         "work/a.txt", "FA3 verified real skill delivery\n",
                         required_skill_ids=(skill_id,))
        plain = AgentTask(task_id + "-PLAIN", "codex-plain-worker", PROVIDER_ID,
                          "work/b.txt", "FA3 plain Codex reference task\n")
        control = scratch / "control"
        result = Coordinator(repo, control).run(
            [task, plain], CodexAdapter(Path(binary), timeout_seconds=timeout_seconds),
            skill_preflight=preflight)
        worker = json.loads(
            (control / "results" / f"{task_id}.json").read_text(encoding="utf-8"))
        if (worker.get("status") != "PASS"
                or worker.get("verified_skill_ids") != [skill_id]
                or worker.get("skill_evidence_scope") != "PKI_AND_SECURITY_GOVERNANCE_SIGNED"
                or not SHA256.fullmatch(str(worker.get("skill_context_sha256", "")))
                or worker.get("changed_paths") != ["work/a.txt"]
                or worker.get("event_summary", {}).get("forbidden_surface_observed") is not False
                or result.get("integration_author") != "FA3 Integration"
                or result.get("cleanup", {}).get("live_processes") != 0
                or result.get("cleanup", {}).get("worktrees") != 0):
            raise SkillHostDenied("real Codex worker did not consume verified skill correctly")
        return {
            "schema": SCHEMA,
            "result": "OBSERVED_PASS",
            "evidence_level": "UNSIGNED_HOST_OBSERVATION_AWAITING_EXISTING_EVIDENCE_AUTHORITY",
            "source_commit": config["source_commit"],
            "skill_id": skill_id, "task_id": task_id,
            "provider_id": PROVIDER_ID, "adapter_id": ADAPTER_ID,
            "provider_binary_sha256": supply["installed_binary_sha256"],
            "provider_archive_sha256": supply["archive_sha256"],
            "provider_code_mode_host_archive_sha256": supply["code_mode_host"]["archive_sha256"],
            "provider_code_mode_host_binary_sha256": supply["code_mode_host"]["installed_binary_sha256"],
            "provider_code_mode_host_enabled": True,
            "provider_runtime_version": runtime["version"],
            "registry_sha256": config["registry_sha256"],
            "skill_content_sha256": binding.package["digests"]["content_sha256"],
            "worker_skill_context_sha256": worker["skill_context_sha256"],
            "signed_claim_receipt_ids": [
                language["authority_receipt"]["receipt_id"],
                binding.admission["authority_receipt"]["receipt_id"],
                binding.selection["authority_receipt"]["receipt_id"],
            ],
            "checked_authority": "FA3-AUTH-SECURITY-GOV-001",
            "existing_evidence_authority": "FA3-AUTH-OBS-EVIDENCE-001",
            "cross_host_replay_claim": False,
            "global_promotion_claim": False,
            "synthetic_provider": False,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--trust-config", default="/etc/fa3/trust/skill-runtime.json")
    ap.add_argument("--bundle", required=True)
    default = Path.home() / ".local/lib/fa3/codex" / CODEX_VERSION
    ap.add_argument("--codex-binary", default=str(default / "bin/codex"))
    ap.add_argument("--archive", default=str(default / "source" / ARCHIVE_NAME))
    ap.add_argument("--timeout-seconds", type=int, default=600)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    report = root / REPORT
    try:
        value = run_observation(
            root, Path(args.trust_config), Path(args.bundle),
            Path(args.codex_binary), Path(args.archive),
            timeout_seconds=args.timeout_seconds)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({
            "schema": SCHEMA, "result": "FAIL", "global_promotion_claim": False,
            "reason": str(exc),
        }, indent=2) + "\n", encoding="utf-8")
        print(f"FA3 SKILL CODEX CURRENT HOST REJECTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
