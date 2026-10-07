#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

WORKLOAD_SCHEMA = "fa3.workload-resource-envelope.v1"
ACQUIRE_CLIENT = Path("/usr/local/bin/fa3-host-resource-broker-acquire")
ADMISSION_CLIENT = Path("/usr/local/bin/fa3-host-resource-broker-admission")
VALIDATOR_CLIENT = Path("/usr/local/bin/fa3-host-resource-broker-validator")
COLLECTOR = Path("evidence/collect-resource-admission-current-host.py")
ENFORCER = Path("bin/fa3-enforce")
RECEIPT = Path("evidence/receipts/resource-admission-current-host.json")
DEFAULT_LEASE = Path(".fa3-current-host/input/resource-hrb-lease.json")
DEFAULT_AUTHORIZATION = Path(".fa3-current-host/input/resource-hrb-authorization.json")
DEFAULT_REPORT = Path("reports/host-bootstrap-admission-orchestrator-report.json")
FORBIDDEN_METRICS = {"cu", "tu", "compute_unit", "tensor_unit", "aggregate.cu", "aggregate.tu"}
_ACCELERATOR_PREFIXES = ("gpu.", "npu.", "accelerator.")
_BDF_RE = re.compile(r"^(?P<domain>[0-9a-fA-F]{4,8}):(?P<bus>[0-9a-fA-F]{2}):(?P<device>[0-9a-fA-F]{2})\.(?P<function>[0-7])$")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str], int], CommandResult]


def run_command(command: Sequence[str], timeout: int = 60) -> CommandResult:
    try:
        proc = subprocess.run(
            list(command),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        return CommandResult(proc.returncode, proc.stdout or "", proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
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


def load_workload(path: Path) -> dict[str, Any]:
    try:
        workload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("WORKLOAD_UNREADABLE") from exc
    if not isinstance(workload, dict) or workload.get("schema") != WORKLOAD_SCHEMA:
        raise ValueError("WORKLOAD_SCHEMA_MISMATCH")
    if not str(workload.get("workload_id", "")).strip():
        raise ValueError("WORKLOAD_ID_MISSING")
    requirements = workload.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("WORKLOAD_REQUIREMENTS_EMPTY")
    for item in requirements:
        if not isinstance(item, dict):
            raise ValueError("WORKLOAD_REQUIREMENT_INVALID")
        metric = str(item.get("metric", "")).strip().lower()
        if metric in FORBIDDEN_METRICS:
            raise ValueError("FORBIDDEN_CU_TU_ADMISSION_METRIC")
        if not metric or item.get("operator") not in {">=", "<=", "==", "contains"} or "value" not in item:
            raise ValueError("WORKLOAD_REQUIREMENT_INVALID")
    return workload


def workload_requires_accelerator(workload: dict[str, Any]) -> bool:
    return any(
        str(item.get("metric", "")).strip().lower().startswith(_ACCELERATOR_PREFIXES)
        for item in workload.get("requirements", [])
        if isinstance(item, dict)
    )


def required_gpu_memory_bytes(workload: dict[str, Any]) -> int:
    values: list[float] = []
    for item in workload.get("requirements", []):
        if str(item.get("metric", "")).strip().lower() != "gpu.vram_gib":
            continue
        if item.get("operator") != ">=":
            raise ValueError("GPU_VRAM_REQUIREMENT_MUST_USE_GTE")
        try:
            gib = float(item.get("value"))
        except (TypeError, ValueError) as exc:
            raise ValueError("GPU_VRAM_REQUIREMENT_INVALID") from exc
        if not math.isfinite(gib) or gib <= 0:
            raise ValueError("GPU_VRAM_REQUIREMENT_INVALID")
        values.append(gib)
    if not values:
        raise ValueError("GPU_VRAM_REQUIREMENT_MISSING")
    return int(math.ceil(max(values) * (1024 ** 3)))


def minimum_compute_capability(workload: dict[str, Any]) -> float:
    floor = 0.0
    for item in workload.get("requirements", []):
        if str(item.get("metric", "")).strip().lower() != "gpu.cuda_compute_capability":
            continue
        if item.get("operator") != ">=":
            raise ValueError("GPU_COMPUTE_CAPABILITY_REQUIREMENT_MUST_USE_GTE")
        try:
            value = float(item.get("value"))
        except (TypeError, ValueError) as exc:
            raise ValueError("GPU_COMPUTE_CAPABILITY_REQUIREMENT_INVALID") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValueError("GPU_COMPUTE_CAPABILITY_REQUIREMENT_INVALID")
        floor = max(floor, value)
    return floor


def discover_candidate(workload: dict[str, Any], runner: Runner = run_command) -> dict[str, Any]:
    required_bytes = required_gpu_memory_bytes(workload)
    cc_floor = minimum_compute_capability(workload)
    result = runner(
        [
            "nvidia-smi",
            "--query-gpu=index,uuid,pci.bus_id,memory.total,compute_cap",
            "--format=csv,noheader,nounits",
        ],
        15,
    )
    if result.returncode != 0:
        raise ValueError("NVIDIA_DISCOVERY_FAILED")
    eligible: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 5:
            continue
        try:
            index = int(parts[0])
            memory_bytes = int(float(parts[3]) * 1024 * 1024)
            compute_capability = float(parts[4])
        except ValueError:
            continue
        if memory_bytes < required_bytes or compute_capability < cc_floor:
            continue
        if not parts[1] or not normalize_bdf(parts[2]):
            continue
        eligible.append(
            {
                "index_observed": index,
                "uuid": parts[1],
                "pci_bdf": normalize_bdf(parts[2]),
                "memory_total_bytes": memory_bytes,
                "cuda_compute_capability": compute_capability,
            }
        )
    if not eligible:
        raise ValueError("NO_ACCELERATOR_SATISFIES_REQUEST_HINT")
    eligible.sort(key=lambda item: int(item["index_observed"]))
    return eligible[0]


def _write_json_private(path: Path, value: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _report(
    *,
    result: str,
    reason: str,
    exit_code: int,
    workload: Path | None = None,
    lease: Path | None = None,
    authorization: Path | None = None,
    candidate: dict[str, Any] | None = None,
    accelerator_required: bool | None = None,
) -> dict[str, Any]:
    return {
        "schema": "fa3.host-bootstrap-admission-orchestrator-report.v2",
        "orchestrator": "FA3-HOST-BOOTSTRAP-ADMISSION-ORCHESTRATOR-001",
        "result": result,
        "decision": {"reason_code": reason, "exit_code": exit_code},
        "inputs": {
            "workload_envelope": str(workload) if workload else None,
            "hrb_authorization": str(authorization) if authorization else None,
            "hrb_lease": str(lease) if lease else None,
        },
        "accelerator_required": accelerator_required,
        "candidate_request_hint": candidate,
        "authority": {
            "resource_admission_authority": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "orchestrator_is_authority": False,
            "orchestrator_can_sign_lease": False,
            "orchestrator_can_sign_authorization": False,
        },
        "claims": ["CURRENT_HOST_RESOURCE_ADMISSION_PASS"] if result == "PASS" else [],
        "non_claims": ["GLOBAL_FA3_PROMOTION", "PROVIDER_RUNTIME_E2E"],
        "capability_delta": 0,
        "authority_delta": 0,
    }


def doctor(root: Path, runner: Runner = run_command) -> tuple[int, dict[str, Any]]:
    checks = {
        "acquire_client": ACQUIRE_CLIENT.is_file() and os.access(ACQUIRE_CLIENT, os.X_OK),
        "admission_client": ADMISSION_CLIENT.is_file() and os.access(ADMISSION_CLIENT, os.X_OK),
        "validator_client": VALIDATOR_CLIENT.is_file() and os.access(VALIDATOR_CLIENT, os.X_OK),
        "collector": (root / COLLECTOR).is_file(),
        "enforcer": (root / ENFORCER).is_file() and os.access(root / ENFORCER, os.X_OK),
        "non_root_runtime": os.geteuid() != 0,
    }
    checks["acquire_bridge_doctor"] = (
        runner([str(ACQUIRE_CLIENT), "--doctor"], 15).returncode == 0 if checks["acquire_client"] else False
    )
    checks["admission_bridge_doctor"] = (
        runner([str(ADMISSION_CLIENT), "--doctor"], 15).returncode == 0 if checks["admission_client"] else False
    )
    passed = all(checks.values())
    report = _report(
        result="PASS" if passed else "BLOCKED",
        reason="HOST_ADMISSION_READY" if passed else "HOST_ADMISSION_PREREQUISITE_MISSING",
        exit_code=0 if passed else 2,
    )
    report["checks"] = checks
    report["hardware_observation"] = {
        "nvidia_smi_available": shutil.which("nvidia-smi") is not None,
        "nvidia_smi_required_for_cpu_only": False,
        "hardware_baseline": "VENDOR_NEUTRAL_CPU_ONLY_VIABLE_ACCELERATORS_0_TO_N",
    }
    return (0 if passed else 2), report


def admit(
    root: Path,
    workload_path: Path,
    *,
    lease_path: Path = DEFAULT_LEASE,
    authorization_path: Path = DEFAULT_AUTHORIZATION,
    report_path: Path = DEFAULT_REPORT,
    runner: Runner = run_command,
    acquire_client: Path = ACQUIRE_CLIENT,
    admission_client: Path = ADMISSION_CLIENT,
) -> tuple[int, dict[str, Any]]:
    root = root.resolve()
    workload_path = workload_path.resolve()
    lease_path = lease_path.resolve() if lease_path.is_absolute() else (root / lease_path).resolve()
    authorization_path = (
        authorization_path.resolve()
        if authorization_path.is_absolute()
        else (root / authorization_path).resolve()
    )
    report_path = report_path.resolve() if report_path.is_absolute() else (root / report_path).resolve()

    try:
        workload = load_workload(workload_path)
    except ValueError as exc:
        report = _report(result="BLOCKED", reason=str(exc), exit_code=2, workload=workload_path)
        _write_json_private(report_path, report)
        return 2, report

    accelerator_required = workload_requires_accelerator(workload)
    candidate: dict[str, Any] | None = None
    collector_args = [
        os.environ.get("PYTHON", "python3"),
        str(root / COLLECTOR),
        "--root",
        str(root),
        "--workload-envelope",
        str(workload_path),
    ]

    if accelerator_required:
        try:
            candidate = discover_candidate(workload, runner)
        except ValueError as exc:
            report = _report(
                result="BLOCKED",
                reason=str(exc),
                exit_code=2,
                workload=workload_path,
                lease=lease_path,
                accelerator_required=True,
            )
            _write_json_private(report_path, report)
            return 2, report
        if not (acquire_client.is_file() and os.access(acquire_client, os.X_OK)):
            report = _report(
                result="PENDING",
                reason="HRB_ACQUIRE_BRIDGE_NOT_INSTALLED",
                exit_code=2,
                workload=workload_path,
                lease=lease_path,
                candidate=candidate,
                accelerator_required=True,
            )
            _write_json_private(report_path, report)
            return 2, report
        try:
            lease_path.unlink()
        except FileNotFoundError:
            pass
        acquired = runner(
            [
                str(acquire_client),
                "--workload",
                str(workload_path),
                "--lease-output",
                str(lease_path),
                "--accelerator-uuid",
                str(candidate["uuid"]),
            ],
            45,
        )
        if acquired.returncode != 0 or not lease_path.is_file() or lease_path.stat().st_size <= 0:
            report = _report(
                result="BLOCKED",
                reason="HRB_ACQUIRE_FAILED",
                exit_code=2,
                workload=workload_path,
                lease=lease_path,
                candidate=candidate,
                accelerator_required=True,
            )
            _write_json_private(report_path, report)
            return 2, report
        collector_args.extend(["--hrb-lease", str(lease_path)])
    else:
        if not (admission_client.is_file() and os.access(admission_client, os.X_OK)):
            report = _report(
                result="PENDING",
                reason="HRB_ADMISSION_BRIDGE_NOT_INSTALLED",
                exit_code=2,
                workload=workload_path,
                authorization=authorization_path,
                accelerator_required=False,
            )
            _write_json_private(report_path, report)
            return 2, report
        try:
            authorization_path.unlink()
        except FileNotFoundError:
            pass
        authorized = runner(
            [
                str(admission_client),
                "authorize",
                "--workload",
                str(workload_path),
                "--output",
                str(authorization_path),
            ],
            45,
        )
        if authorized.returncode != 0 or not authorization_path.is_file() or authorization_path.stat().st_size <= 0:
            report = _report(
                result="BLOCKED",
                reason="HRB_ADMISSION_AUTHORIZATION_FAILED",
                exit_code=2,
                workload=workload_path,
                authorization=authorization_path,
                accelerator_required=False,
            )
            _write_json_private(report_path, report)
            return 2, report
        collector_args.extend(["--hrb-authorization", str(authorization_path)])

    receipt = root / RECEIPT
    try:
        receipt.unlink()
    except FileNotFoundError:
        pass

    collected = runner(collector_args, 90)
    if collected.returncode != 0:
        code = 2 if collected.returncode == 2 else 3
        report = _report(
            result="BLOCKED" if code == 2 else "ERROR",
            reason="CANONICAL_COLLECTOR_BLOCKED" if code == 2 else "CANONICAL_COLLECTOR_ERROR",
            exit_code=code,
            workload=workload_path,
            lease=lease_path if accelerator_required else None,
            authorization=authorization_path if not accelerator_required else None,
            candidate=candidate,
            accelerator_required=accelerator_required,
        )
        _write_json_private(report_path, report)
        return code, report

    gated = runner([str(root / ENFORCER), "resource-admission-current-host"], 90)
    if gated.returncode != 0:
        code = 2 if gated.returncode == 2 else 3
        report = _report(
            result="BLOCKED" if code == 2 else "ERROR",
            reason="CANONICAL_GATE_BLOCKED" if code == 2 else "CANONICAL_GATE_ERROR",
            exit_code=code,
            workload=workload_path,
            lease=lease_path if accelerator_required else None,
            authorization=authorization_path if not accelerator_required else None,
            candidate=candidate,
            accelerator_required=accelerator_required,
        )
        _write_json_private(report_path, report)
        return code, report

    if not receipt.is_file() or receipt.stat().st_size <= 0:
        report = _report(
            result="ERROR",
            reason="CANONICAL_RECEIPT_MISSING_AFTER_PASS",
            exit_code=3,
            workload=workload_path,
            accelerator_required=accelerator_required,
        )
        _write_json_private(report_path, report)
        return 3, report

    report = _report(
        result="PASS",
        reason="CURRENT_HOST_RESOURCE_ADMISSION_PASS",
        exit_code=0,
        workload=workload_path,
        lease=lease_path if accelerator_required else None,
        authorization=authorization_path if not accelerator_required else None,
        candidate=candidate,
        accelerator_required=accelerator_required,
    )
    _write_json_private(report_path, report)
    return 0, report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 host bootstrap / admission orchestrator")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")
    sub.add_parser("smoke")

    admit_parser = sub.add_parser("admit")
    admit_parser.add_argument("--workload", required=True)
    admit_parser.add_argument("--lease-output", default=str(DEFAULT_LEASE))
    admit_parser.add_argument("--authorization-output", default=str(DEFAULT_AUTHORIZATION))
    admit_parser.add_argument("--report", default=str(DEFAULT_REPORT))

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "doctor":
        code, report = doctor(root)
    elif args.command == "smoke":
        smoke = root / "bin/fa3-resource-admission-current-host.sh"
        try:
            proc = subprocess.run(
                [str(smoke), "smoke"],
                stdin=subprocess.DEVNULL,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 3
        return proc.returncode
    else:
        code, report = admit(
            root,
            Path(args.workload),
            lease_path=Path(args.lease_output),
            authorization_path=Path(args.authorization_output),
            report_path=Path(args.report),
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
