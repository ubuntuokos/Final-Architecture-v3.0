from __future__ import annotations

import copy
import unittest
from pathlib import Path

from fa3_task_group import TaskGroupContractError, resolve_task_group, validate_registry

ROOT = Path(__file__).resolve().parents[1]


class TaskGroupTests(unittest.TestCase):
    def test_registry_has_exact_31_groups(self):
        state = validate_registry(ROOT)
        self.assertEqual(set(state["expanded"]), {f"F{i:02d}" for i in range(1, 32)})
        self.assertEqual(state["capability_count"], 175)

    def test_compatibility_alias_resolves_to_f15(self):
        snap = resolve_task_group(ROOT, "research-intelligence")
        self.assertEqual(snap["task_group_id"], "F15")
        self.assertEqual(len(snap["digest"]), 64)
        self.assertFalse(snap["architectural_authority"])

    def test_unknown_group_fails_closed(self):
        with self.assertRaises(TaskGroupContractError):
            resolve_task_group(ROOT, "F99")

    def test_temporal_exclusive_group(self):
        f07 = resolve_task_group(ROOT, "F07")["record"]
        self.assertEqual(f07["classification"], "TEMPORAL_EXCLUSIVE")
        self.assertFalse(f07["workflow_policy"]["conductor_allowed"])
        self.assertEqual(f07["profile_policy"]["permitted_profiles"], [])

    def test_horizontal_authority_groups_not_specialist_owned(self):
        for gid in ("F09", "F10", "F11", "F12", "F13", "F17"):
            record = resolve_task_group(ROOT, gid)["record"]
            self.assertEqual(record["classification"], "AUTHORITY_BOUND")
            self.assertEqual(record["profile_policy"]["permitted_profiles"], [])
            self.assertFalse(record["authority_policy"]["may_grant_authority"])

    def test_workload_mode_never_mutates_resources(self):
        for i in range(1, 32):
            record = resolve_task_group(ROOT, f"F{i:02d}")["record"]
            self.assertFalse(record["workload_mode_policy"]["may_mutate_physical_resources"])
            self.assertTrue(record["resource_policy"]["cpu_only_valid"])
            self.assertFalse(record["resource_policy"]["display_gpu_auto_recruitment"])

    def test_authority_grant_mutation_rejected(self):
        state = validate_registry(ROOT)
        reg = copy.deepcopy(state["registry"])
        reg["groups"][0]["authority_policy"] = {"may_grant_authority": True}
        with self.assertRaises(TaskGroupContractError):
            validate_registry(ROOT, reg)


if __name__ == "__main__":
    unittest.main()
