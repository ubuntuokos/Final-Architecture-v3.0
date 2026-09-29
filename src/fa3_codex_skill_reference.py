"""Offline Codex skill-context consumer reference drill with real file bytes.

A fake Codex binary and synthetic admission receipts are intentionally used.
This is NOT a real Codex provider or current-host production attestation.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fa3_codex_adapter import (
    PROVIDER_ID, CodexAdapter, _init_repo, _write_fake_codex, codex_preflight,
)
from fa3_developer_agent_coordination import AgentTask, Coordinator
from fa3_skill_fabric_gate import good_package, good_use_receipt
from fa3_skill_materialization import snapshot_digests, task_activation_lease, verify_admitted_snapshot
from fa3_skill_task_binding import SkillTaskBinding
from fa3_skill_task_projection import SkillTaskPreflight


def build_reference_fixture(base: Path) -> tuple[SkillTaskPreflight, list[AgentTask]]:
    root = base / "skill-assets"
    content_path = root / "skills/example/SKILL.md"
    content_path.parent.mkdir(parents=True)
    content_path.write_bytes(b"---\nname: example\n---\nUse explicit bounded quality checks.\n")
    package = good_package()
    package["compatibility"]["task_classes"] = ["developer"]
    digests = snapshot_digests(root, ["skills/example/SKILL.md"])
    content_hash = digests["files"][0]["sha256"]
    package["digests"]["content_sha256"] = content_hash
    package["digests"]["manifest_sha256"] = digests["manifest_sha256"]
    package["hash_attestation"]["sha256"] = content_hash
    package["evaluation"]["bound_content_sha256"] = content_hash
    entry = {
        "skill_id": "example", "package_id": package["package_id"],
        "version": "1.0.0", "entrypoint": "skills/example/SKILL.md",
        "admission_status": "ADMITTED",
        "eligibility": {"task_classes": ["developer"]},
    }
    (root / "canonical").mkdir()
    (root / "canonical/skill-registry.json").write_text(
        json.dumps({"id": "FA3-SKILL-REGISTRY-001", "entries": [entry]}), encoding="utf-8")
    admission = {
        "receipt_ref": "skill-admit:codex-fixture", "result": "PASS",
        "package_id": package["package_id"],
        "content_sha256": content_hash,
        "manifest_sha256": digests["manifest_sha256"],
        "dependency_digest_sha256": package["dependencies"]["digest_sha256"],
    }
    selection = {
        "receipt_ref": "skill-select:codex-fixture",
        "package_id": package["package_id"],
        "skill_id": "example", "task_scope": "developer",
        "eligible_skill_ids": ["example"],
    }
    verified = verify_admitted_snapshot(root, package, entry, admission, selection, "developer")
    intent = {k: good_use_receipt()[k] for k in (
        "tool_intent", "model_intent", "resource_intent", "secret_intent")}
    binding = SkillTaskBinding(
        root, package, entry, admission, selection,
        task_activation_lease(verified, task_id="CODEX-CI-A"), intent)
    lang = {
        "primary_language": "hu-HU", "secondary_language": "en-US",
        "user_language": "hu-HU", "work_language": "en-US",
        "output_language": "hu-HU",
        "admitted_language_status": {"hu-HU": "BRIDGED", "en-US": "NATIVE"},
    }
    preflight = SkillTaskPreflight(
        {"example": binding}, lang, root, reference_only=True)
    tasks = [
        AgentTask("CODEX-CI-A", "codex-a", PROVIDER_ID,
                  "work/a.txt", "skill-delivery-ok\n", required_skill_ids=("example",)),
        AgentTask("CODEX-CI-B", "codex-b", PROVIDER_ID,
                  "work/b.txt", "no-skill-delivery\n"),
    ]
    return preflight, tasks


def run_ci_skill_reference_e2e() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="fa3-codex-skill-ci-") as td:
        base = Path(td)
        repo = base / "repo"
        _init_repo(repo)
        fake_codex = base / "codex"
        _write_fake_codex(fake_codex)
        codex_preflight(fake_codex, env={"PATH": os.environ.get("PATH", ""),
                                         "HOME": str(base)})
        preflight, tasks = build_reference_fixture(base)
        control = base / "control"
        result = Coordinator(repo, control).run(
            tasks, CodexAdapter(fake_codex, timeout_seconds=60,
                                allow_ci_reference_skill_context=True),
            skill_preflight=preflight)
        results = [
            json.loads((control / "results" / f"{task.task_id}.json").read_text(encoding="utf-8"))
            for task in tasks
        ]
        ok = (
            result.get("status") == "PASS"
            and results[0].get("verified_skill_ids") == ["example"]
            and results[0].get("skill_evidence_scope") == "CI_REFERENCE_ONLY"
            and bool(results[0].get("skill_context_sha256"))
            and "reasoning" in results[0]["event_summary"]["item_types"]
            and results[1].get("verified_skill_ids") == []
            and not list((control / "ephemeral-skill-context").glob("*.json"))
        )
        return {
            "schema": "fa3.codex-skill-reference-e2e.v1",
            "result": "PASS" if ok else "FAIL",
            "synthetic_codex_binary": True,
            "reference_skill_receipts": True,
            "real_skill_bytes_consumed": ok,
            "current_host_production_claim": False,
            "task_scope": "developer",
            "worker_count": result["worker_count"],
        }
