#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_release_baseline import module_active_capability_count
from fa3_hrb_lease_lifecycle import (
    EVIDENCE_AUTHORITY_ID,
    HMAC_SCOPE,
    HRB_AUTHORITY_ID,
    TRUST_PROFILE_ID,
    HashChainEvidenceSink,
    LeaseKey,
    LeaseKeyring,
    LeaseLedger,
    RuntimeAdapterRegistry,
    SystemdCgroupV2ScopeAdapter,
    capture_systemd_scope_binding,
)

CAPABILITY_COUNT = module_active_capability_count(__file__)
EVIDENCE_LEVEL = "CURRENT_HOST_HRB_LEASE_LIFECYCLE_DEDICATED_TTL_EVICTION_PASS"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _systemctl_user(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["systemctl", "--user", *args])


def _wait_scope(unit_scope: str, timeout: float = 8.0) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        p = _systemctl_user("show", unit_scope, "--property=ActiveState", "--value")
        last = p.stdout.strip()
        if p.returncode == 0 and last == "active":
            cg = _systemctl_user("show", unit_scope, "--property=ControlGroup", "--value")
            if cg.returncode == 0 and cg.stdout.strip():
                return True, cg.stdout.strip()
        time.sleep(0.1)
    return False, last


def _host_attestation_digest() -> str:
    boot = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    machine = Path("/etc/machine-id").read_text(encoding="utf-8").strip()
    return hashlib.sha256(f"{machine}|{boot}".encode("utf-8")).hexdigest()


class TestProjectionHook:
    """Dedicated test projection only; never touches the live Secret Broker store."""

    def __init__(self, path: Path):
        self.path = path
        self.zeroized = False
        self.revoked = False

    def revoke_and_zeroize(self, lease: dict[str, Any]) -> bool:
        if not self.path.is_file():
            return False
        size = self.path.stat().st_size
        with self.path.open("r+b", buffering=0) as fh:
            fh.seek(0)
            fh.write(b"\x00" * size)
            fh.flush()
            os.fsync(fh.fileno())
        self.zeroized = True
        self.path.unlink()
        self.revoked = not self.path.exists()
        return self.zeroized and self.revoked


def _safe_stop(unit_scope: str) -> None:
    _systemctl_user("kill", "--kill-whom=all", "--signal=KILL", unit_scope)
    _systemctl_user("stop", unit_scope)
    _systemctl_user("reset-failed", unit_scope)


def collect(ttl_seconds: float = 2.0) -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("current-host HRB lease lifecycle test requires Linux")
    if not hasattr(os, "pidfd_open"):
        raise RuntimeError("pidfd_open unavailable")
    if not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        raise RuntimeError("unified cgroup v2 unavailable")

    user_probe = _systemctl_user("is-system-running")
    if user_probe.returncode not in {0, 1}:
        raise RuntimeError("systemd user manager unavailable: " + user_probe.stderr[-1000:])

    nonce = secrets.token_hex(6)
    unit_base = f"fa3-hrb-ttl-test-{nonce}"
    unit_scope = unit_base + ".scope"
    lease_id = f"lease-{unit_base}"
    if not unit_base.startswith("fa3-hrb-ttl-test-"):
        raise RuntimeError("unsafe TTL test unit prefix")
    if unit_base.startswith(("fa3-ai", "fa3-secret", "fa3-current", "fa3-model", "fa3-runtime")):
        raise RuntimeError("TTL test unit overlaps protected FA3 namespace")

    started = utc_now()
    process = None
    tempdir = None
    binding = None
    secret_hook = None
    evidence = HashChainEvidenceSink()
    final_record: dict[str, Any] = {}
    cgroup_path = ""
    cleanup_ok = False

    try:
        process = subprocess.Popen(
            [
                "systemd-run",
                "--user",
                "--scope",
                "--unit",
                unit_base,
                "--quiet",
                "/bin/sleep",
                "120",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        ready, cgroup_path = _wait_scope(unit_scope)
        if not ready:
            stderr = process.stderr.read()[-2000:] if process.stderr else ""
            raise RuntimeError(f"dedicated transient scope did not become active: {stderr}")

        binding = capture_systemd_scope_binding(
            lease_id=lease_id,
            generation=1,
            workload_identity=unit_base,
            unit_scope=unit_scope,
            host_attestation_digest=_host_attestation_digest(),
            accelerator_assignments=[],
            user_manager=True,
        )

        # The collector deliberately uses a one-run test-only key. It never reads the
        # production HRB root key and cannot prove or mint a production lease.
        keyring = LeaseKeyring(
            [LeaseKey(f"current-host-test-{nonce}", secrets.token_bytes(32), HMAC_SCOPE)],
            f"current-host-test-{nonce}",
        )
        ledger = LeaseLedger(keyring)

        tempdir = tempfile.TemporaryDirectory(prefix=unit_base + "-")
        secret_path = Path(tempdir.name) / "projection.bin"
        secret_path.write_bytes(secrets.token_bytes(64))
        secret_path.chmod(0o600)
        secret_hook = TestProjectionHook(secret_path)

        issued = ledger.issue(binding, ttl_seconds, lease_id=lease_id, generation=1)
        active = ledger.activate(lease_id, 1)
        deadline_ns = int(active["expires_monotonic_ns"])
        while time.monotonic_ns() < deadline_ns:
            time.sleep(0.02)

        adapter = SystemdCgroupV2ScopeAdapter(user_manager=True)
        final_record = ledger.evict(
            lease_id,
            1,
            secret_hook=secret_hook,
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=evidence,
        )

        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            raise RuntimeError("dedicated TTL workload still alive after eviction")

        show = _systemctl_user("show", unit_scope, "--property=ActiveState", "--value")
        active_state = show.stdout.strip() if show.returncode == 0 else "not-found"
        cleanup_ok = final_record.get("state") == "EVICTED" and active_state not in {"active", "activating", "reloading"}
    finally:
        if unit_scope:
            _safe_stop(unit_scope)
        if process is not None and process.poll() is None:
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        if tempdir is not None:
            tempdir.cleanup()

    history = [x.get("state") for x in final_record.get("state_history", [])]
    receipt = {
        "schema": "fa3.hrb-lease-lifecycle-current-host-receipt.v1",
        "status": "PASS" if (
            final_record.get("state") == "EVICTED"
            and cleanup_ok
            and secret_hook is not None
            and secret_hook.zeroized
            and secret_hook.revoked
            and evidence.verify_chain()
        ) else "FAIL",
        "evidence_level": EVIDENCE_LEVEL,
        "started_at_utc": started,
        "completed_at_utc": utc_now(),
        "resource_authority_id": HRB_AUTHORITY_ID,
        "secret_authority_id": "FA3-AUTH-SECRETS-001",
        "durable_evidence_authority_id": EVIDENCE_AUTHORITY_ID,
        "trust_profile_id": TRUST_PROFILE_ID,
        "capability_count_after": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
        "workload": {
            "name": unit_base,
            "unit_scope": unit_scope,
            "dedicated": True,
            "existing_fa3_workload_targeted": False,
            "ttl_seconds": ttl_seconds,
            "cpu_only": True,
            "accelerator_assignments": [],
        },
        "crypto": {
            "algorithm": "HMAC-SHA256",
            "scope": HMAC_SCOPE,
            "key_id": final_record.get("authentication", {}).get("key_id"),
            "test_only_ephemeral_key": True,
            "production_hmac_master_key_read": False,
            "provider_agent_master_key_access": False,
            "hmac_used_for_durable_evidence_signature": False,
        },
        "runtime_binding": final_record.get("runtime_binding"),
        "runtime": {
            "systemd_user_transient_scope": True,
            "cgroup_v2": True,
            "cgroup_path": cgroup_path,
            "pidfd": True,
            "group_kill_method": final_record.get("group_kill_method"),
            "final_state": final_record.get("state"),
            "state_history": history,
            "lease_record_deleted": False,
            "cleanup_verified": cleanup_ok,
            "gpu_global_reset_used": False,
            "cuda_device_reset_used": False,
        },
        "secret_projection": {
            "test_projection_only": True,
            "live_secret_broker_store_touched": False,
            "zeroized": bool(secret_hook and secret_hook.zeroized),
            "revoked": bool(secret_hook and secret_hook.revoked),
        },
        "evidence_handoff": {
            "typed_hash_chain_valid": evidence.verify_chain(),
            "event_count": len(evidence.events),
            "final_event_sha256": evidence.events[-1]["event_sha256"] if evidence.events else None,
            "external_asymmetric_signature_required": True,
            "durable_signing_authority": EVIDENCE_AUTHORITY_ID,
            "trust_profile": TRUST_PROFILE_ID,
        },
        "safety": {
            "target_derivation_from_client_identity": False,
            "target_derivation_from_generated_container_name": False,
            "test_prefix_enforced": True,
            "preexisting_workload_kill_allowed": False,
            "container_id_used": False,
        },
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect dedicated current-host HRB TTL eviction evidence")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--receipt", default="evidence/receipts/hrb-lease-lifecycle-current-host.json")
    parser.add_argument("--ttl-seconds", type=float, default=2.0)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    path = Path(args.receipt)
    if not path.is_absolute():
        path = root / path
    try:
        receipt = collect(ttl_seconds=args.ttl_seconds)
    except Exception as exc:
        receipt = {
            "schema": "fa3.hrb-lease-lifecycle-current-host-receipt.v1",
            "status": "FAIL",
            "evidence_level": EVIDENCE_LEVEL,
            "error": repr(exc),
            "completed_at_utc": utc_now(),
            "capability_count_after": CAPABILITY_COUNT,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "global_promotion_claim": False,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
