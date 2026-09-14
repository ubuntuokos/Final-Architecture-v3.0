#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

WORKLOAD_ID = "fa3-resource-admission-current-host-smoke-v1"
WORKLOAD_SCHEMA = "fa3.workload-resource-envelope.v1"
CUDA_COMPUTE_CAPABILITY_MIN = 8.6
DEFAULT_WORKLOAD = Path(".fa3-current-host/input/resource-smoke-workload-envelope.json")
DEFAULT_LEASE = Path(".fa3-current-host/input/resource-smoke-hrb-lease.json")
DEFAULT_REPORT = Path("reports/resource-admission-smoke-bootstrap-report.json")
PRODUCTION_RECEIPT = Path("evidence/receipts/resource-admission-current-host.json")
COLLECTOR = Path("evidence/collect-resource-admission-current-host.py")
ENFORCER = Path("bin/fa3-enforce")
_BDF_RE = re.compile(
    r"^(?P<domain>[0-9a-fA-F]{4,8}):(?P<bus>[0-9a-fA-F]{2}):"
    r"(?P<device>[0-9a-fA-F]{2})\.(?P<function>[0-7])$"
)
_ALLOWED_TEMPLATE_FIELDS = {
    "workload",
    "lease",
    "gpu_uuid",
    "pci_bdf",
    "hostname",
    "workload_id",
}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[..., CommandResult]


def default_runner(
    command: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    timeout: int = 30,
) -> CommandResult:
    try:
        proc = subprocess.run(
            list(command),
            env=dict(env) if env is not None else None,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=False,
            timeout=timeout,
        )
        return CommandResult(proc.returncode, proc.stdout or "", proc.stderr or "")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", repr(exc))


def normalize_bdf(value: Any) -> str:
    text = str(value or "").strip().lower()
    match = _BDF_RE.fullmatch(text)
    if not match:
        return text
    return (
        f"{match.group('domain')[-4:].lower()}:"
        f"{match.group('bus').lower()}:"
        f"{match.group('device').lower()}."
        f"{match.group('function')}"
    )


def build_smoke_workload() -> dict[str, Any]:
    return {
        "schema": WORKLOAD_SCHEMA,
        "workload_id": WORKLOAD_ID,
        "requirements": [
            {"metric": "cpu.physical_cores", "operator": ">=", "value": 1},
            {"metric": "memory.total_gib", "operator": ">=", "value": 1},
            {"metric": "gpu.vram_gib", "operator": ">=", "value": 1},
            {
                "metric": "gpu.cuda_compute_capability",
                "operator": ">=",
                "value": CUDA_COMPUTE_CAPABILITY_MIN,
            },
        ],
        "bootstrap_scope": "CURRENT_HOST_RESOURCE_ADMISSION_SMOKE",
        "global_promotion_claim": False,
    }


def _resolve_under_root(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _base_report(root: Path, workload_path: Path, lease_path: Path | None) -> dict[str, Any]:
    return {
        "schema": "fa3.resource-admission-smoke-bootstrap-report.v1",
        "bootstrap": "FA3-RESOURCE-ADMISSION-CURRENT-HOST-SMOKE-001",
        "scope": "CURRENT_HOST_RESOURCE_ADMISSION_SMOKE",
        "result": "PENDING",
        "decision": {"reason_code": "NOT_EVALUATED", "exit_code": 2},
        "authority": {
            "resource_admission_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "bootstrap_can_mint_or_sign_lease": False,
            "external_hrb_validation_still_required": True,
        },
        "inputs": {
            "workload_envelope": str(workload_path.relative_to(root))
            if workload_path.is_relative_to(root)
            else str(workload_path),
            "hrb_lease": (
                str(lease_path.relative_to(root))
                if lease_path is not None and lease_path.is_relative_to(root)
                else str(lease_path) if lease_path is not None else None
            ),
        },
        "selected_accelerator_hint": None,
        "proof_chain": {
            "collector": str(COLLECTOR),
            "gate": "resource-admission-current-host",
            "production_receipt": str(PRODUCTION_RECEIPT),
        },
        "claims": [],
        "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E"],
        "capability_delta": 0,
        "authority_delta": 0,
    }


def _finish(
    report: dict[str, Any],
    report_path: Path,
    result: str,
    reason: str,
    exit_code: int,
) -> tuple[int, dict[str, Any]]:
    report["result"] = result
    report["decision"] = {"reason_code": reason, "exit_code": exit_code}
    if result == "PASS":
        report["claims"] = ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"]
    else:
        report["claims"] = []
    _write_json(report_path, report)
    return exit_code, report


def discover_accelerator(runner: Runner = default_runner) -> tuple[dict[str, Any] | None, str | None]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,uuid,pci.bus_id,compute_cap",
        "--format=csv,noheader,nounits",
    ]
    result = runner(command, timeout=15)
    if result.returncode != 0:
        return None, "NVIDIA_DISCOVERY_FAILED"

    eligible: list[dict[str, Any]] = []
    for raw_line in result.stdout.splitlines():
        parts = [part.strip() for part in raw_line.split(",")]
        if len(parts) != 4:
            continue
        try:
            index = int(parts[0])
            compute_capability = float(parts[3])
        except ValueError:
            continue
        if compute_capability < CUDA_COMPUTE_CAPABILITY_MIN:
            continue
        uuid = parts[1]
        bdf = normalize_bdf(parts[2])
        if not uuid or not bdf:
            continue
        eligible.append(
            {
                "index_observed": index,
                "uuid": uuid,
                "pci_bdf": bdf,
                "cuda_compute_capability": compute_capability,
            }
        )
    if not eligible:
        return None, "NO_ELIGIBLE_NVIDIA_ACCELERATOR"
    eligible.sort(key=lambda item: int(item["index_observed"]))
    return eligible[0], None


class _StrictTemplateValues(dict[str, str]):
    def __missing__(self, key: str) -> str:
        raise KeyError(key)


def render_acquire_command(template: str, values: Mapping[str, str]) -> list[str]:
    tokens = shlex.split(template)
    if not tokens:
        raise ValueError("HRB acquire command is empty")
    unknown_value_keys = set(values) - _ALLOWED_TEMPLATE_FIELDS
    if unknown_value_keys:
        raise ValueError(f"Unsupported HRB template values: {sorted(unknown_value_keys)}")
    strict = _StrictTemplateValues({key: str(value) for key, value in values.items()})
    rendered: list[str] = []
    for token in tokens:
        try:
            rendered.append(token.format_map(strict))
        except KeyError as exc:
            raise ValueError(f"Unknown HRB acquire placeholder: {exc.args[0]}") from exc
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Invalid HRB acquire command template: {exc}") from exc
    return rendered


def _run_existing_proof_chain(
    root: Path,
    workload_path: Path,
    lease_path: Path,
    runner: Runner,
) -> tuple[int, str]:
    receipt_path = root / PRODUCTION_RECEIPT
    try:
        receipt_path.unlink()
    except FileNotFoundError:
        pass

    collector_cmd = [
        os.environ.get("PYTHON", "python3"),
        str(root / COLLECTOR),
        "--root",
        str(root),
        "--workload-envelope",
        str(workload_path),
        "--hrb-lease",
        str(lease_path),
    ]
    collected = runner(collector_cmd, timeout=90)
    if collected.returncode != 0:
        if collected.returncode == 2:
            return 2, "CANONICAL_COLLECTOR_BLOCKED"
        return 3, "CANONICAL_COLLECTOR_ERROR"

    gate_cmd = [str(root / ENFORCER), "resource-admission-current-host"]
    gated = runner(gate_cmd, timeout=90)
    if gated.returncode != 0:
        if gated.returncode == 2:
            return 2, "CANONICAL_GATE_BLOCKED"
        return 3, "CANONICAL_GATE_ERROR"

    try:
        if receipt_path.stat().st_size <= 0:
            return 3, "CANONICAL_RECEIPT_MISSING_AFTER_PASS"
    except OSError:
        return 3, "CANONICAL_RECEIPT_MISSING_AFTER_PASS"
    return 0, "CURRENT_HOST_RESOURCE_ADMISSION_PASS"


def run_smoke(
    root: Path,
    *,
    workload_envelope: str | Path = DEFAULT_WORKLOAD,
    hrb_lease: str | Path | None = None,
    lease_output: str | Path = DEFAULT_LEASE,
    hrb_acquire_command: str | None = None,
    report_path: str | Path = DEFAULT_REPORT,
    prepare_only: bool = False,
    runner: Runner = default_runner,
) -> tuple[int, dict[str, Any]]:
    root = root.resolve()
    workload_path = _resolve_under_root(root, workload_envelope)
    output_lease_path = _resolve_under_root(root, lease_output)
    report_file = _resolve_under_root(root, report_path)

    workload = build_smoke_workload()
    _write_json(workload_path, workload)

    supplied_lease = _resolve_under_root(root, hrb_lease) if hrb_lease is not None else None
    report = _base_report(root, workload_path, supplied_lease or output_lease_path)

    if supplied_lease is not None:
        try:
            if supplied_lease.stat().st_size <= 0:
                return _finish(report, report_file, "BLOCKED", "HRB_LEASE_MISSING_OR_EMPTY", 2)
        except OSError:
            return _finish(report, report_file, "BLOCKED", "HRB_LEASE_MISSING_OR_EMPTY", 2)
        report["inputs"]["lease_source"] = "PREEXISTING_REAL_HRB_LEASE"
        code, reason = _run_existing_proof_chain(root, workload_path, supplied_lease, runner)
        return _finish(report, report_file, "PASS" if code == 0 else ("BLOCKED" if code == 2 else "ERROR"), reason, code)

    accelerator, discovery_error = discover_accelerator(runner)
    if discovery_error:
        return _finish(report, report_file, "BLOCKED", discovery_error, 2)
    report["selected_accelerator_hint"] = accelerator

    if prepare_only:
        report["inputs"]["lease_source"] = "NOT_ACQUIRED_PREPARE_ONLY"
        return _finish(report, report_file, "PENDING", "PREPARED_AWAITING_HRB_LEASE", 2)

    template = hrb_acquire_command or os.environ.get("FA3_HRB_ACQUIRE_COMMAND")
    if not template:
        report["inputs"]["lease_source"] = "HRB_ACQUIRE_COMMAND_UNCONFIGURED"
        return _finish(report, report_file, "PENDING", "HRB_ACQUIRE_COMMAND_UNCONFIGURED", 2)

    values = {
        "workload": str(workload_path),
        "lease": str(output_lease_path),
        "gpu_uuid": str(accelerator["uuid"]),
        "pci_bdf": str(accelerator["pci_bdf"]),
        "hostname": socket.gethostname(),
        "workload_id": WORKLOAD_ID,
    }
    try:
        acquire_cmd = render_acquire_command(template, values)
    except ValueError as exc:
        report["input_error"] = str(exc)
        return _finish(report, report_file, "ERROR", "HRB_ACQUIRE_COMMAND_INVALID", 3)

    output_lease_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_lease_path.unlink()
    except FileNotFoundError:
        pass

    acquire_env = dict(os.environ)
    acquire_env.update(
        {
            "FA3_WORKLOAD_ENVELOPE": str(workload_path),
            "FA3_HRB_LEASE_OUTPUT": str(output_lease_path),
            "FA3_ACCELERATOR_UUID": str(accelerator["uuid"]),
            "FA3_ACCELERATOR_PCI_BDF": str(accelerator["pci_bdf"]),
            "FA3_SMOKE_WORKLOAD_ID": WORKLOAD_ID,
            "FA3_HOSTNAME": socket.gethostname(),
        }
    )
    acquired = runner(acquire_cmd, env=acquire_env, timeout=45)
    report["inputs"]["lease_source"] = "EXTERNAL_HRB_ACQUIRE_COMMAND"
    report["acquire"] = {
        "executed": True,
        "shell": False,
        "return_code": acquired.returncode,
        "stdout_logged": False,
        "stderr_logged": False,
    }
    if acquired.returncode != 0:
        return _finish(report, report_file, "BLOCKED", "HRB_ACQUIRE_FAILED", 2)
    try:
        if output_lease_path.stat().st_size <= 0:
            return _finish(report, report_file, "BLOCKED", "HRB_ACQUIRE_DID_NOT_PRODUCE_LEASE", 2)
    except OSError:
        return _finish(report, report_file, "BLOCKED", "HRB_ACQUIRE_DID_NOT_PRODUCE_LEASE", 2)

    code, reason = _run_existing_proof_chain(root, workload_path, output_lease_path, runner)
    return _finish(report, report_file, "PASS" if code == 0 else ("BLOCKED" if code == 2 else "ERROR"), reason, code)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the fail-closed FA3 current-host resource-admission smoke chain. "
            "This bootstrap never mints or signs an HRB lease."
        )
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--workload-envelope", default=str(DEFAULT_WORKLOAD))
    parser.add_argument("--hrb-lease")
    parser.add_argument("--lease-output", default=str(DEFAULT_LEASE))
    parser.add_argument("--hrb-acquire-command")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    code, report = run_smoke(
        Path(args.root),
        workload_envelope=args.workload_envelope,
        hrb_lease=args.hrb_lease,
        lease_output=args.lease_output,
        hrb_acquire_command=args.hrb_acquire_command,
        report_path=args.report,
        prepare_only=args.prepare_only,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
