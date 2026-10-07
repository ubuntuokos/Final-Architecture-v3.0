import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hrb_lease_lifecycle import (
    HMAC_SCOPE,
    HashChainEvidenceSink,
    LeaseBindingError,
    LeaseExpiredError,
    LeaseIntegrityError,
    LeaseKey,
    LeaseKeyring,
    LeaseLedger,
    LeaseStateError,
    RuntimeAdapterRegistry,
    StaleGenerationError,
    SystemdCgroupV2ScopeAdapter,
    _cgroup_unpopulated,
    _safe_cgroup_path,
    validate_runtime_binding,
)


class FakeClock:
    def __init__(self):
        self.mono = 1_000_000_000
        self.boot_id = "boot-a"
        self.wall = "2026-09-24T00:00:00Z"

    def monotonic_ns(self):
        return self.mono

    def read_boot_id(self):
        return self.boot_id

    def wall_utc(self):
        return self.wall


class FakeSecretHook:
    def __init__(self, ok=True):
        self.ok = ok
        self.calls = 0

    def revoke_and_zeroize(self, lease):
        self.calls += 1
        return self.ok


class FakeAdapter:
    backend = "SYSTEMD_CGROUPV2_SCOPE"

    def __init__(
        self,
        *,
        restart_ok=True,
        binding_ok=True,
        binding_reason="BOUND",
        terminate_ok=True,
        dead_ok=True,
        cleanup_ok=True,
        release_ok=True,
        raise_group_kill=False,
    ):
        self.restart_ok = restart_ok
        self.binding_ok = binding_ok
        self.binding_reason = binding_reason
        self.terminate_ok = terminate_ok
        self.dead_ok = dead_ok
        self.cleanup_ok = cleanup_ok
        self.release_ok = release_ok
        self.raise_group_kill = raise_group_kill
        self.block_calls = 0
        self.verify_calls = 0
        self.terminate_calls = 0
        self.kill_calls = 0
        self.cleanup_calls = 0
        self.release_calls = 0

    def block_restart(self, binding):
        self.block_calls += 1
        return self.restart_ok

    def verify_binding(self, binding):
        self.verify_calls += 1
        return self.binding_ok, self.binding_reason

    def terminate(self, binding):
        self.terminate_calls += 1
        return self.terminate_ok

    def group_kill(self, binding):
        self.kill_calls += 1
        if self.raise_group_kill:
            raise RuntimeError("adapter failure")
        return "FAKE_GROUP_KILL"

    def verify_dead(self, binding, timeout=8.0):
        return self.dead_ok

    def cleanup(self, binding):
        self.cleanup_calls += 1
        return self.cleanup_ok

    def release_resources(self, binding):
        self.release_calls += 1
        return self.release_ok


def binding_seed(*, backend="SYSTEMD_CGROUPV2_SCOPE", accelerators=None):
    return {
        "workload_identity": "fa3-hrb-test",
        "runtime_instance_identity": "pid:123:start:456:cgroup:789",
        "host_attestation_digest": "a" * 64,
        "cgroup_v2_identity": {
            "path": "/user.slice/test.scope",
            "st_dev": 1,
            "st_ino": 789,
            "owner_uid": os.getuid(),
            "owner_gid": os.getgid(),
        },
        "pidfd_subject_reference": {"pid": 123, "start_time_ticks": 456},
        "systemd_unit_scope": "fa3-hrb-test.scope",
        "runtime_backend": backend,
        "backend_instance_id": "fa3-hrb-test.scope" if backend != "PODMAN" else "b" * 64,
        "accelerator_assignments": [] if accelerators is None else accelerators,
        "execution_path": {"cgroup_version": 2, "pidfd_required": True},
    }


def make_env():
    clock = FakeClock()
    keyring = LeaseKeyring([LeaseKey("k1", b"A" * 32, HMAC_SCOPE)], "k1")
    ledger = LeaseLedger(
        keyring,
        boot_id_reader=clock.read_boot_id,
        monotonic_ns=clock.monotonic_ns,
        wall_utc=clock.wall_utc,
    )
    return clock, keyring, ledger


def active_lease(ledger, ttl=10.0, seed=None):
    issued = ledger.issue(seed or binding_seed(), ttl)
    return ledger.activate(issued["lease_id"], issued["generation"])


class HrbLeaseLifecycleTests(unittest.TestCase):
    def test_forged_hmac_mac(self):
        _, keyring, ledger = make_env()
        lease = active_lease(ledger)
        lease["runtime_binding"]["workload_identity"] = "forged"
        with self.assertRaises(LeaseIntegrityError):
            keyring.verify(lease)

    def test_malformed_lease(self):
        with self.assertRaises(LeaseBindingError):
            validate_runtime_binding({"runtime_backend": "SYSTEMD_CGROUPV2_SCOPE"})

    def test_stale_generation(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        renewed = ledger.renew(lease["lease_id"], 1, 10.0)
        self.assertEqual(renewed["generation"], 2)
        self.assertEqual(renewed["state"], "ACTIVE")
        with self.assertRaises(StaleGenerationError):
            ledger.begin_revoke(lease["lease_id"], 1)

    def test_expiry_renewal_race(self):
        clock, _, ledger = make_env()
        lease = active_lease(ledger, ttl=1.0)
        clock.mono += 2_000_000_000
        with self.assertRaises(LeaseExpiredError):
            ledger.renew(lease["lease_id"], 1, 10.0)

    def test_wrong_runtime_kill(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        adapter = FakeAdapter(binding_ok=False, binding_reason="WRONG_RUNTIME")
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(),
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "QUARANTINED")
        self.assertEqual(adapter.terminate_calls, 0)
        self.assertEqual(adapter.kill_calls, 0)

    def test_pid_reuse(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        adapter = FakeAdapter(binding_ok=False, binding_reason="PID_REUSE")
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(),
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "QUARANTINED")
        self.assertEqual(adapter.kill_calls, 0)
        self.assertIn("PID_REUSE", out["failure_reason"])

    def test_cgroup_substitution(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        adapter = FakeAdapter(binding_ok=False, binding_reason="CGROUP_SUBSTITUTION_OR_OWNERSHIP_CHANGE")
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(),
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "QUARANTINED")
        self.assertEqual(adapter.kill_calls, 0)

    def test_symlink_path_ownership_attack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real"
            real.mkdir()
            (root / "link").symlink_to(real, target_is_directory=True)
            with self.assertRaises(LeaseBindingError):
                _safe_cgroup_path("/link", root=root)

    def test_cgroup_events_populated_zero_is_authoritative(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            (path / "cgroup.events").write_text("populated 0\nfrozen 0\n", encoding="utf-8")
            (path / "cgroup.procs").write_text("123\n", encoding="utf-8")
            self.assertTrue(_cgroup_unpopulated(path))
            (path / "cgroup.events").write_text("populated 1\nfrozen 0\n", encoding="utf-8")
            (path / "cgroup.procs").write_text("", encoding="utf-8")
            self.assertFalse(_cgroup_unpopulated(path))

    def test_verify_dead_accepts_gone_original_pid_and_removed_cgroup(self):
        adapter = SystemdCgroupV2ScopeAdapter()
        read_fd, write_fd = os.pipe()
        ident = "pid:123:start:456:cgroup:789"
        adapter._pidfds[ident] = read_fd
        binding = binding_seed()
        binding["runtime_instance_identity"] = ident
        try:
            with patch("fa3_hrb_lease_lifecycle._proc_start_ticks", side_effect=FileNotFoundError()), \
                 patch("fa3_hrb_lease_lifecycle._safe_cgroup_path", side_effect=LeaseBindingError("gone")):
                self.assertTrue(adapter.verify_dead(binding, timeout=0.2))
        finally:
            os.close(write_fd)

    def test_verify_dead_remains_fail_closed_for_live_pid_or_populated_cgroup(self):
        adapter = SystemdCgroupV2ScopeAdapter()
        read_fd, write_fd = os.pipe()
        ident = "pid:123:start:456:cgroup:789"
        adapter._pidfds[ident] = read_fd
        binding = binding_seed()
        binding["runtime_instance_identity"] = ident
        with tempfile.TemporaryDirectory() as td:
            cg = Path(td)
            (cg / "cgroup.events").write_text("populated 1\n", encoding="utf-8")
            (cg / "cgroup.procs").write_text("123\n", encoding="utf-8")
            try:
                with patch("fa3_hrb_lease_lifecycle._proc_start_ticks", return_value=456), \
                     patch("fa3_hrb_lease_lifecycle._proc_state", return_value="S"), \
                     patch("fa3_hrb_lease_lifecycle._safe_cgroup_path", return_value=cg):
                    self.assertFalse(adapter.verify_dead(binding, timeout=0.1))
            finally:
                os.close(write_fd)

    def test_systemd_restart_race(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        adapter = FakeAdapter(restart_ok=False)
        secret = FakeSecretHook()
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=secret,
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "QUARANTINED")
        self.assertEqual(secret.calls, 0)
        self.assertEqual(adapter.kill_calls, 0)

    def test_runtime_adapter_failure(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        adapter = FakeAdapter(raise_group_kill=True, dead_ok=False)
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(),
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "QUARANTINED")
        retained = ledger.get(lease["lease_id"], 1)
        self.assertEqual(retained["state"], "QUARANTINED")
        self.assertIn("RUNTIME_TERMINATION_FAILURE", retained["failure_reason"])

    def test_secret_revoke_failure(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        adapter = FakeAdapter()
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(ok=False),
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "QUARANTINED")
        self.assertEqual(adapter.kill_calls, 1)
        self.assertIn("SECRET_REVOKE_OR_ZEROIZE_FAILED", out["failure_reason"])

    def test_clock_jump_reboot(self):
        clock, _, ledger = make_env()
        lease = active_lease(ledger, ttl=30.0)
        clock.wall = "2099-01-01T00:00:00Z"
        self.assertEqual(ledger.assert_current_valid(lease["lease_id"], 1)["state"], "ACTIVE")
        clock.boot_id = "boot-b"
        with self.assertRaises(LeaseExpiredError):
            ledger.assert_current_valid(lease["lease_id"], 1)

    def test_cpu_only_workload(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger, seed=binding_seed(accelerators=[]))
        adapter = FakeAdapter()
        evidence = HashChainEvidenceSink()
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(),
            adapters=RuntimeAdapterRegistry([adapter]),
            evidence=evidence,
        )
        self.assertEqual(out["state"], "EVICTED")
        self.assertEqual(out["runtime_binding"]["accelerator_assignments"], [])
        self.assertTrue(evidence.verify_chain())

    def test_shared_accelerator(self):
        shared = [{"stable_id": "GPU-TEST", "mode": "SHARED", "share_group_id": "share-a"}]
        _, _, ledger = make_env()
        lease = active_lease(ledger, seed=binding_seed(accelerators=shared))
        out = ledger.evict(
            lease["lease_id"], 1,
            secret_hook=FakeSecretHook(),
            adapters=RuntimeAdapterRegistry([FakeAdapter()]),
            evidence=HashChainEvidenceSink(),
        )
        self.assertEqual(out["state"], "EVICTED")
        self.assertEqual(out["runtime_binding"]["accelerator_assignments"][0]["mode"], "SHARED")

    def test_unknown_backend_device(self):
        bad = binding_seed(backend="UNKNOWN")
        with self.assertRaises(LeaseBindingError):
            validate_runtime_binding({
                **bad,
                "lease_id": "L",
                "generation": 1,
                "issued_at_utc": "x",
                "expires_at_utc": "y",
                "ttl_seconds": 1,
            })
        bad_device = binding_seed(accelerators=[{"mode": "EXCLUSIVE"}])
        with self.assertRaises(LeaseBindingError):
            validate_runtime_binding({
                **bad_device,
                "lease_id": "L",
                "generation": 1,
                "issued_at_utc": "x",
                "expires_at_utc": "y",
                "ttl_seconds": 1,
            })

    def test_evidence_tampering(self):
        evidence = HashChainEvidenceSink()
        evidence.append({"event_type": "TEST", "lease_id": "L", "generation": 1})
        self.assertTrue(evidence.verify_chain())
        evidence.events[0]["generation"] = 2
        self.assertFalse(evidence.verify_chain())

    def test_key_rotation(self):
        _, keyring, ledger = make_env()
        lease = active_lease(ledger)
        keyring.verify(lease)
        keyring.rotate(LeaseKey("k2", b"B" * 32, HMAC_SCOPE))
        keyring.verify(lease)
        new_lease = active_lease(ledger)
        self.assertEqual(new_lease["authentication"]["key_id"], "k2")
        keyring.retire("k1")
        with self.assertRaises(LeaseIntegrityError):
            keyring.verify(lease)

    def test_evicting_generation_never_reactivates(self):
        _, _, ledger = make_env()
        lease = active_lease(ledger)
        record = ledger.begin_revoke(lease["lease_id"], 1)
        ledger._transition(record, "EVICTING")
        with self.assertRaises(LeaseStateError):
            ledger._transition(record, "ACTIVE")


if __name__ == "__main__":
    unittest.main()
