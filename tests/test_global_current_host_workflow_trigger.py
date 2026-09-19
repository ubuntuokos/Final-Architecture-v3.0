import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/fa3-global-current-host-closure.yml"

EXECUTION_SENSITIVE_PATHS = {
    "canonical/FA3-DESKTOP-PLASMA-001.json",
    "src/fa3_current_host_capability_qualification_constituent_orchestrator.py",
    "src/fa3_current_host_capability_test_orchestrator.py",
    "src/fa3_mat001_foundation_current_host.py",
    "src/fa3_mat002_runtime_knowledge_current_host.py",
    "src/fa3_mat003_interaction_creative_current_host.py",
    "src/fa3_desktop_admission.py",
    "src/fa3_plasma_secret_service_diagnostic.py",
    "src/fa3_mat004_media_authoring_verification_current_host.py",
    "src/fa3_full_current_host_capability_producer.py",
    "src/fa3_full_current_host_preflight.py",
    "src/fa3_current_host_runtime_resolver.py",
    "src/fa3_hrb_systemd_manager_current_host_gate.py",
    "evidence/collect-current-host.sh",
    "evidence/collect-hrb-systemd-manager-current-host.py",
    "bin/fa3-current-host-runner-doctor",
    "tests/test_current_host_capability_qualification_constituent_orchestrator.py",
    "tests/test_mat002_runtime_knowledge_current_host.py",
    "tests/test_mat003_interaction_creative_current_host.py",
    "tests/test_desktop_portability.py",
    "tests/test_plasma_secret_service_diagnostic.py",
    ".github/workflows/fa3-global-current-host-closure.yml",
}


def _event_paths(text: str, event: str, next_event: str) -> set[str]:
    start = text.index(f"  {event}:\n")
    end = text.index(f"  {next_event}:\n", start)
    block = text[start:end]
    return set(re.findall(r"^\s+- '([^']+)'$", block, flags=re.MULTILINE))


class GlobalCurrentHostWorkflowTriggerTests(unittest.TestCase):
    def test_main_push_covers_execution_sensitive_surface(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        push_paths = _event_paths(text, "push", "pull_request")
        missing = sorted(EXECUTION_SENSITIVE_PATHS - push_paths)
        self.assertEqual(missing, [], f"main push would not re-run physical current-host closure for: {missing}")

    def test_pr_and_main_push_both_cover_execution_sensitive_surface(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        push_paths = _event_paths(text, "push", "pull_request")
        pr_paths = _event_paths(text, "pull_request", "workflow_dispatch")
        self.assertEqual(sorted(EXECUTION_SENSITIVE_PATHS - push_paths), [])
        self.assertEqual(sorted(EXECUTION_SENSITIVE_PATHS - pr_paths), [])

    def test_every_main_push_path_is_also_pr_validated(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        push_paths = _event_paths(text, "push", "pull_request")
        pr_paths = _event_paths(text, "pull_request", "workflow_dispatch")
        self.assertEqual(
            sorted(push_paths - pr_paths),
            [],
            "a main-push-triggering current-host change must also be validated on pull_request",
        )


if __name__ == "__main__":
    unittest.main()
