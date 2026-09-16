from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fa3_orchestration_workforce import WorkforceContractError, compile_cross_domain_plan, route_task
from fa3_orchestration_workforce_gate import gate

ROOT = Path(__file__).resolve().parents[1]


class OrchestrationWorkforceTests(unittest.TestCase):
    def test_durable_routes_only_to_temporal(self):
        decision = route_task(ROOT, {"task_id":"durable","domain":"durable-workflow","required_capabilities":["durable_lifecycle"]})
        self.assertEqual(decision["status"], "ROUTED")
        self.assertEqual(decision["specialist_id"], "FA3-SPECIALIST-DURABLE-LIFECYCLE-001")
        self.assertEqual(decision["provider"], "Temporal")

    def test_media_director_routes_creative_work(self):
        decision = route_task(ROOT, {"task_id":"creative","domain":"media-production","required_capabilities":["media_production_planning","creative_team_planning"]})
        self.assertEqual(decision["status"], "ROUTED")
        self.assertEqual(decision["specialist_id"], "FA3-MEDIA-PRODUCTION-DIRECTOR-001")

    def test_crewai_cannot_acquire_gpu_authority(self):
        decision = route_task(ROOT, {"task_id":"gpu","domain":"resource-governance","required_capabilities":["gpu_placement"],"required_authorities":["host_resource"]})
        self.assertEqual(decision["specialist_id"], "FA3-SPECIALIST-RESOURCE-GOVERNANCE-001")
        rejected = {entry["specialist_id"]: entry["reasons"] for entry in decision["rejected"]}
        self.assertTrue(any(reason.startswith("ANTI_CAPABILITY:gpu_placement") for reason in rejected["FA3-SPECIALIST-ROLE-TEAM-001"]))
        self.assertTrue(any(reason.startswith("ANTI_CAPABILITY:gpu_placement") for reason in rejected["FA3-MEDIA-PRODUCTION-DIRECTOR-001"]))

    def test_pending_provider_is_fail_closed_for_runtime(self):
        decision = route_task(ROOT, {"task_id":"creative-runtime","domain":"media-production","required_capabilities":["media_production_planning","creative_team_planning"]}, runtime_execution=True)
        self.assertEqual(decision["status"], "HUMAN_ESCALATION")
        self.assertEqual(decision["reason"], "NO_ELIGIBLE_SPECIALIST_AFTER_HARD_FILTERS")

    def test_cross_domain_media_plan_is_provider_neutral_and_ready_for_design(self):
        request = json.loads((ROOT / "examples/orchestration-workforce-media.json").read_text(encoding="utf-8"))
        plan = compile_cross_domain_plan(ROOT, request)
        self.assertEqual(plan["status"], "READY")
        self.assertTrue(plan["provider_neutral"])
        by_task = {decision["task_id"]: decision["specialist_id"] for decision in plan["decisions"]}
        self.assertEqual(by_task["creative"], "FA3-MEDIA-PRODUCTION-DIRECTOR-001")
        self.assertEqual(by_task["transcode"], "FA3-SPECIALIST-ADAPTIVE-JOB-GRAPH-001")
        self.assertEqual(by_task["ingest"], "FA3-SPECIALIST-EVENT-INGEST-001")
        self.assertEqual(by_task["live-avatar"], "FA3-SPECIALIST-REALTIME-MULTIMODAL-001")
        self.assertEqual(by_task["gpu-admission"], "FA3-SPECIALIST-RESOURCE-GOVERNANCE-001")

    def test_invalid_request_is_rejected_before_routing(self):
        with self.assertRaises(WorkforceContractError):
            route_task(ROOT, {"task_id": "bad", "domain": "integration"})

    def test_canonical_gate_passes_without_claiming_runtime_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            for rel in (
                "canonical/FA3-ORCHESTRATION-WORKFORCE-REGISTRY-001.json",
                "canonical/contracts/FA3-ORCHESTRATION-WORKFORCE-CONTRACTS-001.json",
                "canonical/contracts/FA3-ORCHESTRATION-PROVIDER-SPI-001.json",
                "canonical/decisions/FA3-DEC-ORCHESTRATION-WORKFORCE-2026-09-15.json",
                "canonical/profiles/FA3-ORCHESTRATION-WORKFORCE-001.json",
                "examples/orchestration-workforce-media.json",
            ):
                src = ROOT / rel
                dst = temp_root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
            provider_dir = temp_root / "canonical/providers"
            provider_dir.mkdir(parents=True, exist_ok=True)
            wanted = {
                "FA3-PROVIDER-CREWAI-001.json","FA3-PROVIDER-CONDUCTOR-001.json","FA3-PROVIDER-OPEN-MULTI-AGENT-001.json","FA3-PROVIDER-LANGGRAPH-001.json","FA3-PROVIDER-KESTRA-001.json","FA3-PROVIDER-PIPECAT-001.json","FA3-PROVIDER-N8N-001.json","FA3-PROVIDER-HAYSTACK-001.json"
            }
            for src in (ROOT / "canonical/providers").glob("FA3-PROVIDER-*.json"):
                if src.name in wanted:
                    (provider_dir / src.name).write_bytes(src.read_bytes())
            report = gate(temp_root)
            self.assertEqual(report["result"], "PASS")
            self.assertFalse(report["details"]["runtime_provider_promotion_claimed"])


if __name__ == "__main__":
    unittest.main()
