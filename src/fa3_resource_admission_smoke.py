#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fa3_resource_admission_policy import classify_requirements

WORKLOAD_ID = "fa3-resource-admission-current-host-smoke-v2"
WORKLOAD_SCHEMA = "fa3.workload-resource-envelope.v1"
CUDA_COMPUTE_CAPABILITY_MIN = 8.6
AUTH_CLIENT_DEFAULT = "/usr/local/bin/fa3-host-resource-broker-admission"
_BDF_RE = re.compile(r"^(?P<domain>[0-9a-fA-F]{4,8}):(?P<bus>[0-9a-fA-F]{2}):(?P<device>[0-9a-fA-F]{2})\.(?P<function>[0-7])$")
_ALLOWED_PLACEHOLDERS = {"workload", "lease", "gpu_uuid", "pci_bdf", "hostname", "workload_id"}


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def normalize_bdf(value: Any) -> str:
    text = str(value or "").strip().lower()
    match = _BDF_RE.fullmatch(text)
    if not match:
        return text
    return f"{match.group('domain')[-4:].lower()}:{match.group('bus').lower()}:{match.group('device').lower()}.{match.group('function')}"


def build_smoke_workload(*, accelerator_required: bool = False) -> dict[str, Any]:
    requirements: list[dict[str, Any]] = [
        {"metric": "cpu.physical_cores", "operator": ">=", "value": 1},
        {"metric": "memory.total_gib", "operator": ">=", "value": 1},
    ]
    if accelerator_required:
        requirements.extend([
            {"metric": "gpu.vram_gib", "operator": ">=", "value": 1},
            {"metric": "gpu.cuda_compute_capability", "operator": ">=", "value": CUDA_COMPUTE_CAPABILITY_MIN},
        ])
    return {
        "schema": WORKLOAD_SCHEMA,
        "workload_id": WORKLOAD_ID,
        "requirements": requirements,
        "global_promotion_claim": False,
    }


def _run(command: list[str], **kwargs: Any) -> CommandResult:
    try:
        proc = subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)
        return CommandResult(proc.returncode, proc.stdout, proc.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", repr(exc))


def discover_accelerator(runner: Callable[..., CommandResult] = _run) -> tuple[dict[str, Any] | None, str | None]:
    result = runner(
        ["nvidia-smi", "--query-gpu=index,uuid,pci.bus_id,compute_cap", "--format=csv,noheader,nounits"],
        timeout=15,
    )
    if result.returncode != 0:
        return None, "NVIDIA_DISCOVERY_FAILED"
    eligible: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 4:
            continue
        try:
            index = int(parts[0])
            compute_capability = float(parts[3])
        except ValueError:
            continue
        if compute_capability < CUDA_COMPUTE_CAPABILITY_MIN:
            continue
        eligible.append({
            "index": index,
            "uuid": parts[1],
            "pci_bdf": normalize_bdf(parts[2]),
            "cuda_compute_capability": compute_capability,
        })
    if not eligible:
        return None, "NO_ELIGIBLE_NVIDIA_ACCELERATOR"
    eligible.sort(key=lambda item: item["index"])
    return eligible[0], None


def render_acquire_command(template: str, values: dict[str, str]) -> list[str]:
    tokens = shlex.split(template)
    rendered: list[str] = []
    placeholder_re = re.compile(r"\{([^{}]+)\}")
    for token in tokens:
        names = placeholder_re.findall(token)
        unknown = sorted(set(names) - _ALLOWED_PLACEHOLDERS)
        if unknown:
            raise ValueError("Unknown HRB acquire placeholder: " + ",".join(unknown))
        value = token
        for name in names:
            value = value.replace("{" + name + "}", values[name])
        rendered.append(value)
    return rendered


def _report(
    result: str,
    reason_code: str,
    *,
    workload: dict[str, Any],
    accelerator: dict[str, Any] | None = None,
    acquire: dict[str, Any] | None = None,
    claims: list[str] | None = None,
) -> dict[str, Any]:
    classes, accelerator_required = classify_requirements(workload.get("requirements", []))
    return {
        "schema": "fa3.resource-admission-smoke-bootstrap-report.v2",
        "result": result,
        "decision": {"reason_code": reason_code, "exit_code": 0 if result == "PASS" else 2},
        "workload": workload,
        "requested_resource_classes": classes,
        "accelerator_required": accelerator_required,
        "accelerator": accelerator,
        "acquire": acquire or {},
        "authority": {
            "authoritative_admission_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "bootstrap_can_mint_or_sign_lease": False,
            "bootstrap_can_mint_non_accelerator_authorization": False,
        },
        "claims": claims or [],
        "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E"],
        "capability_delta": 0,
        "authority_delta": 0,
    }


def run_smoke(
    root: Path,
    *,
    workload_envelope: Path | None = None,
    hrb_lease: Path | None = None,
    hrb_authorization: Path | None = None,
    authorization_client: str = AUTH_CLIENT_DEFAULT,
    prepare_only: bool = False,
    hrb_acquire_command: str | None = None,
    accelerator_required: bool = False,
    runner: Callable[..., CommandResult] = _run,
) -> tuple[int, dict[str, Any]]:
    root = root.resolve()
    workload = build_smoke_workload(accelerator_required=accelerator_required)
    workload_path = workload_envelope or (root / ".fa3-current-host/input/resource-smoke-workload-envelope.json")
    workload_path = workload_path if workload_path.is_absolute() else root / workload_path
    workload_path.parent.mkdir(parents=True, exist_ok=True)
    workload_path.write_text(json.dumps(workload, indent=2) + "\n", encoding="utf-8")

    report_path = root / "reports/resource-admission-smoke-bootstrap-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if not accelerator_required:
        if prepare_only:
            report = _report("PENDING", "PREPARED_AWAITING_HRB_NON_ACCELERATOR_AUTHORIZATION", workload=workload)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 2, report
        authorization_path = hrb_authorization
        acquire_meta: dict[str, Any] = {}
        if authorization_path is None:
            authorization_path = root / ".fa3-current-host/input/resource-smoke-hrb-authorization.json"
            authorization_path.parent.mkdir(parents=True, exist_ok=True)
            authorized = runner([
                authorization_client,
                "authorize",
                "--workload", str(workload_path.resolve()),
                "--output", str(authorization_path.resolve()),
            ], timeout=30)
            acquire_meta = {"return_code": authorized.returncode, "command_name": authorization_client}
            if authorized.returncode != 0 or not authorization_path.is_file():
                result = "PENDING" if authorized.returncode == 127 else "BLOCKED"
                reason = "HRB_AUTHORIZATION_BRIDGE_UNAVAILABLE" if result == "PENDING" else "HRB_AUTHORIZATION_FAILED"
                report = _report(result, reason, workload=workload, acquire=acquire_meta)
                report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                return 2, report
        else:
            authorization_path = authorization_path if authorization_path.is_absolute() else root / authorization_path

        collector = root / "evidence/collect-resource-admission-current-host.py"
        receipt = root / "evidence/receipts/resource-admission-current-host.json"
        collected = runner([
            sys.executable,
            str(collector),
            "--root", str(root),
            "--workload-envelope", str(workload_path.resolve()),
            "--hrb-authorization", str(authorization_path.resolve()),
            "--receipt", str(receipt),
        ], timeout=60)
        if collected.returncode != 0:
            report = _report("BLOCKED", "CURRENT_HOST_COLLECTOR_BLOCKED", workload=workload, acquire=acquire_meta)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 2, report
        gated = runner([str(root / "bin/fa3-enforce"), "resource-admission-current-host"], timeout=60)
        if gated.returncode != 0:
            report = _report("BLOCKED", "CURRENT_HOST_GATE_BLOCKED", workload=workload, acquire=acquire_meta)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 2, report
        report = _report("PASS", "CURRENT_HOST_RESOURCE_ADMISSION_PASS", workload=workload, acquire=acquire_meta, claims=["CURRENT_HOST_RESOURCE_ADMISSION_PASS"])
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 0, report

    accelerator, discovery_error = discover_accelerator(runner)
    if discovery_error or accelerator is None:
        report = _report("BLOCKED", discovery_error or "ACCELERATOR_DISCOVERY_FAILED", workload=workload)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 2, report

    if prepare_only:
        report = _report("PENDING", "PREPARED_AWAITING_HRB_LEASE", workload=workload, accelerator=accelerator)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 2, report

    lease_path = hrb_lease
    acquire_meta: dict[str, Any] = {}
    if lease_path is None:
        template = hrb_acquire_command or os.environ.get("FA3_HRB_ACQUIRE_COMMAND", "").strip()
        if not template:
            report = _report("PENDING", "HRB_ACQUIRE_COMMAND_UNCONFIGURED", workload=workload, accelerator=accelerator)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 2, report
        lease_path = root / ".fa3-current-host/input/resource-smoke-hrb-lease.json"
        lease_path.parent.mkdir(parents=True, exist_ok=True)
        values = {
            "workload": str(workload_path.resolve()),
            "lease": str(lease_path.resolve()),
            "gpu_uuid": str(accelerator["uuid"]),
            "pci_bdf": str(accelerator["pci_bdf"]),
            "hostname": socket.gethostname(),
            "workload_id": WORKLOAD_ID,
        }
        try:
            command = render_acquire_command(template, values)
        except ValueError as exc:
            report = _report("BLOCKED", "HRB_ACQUIRE_COMMAND_INVALID", workload=workload, accelerator=accelerator, acquire={"error": str(exc)})
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 2, report
        acquired = runner(command, timeout=30)
        acquire_meta = {"return_code": acquired.returncode, "command_name": command[0] if command else None}
        if acquired.returncode != 0 or not lease_path.is_file():
            report = _report("BLOCKED", "HRB_ACQUIRE_FAILED", workload=workload, accelerator=accelerator, acquire=acquire_meta)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 2, report
    else:
        lease_path = lease_path if lease_path.is_absolute() else root / lease_path

    collector = root / "evidence/collect-resource-admission-current-host.py"
    receipt = root / "evidence/receipts/resource-admission-current-host.json"
    collected = runner([
        sys.executable,
        str(collector),
        "--root", str(root),
        "--workload-envelope", str(workload_path.resolve()),
        "--hrb-lease", str(lease_path.resolve()),
        "--receipt", str(receipt),
    ], timeout=60)
    if collected.returncode != 0:
        report = _report("BLOCKED", "CURRENT_HOST_COLLECTOR_BLOCKED", workload=workload, accelerator=accelerator, acquire=acquire_meta)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 2, report

    gated = runner([str(root / "bin/fa3-enforce"), "resource-admission-current-host"], timeout=60)
    if gated.returncode != 0:
        report = _report("BLOCKED", "CURRENT_HOST_GATE_BLOCKED", workload=workload, accelerator=accelerator, acquire=acquire_meta)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 2, report

    report = _report("PASS", "CURRENT_HOST_RESOURCE_ADMISSION_PASS", workload=workload, accelerator=accelerator, acquire=acquire_meta, claims=["CURRENT_HOST_RESOURCE_ADMISSION_PASS"])
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed FA3 resource admission smoke bootstrap")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workload-envelope")
    parser.add_argument("--hrb-lease")
    parser.add_argument("--hrb-authorization")
    parser.add_argument("--authorization-client", default=AUTH_CLIENT_DEFAULT)
    parser.add_argument("--hrb-acquire-command")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--accelerator-required", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    code, report = run_smoke(
        root,
        workload_envelope=Path(args.workload_envelope) if args.workload_envelope else None,
        hrb_lease=Path(args.hrb_lease) if args.hrb_lease else None,
        hrb_authorization=Path(args.hrb_authorization) if args.hrb_authorization else None,
        authorization_client=args.authorization_client,
        prepare_only=args.prepare_only,
        hrb_acquire_command=args.hrb_acquire_command,
        accelerator_required=args.accelerator_required,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
