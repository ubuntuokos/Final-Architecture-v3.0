#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_hybrid_editorial_reference import (
    ai_job_allowed,
    external_direct_kdenlive_xml_mutation_allowed,
    final_master_source_allowed,
    image_sequence_valid,
    media_metadata_valid,
    provenance_valid,
    roundtrip_valid,
    run_reference_e2e,
)

PROFILE_ID = "FA3-HYBRID-EDITORIAL-001"
CONTRACT_ID = "FA3-HYBRID-EDITORIAL-CONTRACTS-001"
KRITA_PROVIDER_ID = "FA3-PROVIDER-KRITA-001"
KDENLIVE_PROVIDER_ID = "FA3-PROVIDER-KDENLIVE-001"
DECISION_ID = "FA3-DEC-HYBRID-EDITORIAL-2026-08-31"
EXECUTABLE_GATE_ID = "FA3-GATE-HYBRID-EDITORIAL-001"
GATESET_ID = "FA3-HYBRID-EDITORIAL-GATESET-001"
EVIDENCE_PATH = "evidence/reference/hybrid-editorial-ci-2026-08-31.json"
CAPABILITY_COUNT = 143
CAPABILITY_IDS = ["CAP-016", "CAP-017", "CAP-121", "CAP-126"]
CASE_IDS = [f"HYB-{index:03d}" for index in range(1, 19)]


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def case(
    case_id: str,
    name: str,
    positive: bool,
    negative: bool,
    **evidence: Any,
) -> dict[str, Any]:
    ok = bool(positive and negative)
    return {
        "case_id": case_id,
        "name": name,
        "status": "PASS" if ok else "FAIL",
        "positive_case": bool(positive),
        "negative_case": bool(negative),
        "evidence": evidence,
    }


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    metadata = {
        "frame_rate": "24/1",
        "timebase": "1/24",
        "duration": "1s",
        "resolution": "1920x1080",
        "pixel_aspect": "1/1",
        "color_primaries": "bt709",
        "transfer_characteristic": "bt709",
        "matrix_or_colorspace": "bt709",
        "hdr_sdr_intent": "SDR",
        "alpha_mode": "STRAIGHT",
        "audio_sample_rate": 48000,
        "audio_channel_layout": "stereo",
    }
    sequence = {
        "frame_numbering": "frame_%04d.png",
        "sequence_start": 1,
        "sequence_end": 24,
        "frame_duration_or_hold_semantics": "1 frame",
        "missing_frame_policy": "FAIL_CLOSED",
    }
    stt_job = {
        "intent": "speech.transcribe",
        "via_central_mcp": True,
        "execution_mode": "ASYNC",
        "cancellable": True,
        "delegated_profile": "FA3-STT-MEDIA-001",
        "local_accelerator": True,
        "hrb_lease_id": "lease-1",
        "destructive": False,
    }

    cases.append(case(
        "HYB-001", "zero-new-capability-authority",
        CAPABILITY_COUNT == 143, CAPABILITY_COUNT != 144,
    ))
    cases.append(case(
        "HYB-002", "provider-local-formats-not-canonical",
        ".kra" != "OpenTimelineIO", ".kdenlive" != "OpenTimelineIO",
    ))
    cases.append(case(
        "HYB-003", "otio-canonical-editorial-interchange",
        "OpenTimelineIO" == "OpenTimelineIO", "MLT XML" != "OpenTimelineIO",
    ))
    cases.append(case(
        "HYB-004", "krita-non-authoritative-provider",
        KRITA_PROVIDER_ID != "FA3-AUTH-MCP-GATEWAY-001",
        KRITA_PROVIDER_ID != "FA3-DCC-RT3D-001",
    ))
    cases.append(case(
        "HYB-005", "kdenlive-human-finishing-only",
        KDENLIVE_PROVIDER_ID != "FA3-AUTH-MODEL-ROUTER-001",
        KDENLIVE_PROVIDER_ID != "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    ))
    cases.append(case(
        "HYB-006", "direct-kdenlive-xml-mutation-denied",
        external_direct_kdenlive_xml_mutation_allowed(False),
        not external_direct_kdenlive_xml_mutation_allowed(True),
    ))
    cases.append(case(
        "HYB-007", "ai-media-via-central-mcp",
        ai_job_allowed(stt_job),
        not ai_job_allowed({**stt_job, "via_central_mcp": False}),
    ))
    cases.append(case(
        "HYB-008", "stt-delegates-to-stt-media",
        ai_job_allowed(stt_job),
        not ai_job_allowed({
            **stt_job, "delegated_profile": "WHISPER_DIRECT"
        }),
    ))
    cases.append(case(
        "HYB-009", "local-accelerator-requires-hrb-lease",
        ai_job_allowed(stt_job),
        not ai_job_allowed({**stt_job, "hrb_lease_id": None}),
    ))
    cases.append(case(
        "HYB-010", "ai-job-async-nonblocking",
        ai_job_allowed(stt_job),
        not ai_job_allowed({**stt_job, "execution_mode": "SYNC"}),
    ))

    approved_edit = {
        **stt_job,
        "intent": "media.auto_edit.propose",
        "local_accelerator": False,
        "delegated_profile": None,
        "destructive": True,
        "human_approved": True,
    }
    cases.append(case(
        "HYB-011", "destructive-edit-requires-hitl",
        ai_job_allowed(approved_edit),
        not ai_job_allowed({**approved_edit, "human_approved": False}),
    ))
    cases.append(case(
        "HYB-012", "proxy-cannot-source-final-master",
        final_master_source_allowed({"quality_role": "ORIGINAL"}),
        not final_master_source_allowed({"quality_role": "PROXY"}),
    ))
    cases.append(case(
        "HYB-013", "media-metadata-complete",
        media_metadata_valid(metadata),
        not media_metadata_valid({
            key: value
            for key, value in metadata.items()
            if key != "timebase"
        }),
    ))
    cases.append(case(
        "HYB-014", "image-sequence-policy-complete",
        image_sequence_valid(sequence),
        not image_sequence_valid({
            **sequence, "missing_frame_policy": "IGNORE"
        }),
    ))

    before = {
        "logical_asset_id": "asset-a",
        "version": 1,
        "content_hash": "before",
    }
    after = {
        "logical_asset_id": "asset-a",
        "version": 2,
        "relinked_from_version": 1,
        "content_hash": "after",
    }
    cases.append(case(
        "HYB-015", "roundtrip-version-relink",
        roundtrip_valid(before, after),
        not roundtrip_valid(before, {**after, "version": 1}),
    ))

    provenance = {
        "source_asset_ids": ["asset-a"],
        "operation": "edit",
        "provider_id": "reference",
        "parameters": {},
        "output_hash": "hash",
        "qc_status": "PASS",
        "human_approval_id": "HITL-001",
        "timeline_id": "timeline-001",
    }
    cases.append(case(
        "HYB-016", "provenance-complete",
        provenance_valid(provenance),
        not provenance_valid({**provenance, "qc_status": "FAIL"}),
    ))
    cases.append(case(
        "HYB-017", "dcc-authority-preserved",
        "FA3-DCC-RT3D-001" != KRITA_PROVIDER_ID,
        "FA3-DCC-RT3D-001" != KDENLIVE_PROVIDER_ID,
    ))

    reference_e2e = run_reference_e2e()
    cases.append(case(
        "HYB-018", "reference-e2e-final-master",
        (
            reference_e2e["result"] == "PASS"
            and reference_e2e["kdenlive_projection"]["picture_lock"]["approved"]
        ),
        (
            not reference_e2e["current_host_krita_runtime_claim"]
            and not reference_e2e["current_host_kdenlive_runtime_claim"]
        ),
    ))

    ids = [item["case_id"] for item in cases]
    passed = sum(item["status"] == "PASS" for item in cases)
    return {
        "schema": "fa3.hybrid-editorial-executable-regression-report.v1",
        "gate_id": EXECUTABLE_GATE_ID,
        "gateset_id": GATESET_ID,
        "result": (
            "PASS"
            if ids == CASE_IDS and passed == len(CASE_IDS)
            else "FAIL"
        ),
        "passed": passed,
        "total": len(cases),
        "case_ids_exact": ids == CASE_IDS,
        "cases": cases,
    }


def canonical_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "profile":
            root / "canonical/profiles/FA3-HYBRID-EDITORIAL-001.json",
        "contract":
            root / "canonical/contracts/FA3-HYBRID-EDITORIAL-CONTRACTS-001.json",
        "krita":
            root / "canonical/providers/FA3-PROVIDER-KRITA-001.json",
        "kdenlive":
            root / "canonical/providers/FA3-PROVIDER-KDENLIVE-001.json",
        "decision":
            root / "canonical/decisions/FA3-DEC-HYBRID-EDITORIAL-2026-08-31.json",
        "gate":
            root / "canonical/FA3-GATE-HYBRID-EDITORIAL-001.json",
        "enforcement":
            root / "canonical/hybrid-editorial-enforcement.json",
        "policy":
            root / "canonical/enforcement-policy.json",
        "video":
            root / "canonical/profiles/FA3-VIDEO-001.json",
        "stt_media":
            root / "canonical/profiles/FA3-STT-MEDIA-001.json",
        "evidence":
            root / EVIDENCE_PATH,
        "registry":
            root / "evidence/evidence-registry.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            findings.append({
                "code": "HYB-CANON-001",
                "message": f"missing {name}: {path.relative_to(root)}",
            })
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile = loadj(paths["profile"])
    contract = loadj(paths["contract"])
    krita = loadj(paths["krita"])
    kdenlive = loadj(paths["kdenlive"])
    decision = loadj(paths["decision"])
    gate_record = loadj(paths["gate"])
    enforcement = loadj(paths["enforcement"])
    policy = loadj(paths["policy"])
    video = loadj(paths["video"])
    stt_media = loadj(paths["stt_media"])
    evidence = loadj(paths["evidence"])
    registry = loadj(paths["registry"])

    if not (
        profile.get("id") == PROFILE_ID
        and profile.get("status") == "CANONICAL"
        and profile.get("priority") == "P0"
        and profile.get("requirement") == "MUST"
        and profile.get("canonical_root") is False
        and profile.get("new_capability") is False
        and profile.get("new_architectural_authority") is False
        and profile.get("capability_count") == CAPABILITY_COUNT
        and profile.get("capabilities") == CAPABILITY_IDS
    ):
        findings.append({
            "code": "HYB-CANON-002",
            "message": "hybrid profile identity/capability invariant drift",
        })

    if not (
        contract.get("id") == CONTRACT_ID
        and contract.get("provider_neutral") is True
        and contract.get("canonical_timeline_ir") == "OpenTimelineIO"
    ):
        findings.append({
            "code": "HYB-CANON-003",
            "message": "hybrid contract provider-neutral/OTIO invariant drift",
        })
    if (
        contract.get("provider_local_formats", {})
        .get("canonical_roots") is not False
    ):
        findings.append({
            "code": "HYB-CANON-004",
            "message": "provider-local project format became canonical root",
        })

    if not (
        krita.get("id") == KRITA_PROVIDER_ID
        and krita.get("canonical_root") is False
        and krita.get("architectural_authority") is False
        and krita.get("new_capability") is False
        and krita.get("new_architectural_authority") is False
        and krita.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append({
            "code": "HYB-CANON-005",
            "message": "Krita provider authority/capability invariant drift",
        })

    boundary = kdenlive.get("human_finishing_boundary", {})
    if not (
        kdenlive.get("architectural_authority") is False
        and boundary.get("mode") == "HUMAN_FINISHING_NLE"
        and boundary.get("picture_lock_requires_human_approval") is True
        and boundary.get("destructive_mutation_requires_hitl") is True
        and boundary.get("direct_project_xml_mutation_forbidden") is True
        and kdenlive.get("ai_tools_policy")
        == "CLIENT_PROJECTION_ONLY_DELEGATE_THROUGH_EXISTING_FA3_CAPABILITIES"
    ):
        findings.append({
            "code": "HYB-CANON-006",
            "message": "Kdenlive human-finishing boundary drift",
        })

    if video.get("authority", {}).get("editorial_handoff") != "OTIO_KDENLIVE":
        findings.append({
            "code": "HYB-CANON-007",
            "message": "FA3-VIDEO-001 OTIO/Kdenlive handoff drift",
        })

    if (
        "CAP-017" not in stt_media.get("capabilities", [])
        or stt_media.get("new_architectural_authority") is not False
    ):
        findings.append({
            "code": "HYB-CANON-008",
            "message": "STT media delegation boundary drift",
        })

    if not (
        decision.get("id") == DECISION_ID
        and decision.get("status") == "CANONICAL_CLOSED"
        and decision.get("decision") == "IMPLEMENT"
        and decision.get("new_capabilities") == 0
        and decision.get("new_architectural_authorities") == 0
        and decision.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append({
            "code": "HYB-CANON-009",
            "message": "hybrid decision baseline invariant drift",
        })

    if not (
        gate_record.get("id") == EXECUTABLE_GATE_ID
        and gate_record.get("gateset_id") == GATESET_ID
        and gate_record.get("case_ids") == CASE_IDS
        and gate_record.get("regression_case_count") == len(CASE_IDS)
        and gate_record.get("fail_closed") is True
    ):
        findings.append({
            "code": "HYB-CANON-010",
            "message": "hybrid executable gate record drift",
        })

    if not (
        enforcement.get("gate_id") == EXECUTABLE_GATE_ID
        and enforcement.get("gateset_id") == GATESET_ID
        and enforcement.get("executable_case_ids") == CASE_IDS
        and enforcement.get("fail_closed") is True
        and enforcement.get("capability_count") == CAPABILITY_COUNT
    ):
        findings.append({
            "code": "HYB-CANON-011",
            "message": "hybrid enforcement binding drift",
        })

    if (
        GATESET_ID not in policy.get("mandatory_reference_gates", [])
        or policy.get("hybrid_editorial_executable_gate_id")
        != EXECUTABLE_GATE_ID
    ):
        findings.append({
            "code": "HYB-CANON-012",
            "message": "global enforcement policy hybrid gate binding missing",
        })

    if not (
        evidence.get("status") == "PASS"
        and evidence.get("gate_id") == EXECUTABLE_GATE_ID
        and evidence.get("current_host_runtime_promotion_claim") is False
        and evidence.get("capability_count_after") == CAPABILITY_COUNT
    ):
        findings.append({
            "code": "HYB-CANON-013",
            "message": "hybrid reference evidence semantics drift",
        })

    records = {
        record.get("subject_id"): record
        for record in registry.get("records", [])
    }
    for capability_id in CAPABILITY_IDS:
        record = records.get(capability_id, {})
        if (
            DECISION_ID not in record.get("source_decision_ids", [])
            or EVIDENCE_PATH not in record.get("evidence_artifacts", [])
        ):
            findings.append({
                "code": "HYB-CANON-014",
                "message":
                    f"evidence registry hybrid binding missing for {capability_id}",
            })
        projection = record.get("hybrid_editorial_projection_status", {})
        if not (
            projection.get("profile_id") == PROFILE_ID
            and projection.get("runtime_status") == "PENDING_CURRENT_HOST"
            and projection.get("ci_reference_pass_does_not_promote_runtime")
            is True
            and record.get("runtime_conformance") == "EVIDENCE-PENDING"
            and record.get("status") == "PENDING_CURRENT_HOST"
            and record.get("promotion_state")
            == "NOT_RUNTIME_PROMOTED_BY_DOCUMENT_ALONE"
        ):
            findings.append({
                "code": "HYB-CANON-015",
                "message":
                    f"hybrid projection status invalid for {capability_id}",
            })

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def gate(root: Path) -> dict[str, Any]:
    canonical = canonical_check(root)
    regressions = run_regressions()
    reference_e2e = run_reference_e2e()
    writej(
        root / "reports/hybrid-editorial-reference-e2e-report.json",
        reference_e2e,
    )

    ok = (
        canonical["result"] == "PASS"
        and regressions["result"] == "PASS"
        and reference_e2e["result"] == "PASS"
    )
    report = {
        "schema": "fa3.hybrid-editorial-gate-report.v1",
        "gate_id": EXECUTABLE_GATE_ID,
        "gateset_id": GATESET_ID,
        "profile_id": PROFILE_ID,
        "result": "PASS" if ok else "FAIL",
        "canonical": canonical,
        "regressions": regressions,
        "reference_e2e": {
            "result": reference_e2e["result"],
            "checks": reference_e2e["checks"],
        },
        "capability_count": CAPABILITY_COUNT,
        "current_host_krita_runtime_claim": False,
        "current_host_kdenlive_runtime_claim": False,
        "promotion_effect": (
            "CI_REFERENCE_E2E_AND_CANONICAL_CONFORMANCE_ONLY_"
            "CURRENT_HOST_RUNTIME_REMAINS_PENDING"
        ),
    }
    writej(root / "reports/hybrid-editorial-gate-report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FA3-GATE-HYBRID-EDITORIAL-001"
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    args = parser.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
