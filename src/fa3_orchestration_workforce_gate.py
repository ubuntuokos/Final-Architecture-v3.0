#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_orchestration_workforce import compile_cross_domain_plan, load_registry, route_task

PROFILE_REL = Path("canonical/profiles/FA3-ORCHESTRATION-WORKFORCE-001.json")
CONTRACT_REL = Path("canonical/contracts/FA3-ORCHESTRATION-WORKFORCE-CONTRACTS-001.json")
DECISION_REL = Path("canonical/decisions/FA3-DEC-ORCHESTRATION-WORKFORCE-2026-09-15.json")
REPORT_REL = Path("reports/orchestration-workforce-gate-report.json")

EXPECTED_PROVIDER_RECORDS = {
    "FA3-PROVIDER-CREWAI-001",
    "FA3-PROVIDER-CONDUCTOR-001",
    "FA3-PROVIDER-OPEN-MULTI-AGENT-001",
    "FA3-PROVIDER-LANGGRAPH-001",
    "FA3-PROVIDER-KESTRA-001",
    "FA3-PROVIDER-PIPECAT-001",
    "FA3-PROVIDER-N8N-001",
    "FA3-PROVIDER-HAYSTACK-001",
}

EXPECTED_ROUTES = [
    ({"task_id":"durable","domain":"durable-workflow","required_capabilities":["durable_lifecycle"]}, "FA3-SPECIALIST-DURABLE-LIFECYCLE-001"),
    ({"task_id":"creative","domain":"media-production","required_capabilities":["media_production_planning","creative_team_planning"]}, "FA3-MEDIA-PRODUCTION-DIRECTOR-001"),
    ({"task_id":"job","domain":"media-job","required_capabilities":["adaptive_job_graph","media_batch_job"]}, "FA3-SPECIALIST-ADAPTIVE-JOB-GRAPH-001"),
    ({"task_id":"governed","domain":"governed-agent-team","required_capabilities":["governed_agent_team","execution_journal"]}, "FA3-SPECIALIST-GOVERNED-AGENT-TEAM-001"),
    ({"task_id":"graph","domain":"stateful-agent-graph","required_capabilities":["stateful_agent_graph","conditional_edges"]}, "FA3-SPECIALIST-STATEFUL-AGENT-GRAPH-001"),
    ({"task_id":"ingest","domain":"event-ingest","required_capabilities":["event_ingest","file_arrival_trigger"]}, "FA3-SPECIALIST-EVENT-INGEST-001"),
    ({"task_id":"live","domain":"realtime-multimodal","required_capabilities":["realtime_multimodal","audio_video_streaming"]}, "FA3-SPECIALIST-REALTIME-MULTIMODAL-001"),
    ({"task_id":"integration","domain":"integration","required_capabilities":["integration_workflow","webhook"]}, "FA3-SPECIALIST-INTEGRATION-001"),
    ({"task_id":"knowledge","domain":"knowledge","required_capabilities":["rag_pipeline","retrieval"]}, "FA3-SPECIALIST-KNOWLEDGE-001"),
    ({"task_id":"gpu","domain":"resource-governance","required_capabilities":["gpu_placement"],"required_authorities":["host_resource"]}, "FA3-SPECIALIST-RESOURCE-GOVERNANCE-001"),
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def _check(condition: bool, findings: list[dict[str, Any]], code: str, message: str, **details: Any) -> None:
    if not condition:
        findings.append(_finding(code, message, **details))


def gate(root: Path | str) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    profile = _load(root / PROFILE_REL)
    contracts = _load(root / CONTRACT_REL)
    decision = _load(root / DECISION_REL)
    registry = load_registry(root)

    _check(profile.get("status") == "CANONICAL", findings, "FA3-ORCH-001", "Workforce profile is not canonical")
    _check(profile.get("priority") == "P0" and profile.get("requirement") == "MUST", findings, "FA3-ORCH-002", "Workforce profile is not P0/MUST")
    _check(profile.get("capability_count") == 143 and not profile.get("new_capability"), findings, "FA3-ORCH-003", "Capability-count invariant changed")
    _check(not profile.get("new_architectural_authority"), findings, "FA3-ORCH-004", "Workforce profile must not create a new architectural authority")
    _check(decision.get("status") == "CANONICAL_CLOSED" and decision.get("decision") == "ACCEPT", findings, "FA3-ORCH-005", "Canonical decision record is not closed/accepted")
    _check(contracts.get("id") == "FA3-ORCHESTRATION-WORKFORCE-CONTRACTS-001", findings, "FA3-ORCH-006", "Contract set mismatch")

    director = registry.get("director", {})
    _check(director.get("provider") is None, findings, "FA3-ORCH-007", "Top-level Director must be FA3-owned and provider-neutral")
    _check(director.get("architectural_authority") is False, findings, "FA3-ORCH-008", "Director must not become an architectural authority")

    durable = [s for s in registry["specialists"] if "durable_lifecycle" in set(s.get("authority_scope", []))]
    _check(len(durable) == 1 and durable[0].get("provider") == "Temporal", findings, "FA3-ORCH-009", "Temporal must remain the sole global durable-lifecycle authority", durable_specialists=[s.get("id") for s in durable])
    resource = [s for s in registry["specialists"] if "host_resource" in set(s.get("authority_scope", []))]
    _check(len(resource) == 1 and resource[0].get("provider") == "FA3_HRB_PLUS_ACCEL_GUARD", findings, "FA3-ORCH-010", "FA3 HRB + ACCEL-GUARD must remain the sole host-resource workforce authority", resource_specialists=[s.get("id") for s in resource])

    external_provider_ids = {s.get("provider_id") for s in registry["specialists"] if isinstance(s.get("provider_id"), str) and s["provider_id"].startswith("FA3-PROVIDER-")}
    _check(EXPECTED_PROVIDER_RECORDS.issubset(external_provider_ids), findings, "FA3-ORCH-011", "Selected specialist provider bindings are incomplete", missing=sorted(EXPECTED_PROVIDER_RECORDS - external_provider_ids))

    for provider_id in sorted(EXPECTED_PROVIDER_RECORDS):
        path = root / "canonical/providers" / f"{provider_id}.json"
        _check(path.exists(), findings, "FA3-ORCH-012", "Provider record missing", provider_id=provider_id)
        if not path.exists():
            continue
        provider = _load(path)
        _check(provider.get("architectural_authority") is False, findings, "FA3-ORCH-013", "External provider attempted architectural authority", provider_id=provider_id)
        _check(provider.get("new_capability") is False and provider.get("capability_count") == 143, findings, "FA3-ORCH-014", "Provider changed capability-count invariant", provider_id=provider_id)
        _check(bool(provider.get("anti_capabilities")), findings, "FA3-ORCH-015", "Provider must declare anti-capabilities", provider_id=provider_id)
        _check(bool(provider.get("prohibited_authority_roles")), findings, "FA3-ORCH-016", "Provider must declare prohibited authority roles", provider_id=provider_id)
        _check(provider.get("runtime_promotion_status") == "PENDING_CURRENT_HOST", findings, "FA3-ORCH-017", "This materialization must not claim current-host provider promotion", provider_id=provider_id)

    for task, expected in EXPECTED_ROUTES:
        actual = route_task(root, task)
        _check(actual.get("status") == "ROUTED" and actual.get("specialist_id") == expected, findings, "FA3-ORCH-018", "Deterministic specialist routing mismatch", task=task, expected=expected, actual=actual)

    gpu_task = {"task_id":"gpu-negative","domain":"resource-governance","required_capabilities":["gpu_placement"],"required_authorities":["host_resource"]}
    gpu_decision = route_task(root, gpu_task)
    rejected = {r["specialist_id"]: r["reasons"] for r in gpu_decision.get("rejected", [])}
    _check(any(reason.startswith("ANTI_CAPABILITY:gpu_placement") for reason in rejected.get("FA3-SPECIALIST-ROLE-TEAM-001", [])), findings, "FA3-ORCH-019", "CrewAI role-team specialist is not hard-blocked from GPU placement")
    _check(any(reason.startswith("ANTI_CAPABILITY:gpu_placement") for reason in rejected.get("FA3-MEDIA-PRODUCTION-DIRECTOR-001", [])), findings, "FA3-ORCH-020", "Media Production Director is not hard-blocked from GPU placement")

    runtime_creative = route_task(root, {"task_id":"creative-runtime","domain":"media-production","required_capabilities":["media_production_planning","creative_team_planning"]}, runtime_execution=True)
    _check(runtime_creative.get("status") == "HUMAN_ESCALATION", findings, "FA3-ORCH-021", "Pending current-host provider was runtime-selected", actual=runtime_creative)

    media_request = _load(root / "examples/orchestration-workforce-media.json")
    media_plan = compile_cross_domain_plan(root, media_request)
    expected_media = {"creative":"FA3-MEDIA-PRODUCTION-DIRECTOR-001","transcode":"FA3-SPECIALIST-ADAPTIVE-JOB-GRAPH-001","ingest":"FA3-SPECIALIST-EVENT-INGEST-001","live-avatar":"FA3-SPECIALIST-REALTIME-MULTIMODAL-001","gpu-admission":"FA3-SPECIALIST-RESOURCE-GOVERNANCE-001"}
    actual_media = {d["task_id"]: d.get("specialist_id") for d in media_plan["decisions"] if d["status"] == "ROUTED"}
    _check(media_plan.get("status") == "READY" and all(actual_media.get(k) == v for k, v in expected_media.items()), findings, "FA3-ORCH-022", "Cross-domain media workforce plan does not match the canonical specialist split", expected=expected_media, actual=actual_media)

    result = "PASS" if not findings else "FAIL"
    report = {
        "schema":"fa3.orchestration-workforce-gate-report.v1",
        "profile_id":profile.get("id"),
        "result":result,
        "blocking_findings":len(findings),
        "findings":findings,
        "details":{
            "capability_count":profile.get("capability_count"),
            "specialist_count":len(registry["specialists"]),
            "external_provider_record_count":len(EXPECTED_PROVIDER_RECORDS),
            "director_provider_neutral":director.get("provider") is None,
            "durable_lifecycle_authority":durable[0].get("provider") if len(durable) == 1 else None,
            "resource_authority":resource[0].get("provider") if len(resource) == 1 else None,
            "runtime_provider_promotion_claimed":False,
            "media_reference_plan_status":media_plan.get("status"),
        },
    }
    out = root / REPORT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _main() -> int:
    parser = argparse.ArgumentParser(description="FA3 orchestration workforce canonical gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(_main())
