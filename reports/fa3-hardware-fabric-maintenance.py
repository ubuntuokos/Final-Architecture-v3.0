#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_REL = Path("canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")
BASE_COMMIT = "1d8a3ffaa2b4d11abcc6003250ff66b4798eef60"
MUTABLE_TOP = {".git", "reports", "acceptance", "promotion", ".pytest_cache", ".mypy_cache", ".fa3-current-host"}
MUTABLE_DIRS = {"__pycache__"}


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def git(*args: str) -> str:
    return run("git", *args).stdout.strip()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"expected maintenance pattern missing in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_loop_profile() -> None:
    path = ROOT / "canonical/profiles/FA3-CLOSED-LOOP-AGENT-OPERATIONS-001.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["version"] = "1.0.2"
    hw = obj["portable_hardware_minimum"]
    hw["gpu"] = {
        "device_count_min": 1,
        "vendor": "NVIDIA",
        "cuda_compute_capability_min": 8.6,
        "sku_series_admission_authority": False,
        "marketing_identity_required": False,
        "specific_sku_pinned": False,
        "specific_vram_pinned": False,
        "specific_sm_pinned": False,
    }
    hw["semantic_reconciliation"] = "RTX_MARKETING_SERIES_SUPERSEDED_BY_CUDA_COMPUTE_CAPABILITY_8_6"
    write_json(path, obj)


def patch_global_policy() -> None:
    path = ROOT / "canonical/enforcement-policy.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    env = obj.setdefault("fa3_portable_minimum_hardware_envelope", {})
    env["gpu"] = {
        "device_count_min": 1,
        "vendor": "NVIDIA",
        "cuda_compute_capability_min": 8.6,
        "sku_series_admission_authority": False,
        "marketing_identity_required": False,
        "specific_sku_restriction": "NONE",
        "specific_vram_restriction": "NONE",
        "specific_sm_restriction": "NONE",
    }
    env["semantic_reconciliation"] = "FA3-HARDWARE-FABRIC-RECONCILIATION-001"
    write_json(path, obj)


def patch_reference_helper() -> None:
    path = ROOT / "src/fa3_closed_loop_agent_ops_reference.py"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"def portable_hardware_floor_valid\(\*, cpu_packages: int,.*?\n\s*\)\n(?=def disabled_provider_valid)", re.S)
    replacement = '''def portable_hardware_floor_valid(*, cpu_packages: int,
                                  physical_cores_per_package: int,
                                  cpu_vendor_pinned: bool,
                                  cpu_model_pinned: bool,
                                  gpu_count: int,
                                  gpu_vendor: str = "NVIDIA",
                                  gpu_compute_capability: float | None = None,
                                  gpu_specific_sku_pinned: bool,
                                  gpu_specific_vram_pinned: bool,
                                  gpu_specific_sm_pinned: bool,
                                  gpu_rtx_series: int | None = None,
                                  newer_rtx_generations_allowed: bool | None = None) -> bool:
    """Portable global floor is capability-based; legacy RTX args are compatibility-only."""
    if gpu_compute_capability is None:
        legacy_eligible = (
            gpu_rtx_series is not None
            and gpu_rtx_series >= 30
            and newer_rtx_generations_allowed is True
        )
        gpu_compute_capability = 8.6 if legacy_eligible else 0.0
    return (
        cpu_packages >= 1
        and physical_cores_per_package >= 8
        and not cpu_vendor_pinned
        and not cpu_model_pinned
        and gpu_count >= 1
        and str(gpu_vendor).strip().upper() == "NVIDIA"
        and float(gpu_compute_capability) >= 8.6
        and not gpu_specific_sku_pinned
        and not gpu_specific_vram_pinned
        and not gpu_specific_sm_pinned
    )

'''
    new_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        if "Portable global floor is capability-based" in text:
            return
        raise RuntimeError("portable_hardware_floor_valid block not found")
    path.write_text(new_text, encoding="utf-8")


def patch_loop_gate() -> None:
    path = ROOT / "src/fa3_loop_engineering_gate.py"
    text = path.read_text(encoding="utf-8")

    text = text.replace(
        'gpu_count=1, gpu_rtx_series=30, gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False, gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True)',
        'gpu_count=1, gpu_vendor="NVIDIA", gpu_compute_capability=8.6, gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False, gpu_specific_sm_pinned=False)'
    )
    text = text.replace(
        'gpu_count=2, gpu_rtx_series=50, gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False, gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True)',
        'gpu_count=2, gpu_vendor="NVIDIA", gpu_compute_capability=12.0, gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False, gpu_specific_sm_pinned=False)'
    )
    text = text.replace(
        'gpu_count=1, gpu_rtx_series=20, gpu_specific_sku_pinned=True, gpu_specific_vram_pinned=False, gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True)',
        'gpu_count=1, gpu_vendor="NVIDIA", gpu_compute_capability=8.0, gpu_specific_sku_pinned=True, gpu_specific_vram_pinned=False, gpu_specific_sm_pinned=False)'
    )

    old_a = '''        and hw_gpu.get("device_count_min") == 1
        and hw_gpu.get("rtx_series_floor") == 30
        and hw_gpu.get("newer_rtx_generations_allowed") is True
        and hw_gpu.get("specific_sku_pinned") is False
        and hw_gpu.get("specific_vram_pinned") is False
        and hw_gpu.get("specific_sm_pinned") is False'''
    new_a = '''        and hw_gpu.get("device_count_min") == 1
        and hw_gpu.get("vendor") == "NVIDIA"
        and float(hw_gpu.get("cuda_compute_capability_min", 0)) == 8.6
        and hw_gpu.get("sku_series_admission_authority") is False
        and hw_gpu.get("marketing_identity_required") is False
        and hw_gpu.get("specific_sku_pinned") is False
        and hw_gpu.get("specific_vram_pinned") is False
        and hw_gpu.get("specific_sm_pinned") is False'''
    if old_a in text:
        text = text.replace(old_a, new_a, 1)

    old_b = '''        and hw_global_gpu.get("minimum_qualifying_device_count") == 1
        and hw_global_gpu.get("minimum_product_series") == "NVIDIA_RTX_30_SERIES"
        and hw_global_gpu.get("accepted_product_series") == "NVIDIA_RTX_30_SERIES_OR_NEWER"
        and hw_global_gpu.get("newer_rtx_series") == "ALLOWED"
        and hw_global_gpu.get("exact_sku_pin") == "FORBIDDEN"
        and hw_global_gpu.get("architecture_equivalence_without_rtx30_or_newer_series_identity") == "DOES_NOT_SATISFY_MINIMUM"
        and hardware_contract.get("id") == "FA3-HW-CONTRACTS-001"
        and hw_contract_floor.get("cpu", {}).get("package_count_min") == 1
        and hw_contract_floor.get("cpu", {}).get("physical_cores_per_qualifying_cpu_min") == 8
        and hw_contract_floor.get("gpu", {}).get("rtx_series_floor") == 30
        and hw_contract_floor.get("gpu", {}).get("newer_rtx_series_allowed") is True
        and hw_contract_floor.get("gpu", {}).get("architecture_equivalence_alone_insufficient") is True'''
    new_b = '''        and hw_global_gpu.get("minimum_qualifying_device_count") == 1
        and hw_global_gpu.get("vendor") == "NVIDIA"
        and float(hw_global_gpu.get("cuda_compute_capability_min", 0)) == 8.6
        and hw_global_gpu.get("sku_series_admission_authority") is False
        and hw_global_gpu.get("marketing_identity_required") is False
        and hw_global_gpu.get("exact_sku_pin") == "FORBIDDEN"
        and hardware_contract.get("id") == "FA3-HW-CONTRACTS-001"
        and hw_contract_floor.get("cpu", {}).get("package_count_min") == 1
        and hw_contract_floor.get("cpu", {}).get("physical_cores_per_qualifying_cpu_min") == 8
        and hw_contract_floor.get("gpu", {}).get("vendor") == "NVIDIA"
        and float(hw_contract_floor.get("gpu", {}).get("cuda_compute_capability_min", 0)) == 8.6
        and hw_contract_floor.get("gpu", {}).get("sku_series_is_admission_authority") is False
        and hw_contract_floor.get("gpu", {}).get("marketing_identity_required") is False'''
    if old_b in text:
        text = text.replace(old_b, new_b, 1)

    old_policy = '''        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("rtx_series_floor") == 30
        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("newer_rtx_generations_allowed") is True
        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("specific_sku_restriction") == "NONE"'''
    new_policy = '''        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("vendor") == "NVIDIA"
        and float(policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("cuda_compute_capability_min", 0)) == 8.6
        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("sku_series_admission_authority") is False
        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("marketing_identity_required") is False
        and policy.get("fa3_portable_minimum_hardware_envelope", {}).get("gpu", {}).get("specific_sku_restriction") == "NONE"'''
    if old_policy in text:
        text = text.replace(old_policy, new_policy, 1)

    if 'hw_global_gpu.get("minimum_product_series")' in text or 'hw_contract_floor.get("gpu", {}).get("rtx_series_floor")' in text:
        raise RuntimeError("legacy root hardware checks remain in Loop Engineering gate")
    path.write_text(text, encoding="utf-8")


def patch_loop_tests() -> None:
    path = ROOT / "tests/test_loop_engineering_gate.py"
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'gpu_count=1, gpu_rtx_series=30,\n\s*gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,\n\s*gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True,',
        'gpu_count=1, gpu_vendor="NVIDIA", gpu_compute_capability=8.6,\n            gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,\n            gpu_specific_sm_pinned=False,',
        text,
    )
    text = re.sub(
        r'gpu_count=1, gpu_rtx_series=50,\n\s*gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,\n\s*gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True,',
        'gpu_count=1, gpu_vendor="NVIDIA", gpu_compute_capability=12.0,\n            gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,\n            gpu_specific_sm_pinned=False,',
        text,
    )
    text = re.sub(
        r'gpu_count=1, gpu_rtx_series=20,\n\s*gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,\n\s*gpu_specific_sm_pinned=False, newer_rtx_generations_allowed=True,',
        'gpu_count=1, gpu_vendor="NVIDIA", gpu_compute_capability=8.0,\n            gpu_specific_sku_pinned=False, gpu_specific_vram_pinned=False,\n            gpu_specific_sm_pinned=False,',
        text,
    )
    path.write_text(text, encoding="utf-8")


def patch_reconciliation_record() -> None:
    path = ROOT / "canonical/FA3-HARDWARE-FABRIC-RECONCILIATION-001.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj["dependent_semantic_reconciliations"] = {
        "closed_loop_agent_operations": "CUDA_COMPUTE_CAPABILITY_8_6_GLOBAL_FLOOR_INHERITED",
        "global_enforcement_policy": "CUDA_COMPUTE_CAPABILITY_8_6_GLOBAL_FLOOR_INHERITED",
        "legacy_rule_identifier_retained_for_compatibility": "FA3_PORTABLE_HARDWARE_FLOOR_CPU_1X8C_GPU_RTX30_OR_NEWER_NO_MODEL_PIN",
        "legacy_rule_identifier_is_admission_authority": False,
    }
    write_json(path, obj)


def patch_files() -> None:
    patch_loop_profile()
    patch_global_policy()
    patch_reference_helper()
    patch_loop_gate()
    patch_loop_tests()
    patch_reconciliation_record()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def is_mutable(rel: str) -> bool:
    parts = Path(rel).parts
    if not parts:
        return True
    if parts[0] in MUTABLE_TOP:
        return True
    if any(part in MUTABLE_DIRS for part in parts):
        return True
    if rel.startswith("evidence/receipts/") and rel != "evidence/receipts/.gitkeep":
        return True
    return False


def diff_rows(snapshot: str) -> list[tuple[str, str]]:
    raw = git("diff", "--name-status", "--find-renames", BASE_COMMIT, snapshot)
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        rows.append((status, path))
    return rows


def baseline_status(rel: str) -> str:
    exists = run("git", "cat-file", "-e", f"{BASE_COMMIT}:{rel}", check=False).returncode == 0
    if not exists:
        return "added"
    base_sha = git("rev-parse", f"{BASE_COMMIT}:{rel}")
    return "unchanged" if base_sha == git_blob_sha(ROOT / rel) else "modified"


def regenerate_projection() -> None:
    path = ROOT / PROJECTION_REL
    obj = json.loads(path.read_text(encoding="utf-8"))
    snapshot = git("rev-parse", "HEAD")
    rows = diff_rows(snapshot)
    paths = [p for _, p in rows]
    added = sum(s.startswith("A") for s, _ in rows)
    modified = sum(s.startswith("M") for s, _ in rows)
    removed = sum(s.startswith("D") for s, _ in rows)
    other = len(rows) - added - modified - removed

    source = obj.setdefault("source_snapshot", {})
    source.update({
        "snapshot_semantics": "PRE_MAINTENANCE_CANONICAL_MAIN_ANCHOR",
        "baseline_commit_sha": BASE_COMMIT,
        "pre_projection_head_sha": snapshot,
        "pre_projection_root_tree_sha": git("rev-parse", f"{snapshot}^{{tree}}"),
        "pre_projection_canonical_tree_sha": git("rev-parse", f"{snapshot}:canonical"),
        "commits_ahead_of_v3_0_11_conformance_commit": int(git("rev-list", "--count", f"{BASE_COMMIT}..{snapshot}")),
        "total_post_baseline_commits": int(git("rev-list", "--count", f"{BASE_COMMIT}..{snapshot}")),
        "delta_file_count": len(rows),
        "delta_added_files": added,
        "delta_modified_files": modified,
        "delta_removed_files": removed,
        "delta_other_files": other,
    })

    def pref(prefix: str) -> list[str]:
        return sorted(p for p in paths if p.startswith(prefix))

    inventory = obj.setdefault("overlay_inventory", {})
    inventory.update({
        "canonical_files_in_post_baseline_delta": len(pref("canonical/")),
        "evidence_files_in_post_baseline_delta": len(pref("evidence/")),
        "source_files_in_post_baseline_delta": len(pref("src/")),
        "test_files_in_post_baseline_delta": len(pref("tests/")),
        "workflow_files_in_post_baseline_delta": len(pref(".github/workflows/")),
        "provider_records": pref("canonical/providers/"),
        "profile_records": pref("canonical/profiles/"),
        "contract_records": pref("canonical/contracts/"),
        "decision_records": pref("canonical/decisions/"),
        "upstream_reference_records": pref("canonical/references/"),
        "reference_evidence_records": pref("evidence/reference/"),
    })

    release_files: list[str] = []
    for file in ROOT.rglob("*"):
        if not file.is_file():
            continue
        rel = file.relative_to(ROOT).as_posix()
        if rel == PROJECTION_REL.as_posix() or is_mutable(rel):
            continue
        release_files.append(rel)
    release_files.sort()
    manifest = [
        {
            "path": rel,
            "git_blob_sha": git_blob_sha(ROOT / rel),
            "baseline_delta_status": baseline_status(rel),
        }
        for rel in release_files
    ]
    obj["manifest"] = manifest
    obj["manifest_entry_count"] = len(manifest)
    obj["manifest_scope"] = {
        "repository_release_surface_complete": True,
        "self_excluded_path": PROJECTION_REL.as_posix(),
        "mutable_runtime_evidence_receipts_excluded": True,
    }
    write_json(path, obj)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("patch", "projection", "all"))
    args = parser.parse_args()
    if args.mode in {"patch", "all"}:
        patch_files()
    if args.mode in {"projection", "all"}:
        regenerate_projection()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
