from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_shared_web_acquisition_state import (
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStateError,
    AcquisitionStateStore,
    Backend,
    OriginPolicy,
    RequestStatus,
    SessionStatus,
)


class SharedWebAcquisitionStateTests(unittest.TestCase):
    def req(self, request_id="r1", backend=Backend.HTTP, max_attempts=3):
        return AcquisitionRequest(
            request_id=request_id,
            url="https://example.com/a",
            dedupe_key="GET:https://example.com/a",
            backend=backend,
            policy_revision="policy-1",
            provenance_ref="source-1",
            max_attempts=max_attempts,
        )

    def policy(self, **kw):
        return OriginPolicy(
            origin="https://example.com",
            robots_allowed=kw.get("robots_allowed", True),
            min_interval_ms=kw.get("min_interval_ms", 0),
            max_parallel_advisory=kw.get("max_parallel_advisory", 2),
        )

    def test_dedupe_and_identity_conflict(self):
        store = AcquisitionStateStore()
        first = store.enqueue(self.req())
        self.assertIs(first, store.enqueue(self.req()))
        changed = self.req(request_id="r2")
        with self.assertRaisesRegex(
            AcquisitionStateError, "DEDUPE_KEY_IDENTITY_CONFLICT"
        ):
            store.enqueue(changed)

    def test_competing_workers_and_expired_recovery(self):
        store = AcquisitionStateStore()
        store.enqueue(self.req())
        store.claim(
            "r1", "w1", now_ms=100, lease_ms=50, origin_policy=self.policy()
        )
        with self.assertRaisesRegex(AcquisitionStateError, "REQUEST_NOT_CLAIMABLE"):
            store.claim(
                "r1", "w2", now_ms=120, lease_ms=50, origin_policy=self.policy()
            )
        receipts = store.recover_expired(now_ms=150)
        self.assertEqual([r.request_id for r in receipts], ["r1"])
        rec = store.claim(
            "r1", "w2", now_ms=151, lease_ms=20, origin_policy=self.policy()
        )
        self.assertEqual(rec.lease_owner, "w2")
        self.assertEqual(rec.lease_generation, 2)

    def test_lease_extension_and_completion_binding(self):
        store = AcquisitionStateStore()
        store.enqueue(self.req(backend=Backend.BROWSER))
        store.claim("r1", "w1", now_ms=0, lease_ms=10, origin_policy=self.policy())
        store.extend_lease("r1", "w1", now_ms=5, extension_ms=10)
        bad = AcquisitionResult(
            "r1", Backend.HTTP, 200, "d", "source-1", "policy-1"
        )
        with self.assertRaisesRegex(
            AcquisitionStateError, "BACKEND_PARITY_BINDING_MISMATCH"
        ):
            store.complete("r1", "w1", bad, now_ms=11)
        good = AcquisitionResult(
            "r1", Backend.BROWSER, 200, "d", "source-1", "policy-1"
        )
        self.assertEqual(
            store.complete("r1", "w1", good, now_ms=11).status,
            RequestStatus.HANDLED,
        )

    def test_retry_limit_and_wait(self):
        store = AcquisitionStateStore()
        store.enqueue(self.req(max_attempts=2))
        store.claim("r1", "w1", now_ms=0, lease_ms=10, origin_policy=self.policy())
        rec = store.fail(
            "r1",
            "w1",
            now_ms=1,
            failure_code="HTTP_500",
            retryable=True,
            retry_after_ms=50,
        )
        self.assertEqual(rec.status, RequestStatus.RETRY_WAIT)
        with self.assertRaisesRegex(
            AcquisitionStateError, "REQUEST_RETRY_NOT_YET_ELIGIBLE"
        ):
            store.claim(
                "r1", "w2", now_ms=40, lease_ms=10, origin_policy=self.policy()
            )
        store.claim("r1", "w2", now_ms=51, lease_ms=10, origin_policy=self.policy())
        rec = store.fail(
            "r1", "w2", now_ms=52, failure_code="HTTP_500", retryable=True
        )
        self.assertEqual(rec.status, RequestStatus.FAILED)

    def test_robots_and_politeness_fail_closed(self):
        store = AcquisitionStateStore()
        store.enqueue(self.req())
        with self.assertRaisesRegex(AcquisitionStateError, "ROBOTS_POLICY_DENIED"):
            store.claim(
                "r1",
                "w",
                now_ms=0,
                lease_ms=10,
                origin_policy=self.policy(robots_allowed=False),
            )
        self.assertEqual(store.get("r1").status, RequestStatus.BLOCKED)

        store = AcquisitionStateStore()
        store.enqueue(self.req("r1"))
        store.enqueue(
            AcquisitionRequest(
                "r2",
                "https://example.com/b",
                "GET:https://example.com/b",
                Backend.HTTP,
                "policy-1",
                "source-2",
            )
        )
        store.claim(
            "r1",
            "w1",
            now_ms=100,
            lease_ms=10,
            origin_policy=self.policy(min_interval_ms=50),
        )
        with self.assertRaisesRegex(
            AcquisitionStateError, "ORIGIN_POLITENESS_DELAY"
        ):
            store.claim(
                "r2",
                "w2",
                now_ms=120,
                lease_ms=10,
                origin_policy=self.policy(min_interval_ms=50),
            )

    def test_snapshot_restart_and_recovery(self):
        store = AcquisitionStateStore()
        store.enqueue(self.req())
        store.claim("r1", "w1", now_ms=10, lease_ms=10, origin_policy=self.policy())
        restored = AcquisitionStateStore.from_snapshot(store.snapshot())
        receipts = restored.recover_expired(now_ms=20)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(restored.get("r1").status, RequestStatus.PENDING)
        self.assertEqual(
            restored.snapshot(),
            AcquisitionStateStore.from_snapshot(restored.snapshot()).snapshot(),
        )

    def test_session_retirement_and_replacement(self):
        store = AcquisitionStateStore()
        store.session_create("s1")
        with self.assertRaisesRegex(
            AcquisitionStateError, "SESSION_REPLACEMENT_SOURCE_NOT_RETIRED"
        ):
            store.session_create("s2", replacement_of="s1")
        store.session_retire("s1", blocked=True)
        s2 = store.session_create("s2", replacement_of="s1")
        self.assertEqual(s2.generation, 2)
        self.assertEqual(store._sessions["s1"].status, SessionStatus.BLOCKED)

    def test_hrb_observation_is_advisory_only(self):
        store = AcquisitionStateStore()
        store.enqueue(self.req())
        obs = store.hrb_load_observation()
        self.assertTrue(obs["advisory_only"])
        self.assertFalse(obs["may_change_concurrency"])
        self.assertEqual(
            obs["resource_authority"], "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        )


if __name__ == "__main__":
    unittest.main()
