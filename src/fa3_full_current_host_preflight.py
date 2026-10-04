#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from fa3_accelerator_backend_probe import enrich_accelerator_backends
from fa3_application_installation_resolver import discover_group
from fa3_current_host_batch_planner import build_plan
from fa3_current_host_runtime_resolver import resolve_python_runtime
from fa3_desktop_admission import (
    collect_runtime_probes,
    discover_current_user_session_environment,
    evaluate_desktop,
)
from fa3_hardware_discovery import discover_accelerator_devices
from fa3_full_current_host_capability_producer import desktop_wayland_scoped_admission
from fa3_hardware_portability_gate import evaluate as evaluate_hardware_portability
from fa3_release_baseline import load_active_release_baseline


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def command(name: str) -> str | None:
    return shutil.which(name)


def any_command(names: tuple[str, ...]) -> tuple[str, str] | None:
    for name in names:
        path = command(name)
        if path:
            return name, path
    return None


def run(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
    )


def merged_user_session_environment() -> dict[str, str]:
    merged = dict(os.environ)
    systemctl = command("systemctl")
    if not systemctl:
        return merged
    proc = run([systemctl, "--user", "show-environment"], 10)
    if proc.returncode != 0:
        return merged
    wanted = {
        "XDG_CURRENT_DESKTOP",
        "DESKTOP_SESSION",
        "XDG_SESSION_TYPE",
        "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS",
        "WAYLAND_DISPLAY",
        "DISPLAY",
    }
    for line in proc.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in wanted and value and not merged.get(key):
            merged[key] = value
    return merged


def desktop_preflight_admission(
    report: dict[str, Any],
    session_evidence: dict[str, Any],
) -> dict[str, Any]:
    """Apply the same GUI/XDG scope used by the physical desktop proof producer."""
    return desktop_wayland_scoped_admission(report, session_evidence)


def required_primitives(root: Path) -> tuple[set[str], dict[str, dict[str, Any]]]:
    data = load_json(root / "canonical/current-host-capability-proof-recipes.json")
    recipes = data.get("recipes")
    if not isinstance(recipes, list):
        raise RuntimeError("proof recipe registry malformed")
    mapping: dict[str, dict[str, Any]] = {}
    for row in recipes:
        if not isinstance(row, dict) or not isinstance(row.get("capability_id"), str):
            raise RuntimeError("proof recipe row malformed")
        mapping[row["capability_id"]] = row
    shared_count = data.get("shared_recipe_count", data.get("capability_count"))
    if len(mapping) != shared_count:
        raise RuntimeError("shared proof recipe count mismatch")
    baseline = load_active_release_baseline(root)
    active_count = data.get("active_capability_count", data.get("capability_count"))
    if active_count != baseline.capability_count:
        raise RuntimeError("proof recipe active capability count does not match release baseline")
    dedicated = data.get("dedicated_capability_ids", [])
    if not isinstance(dedicated, list) or any(not isinstance(cap, str) for cap in dedicated):
        raise RuntimeError("dedicated capability coverage metadata malformed")
    if len(set(dedicated)) != len(dedicated):
        raise RuntimeError("duplicate dedicated capability coverage")
    if set(mapping).intersection(dedicated):
        raise RuntimeError("shared/dedicated capability coverage overlap")
    evidence = load_json(root / "evidence/evidence-registry.json")
    active_ids = {
        str(row.get("subject_id"))
        for row in evidence.get("records", [])
        if isinstance(row, dict) and isinstance(row.get("subject_id"), str)
    }
    covered_ids = set(mapping).union(dedicated)
    if covered_ids != active_ids or len(covered_ids) != baseline.capability_count:
        raise RuntimeError("shared + dedicated proof coverage does not exactly match active capability registry")
    if data.get("required_test_obligation_count") != baseline.capability_count * 3:
        raise RuntimeError("proof recipe obligation count does not match active 3-way current-host model")
    return {str(row.get("primitive")) for row in mapping.values()}, mapping


def preflight(root: Path) -> dict[str, Any]:
    findings: list[str] = []
    root = root.resolve()

    if os.geteuid() == 0:
        findings.append("full current-host closure execution must be rootless")

    plan = build_plan(root, batch_size=5)
    if plan.get("materialized_obligation_count") != plan.get("required_test_obligation_count"):
        findings.append(
            f"current-host materialization incomplete: {plan.get('materialized_obligation_count')}/"
            f"{plan.get('required_test_obligation_count')} obligations materialized"
        )
    if plan.get("pending_obligation_count") != 0:
        findings.append("pending current-host materialization remains")
    if plan.get("fully_materialized_capability_count") != plan.get("capability_count"):
        findings.append(
            f"not all active capabilities are execution-ready: "
            f"{plan.get('fully_materialized_capability_count')}/{plan.get('capability_count')}"
        )
    if plan.get("next_materialization_batch") is not None:
        findings.append("materialization batch still pending")

    primitives, recipes = required_primitives(root)

    hardware_gate = evaluate_hardware_portability(root)
    if hardware_gate.get("result") != "PASS":
        findings.append("mandatory Hardware Safety / portability gate is not PASS")

    cap175 = recipes.get("CAP-175")
    coexistence_guard = {
        "capability_id": "CAP-175",
        "recipe_present": isinstance(cap175, dict),
        "primitive": cap175.get("primitive") if isinstance(cap175, dict) else None,
        "execution_ready": "CAP-175" in set(plan.get("execution_ready_capabilities", [])),
        "required": True,
    }
    if not coexistence_guard["recipe_present"] or not coexistence_guard["execution_ready"]:
        findings.append("CAP-175 Software Coexistence current-host proof is not execution-ready")

    required_commands = {"python3", "git", "wasmtime"}
    if {"audio_local", "media_video"} & primitives:
        required_commands.update({"ffmpeg", "ffprobe"})
    if "system_runtime" in primitives:
        required_commands.add("uname")

    commands = {name: command(name) for name in sorted(required_commands)}
    for name, path in commands.items():
        if not path:
            findings.append(f"required command missing: {name}")

    any_groups: dict[str, dict[str, Any]] = {}
    if {"graphics_3d", "metric_3d_reconstruction"} & primitives:
        dcc_instances = discover_group(root, "DCC", perform_health_check=True)
        healthy_dcc = [row for row in dcc_instances if row.get("health") == "HEALTHY"]
        any_groups["graphics_3d"] = {
            "discovery": "FA3-APPLICATION-INSTALLATION-REGISTRY-001",
            "instances": dcc_instances,
            "healthy_instance_count": len(healthy_dcc),
            "selected": None,
            "selection_semantics": "NO_PREFLIGHT_RUNTIME_SELECTION_NO_SILENT_FALLBACK",
            "used_by": sorted({"graphics_3d", "metric_3d_reconstruction"} & primitives),
        }
        if not healthy_dcc:
            findings.append("no healthy registered DCC installation instance")
    if "toolchain_build" in primitives:
        found = any_command(("cc", "gcc", "clang"))
        any_groups["toolchain_build"] = {
            "candidates": ["cc", "gcc", "clang"],
            "selected": found[0] if found else None,
            "path": found[1] if found else None,
        }
        if not found:
            findings.append("C compiler missing")

    python_runtimes: dict[str, Any] = {}
    accelerator_inventory: list[dict[str, Any]] = []
    accelerator_runtime: dict[str, Any] = {"required": "gpu_compute" in primitives}
    if accelerator_runtime["required"]:
        accelerator_inventory = [
            device.as_dict()
            for device in enrich_accelerator_backends(
                discover_accelerator_devices(),
                include_framework_probes=False,
            )
        ]
        if not accelerator_inventory:
            findings.append("accelerator-required proof has no physical accelerator inventory")
        gpu_python = resolve_python_runtime(
            require_torch=True,
            require_pytorch3d=False,
            require_cuda=False,
            require_accelerator=True,
        )
        python_runtimes["gpu_compute"] = gpu_python
        selected = gpu_python.get("selected")
        if not isinstance(selected, dict):
            findings.append("no approved local Python runtime with a supported Torch accelerator backend")
            accelerator_runtime.update({"available": False, "backend": None, "python": None})
        else:
            accelerator_runtime.update({
                "available": True,
                "backend": selected.get("accelerator_backend"),
                "python": selected.get("path"),
                "torch_version": selected.get("torch_version"),
                "cuda_available": selected.get("cuda_available"),
                "hip_version": selected.get("hip_version"),
                "xpu_available": selected.get("xpu_available"),
            })

    cuda: dict[str, Any] = {
        "required": False,
        "global_requirement": False,
        "provider_scoped_only": True,
    }
    selected_runtime = python_runtimes.get("gpu_compute", {}).get("selected")
    if isinstance(selected_runtime, dict):
        cuda.update({
            "observed": bool(selected_runtime.get("cuda_available")),
            "count": int(selected_runtime.get("cuda_count", 0) or 0),
        })

    desktop: dict[str, Any] = {"required": "desktop_wayland" in primitives}
    if desktop["required"]:
        session = discover_current_user_session_environment()
        session_env = session["environment"]
        admission = evaluate_desktop(
            session_env,
            collect_runtime_probes(session_env),
            require_gui=True,
        )
        scoped_admission = desktop_preflight_admission(
            admission,
            session.get("evidence", {}),
        )
        desktop.update({
            "legacy_primitive_name": "desktop_wayland",
            "semantics": "GENERIC_QT6_DESKTOP_SESSION_WAYLAND_PREFERRED_X11_SUPPORTED",
            "admission": admission,
            "scope_admission": scoped_admission,
            "session_discovery": session.get("evidence", {}),
        })
        if scoped_admission.get("result") != "PASS":
            findings.append("supported local Qt6/XDG desktop session unavailable to runner")

    if any(row.get("external_side_effects_allowed") is not False for row in recipes.values()):
        findings.append("recipe registry permits external side effects")
    if any(row.get("global_promotion_claim") is not False for row in recipes.values()):
        findings.append("recipe registry contains promotion claim")

    return {
        "schema": "fa3.full-current-host-preflight.v1",
        "result": "PASS" if not findings else "BLOCKED",
        "status": "READY_FOR_FULL_ACTIVE_RELEASE_EXECUTION" if not findings else "BLOCKED_PRE_EXECUTION",
        "execution_scope": "CURRENT_HOST",
        "synthetic": False,
        "global_promotion_claim": False,
        "materialization": {
            "capability_count": plan.get("capability_count"),
            "required_test_obligation_count": plan.get("required_test_obligation_count"),
            "materialized_obligation_count": plan.get("materialized_obligation_count"),
            "pending_obligation_count": plan.get("pending_obligation_count"),
            "fully_materialized_capability_count": plan.get("fully_materialized_capability_count"),
            "pending_materialization_capability_count": plan.get("pending_materialization_capability_count"),
            "next_materialization_batch": plan.get("next_materialization_batch"),
        },
        "shared_recipe_count": len(recipes),
        "primitives": sorted(primitives),
        "commands": commands,
        "any_command_groups": any_groups,
        "python_runtimes": python_runtimes,
        "accelerator_inventory": accelerator_inventory,
        "accelerator_runtime": accelerator_runtime,
        "cuda": cuda,
        "desktop": desktop,
        "hardware_safety_gate": hardware_gate,
        "software_coexistence_guard": coexistence_guard,
        "findings": sorted(set(findings)),
        "truth_constraints": {
            "preflight_pass_is_runtime_closure": False,
            "preflight_pass_is_global_promotion": False,
            "real_active_release_execution_still_required": True,
            "external_side_effects_default": "DENY",
            "hardware_safety_preflight_mandatory": True,
            "software_coexistence_cap175_mandatory": True,
            "historical_current_host_evidence_auto_inheritance": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", default=".fa3-current-host/full-closure/preflight.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = preflight(root)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    write_json(output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
