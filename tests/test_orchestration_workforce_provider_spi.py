from __future__ import annotations

import json
import unittest
from pathlib import Path

from fa3_orchestration_provider_spi import (
    ProviderAdapterError,
    ProviderRuntimeNotPromoted,
    compile_plan_envelopes,
    compile_provider_envelope,
)
from fa3_orchestration_workforce import compile_cross_domain_plan, route_task

ROOT = Path(__file__).resolve().parents[1]


class OrchestrationProviderSPITests(unittest.TestCase):
    def test_media_director_design_compiles_to_crewai_adapter_kind(self):
        task = {
            "task_id": "creative",
            "domain": "media-production",
            "required_capabilities": ["media_production_planning", "creative_team_planning"],
        }
        route = route_task(ROOT, task)
        envelope = compile_provider_envelope(ROOT, task, route)
        self.assertEqual(envelope["adapter_kind"], "crewai.team-intent/v1")
        self.assertFalse(envelope["canonical"])
        self.assertEqual(envelope["delegated_authority_scope"], [])
        self.assertFalse(envelope["constraints"]["may_expand_authority"])

    def test_conductor_design_compiles_as_bounded_job_intent(self):
        task = {
            "task_id": "transcode",
            "domain": "media-job",
            "required_capabilities": ["adaptive_job_graph", "media_batch_job"],
        }
        route = route_task(ROOT, task)
        envelope = compile_provider_envelope(ROOT, task, route)
        self.assertEqual(envelope["provider_id"], "FA3-PROVIDER-CONDUCTOR-001")
        self.assertEqual(envelope["adapter_kind"], "conductor.job-graph-intent/v1")

    def test_pipecat_design_compiles_as_realtime_pipeline_intent(self):
        task = {
            "task_id": "live",
            "domain": "realtime-multimodal",
            "required_capabilities": ["realtime_multimodal", "audio_video_streaming"],
        }
        route = route_task(ROOT, task)
        envelope = compile_provider_envelope(ROOT, task, route)
        self.assertEqual(envelope["adapter_kind"], "pipecat.realtime-pipeline-intent/v1")

    def test_pending_crewai_runtime_adapter_fails_closed(self):
        task = {
            "task_id": "creative-runtime",
            "domain": "media-production",
            "required_capabilities": ["media_production_planning", "creative_team_planning"],
        }
        design_route = route_task(ROOT, task)
        with self.assertRaises(ProviderRuntimeNotPromoted):
            compile_provider_envelope(ROOT, task, design_route, runtime_execution=True)

    def test_temporal_existing_authority_can_compile_runtime_intent(self):
        task = {
            "task_id": "durable",
            "domain": "durable-workflow",
            "required_capabilities": ["durable_lifecycle"],
            "required_authorities": ["durable_lifecycle"],
        }
        route = route_task(ROOT, task, runtime_execution=True)
        envelope = compile_provider_envelope(ROOT, task, route, runtime_execution=True)
        self.assertEqual(envelope["provider"], "Temporal")
        self.assertEqual(envelope["mode"], "runtime")
        self.assertEqual(envelope["delegated_authority_scope"], ["durable_lifecycle"])

    def test_hrb_runtime_envelope_preserves_resource_authority_only(self):
        task = {
            "task_id": "gpu",
            "domain": "resource-governance",
            "required_capabilities": ["gpu_placement"],
            "required_authorities": ["host_resource"],
        }
        route = route_task(ROOT, task, runtime_execution=True)
        envelope = compile_provider_envelope(ROOT, task, route, runtime_execution=True)
        self.assertEqual(envelope["adapter_kind"], "fa3.hrb-admission-intent/v1")
        self.assertEqual(envelope["delegated_authority_scope"], ["accelerator_conflict", "host_resource"])
        self.assertNotIn("security_policy", envelope["delegated_authority_scope"])

    def test_cross_domain_design_plan_compiles_all_specialist_envelopes(self):
        request = json.loads((ROOT / "examples/orchestration-workforce-media.json").read_text(encoding="utf-8"))
        plan = compile_cross_domain_plan(ROOT, request)
        adapter_plan = compile_plan_envelopes(ROOT, request, plan)
        kinds = {entry["task_id"]: entry["adapter_kind"] for entry in adapter_plan["envelopes"]}
        self.assertEqual(kinds["creative"], "crewai.team-intent/v1")
        self.assertEqual(kinds["transcode"], "conductor.job-graph-intent/v1")
        self.assertEqual(kinds["ingest"], "kestra.event-flow-intent/v1")
        self.assertEqual(kinds["live-avatar"], "pipecat.realtime-pipeline-intent/v1")
        self.assertEqual(kinds["gpu-admission"], "fa3.hrb-admission-intent/v1")

    def test_non_routed_decision_cannot_reach_provider_adapter(self):
        task = {
            "task_id": "blocked",
            "domain": "media-production",
            "required_capabilities": ["gpu_placement"],
        }
        route = route_task(ROOT, task)
        self.assertEqual(route["status"], "HUMAN_ESCALATION")
        with self.assertRaises(ProviderAdapterError):
            compile_provider_envelope(ROOT, task, route)


if __name__ == "__main__":
    unittest.main()
