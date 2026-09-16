#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Iterable

NO_CONTENTION = "NO_CONTENTION"
PRE_EXISTING_EXTERNAL_OCCUPANCY = "PRE_EXISTING_EXTERNAL_OCCUPANCY"
RUNTIME_EXTERNAL_CONTENTION = "RUNTIME_EXTERNAL_CONTENTION"
OBSERVABILITY_INSUFFICIENT = "OBSERVABILITY_INSUFFICIENT"


@dataclass(frozen=True)
class AcceleratorProcess:
    provider: str
    accelerator_id: str
    pid: int
    process_name: str = "unknown"
    used_memory_mib: int | None = None


@dataclass(frozen=True)
class Snapshot:
    observable: bool
    processes: tuple[AcceleratorProcess, ...]
    probes: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "observable": self.observable,
            "processes": [asdict(item) for item in self.processes],
            "probes": list(self.probes),
        }


def _external(snapshot: Snapshot, fa3_owned_pids: set[int]) -> set[tuple[str, str, int]]:
    return {
        (item.provider, item.accelerator_id, item.pid)
        for item in snapshot.processes
        if item.pid not in fa3_owned_pids
    }


def classify(
    baseline: Snapshot,
    current: Snapshot,
    fa3_owned_pids: Iterable[int] = (),
) -> str:
    owned = {int(pid) for pid in fa3_owned_pids}
    if not baseline.observable or not current.observable:
        return OBSERVABILITY_INSUFFICIENT
    before = _external(baseline, owned)
    now = _external(current, owned)
    if now - before:
        return RUNTIME_EXTERNAL_CONTENTION
    if before:
        return PRE_EXISTING_EXTERNAL_OCCUPANCY
    return NO_CONTENTION


def decide(state: str, explicit_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    if state == NO_CONTENTION:
        return {
            "mode": "RECOMMEND",
            "action": "CONTINUE_AND_OBSERVE",
            "user_decision_required": False,
            "automatic_resolution": False,
            "destructive_action_authorized": False,
        }
    if state == OBSERVABILITY_INSUFFICIENT:
        return {
            "mode": "RECOMMEND",
            "action": "RECOMMEND_OBSERVABILITY_REMEDIATION",
            "user_decision_required": True,
            "automatic_resolution": False,
            "destructive_action_authorized": False,
        }

    policy = explicit_policy or {}
    automatic = (
        policy.get("explicit_user_policy") is True
        and policy.get("created_before_conflict") is True
        and policy.get("automatic_resolution") is True
        and isinstance(policy.get("policy_id"), str)
        and bool(policy.get("policy_id", "").strip())
        and isinstance(policy.get("bounded_action"), str)
        and bool(policy.get("bounded_action", "").strip())
    )
    if automatic:
        return {
            "mode": "EXPLICIT_POLICY",
            "action": "APPLY_EXPLICIT_POLICY",
            "policy_id": policy["policy_id"],
            "bounded_action": policy["bounded_action"],
            "user_decision_required": False,
            "automatic_resolution": True,
            "destructive_action_authorized": False,
        }
    return {
        "mode": "RECOMMEND",
        "action": "NOTIFY_AND_REQUIRE_USER_DECISION",
        "user_decision_required": True,
        "automatic_resolution": False,
        "destructive_action_authorized": False,
    }


def _run(command: list[str]) -> tuple[bool, str, str]:
    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "", str(exc)
    return proc.returncode == 0, proc.stdout or "", proc.stderr or ""


def _probe_nvidia() -> tuple[bool, list[AcceleratorProcess], dict[str, Any]]:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return False, [], {"provider": "NVIDIA", "available": False, "result": "TOOL_NOT_FOUND"}
    ok, out, err = _run([
        binary,
        "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory",
        "--format=csv,noheader,nounits",
    ])
    if not ok:
        return False, [], {"provider": "NVIDIA", "available": True, "result": "PROBE_FAILED", "stderr": err[-1000:]}
    items: list[AcceleratorProcess] = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) < 3:
            continue
        try:
            pid = int(row[1].strip())
        except ValueError:
            continue
        memory = None
        if len(row) > 3:
            try:
                memory = int(row[3].strip())
            except ValueError:
                pass
        items.append(AcceleratorProcess("NVIDIA", row[0].strip() or "UNKNOWN", pid, row[2].strip() or "unknown", memory))
    return True, items, {"provider": "NVIDIA", "available": True, "result": "OBSERVED", "process_count": len(items)}


def _extract_generic_pids(provider: str, text: str) -> list[AcceleratorProcess]:
    pids: set[int] = set()
    try:
        payload = json.loads(text)
        serialized = json.dumps(payload)
    except Exception:
        serialized = text
    for match in re.finditer(r'(?i)(?:"?pid"?\s*[:=]\s*|\bpid\s+)(\d+)', serialized):
        try:
            pids.add(int(match.group(1)))
        except ValueError:
            pass
    return [AcceleratorProcess(provider, "UNRESOLVED_DEVICE", pid) for pid in sorted(pids)]


def _probe_generic(provider: str, binary_name: str, args: list[str]) -> tuple[bool, list[AcceleratorProcess], dict[str, Any]]:
    binary = shutil.which(binary_name)
    if not binary:
        return False, [], {"provider": provider, "available": False, "result": "TOOL_NOT_FOUND"}
    ok, out, err = _run([binary, *args])
    if not ok:
        return False, [], {"provider": provider, "available": True, "result": "PROBE_FAILED", "stderr": err[-1000:]}
    items = _extract_generic_pids(provider, out)
    return True, items, {"provider": provider, "available": True, "result": "OBSERVED", "process_count": len(items)}


def observe_host() -> Snapshot:
    probes = [
        _probe_nvidia(),
        _probe_generic("AMD", "rocm-smi", ["--showpids", "--json"]),
        _probe_generic("INTEL", "xpu-smi", ["ps", "-j"]),
    ]
    successful = [item for item in probes if item[0]]
    processes: list[AcceleratorProcess] = []
    for ok, items, _meta in successful:
        if ok:
            processes.extend(items)
    provider_tools_present = any(meta.get("available") for _ok, _items, meta in probes)
    observable = bool(successful) or not provider_tools_present
    if not provider_tools_present:
        # No typed accelerator telemetry exists on this host. This is not sufficient
        # for runtime promotion of an accelerator-required FA3 host.
        observable = False
    return Snapshot(observable, tuple(processes), tuple(meta for _ok, _items, meta in probes))


def owned_pids_from_environment() -> set[int]:
    raw = os.environ.get("FA3_OWNED_PIDS", "")
    result: set[int] = {os.getpid()}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            result.add(int(token))
        except ValueError:
            continue
    return result
