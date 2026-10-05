import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_sysctl_governance import (
    SysctlGovernanceDenied,
    build_change_plan,
    classify_key,
    validate_persistence_path,
    validate_post_apply,
    validate_rollback,
    OBSERVE_ONLY,
    WORKLOAD_SENSITIVE,
    SAFETY_SECURITY_SENSITIVE,
    FORBIDDEN_AUTOMATIC_MUTATION,
)
from fa3_sysctl_governance_gate import evaluate


class SysctlGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.current = {
            "vm.swappiness": "60",
            "kernel.kptr_restrict": "1",
            "kernel.core_pattern": "core",
        }

    def test_gate_passes_without_current_host_overclaim(self):
        result = evaluate(ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["summary"], {"passed": 24, "total": 24})
        self.assertFalse(result["current_host_runtime_promotion_claim"])

    def test_classification(self):
        self.assertEqual(classify_key("vm.swappiness"), WORKLOAD_SENSITIVE)
        self.assertEqual(classify_key("kernel.kptr_restrict"), SAFETY_SECURITY_SENSITIVE)
        self.assertEqual(classify_key("kernel.core_pattern"), FORBIDDEN_AUTOMATIC_MUTATION)
        self.assertEqual(classify_key("net.ipv4.tcp_syncookies"), OBSERVE_ONLY)

    def test_observe_only_rejects_mutation(self):
        with self.assertRaises(SysctlGovernanceDenied):
            build_change_plan(self.current, {"vm.swappiness": "40"})

    def test_workload_sensitive_requires_full_admission(self):
        with self.assertRaises(SysctlGovernanceDenied):
            build_change_plan(
                self.current,
                {"vm.swappiness": "40"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                rollback_ready=True,
            )
        plan = build_change_plan(
            self.current,
            {"vm.swappiness": "40"},
            mode="EPHEMERAL_MUTATION",
            hrb_authorized=True,
            explicit_user_approval=True,
            benchmark_evidence=True,
            rollback_ready=True,
        )
        self.assertEqual(plan["changes"][0]["rollback_value"], "60")

    def test_security_sensitive_requires_security_authorization(self):
        with self.assertRaises(SysctlGovernanceDenied):
            build_change_plan(
                self.current,
                {"kernel.kptr_restrict": "2"},
                mode="EPHEMERAL_MUTATION",
                hrb_authorized=True,
                explicit_user_approval=True,
                rollback_ready=True,
            )

    def test_persistent_path_is_namespaced(self):
        self.assertTrue(validate_persistence_path("/etc/sysctl.d/90-fa3-memory-pressure.conf"))
        for path in (
            "/etc/sysctl.conf",
            "/etc/sysctl.d/99-sysctl.conf",
            "/etc/sysctl.d/90-fa3.conf",
            "/etc/sysctl.d/50-vendor.conf",
        ):
            self.assertFalse(validate_persistence_path(path))

    def test_post_apply_and_rollback_are_verified(self):
        plan = build_change_plan(
            self.current,
            {"vm.swappiness": "40"},
            mode="EPHEMERAL_MUTATION",
            hrb_authorized=True,
            explicit_user_approval=True,
            benchmark_evidence=True,
            rollback_ready=True,
        )
        self.assertEqual(validate_post_apply(plan, {"vm.swappiness": "40"})["status"], "PASS")
        self.assertEqual(validate_post_apply(plan, {"vm.swappiness": "60"})["status"], "FAIL")
        self.assertEqual(validate_rollback(plan, {"vm.swappiness": "60"})["status"], "PASS")
        self.assertEqual(validate_rollback(plan, {"vm.swappiness": "40"})["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
