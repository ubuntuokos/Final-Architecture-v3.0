#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

GATE_ID = "FA3-FREE-ONLY-GATESET-001"
POLICY_ID = "FA3-FREE-SELF-HOSTED-ONLY-001"
CAPABILITY_COUNT = 143
BLOCKED = {
    "FA3-PROVIDER-CODEX-001",
    "FA3-PROVIDER-KLING-001",
    "FA3-PROVIDER-SEEDANCE-001",
    "FA3-PROVIDER-MINIMAX-H3-001",
    "FA3-PROVIDER-SD35-NVIDIA-NIM-001",
}
TOMBSTONES = {
    provider_id: f"canonical/providers/{provider_id}.json" for provider_id in BLOCKED
}
REMOVED_RUNTIME_PATHS = [
    ".github/workflows/fa3-codex-current-host.yml",
    "bin/fa3-codex-bootstrap.sh",
    "bin/fa3-codex-current-host.sh",
    "canonical/codex-runtime-admission.json",
    "canonical/contracts/FA3-CODEX-ADAPTER-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-CODEX-ADAPTER-2026-08-31.json",
    "canonical/references/FA3-CODEX-UPSTREAM-REFERENCE-2026-08-31.json",
    "docs/codex-current-host.md",
    "evidence/collect-codex-current-host.py",
    "evidence/reference/codex-adapter-ci-2026-08-31.json",
    "examples/codex-delegated-agent-request.json",
    "src/fa3_codex_adapter.py",
    "tests/test_codex_adapter.py",
    ".github/workflows/fa3-minimax-h3-current-host.yml",
    "bin/fa3-minimax-h3-current-host.sh",
    "canonical/FA3-MINIMAX-H3-RUNTIME-ADMISSION-001.json",
    "canonical/contracts/FA3-MINIMAX-H3-ADAPTER-CONTRACTS-001.json",
    "canonical/decisions/FA3-DEC-MINIMAX-H3-PROJECTION-2026-08-30.json",
    "canonical/decisions/FA3-DEC-MINIMAX-H3-RUNTIME-ADMISSION-2026-09-07.json",
    "canonical/decisions/FA3-DEC-MINIMAX-H3-SERVICE-ACCESS-2026-09-07.json",
    "canonical/decisions/FA3-DEC-VIDEO-H3-2026-08-30.json",
    "canonical/references/FA3-MINIMAX-H3-INTEGRATION-INDEX-REFERENCE-2026-09-12.json",
    "canonical/references/FA3-MINIMAX-H3-SERVICE-REFERENCE-2026-09-07.json",
    "canonical/references/FA3-MINIMAX-H3-UPSTREAM-REFERENCE-2026-08-30.json",
    "canonical/minimax-h3-runtime-admission-enforcement.json",
    "evidence/collect-minimax-h3-current-host.py",
    "evidence/reference/minimax-h3-service-access-ci-2026-09-07.json",
    "src/fa3_minimax_h3_provider_adapter.py",
    "src/fa3_minimax_h3_runtime_admission_gate.py",
    "tests/test_minimax_h3_runtime_admission.py",
    "tests/test_minimax_h3_runtime_gate.py",
]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def active_profile_provider_ids(root: Path) -> set[str]:
    active: set[str] = set()
    for path in (root / "canonical/profiles").glob("*.json"):
        try:
            data = loadj(path)
        except Exception:
            continue
        for key in ("providers", "provider_ids"):
            values = data.get(key, [])
            if isinstance(values, list):
                active.update(x for x in values if isinstance(x, str) and x.startswith("FA3-PROVIDER-"))
    return active


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    policy_path = root / "canonical/policies/FA3-FREE-SELF-HOSTED-ONLY-001.json"
    contract_path = root / "canonical/contracts/FA3-PROVIDER-ECONOMICS-CONTRACTS-001.json"
    if not policy_path.is_file() or not contract_path.is_file():
        return {"gate_id": GATE_ID, "result": "FAIL", "findings": [finding("FREE-ONLY-001", "free-only economics policy/contract missing")]}
    policy = loadj(policy_path)
    contract = loadj(contract_path)
    if not (
        policy.get("id") == POLICY_ID
        and policy.get("priority") == "P0"
        and policy.get("requirement") == "MUST"
        and policy.get("capability_count") == CAPABILITY_COUNT
        and policy.get("supersedes_conflicting_paid_routes_in_prior_records") is True
    ):
        findings.append(finding("FREE-ONLY-002", "free-only policy identity or closure drift"))
    if not (
        contract.get("id") == "FA3-PROVIDER-ECONOMICS-CONTRACTS-001"
        and contract.get("provider_neutral") is True
        and contract.get("capability_count") == CAPABILITY_COUNT
        and contract.get("policy") == POLICY_ID
    ):
        findings.append(finding("FREE-ONLY-003", "provider economics contract drift"))

    active = active_profile_provider_ids(root)
    leaked = sorted(active & BLOCKED)
    if leaked:
        findings.append(finding("FREE-ONLY-004", "removed payment-bearing provider returned to an active profile", providers=leaked))

    for provider_id, rel in sorted(TOMBSTONES.items()):
        path = root / rel
        if not path.is_file():
            findings.append(finding("FREE-ONLY-005", "removed provider tombstone missing", provider=provider_id))
            continue
        d = loadj(path)
        if not (
            str(d.get("status", "")).startswith("REMOVED_")
            and d.get("active") is False
            and d.get("routing_eligible") is False
            and d.get("production_admission") == "DENY"
            and d.get("runtime_surface") == "ABSENT"
            and d.get("capability_count") == CAPABILITY_COUNT
        ):
            findings.append(finding("FREE-ONLY-006", "removed provider tombstone became usable", provider=provider_id))

    returned = [rel for rel in REMOVED_RUNTIME_PATHS if (root / rel).exists()]
    if returned:
        findings.append(finding("FREE-ONLY-007", "removed paid runtime/service surface returned", paths=returned))

    video = loadj(root / "canonical/profiles/FA3-VIDEO-001.json")
    if set(video.get("providers", [])) & BLOCKED or video.get("paid_provider_fallback") is not False or video.get("economics_policy") != POLICY_ID:
        findings.append(finding("FREE-ONLY-008", "video profile is not free-only"))

    stability = loadj(root / "canonical/profiles/FA3-STABILITY-PORTFOLIO-001.json")
    if "FA3-PROVIDER-SD35-NVIDIA-NIM-001" in stability.get("providers", []) or stability.get("paid_provider_fallback") is not False or stability.get("economics_policy") != POLICY_ID:
        findings.append(finding("FREE-ONLY-009", "Stability portfolio is not free-only"))

    stable_audio = loadj(root / "canonical/providers/FA3-PROVIDER-STABLE-AUDIO-3-001.json")
    routes = stable_audio.get("routes", {})
    if not (
        stable_audio.get("paid_routes_allowed") is False
        and stable_audio.get("remote_paid_fallback") is False
        and stable_audio.get("economics_policy") == POLICY_ID
        and routes.get("large") == "REMOVED_PAID_ROUTE"
        and routes.get("small_music") == "CPU_LOCAL_CANDIDATE"
        and routes.get("small_sfx") == "CPU_LOCAL_CANDIDATE"
        and routes.get("medium") == "CUDA_LOCAL_CANDIDATE_SUBJECT_TO_HRB_E2E"
    ):
        findings.append(finding("FREE-ONLY-010", "Stable Audio paid route removal/local-route retention drift"))

    obsidian = loadj(root / "canonical/providers/FA3-PROVIDER-OBSIDIAN-001.json")
    if not (
        obsidian.get("free_core_only") is True
        and obsidian.get("paid_addons_allowed") is False
        and obsidian.get("economics_policy") == POLICY_ID
        and obsidian.get("canonical_projection", {}).get("sync_and_publish") == "FORBIDDEN_PAID_ADDONS"
    ):
        findings.append(finding("FREE-ONLY-011", "Obsidian paid add-on removal drift"))
    workspace = loadj(root / "canonical/contracts/FA3-HUMAN-KNOWLEDGE-WORKSPACE-CONTRACTS-001.json")
    surfaces = workspace.get("provider_surfaces", {})
    if surfaces.get("sync") != "FORBIDDEN_PAID_ADDON" or surfaces.get("publish") != "FORBIDDEN_PAID_ADDON":
        findings.append(finding("FREE-ONLY-012", "Obsidian Sync/Publish became admissible again"))

    manifest = loadj(root / "fa3-current-host/manifest.json")
    current_names = {x.get("name") for x in manifest.get("registered_current_host_surfaces", [])}
    if {"codex", "minimax-h3"} & current_names:
        findings.append(finding("FREE-ONLY-013", "removed paid provider remains in current-host runtime surfaces", surfaces=sorted({"codex", "minimax-h3"} & current_names)))
    if manifest.get("economics_policy") != POLICY_ID or manifest.get("paid_provider_runtime_surfaces") != "FORBIDDEN":
        findings.append(finding("FREE-ONLY-014", "current-host projection does not enforce free-only economics policy"))

    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.free-only-gate-report.v1",
        "gate_id": GATE_ID,
        "policy_id": POLICY_ID,
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "blocked_provider_count": len(BLOCKED),
        "removed_runtime_surface_count": len(REMOVED_RUNTIME_PATHS),
        "active_profile_provider_count": len(active),
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
    }
    out = root / "reports/free-only-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
