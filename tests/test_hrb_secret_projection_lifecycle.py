import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hrb_lease_lifecycle import (
    HMAC_SCOPE,
    LeaseKey,
    LeaseKeyring,
    LeaseLedger,
    SecretBrokerProjectionLifecycleHook,
    StaleGenerationError,
)
from fa3_secret_broker import ProjectionLeaseStore


def seed():
    return {
        "workload_identity": "projection-test",
        "runtime_instance_identity": "pid:1:start:1:cgroup:1",
        "host_attestation_digest": "a" * 64,
        "cgroup_v2_identity": {
            "path": "/test.scope",
            "st_dev": 1,
            "st_ino": 1,
            "owner_uid": os.getuid(),
            "owner_gid": os.getgid(),
        },
        "pidfd_subject_reference": {"pid": 1, "start_time_ticks": 1},
        "systemd_unit_scope": "projection-test.scope",
        "runtime_backend": "SYSTEMD_CGROUPV2_SCOPE",
        "backend_instance_id": "projection-test.scope",
        "accelerator_assignments": [],
        "execution_path": {"cgroup_version": 2},
    }


class SecretProjectionLifecycleTests(unittest.TestCase):
    def test_projection_store_is_hrb_generation_bound(self):
        with tempfile.TemporaryDirectory() as td:
            store = ProjectionLeaseStore(Path(td) / "projection-leases.json")
            digest = "d" * 64
            item = store.issue(
                grant_id="grant-1",
                projection="FILE_OR_FD_BASED",
                consumer_identity_ref={"uid": os.getuid(), "gid": os.getgid(), "pid": os.getpid(), "consumer_id": "TEST"},
                expires_monotonic_ns=10**30,
                boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                secret_ref_sha256="a" * 64,
                hrb_lease_id="hrb-1",
                hrb_generation=7,
                hrb_runtime_binding_sha256=digest,
                execution_binding={"cgroup_v2_path": "/x", "pidfd_subject_ref": {"pid": os.getpid(), "start_time_ticks": 1}},
            )
            with self.assertRaises(PermissionError):
                store.revoke(item["lease_id"], "hrb-1", 8, digest)
            with self.assertRaises(PermissionError):
                store.revoke(item["lease_id"], "hrb-1", 7, "e" * 64)
            revoked = store.revoke(item["lease_id"], "hrb-1", 7, digest)
            self.assertEqual(revoked["state"], "REVOKED")
            zeroized = store.zeroized(item["lease_id"], "hrb-1", 7, digest)
            self.assertEqual(zeroized["state"], "ZEROIZED")
            self.assertIsNone(zeroized["artifact"])

    def test_hrb_hook_uses_only_opaque_projection_handle(self):
        calls = []
        def request(payload):
            calls.append(dict(payload))
            self.assertNotIn("secret_id", payload)
            self.assertRegex(str(payload.get("runtime_binding_sha256","")), r"^[0-9a-f]{64}$")
            if payload["op"] == "projection_revoke":
                return {"ok": True, "state": "REVOKED", "zeroize_target": None}
            if payload["op"] == "projection_zeroized":
                return {"ok": True, "state": "ZEROIZED"}
            return {"ok": False}
        hook = SecretBrokerProjectionLifecycleHook(request_fn=request)
        lease = {
            "lease_id": "hrb-1",
            "generation": 3,
            "secret_projection_leases": [{"projection_lease_id": "spl-" + "a" * 32}],
        }
        self.assertTrue(hook.revoke_and_zeroize(lease))
        self.assertEqual([x["op"] for x in calls], ["projection_revoke", "projection_zeroized"])

    def test_hrb_hook_rejects_secret_object_reference(self):
        hook = SecretBrokerProjectionLifecycleHook(request_fn=lambda _: {"ok": True})
        lease = {
            "lease_id": "hrb-1",
            "generation": 1,
            "secret_projection_leases": [{"projection_lease_id": "spl-" + "b" * 32, "secret_id": "do-not-delete"}],
        }
        self.assertFalse(hook.revoke_and_zeroize(lease))

    def test_projection_handle_does_not_carry_into_renewed_generation(self):
        keyring = LeaseKeyring([LeaseKey("k1", b"K" * 32, HMAC_SCOPE)], "k1")
        ledger = LeaseLedger(keyring)
        issued = ledger.issue(seed(), 60)
        lease_id = issued["lease_id"]
        ledger.activate(lease_id, 1)
        attached = ledger.attach_secret_projection_lease(lease_id, 1, "spl-" + "c" * 32)
        self.assertEqual(len(attached["secret_projection_leases"]), 1)
        renewed = ledger.renew(lease_id, 1, 60)
        self.assertEqual(renewed["generation"], 2)
        self.assertEqual(renewed["secret_projection_leases"], [])
        with self.assertRaises(StaleGenerationError):
            ledger.attach_secret_projection_lease(lease_id, 1, "spl-" + "d" * 32)


if __name__ == "__main__":
    unittest.main()
