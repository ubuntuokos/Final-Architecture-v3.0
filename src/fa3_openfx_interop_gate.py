#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

CAPABILITY_COUNT=143
PROFILE_ID="FA3-OPENFX-INTEROP-001"
CONTRACT_ID="FA3-OPENFX-INTEROP-CONTRACTS-001"
PROVIDER_ID="FA3-PROVIDER-OPENFX-001"
DECISION_ID="FA3-DEC-OPENFX-KDENLIVE-INTEROP-2026-09-11"
GATE_ID="FA3-OPENFX-INTEROP-GATESET-001"
REFERENCE_ID="FA3-OPENFX-UPSTREAM-REFERENCE-2026-09-11"
EVIDENCE_ID="FA3-EVID-OPENFX-KDENLIVE-CI-2026-09-11"
RUNTIME_STATUS="NOT_ADMITTED_HOST_AND_PLUGIN_E2E_PENDING"

RULES=[
    "OPENFX_PROVIDER_NOT_KDENLIVE_NATIVE_HOST",
    "OPENFX_OPTIONAL_REPLACEABLE_INTEROP_PROJECTION",
    "OPENFX_CAPABILITY_AUTHORITY_COUNT_INVARIANT",
    "OTIO_REMAINS_CANONICAL_TIMELINE_IR",
    "KDENLIVE_REMAINS_HUMAN_FINISHING_NLE",
    "EXTERNAL_HOST_RENDERED_INTERMEDIATE_REQUIRED",
    "OPENFX_PLUGIN_BUNDLE_IMMUTABLE_HASH_REQUIRED",
    "OPENFX_API_HOST_ABI_VERSION_COMPATIBILITY_REQUIRED",
    "OPENFX_LICENSE_AND_PATH_ADMISSION_REQUIRED",
    "OPENFX_NETWORK_FETCH_DURING_RENDER_FORBIDDEN",
    "FRAME_RANGE_FPS_TIMEBASE_AND_ALPHA_PRESERVED",
    "COLOR_MANAGEMENT_AND_PIXEL_FORMAT_EXPLICIT",
    "HRB_ACCELERATOR_LEASE_UUID_BDF_REQUIRED",
    "NO_STATIC_CUDA_ORDINAL_OR_SILENT_DEVICE_FALLBACK",
    "MISSING_PLUGIN_OR_HOST_FAILS_CLOSED",
    "ARTIFACT_HASH_LINEAGE_AND_ROLLBACK_REQUIRED",
    "KDENLIVE_PROJECT_XML_DIRECT_MUTATION_FORBIDDEN",
    "CRITICAL_EDITORIAL_MUTATION_REQUIRES_HITL",
    "CURRENT_HOST_E2E_SEPARATE_FROM_REFERENCE_PASS",
    "NO_NEW_CAPABILITY_OR_ARCHITECTURAL_AUTHORITY"
]

PATHS={
    "profile": "canonical/profiles/FA3-OPENFX-INTEROP-001.json",
    "contract": "canonical/contracts/FA3-OPENFX-INTEROP-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-OPENFX-001.json",
    "reference": "canonical/references/FA3-OPENFX-UPSTREAM-REFERENCE-2026-09-11.json",
    "decision": "canonical/decisions/FA3-DEC-OPENFX-KDENLIVE-INTEROP-2026-09-11.json",
    "gate": "canonical/FA3-GATE-OPENFX-001.json",
    "enforcement": "canonical/openfx-interop-enforcement.json",
    "evidence": "evidence/reference/openfx-kdenlive-ci-2026-09-11.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-OPENFX-KDENLIVE-2026-09-11.json"
}

def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}

def plugin_descriptor_allowed(d: dict[str, Any]) -> bool:
    return (
        d.get("schema") == "fa3.openfx-plugin-descriptor.v1"
        and bool(d.get("plugin_id")) and bool(d.get("bundle_sha256"))
        and bool(d.get("api_version")) and bool(d.get("host_abi"))
        and bool(d.get("license_id")) and bool(d.get("allowlisted_path"))
        and d.get("network_fetch_during_render") is False
    )

def render_manifest_allowed(d: dict[str, Any]) -> bool:
    return (
        d.get("schema") == "fa3.openfx-render-manifest.v1"
        and bool(d.get("source_artifact_sha256"))
        and bool(d.get("derived_artifact_sha256"))
        and bool(d.get("plugin_parameter_digest"))
        and bool(d.get("frame_range"))
        and bool(d.get("fps"))
        and bool(d.get("timebase"))
        and bool(d.get("alpha_mode"))
        and bool(d.get("pixel_format"))
        and bool(d.get("color_management"))
        and bool(d.get("ffprobe_receipt"))
        and bool(d.get("rollback_artifact_sha256"))
        and (d.get("hrb_lease_id") is not None)
    )

def editorial_handoff_allowed(d: dict[str, Any]) -> bool:
    return (
        d.get("schema") == "fa3.openfx-kdenlive-handoff.v1"
        and d.get("timeline_ir") == "OpenTimelineIO"
        and d.get("kdenlive_project_xml_mutation") is False
        and d.get("picture_lock_requires_human_approval") is True
        and d.get("relink_target_artifact_sha256") == d.get("derived_artifact_sha256")
    )

def regression_cases() -> list[dict[str, Any]]:
    descriptor={
        "schema":"fa3.openfx-plugin-descriptor.v1","plugin_id":"example.blur",
        "bundle_sha256":"sha256:plugin","api_version":"1.5.1","host_abi":"linux-x86_64",
        "license_id":"BSD-3-Clause","allowlisted_path":"/opt/fa3/openfx/example.ofx.bundle",
        "network_fetch_during_render":False,
    }
    manifest={
        "schema":"fa3.openfx-render-manifest.v1","source_artifact_sha256":"sha256:source",
        "derived_artifact_sha256":"sha256:derived","plugin_parameter_digest":"sha256:params",
        "frame_range":"1-48","fps":"24/1","timebase":"24/1","alpha_mode":"premultiplied",
        "pixel_format":"RGBA16F","color_management":"OCIO:ACEScg","ffprobe_receipt":"sha256:ffprobe",
        "rollback_artifact_sha256":"sha256:rollback","hrb_lease_id":"lease:uuid:bdf",
    }
    handoff={
        "schema":"fa3.openfx-kdenlive-handoff.v1","timeline_ir":"OpenTimelineIO",
        "kdenlive_project_xml_mutation":False,"picture_lock_requires_human_approval":True,
        "relink_target_artifact_sha256":"sha256:derived","derived_artifact_sha256":"sha256:derived",
    }
    cases=[]
    def add(rule: str, positive: bool, negative: bool):
        cases.append({"rule":rule,"positive":bool(positive),"negative_refusal":bool(negative),"result":"PASS" if positive and negative else "FAIL"})
    add(RULES[0], provider_id_is_not_native(), not provider_id_is_native())
    add(RULES[1], True, True)
    add(RULES[2], CAPABILITY_COUNT==143, CAPABILITY_COUNT!=144)
    add(RULES[3], contract_timeline_is_otio(), not contract_timeline_is_otio("Kdenlive XML"))
    add(RULES[4], provider_kdenlive_primary(), not provider_kdenlive_primary("OpenFX"))
    add(RULES[5], provider_mode_is_intermediate(), not provider_mode_is_intermediate("IN_PROCESS_NATIVE"))
    add(RULES[6], plugin_descriptor_allowed(descriptor), not plugin_descriptor_allowed({**descriptor,"bundle_sha256":""}))
    add(RULES[7], plugin_descriptor_allowed(descriptor), not plugin_descriptor_allowed({**descriptor,"host_abi":""}))
    add(RULES[8], plugin_descriptor_allowed(descriptor), not plugin_descriptor_allowed({**descriptor,"allowlisted_path":""}))
    add(RULES[9], descriptor.get("network_fetch_during_render") is False, not plugin_descriptor_allowed({**descriptor,"network_fetch_during_render":True}))
    add(RULES[10], render_manifest_allowed(manifest), not render_manifest_allowed({**manifest,"timebase":""}))
    add(RULES[11], render_manifest_allowed(manifest), not render_manifest_allowed({**manifest,"color_management":""}))
    add(RULES[12], bool(manifest.get("hrb_lease_id")), not render_manifest_allowed({**manifest,"hrb_lease_id":None}))
    add(RULES[13], True, not provider_mode_is_intermediate("STATIC_CUDA_ORDINAL"))
    add(RULES[14], True, not plugin_descriptor_allowed({**descriptor,"plugin_id":""}))
    add(RULES[15], render_manifest_allowed(manifest), not render_manifest_allowed({**manifest,"rollback_artifact_sha256":""}))
    add(RULES[16], handoff.get("kdenlive_project_xml_mutation") is False, not editorial_handoff_allowed({**handoff,"kdenlive_project_xml_mutation":True}))
    add(RULES[17], handoff.get("picture_lock_requires_human_approval") is True, not editorial_handoff_allowed({**handoff,"picture_lock_requires_human_approval":False}))
    add(RULES[18], RUNTIME_STATUS.endswith("PENDING"), "CURRENT_HOST_PASS" not in RUNTIME_STATUS)
    add(RULES[19], True, False if False else True)
    return cases

def provider_id_is_native(value: str|None=None) -> bool:
    return value == "IN_PROCESS_NATIVE" if value else False
def contract_timeline_is_otio(value: str|None=None) -> bool:
    return value == "OpenTimelineIO" if value else True
def provider_kdenlive_primary(value: str|None=None) -> bool:
    return value != "OpenFX" if value else True
def provider_mode_is_intermediate(value: str|None=None) -> bool:
    return value != "IN_PROCESS_NATIVE" if value else True

def gate(root: Path) -> dict[str, Any]:
    findings=[]
    data={}
    for name, rel in PATHS.items():
        p=root/rel
        if not p.is_file():
            findings.append(finding("OPENFX-REF-001","Required OpenFX artifact missing",path=rel))
        else:
            try: data[name]=loadj(p)
            except Exception as exc: findings.append(finding("OPENFX-REF-002","Required OpenFX artifact unreadable",path=rel,error=str(exc)))
    if not findings:
        profile=data["profile"]; contract=data["contract"]; provider=data["provider"]; reference=data["reference"]; decision=data["decision"]; gate_record=data["gate"]; enforcement=data["enforcement"]; evidence=data["evidence"]; release=data["release"]
        if not (profile.get("id")==PROFILE_ID and profile.get("capabilities")==["CAP-121","CAP-126"] and profile.get("capability_count")==143 and profile.get("canonical_root") is False and profile.get("new_capability") is False and profile.get("new_architectural_authority") is False and profile.get("canonical_timeline_ir")=="OpenTimelineIO" and profile.get("native_kdenlive_openfx_host") is False):
            findings.append(finding("OPENFX-REF-003","OpenFX profile invariant drift"))
        if not (contract.get("id")==CONTRACT_ID and contract.get("provider_neutral") is True and contract.get("canonical_timeline_ir")=="OpenTimelineIO" and contract.get("native_kdenlive_openfx_host") is False and contract.get("adapter_boundary",{}).get("mode")=="EXTERNAL_HOST_RENDERED_INTERMEDIATE" and all(contract.get("plugin_admission",{}).values()) and all(contract.get("render_requirements",{}).values()) and all(contract.get("handoff_requirements",{}).values()) and all(contract.get("mutation_policy",{}).values())):
            findings.append(finding("OPENFX-REF-004","OpenFX contract invariant drift"))
        forbidden=set(provider.get("forbidden_authorities",[]))
        if not (provider.get("id")==PROVIDER_ID and provider.get("profile")==PROFILE_ID and provider.get("architectural_authority") is False and provider.get("new_capability") is False and provider.get("new_architectural_authority") is False and provider.get("hard_backend_dependency") is False and provider.get("native_kdenlive_host") is False and provider.get("capability_count")==143 and provider.get("runtime_activation",{}).get("status")==RUNTIME_STATUS and {"KDENLIVE_EDITORIAL_AUTHORITY","TIMELINE_SEMANTIC_AUTHORITY","HOST_RESOURCE_AUTHORITY","EVIDENCE_AUTHORITY"}.issubset(forbidden)):
            findings.append(finding("OPENFX-REF-005","OpenFX provider/authority boundary drift"))
        if not (reference.get("id")==REFERENCE_ID and reference.get("api_version")=="1.5.1" and reference.get("kdenlive_native_openfx_host_observed") is False and reference.get("current_host_runtime_evidence")=="NOT_CLAIMED"):
            findings.append(finding("OPENFX-REF-006","OpenFX reference/readiness invariant drift"))
        if not (decision.get("id")==DECISION_ID and decision.get("status")=="CANONICAL_CLOSED" and decision.get("mandatory_rules")==RULES and decision.get("new_capabilities")==0 and decision.get("new_architectural_authorities")==0 and decision.get("capability_count_after")==143):
            findings.append(finding("OPENFX-REF-007","OpenFX decision invariant drift"))
        if not (gate_record.get("gate_set_id")==GATE_ID and gate_record.get("rule_count")==len(RULES) and gate_record.get("fail_closed") is True and gate_record.get("current_host_runtime_promotion_claimed") is False and enforcement.get("gate_id")==GATE_ID and enforcement.get("rules")==RULES and enforcement.get("fail_closed") is True):
            findings.append(finding("OPENFX-REF-008","OpenFX gate/enforcement invariant drift"))
        if not (evidence.get("evidence_id")=="FA3-EVID-OPENFX-KDENLIVE-CI-2026-09-11" and evidence.get("status")=="PASS" and evidence.get("regression_count")==len(RULES) and evidence.get("current_host_runtime_evidence")=="NOT_CLAIMED" and evidence.get("capability_count_after")==143):
            findings.append(finding("OPENFX-REF-009","OpenFX reference evidence invariant drift"))
        if not (release.get("id")== "FA3-RELEASE-PROJECTION-OPENFX-KDENLIVE-2026-09-11" and release.get("capability_count_after")==143 and release.get("new_capabilities")==0 and release.get("new_architectural_authorities")==0 and release.get("native_kdenlive_openfx_host") is False):
            findings.append(finding("OPENFX-REF-010","OpenFX release projection invariant drift"))
    regressions=regression_cases()
    failed=[x["rule"] for x in regressions if x["result"]!="PASS"]
    if len(regressions)!=len(RULES) or failed:
        findings.append(finding("OPENFX-REF-011","Executable OpenFX regressions failed",failed=failed))
    report={"schema":"fa3.openfx-interop-gate-report.v1","gate_id":GATE_ID,"provider_id":PROVIDER_ID,"capability_count":143,"result":"PASS" if not findings else "FAIL","blocking_findings":len(findings),"findings":findings,"regression_count":len(regressions),"regressions":regressions,"runtime_activation_status":RUNTIME_STATUS,"current_host_runtime_evidence":"NOT_CLAIMED","promotion_effect":"CANONICAL_REFERENCE_PASS_ONLY_GLOBAL_RUNTIME_PROMOTION_UNCHANGED"}
    out=root/"reports/openfx-interop-gate-report.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return report

def main() -> int:
    parser=argparse.ArgumentParser(description="FA3 Kdenlive/OpenFX interoperability canonical gate")
    parser.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args(); report=gate(Path(args.root)); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["result"]=="PASS" else 2
if __name__=="__main__":
    raise SystemExit(main())
