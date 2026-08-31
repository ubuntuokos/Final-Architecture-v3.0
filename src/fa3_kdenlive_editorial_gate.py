#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-KDENLIVE-EDITORIAL-001"
PROVIDER_ID = "FA3-PROVIDER-KDENLIVE-001"
CONTRACT_ID = "FA3-KDENLIVE-EDITORIAL-CONTRACTS-001"
DECISION_ID = "FA3-DEC-KDENLIVE-EDITORIAL-CONSOLIDATION-2026-08-30"
GATE_ID = "FA3-KDENLIVE-EDITORIAL-GATESET-001"
CAPABILITY_COUNT = 143

RULES = [
    "KDENLIVE_PRIMARY_LINUX_EDITORIAL_FRONTEND",
    "KDENLIVE_NOT_HARD_BACKEND_DEPENDENCY",
    "OTIO_CANONICAL_TIMELINE_IR",
    "KDENLIVE_NATIVE_OTIO_IMPORT_EXPORT_PROJECTION",
    "API_FIRST_EDITORIAL_AUTOMATION",
    "GUI_AUTOMATION_FALLBACK_ONLY",
    "GUI_FALLBACK_AUDITED_REPRODUCIBLE",
    "CRITICAL_EDITORIAL_MUTATION_REQUIRES_HITL",
    "DIRECT_KDENLIVE_PROJECT_XML_MUTATION_FORBIDDEN",
    "DETERMINISTIC_FFMPEG_FFPROBE_MEDIA_CORE",
    "PROVIDER_NEUTRAL_TIMELINE_AND_ARTIFACT_CONTRACTS",
    "ROUNDTRIP_PROVENANCE_AND_HASH_LINEAGE_REQUIRED",
    "KDENLIVE_MLT_DBUS_CONTROL_MUST_BE_TYPED_VERSIONED_CAPABILITY_DISCOVERED",
    "HUMAN_EDITORIAL_STATE_REMAINS_KDENLIVE_OWNED",
    "KUBUNTU_KDE_WAYLAND_FIRST_CLASS",
    "NO_NEW_CAPABILITY_OR_AUTHORITY",
]

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-KDENLIVE-EDITORIAL-001.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-KDENLIVE-001.json",
        "contracts": root / "canonical/contracts/FA3-KDENLIVE-EDITORIAL-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-KDENLIVE-EDITORIAL-CONSOLIDATION-2026-08-30.json",
        "enforcement": root / "canonical/kdenlive-editorial-enforcement.json",
        "blackhole": root / "canonical/profiles/FA3-BLACKHOLE-KDENLIVE-001.json",
    }
    for i, (name, path) in enumerate(paths.items(), 1):
        if not path.is_file():
            findings.append(finding(f"KDENLIVE-REF-{i:03d}", f"Missing Kdenlive canonical artifact: {path.relative_to(root)}", artifact=name))
    if findings:
        report = {"schema": "fa3.kdenlive-editorial-gate-report.v1", "gate_id": GATE_ID, "result": "FAIL", "findings": findings}
        _write(root / "reports/kdenlive-editorial-gate-report.json", report)
        return report

    profile = _load(paths["profile"])
    provider = _load(paths["provider"])
    contracts = _load(paths["contracts"])
    decision = _load(paths["decision"])
    enforcement = _load(paths["enforcement"])
    blackhole = _load(paths["blackhole"])

    if profile.get("id") != PROFILE_ID or profile.get("status") != "CANONICAL":
        findings.append(finding("KDENLIVE-REF-020", "Kdenlive editorial profile identity/status drift"))
    if any(profile.get(k) is not False for k in ("canonical_root", "new_capability", "new_architectural_authority")):
        findings.append(finding("KDENLIVE-REF-021", "Kdenlive projection became forbidden root/capability/authority"))
    if profile.get("capabilities") != ["CAP-121", "CAP-126"]:
        findings.append(finding("KDENLIVE-REF-022", "Kdenlive capability projection drift"))
    if profile.get("canonical_timeline_ir") != "OpenTimelineIO":
        findings.append(finding("KDENLIVE-REF-023", "OTIO is no longer the canonical timeline IR"))
    if profile.get("hard_backend_dependency") is not False:
        findings.append(finding("KDENLIVE-REF-024", "Kdenlive became a hard backend dependency"))
    if profile.get("kdenlive_role") != "PRIMARY_LINUX_KUBUNTU_HUMAN_NLE_AND_FINAL_ASSEMBLY_FRONTEND":
        findings.append(finding("KDENLIVE-REF-025", "Kdenlive primary editorial role drift"))
    automation = profile.get("automation_policy", {})
    if automation.get("mode") != "API_FIRST" or automation.get("gui_automation") != "FALLBACK_ONLY":
        findings.append(finding("KDENLIVE-REF-026", "API-first / GUI-fallback automation policy drift"))
    reqs = set(automation.get("gui_fallback_requirements", []))
    required_gui = {
        "explicit capability-unavailable evidence",
        "auditable action trace",
        "reproducible target/action specification",
        "pre/post project identity evidence",
        "HITL approval for critical mutations",
    }
    if not required_gui.issubset(reqs):
        findings.append(finding("KDENLIVE-REF-027", "GUI fallback audit/reproducibility/HITL requirements incomplete"))
    if profile.get("project_mutation_policy") != "NO_EXTERNAL_DIRECT_KDENLIVE_XML_MUTATION":
        findings.append(finding("KDENLIVE-REF-028", "External direct .kdenlive XML mutation was enabled"))
    media_core = profile.get("media_core", {})
    if media_core.get("probe") != "ffprobe" or media_core.get("transform") != "ffmpeg":
        findings.append(finding("KDENLIVE-REF-029", "Deterministic FFmpeg/ffprobe media core drift"))

    if provider.get("id") != PROVIDER_ID or provider.get("profile") != PROFILE_ID:
        findings.append(finding("KDENLIVE-REF-030", "Kdenlive provider identity/profile mismatch"))
    if provider.get("architectural_authority") is not False or provider.get("new_capability") is not False:
        findings.append(finding("KDENLIVE-REF-031", "Kdenlive provider acquired forbidden authority/capability"))
    if provider.get("hard_backend_dependency") is not False:
        findings.append(finding("KDENLIVE-REF-032", "Kdenlive provider became hard backend dependency"))
    if any(provider.get(k) is not False for k in ("automation_authority", "timeline_semantic_authority", "orchestration_authority", "host_resource_authority")):
        findings.append(finding("KDENLIVE-REF-033", "Kdenlive provider crossed an authority boundary"))

    human_boundary = provider.get("human_finishing_boundary", {})
    if not (
        human_boundary.get("mode") == "HUMAN_FINISHING_NLE"
        and human_boundary.get("picture_lock_requires_human_approval") is True
        and human_boundary.get("destructive_mutation_requires_hitl") is True
        and human_boundary.get("direct_project_xml_mutation_forbidden") is True
    ):
        findings.append(finding(
            "KDENLIVE-REF-045",
            "Kdenlive explicit human-finishing boundary drift",
        ))
    required_forbidden = {
        "AI_MODEL_AUTHORITY",
        "PROVIDER_ROUTING_AUTHORITY",
        "STT_AUTHORITY",
        "WORKFLOW_AUTHORITY",
        "ARTIFACT_REGISTRY_AUTHORITY",
        "EVIDENCE_AUTHORITY",
        "HOST_RESOURCE_AUTHORITY",
        "SCENE_CAMERA_GEOMETRY_AUTHORITY",
        "MCP_GATEWAY_AUTHORITY",
    }
    if (
        provider.get("ai_tools_policy")
        != "CLIENT_PROJECTION_ONLY_DELEGATE_THROUGH_EXISTING_FA3_CAPABILITIES"
        or not required_forbidden.issubset(
            set(provider.get("forbidden_authorities", []))
        )
    ):
        findings.append(finding(
            "KDENLIVE-REF-046",
            "Kdenlive AI-tools/forbidden-authority boundary drift",
        ))

    if contracts.get("id") != CONTRACT_ID or contracts.get("profile") != PROFILE_ID or contracts.get("provider_neutral") is not True:
        findings.append(finding("KDENLIVE-REF-034", "Kdenlive contract identity/provider-neutrality drift"))
    timeline = contracts.get("timeline_semantics", {})
    if timeline.get("canonical_ir") != "OpenTimelineIO" or timeline.get("kdenlive_project_format_is_canonical_ir") is not False:
        findings.append(finding("KDENLIVE-REF-035", "Kdenlive project format incorrectly became canonical timeline IR"))
    gui = contracts.get("gui_fallback", {})
    if not (gui.get("allowed") and gui.get("fallback_only") and gui.get("requires_audit_trace") and gui.get("requires_reproducible_action_specification") and gui.get("critical_mutation_requires_hitl")):
        findings.append(finding("KDENLIVE-REF-036", "GUI fallback contract lost fail-closed audit/HITL semantics"))
    priority = contracts.get("control_surface_priority", [])
    if priority[:1] != ["OTIO_NATIVE_IMPORT_EXPORT"] or priority[-1:] != ["AUDITED_REPRODUCIBLE_GUI_FALLBACK"]:
        findings.append(finding("KDENLIVE-REF-037", "Kdenlive control-surface priority drift"))
    if contracts.get("media_core_policy") != "DETERMINISTIC_FFMPEG_FFPROBE":
        findings.append(finding("KDENLIVE-REF-038", "Deterministic media-core contract drift"))

    if decision.get("id") != DECISION_ID or decision.get("status") != "CANONICAL_CLOSED" or decision.get("decision") != "IMPLEMENT":
        findings.append(finding("KDENLIVE-REF-039", "Kdenlive consolidation decision is not closed IMPLEMENT"))
    if decision.get("mandatory_rules") != RULES or decision.get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(finding("KDENLIVE-REF-040", "Kdenlive decision rule/count invariant drift"))
    if decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0:
        findings.append(finding("KDENLIVE-REF-041", "Kdenlive decision changed capability/authority count"))

    if enforcement.get("gate_id") != GATE_ID or enforcement.get("rules") != RULES or enforcement.get("rule_count") != len(RULES):
        findings.append(finding("KDENLIVE-REF-042", "Kdenlive enforcement rule set drift"))
    if enforcement.get("capability_count") != CAPABILITY_COUNT or enforcement.get("fail_closed") is not True:
        findings.append(finding("KDENLIVE-REF-043", "Kdenlive enforcement count/fail-closed invariant drift"))

    if PROFILE_ID not in blackhole.get("dependencies", []):
        findings.append(finding("KDENLIVE-REF-044", "Blackhole/Kdenlive integration is not bound to the global Kdenlive editorial projection"))

    report = {
        "schema": "fa3.kdenlive-editorial-gate-report.v1",
        "gate_id": GATE_ID,
        "profile_id": PROFILE_ID,
        "provider_id": PROVIDER_ID,
        "capability_count": CAPABILITY_COUNT,
        "result": "PASS" if not findings else "FAIL",
        "rules_checked": len(RULES),
        "findings": findings,
        "runtime_required_for_global_promotion": False,
        "promotion_effect": "MANDATORY_CANONICAL_EDITORIAL_CONTRACTS_RUNTIME_CONDITIONAL",
    }
    _write(root / "reports/kdenlive-editorial-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Kdenlive editorial canonical gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
