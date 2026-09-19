import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/fa3-global-current-host-closure.yml"

REAL_EXECUTION_CRITICAL_PATHS = {
    "canonical/current-host-capability-test-executors.json",
    "canonical/current-host-capability-test-qualifications.json",
    "canonical/current-host-capability-qualification-constituent-producers.json",
    "canonical/current-host-capability-proof-recipes.json",
    "canonical/decisions/FA3-DEC-CURRENT-HOST-FULL-MATERIALIZATION-2026-09-19.json",
    "src/fa3_current_host_evidence_audit.py",
    "src/fa3_current_host_capability_handoff.py",
    "src/fa3_current_host_capability_attest.py",
    "src/fa3_current_host_capability_test_bundle.py",
    "src/fa3_current_host_capability_test_qualification_audit.py",
    "src/fa3_current_host_capability_test_qualifier.py",
    "src/fa3_current_host_capability_qualification_constituent_producer_audit.py",
    "src/fa3_current_host_capability_qualification_constituent_orchestrator.py",
    "src/fa3_current_host_capability_test_executor_audit.py",
    "src/fa3_current_host_capability_test_orchestrator.py",
    "src/fa3_current_host_batch_planner.py",
    "src/fa3_cap075_contract_registry_current_host.py",
    "src/fa3_cap076_acceptance_resilience_current_host.py",
    "src/fa3_cap054_external_asset_inventory_current_host.py",
    "src/fa3_cap074_service_catalog_current_host.py",
    "src/fa3_cap080_verified_skill_supply_chain_current_host.py",
    "src/fa3_cap028_agent_execution_current_host.py",
    "src/fa3_mat001_foundation_current_host.py",
    "src/fa3_mat002_runtime_knowledge_current_host.py",
    "src/fa3_mat003_interaction_creative_current_host.py",
    "src/fa3_mat004_media_authoring_verification_current_host.py",
    "src/fa3_full_current_host_capability_producer.py",
    "src/fa3_full_current_host_preflight.py",
    "src/fa3_current_host_runtime_resolver.py",
    "src/fa3_pytorch3d_build_readiness.py",
    "evidence/collect-hrb-systemd-manager-current-host.py",
    "bin/fa3-bootstrap-wasmtime",
    ".github/workflows/fa3-global-current-host-closure.yml",
}


def event_paths(text: str, event: str) -> set[str]:
    lines = text.splitlines()
    event_line = f"  {event}:"
    try:
        start = lines.index(event_line)
    except ValueError as exc:
        raise AssertionError(f"missing workflow event: {event}") from exc
    paths_start = None
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            break
        if line == "    paths:":
            paths_start = index + 1
            break
    if paths_start is None:
        raise AssertionError(f"missing paths filter for event: {event}")
    paths: set[str] = set()
    for line in lines[paths_start:]:
        if not line.startswith("      - "):
            break
        value = line.split("- ", 1)[1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        paths.add(value)
    return paths


class GlobalCurrentHostWorkflowTriggerTests(unittest.TestCase):
    def test_main_push_covers_every_real_execution_critical_path(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        push = event_paths(text, "push")
        missing = sorted(REAL_EXECUTION_CRITICAL_PATHS - push)
        self.assertEqual(missing, [], f"main push would skip physical current-host verification for: {missing}")

    def test_pull_request_covers_every_real_execution_critical_path(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        pull_request = event_paths(text, "pull_request")
        missing = sorted(REAL_EXECUTION_CRITICAL_PATHS - pull_request)
        self.assertEqual(missing, [], f"PR would skip current-host regression coverage for: {missing}")

    def test_workflow_self_change_always_retriggers(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        workflow = ".github/workflows/fa3-global-current-host-closure.yml"
        self.assertIn(workflow, event_paths(text, "push"))
        self.assertIn(workflow, event_paths(text, "pull_request"))


if __name__ == "__main__":
    unittest.main()
